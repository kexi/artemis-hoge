import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "dev.kexi.artemishoge"


def adb(serial: str, *args: str) -> bytes:
    return subprocess.run(
        ["adb", "-s", serial, *args], check=True, capture_output=True, timeout=30
    ).stdout


def capture_screen(serial: str, output: Path) -> bytes:
    adb(serial, "shell", "uiautomator", "dump", "/sdcard/artemis-expo.xml")
    xml = adb(serial, "exec-out", "cat", "/sdcard/artemis-expo.xml")
    (output / "screen.xml").write_bytes(xml)
    (output / "screen.png").write_bytes(adb(serial, "exec-out", "screencap", "-p"))
    return xml


def verify_screen(xml: bytes, phase: str) -> dict[str, bool]:
    nodes = [node for node in ET.fromstring(xml).iter("node") if node.get("package") == PACKAGE]
    labels = [node.get(key, "") for node in nodes for key in ("text", "content-desc")]
    tasks = [node for node in nodes if node.get("checkable") == "true"]
    is_empty_phase = phase == "empty"
    if is_empty_phase:
        inputs = [node for node in nodes if node.get("class") == "android.widget.EditText"]
        input_text = inputs[0].get("text", "") if len(inputs) == 1 else None
        input_hint = inputs[0].get("hint", "") if len(inputs) == 1 else None
        # Android は空欄の TextInput の text にもプレースホルダーを返す。
        is_input_empty = len(inputs) == 1 and input_text in {"", input_hint}
        checks = {
            "empty_summary": "タスク 0件 / 完了 0件" in labels,
            "empty_message": "タスクはありません" in labels,
            "no_tasks": len(tasks) == 0,
            "empty_input": is_input_empty,
            "add_disabled": any(
                node.get("content-desc") == "追加" and node.get("enabled") == "false"
                for node in nodes
            ),
        }
    else:
        is_completed = phase == "completed"
        is_known_phase = phase in {"added", "completed"}
        if not is_known_phase:
            raise ValueError(f"Unknown phase: {phase}")
        summary = f"タスク 1件 / 完了 {1 if is_completed else 0}件"
        checks = {
            "summary": summary in labels,
            "one_matching_task": len(tasks) == 1
            and tasks[0].get("content-desc") == "Buy milk"
            and tasks[0].get("checked") == str(is_completed).lower(),
        }
    has_expected_screen = all(checks.values())
    if not has_expected_screen:
        raise AssertionError(f"UI 検証失敗 ({phase}): {checks}")
    return checks
