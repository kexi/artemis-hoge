import xml.etree.ElementTree as ET

import pytest

from scripts.android_device import PACKAGE, verify_screen


def screen(phase, *, input_text="例: 牛乳を買う", enabled="false", checked=None):
    root = ET.Element("hierarchy")
    labels = (
        ["タスク 0件 / 完了 0件", "タスクはありません"]
        if phase == "empty"
        else [f"タスク 1件 / 完了 {1 if phase == 'completed' else 0}件"]
    )
    for label in labels:
        ET.SubElement(root, "node", {"package": PACKAGE, "text": label})
    ET.SubElement(
        root,
        "node",
        {
            "package": PACKAGE,
            "class": "android.widget.EditText",
            "text": input_text,
            "hint": "例: 牛乳を買う",
        },
    )
    ET.SubElement(root, "node", {"package": PACKAGE, "content-desc": "追加", "enabled": enabled})
    has_task = phase != "empty"
    if has_task:
        ET.SubElement(
            root,
            "node",
            {
                "package": PACKAGE,
                "content-desc": "Buy milk",
                "checkable": "true",
                "checked": checked or str(phase == "completed").lower(),
            },
        )
    return ET.tostring(root)


@pytest.mark.parametrize("phase", ["empty", "added", "completed"])
def test_expected_intermediate_state_passes(phase):
    assert all(verify_screen(screen(phase), phase).values())


@pytest.mark.parametrize("changes", [{"input_text": "Buy milk"}, {"enabled": "true"}])
def test_empty_state_rejects_nonempty_input_or_enabled_add(changes):
    with pytest.raises(AssertionError):
        verify_screen(screen("empty", **changes), "empty")


@pytest.mark.parametrize("phase,checked", [("added", "true"), ("completed", "false")])
def test_wrong_checkbox_state_is_rejected(phase, checked):
    with pytest.raises(AssertionError):
        verify_screen(screen(phase, checked=checked), phase)


def test_other_apps_ui_cannot_satisfy_checks():
    xml = screen("completed").replace(PACKAGE.encode(), b"other.app")
    with pytest.raises(AssertionError):
        verify_screen(xml, "completed")
