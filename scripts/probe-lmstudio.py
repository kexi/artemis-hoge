import base64
import json
import os
import sys
import time
from pathlib import Path

from artemis_client.transport import JsonTransport


def main() -> None:
    screenshot = Path(sys.argv[1])
    transport = JsonTransport(
        os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        token=os.environ.get("LMSTUDIO_API_TOKEN") or "lm-studio",
        timeout=600,
    )
    encoded = base64.b64encode(screenshot.read_bytes()).decode()
    started = time.monotonic()
    response = transport.request(
        "POST",
        "/chat/completions",
        json_body={
            "model": os.environ.get("LMSTUDIO_MODEL", "artemis-gemma4"),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Read this app screenshot. Call record_check with the displayed app title, total task count, and completed task count. Do not answer in prose.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64," + encoded},
                        },
                    ],
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "record_check",
                        "description": "Record the app state visible in the screenshot.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "app_title": {"type": "string"},
                                "task_count": {"type": "integer"},
                                "completed_count": {"type": "integer"},
                            },
                            "required": ["app_title", "task_count", "completed_count"],
                        },
                    },
                }
            ],
            "tool_choice": "required",
            "temperature": 0,
            "max_tokens": 2048,
        },
    )
    output = Path("artifacts/lmstudio-probe.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(response, ensure_ascii=False, indent=2))
    calls = response["choices"][0]["message"].get("tool_calls") or []
    has_call = len(calls) == 1 and calls[0]["function"]["name"] == "record_check"
    if not has_call:
        raise AssertionError(f"構造化されたツール呼び出しがありません。{output} を確認。")
    args = json.loads(calls[0]["function"]["arguments"])
    print(
        json.dumps(
            {
                "event": "local_vision_tool_probe",
                "seconds": round(time.monotonic() - started, 1),
                "arguments": args,
            },
            ensure_ascii=False,
        )
    )
    expected = {"app_title": "Artemis Todo", "task_count": 1, "completed_count": 1}
    is_expected = args == expected
    if not is_expected:
        raise AssertionError("スクリーンショットの読み取り結果が期待値と一致しません。")


if __name__ == "__main__":
    main()
