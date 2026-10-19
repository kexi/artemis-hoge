import asyncio
import json
import os
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from android_device import PACKAGE, adb, capture_screen, verify_screen
from artemis_client import ArtemisClient
from artemis_client.errors import ArtemisClientError, TaskTimeoutError

PHASES = (
    ("empty", "Tap すべてリセット once. Leave the task input empty and finish."),
    ("added", "Enter Buy milk into タスク名 and tap 追加 once. Do not mark it complete. Finish."),
    (
        "completed",
        "Tap the Buy milk checkbox once to mark it complete. Keep this screen open and finish.",
    ),
)


async def stop_previous(client: ArtemisClient, task_id: str) -> None:
    has_previous = bool(task_id)
    if not has_previous:
        return
    task_id = str(uuid.UUID(task_id))
    result = await client.get_task(task_id)
    is_finished = result.done
    if is_finished:
        return
    print(json.dumps({"event": "stop_previous_requested", "trace_id": task_id}), flush=True)
    await client.stop(task_id)
    await client.wait_for_task(task_id, timeout=60)


async def main() -> None:
    serial = os.environ.get("ADB_DEVICE_SERIAL", "").strip()
    has_serial = bool(serial)
    if not has_serial:
        raise RuntimeError("ADB_DEVICE_SERIAL を設定してください。")
    client = ArtemisClient(
        os.environ.get("ARTEMIS_BASE_URL", "http://localhost:8001"),
        device_serial=serial,
        poll_interval=3,
    )
    await client.health()
    await stop_previous(client, os.environ.get("ARTEMIS_STOP_TASK", ""))
    for _ in range(15):
        devices = await client.list_devices()
        is_available = any(device.serial == serial and not device.busy for device in devices)
        if is_available:
            break
        await asyncio.sleep(1)
    else:
        raise RuntimeError("対象端末が他のタスクで使用中です。新しいテストは開始していません。")

    is_installed = adb(serial, "shell", "pm", "path", PACKAGE).decode().startswith("package:")
    if not is_installed:
        raise RuntimeError("先に just install-android を実行してください。")
    adb(serial, "reverse", "tcp:8081", "tcp:8081")
    adb(serial, "shell", "am", "force-stop", PACKAGE)
    adb(serial, "shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")

    run_id = str(uuid.uuid4())
    output = Path("artifacts") / run_id
    output.mkdir(parents=True)
    summary = {"run_id": run_id, "profile": "flash", "status": "running", "phases": []}
    print(json.dumps({"event": "test_started", "trace_id": run_id, "profile": "flash"}), flush=True)
    try:
        for phase, instruction in PHASES:
            task_id = str(uuid.uuid4())
            folder = output / phase
            folder.mkdir()
            entry = {"phase": phase, "task_id": task_id, "status": "running"}
            summary["phases"].append(entry)
            print(
                json.dumps({"event": "phase_started", "trace_id": task_id, "phase": phase}),
                flush=True,
            )
            goal = (
                f"In the already open Artemis Todo app ({PACKAGE}), do only this task: "
                + instruction
                + " Do not open other apps or change system settings."
            )
            await client.submit(goal, task_id=task_id, profile="flash", locked_app_package=PACKAGE)
            try:
                result = await client.wait_for_task(
                    task_id, timeout=float(os.environ.get("ARTEMIS_TEST_TIMEOUT", "300"))
                )
            except (TaskTimeoutError, asyncio.CancelledError):
                await client.stop(task_id)
                raise
            (folder / "result.json").write_text(
                json.dumps(result.raw, ensure_ascii=False, indent=2)
            )
            xml = capture_screen(serial, folder)
            is_success = result.succeeded
            if not is_success:
                raise RuntimeError(f"Artemis ({phase}): {result.error or result.status}")
            # Flash には Checker の検証台帳がないため、各状態を実機の UI ツリーで確認する。
            entry["checks"] = verify_screen(xml, phase)
            entry["status"] = "passed"
            print(
                json.dumps({"event": "phase_passed", "trace_id": task_id, "phase": phase}),
                flush=True,
            )
        summary["status"] = "passed"
        print(json.dumps({"event": "test_passed", "trace_id": run_id, "artifacts": str(output)}))
    except BaseException as error:
        summary["status"] = "failed"
        summary["error"] = str(error)
        raise
    finally:
        (output / "run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (
        ArtemisClientError,
        RuntimeError,
        AssertionError,
        ValueError,
        OSError,
        subprocess.SubprocessError,
        ET.ParseError,
    ) as error:
        print(json.dumps({"event": "test_failed", "error": str(error)}, ensure_ascii=False))
        sys.exit(1)
