import asyncio
import json
import os
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from artemis_client import ArtemisClient
from artemis_client.errors import ArtemisClientError, TaskTimeoutError
from artemis_client.transport import JsonTransport
from checks import verify_checks

PACKAGE = "dev.kexi.artemishoge"
GOAL = """
Test only the already installed Android app Artemis Todo (dev.kexi.artemishoge).
Do not open other apps or change system settings.
1. Tap すべてリセット. Verify タスク 0件 / 完了 0件 and タスクはありません.
2. Verify 追加 is disabled while タスク名 is empty.
3. Enter Buy milk in タスク名 and tap 追加.
4. Verify exactly one task Buy milk exists and the summary is タスク 1件 / 完了 0件.
5. Tap the Buy milk checkbox to mark it complete.
6. Verify the checkbox is checked, 完了 is visible, and the summary is タスク 1件 / 完了 1件.
Leave the app on this final screen. Report failure if any check fails or a crash dialog appears.
""".strip()


def adb(serial: str, *args: str) -> bytes:
    return subprocess.run(
        ["adb", "-s", serial, *args], check=True, capture_output=True, timeout=30
    ).stdout


async def main() -> None:
    serial = os.environ.get("ADB_DEVICE_SERIAL", "").strip()
    has_serial = bool(serial)
    if not has_serial:
        raise RuntimeError("ADB_DEVICE_SERIAL を設定してください（adb devices -l で確認）。")

    transport = JsonTransport(os.environ.get("ARTEMIS_BASE_URL", "http://127.0.0.1:8000"))
    client = ArtemisClient(
        transport=transport,
        device_serial=serial,
        request_timeout=30,
        poll_interval=3,
    )
    await client.health()
    adb(serial, "get-state")
    installed = adb(serial, "shell", "pm", "path", PACKAGE).decode().strip()
    is_installed = installed.startswith("package:")
    if not is_installed:
        raise RuntimeError("先に just install-android でサンプルをインストールしてください。")

    adb(serial, "reverse", "tcp:8081", "tcp:8081")
    adb(serial, "shell", "am", "force-stop", PACKAGE)
    adb(serial, "shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")
    task_id = str(uuid.uuid4())
    output = Path("artifacts") / task_id
    output.mkdir(parents=True)
    print(json.dumps({"event": "test_started", "trace_id": task_id, "device": serial}), flush=True)
    try:
        await client.submit(
            GOAL,
            task_id=task_id,
            profile="pro",
            verification_level="strict",
            locked_app_package=PACKAGE,
        )
        try:
            result = await client.wait_for_task(task_id, timeout=600)
        except (TaskTimeoutError, asyncio.CancelledError):
            await client.stop(task_id)
            raise
        (output / "result.json").write_text(
            json.dumps(result.raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        is_success = result.succeeded
        if not is_success:
            raise RuntimeError(f"Artemis failed: {result.error or result.status}")

        # モデルの完了報告だけでは、画面上の期待値を保証できないため。
        adb(serial, "shell", "uiautomator", "dump", "/sdcard/artemis-expo.xml")
        xml = adb(serial, "exec-out", "cat", "/sdcard/artemis-expo.xml")
        (output / "screen.xml").write_bytes(xml)
        nodes = list(ET.fromstring(xml).iter("node"))
        app_nodes = [node for node in nodes if node.get("package") == PACKAGE]
        labels = [node.get(key, "") for node in app_nodes for key in ("text", "content-desc")]
        has_summary = "タスク 1件 / 完了 1件" in labels
        has_checked_task = any(
            node.get("checked") == "true"
            and "Buy milk" in (node.get("text", "") + node.get("content-desc", ""))
            for node in app_nodes
        )
        has_expected_screen = has_summary and has_checked_task
        if not has_expected_screen:
            raise AssertionError(
                "最終画面に完了済みの Buy milk 1件がありません。screen.xml を確認。"
            )
        checks = await asyncio.to_thread(
            transport.request, "GET", f"/api/sessions/{task_id}/checks"
        )
        (output / "checks.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        verify_checks(checks)
        print(json.dumps({"event": "test_passed", "trace_id": task_id, "artifacts": str(output)}))
    finally:
        try:
            (output / "screen.png").write_bytes(adb(serial, "exec-out", "screencap", "-p"))
        except (subprocess.SubprocessError, OSError) as error:
            print(
                json.dumps({"event": "screenshot_failed", "trace_id": task_id, "error": str(error)})
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (
        ArtemisClientError,
        RuntimeError,
        AssertionError,
        OSError,
        subprocess.SubprocessError,
        ET.ParseError,
        ValueError,
    ) as error:
        print(json.dumps({"event": "test_failed", "error": str(error)}, ensure_ascii=False))
        sys.exit(1)
