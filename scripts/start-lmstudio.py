# /// script
# requires-python = ">=3.12"
# ///
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("LMSTUDIO_MODEL", "artemis-gemma4")
NODES = (
    "planner",
    "summarizer",
    "operator",
    "operator_summarizer",
    "log_reader_sub_agent",
    "log_analyzer",
    "diagnoser",
    "checker",
    "planner_avatar",
    "history_analyzer_expert",
    "diagnoser_expert",
    "explorer",
    "history_analyzer",
    "validator_pixel_safety_net",
    "planner_validation",
    "output_analyzer",
)


def main() -> None:
    checkout = subprocess.check_output(
        ["ghq", "list", "-p", "-e", "github.com/google/artemis"], text=True
    ).strip()
    has_checkout = bool(checkout)
    if not has_checkout:
        raise SystemExit("ghq get https://github.com/google/artemis を先に実行してください。")
    python = Path(checkout) / ".venv/bin/python"
    has_environment = python.is_file()
    if not has_environment:
        raise SystemExit("Artemis 本体で uv sync を実行してください。")

    work = ROOT / "artifacts/lmstudio"
    work.mkdir(parents=True, exist_ok=True)
    model = {
        "provider": "openai",
        "model": MODEL,
        "timeout": 600,
        "fallback": {"provider": "openai", "model": MODEL},
    }
    config = {name: model for name in NODES}
    config["utils"] = {
        name: model for name in ("outputter", "hopper", "video_analyzer", "object_detector")
    }
    config["agent"] = {
        "flash": {"step_summarizer": {"model": MODEL}},
        "memory": {"runtime": {"max_concurrency": 1}, "chunking": {"model": MODEL}},
        "pro": {"explorer": {"mode": "pro"}},
    }
    config_path = work / "artemis.jsonc"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    env = os.environ.copy()
    for key in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GCP_API_KEY",
        "API_KEY",
        "ANTHROPIC_API_KEY",
        "OPEN_ROUTER_API_KEY",
        "XAI_API_KEY",
        "OCR_API_KEY",
        "VISION_API_KEY",
    ):
        env[key] = ""
    env.update(
        {
            "ARTEMIS_LOCAL_MODEL": MODEL,
            "OPENAI_API_KEY": os.environ.get("LMSTUDIO_API_TOKEN") or "lm-studio",
            "OPENAI_BASE_URL": os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            "ARTEMIS_ARTEMIS_JSONC": str(config_path),
            "ARTEMIS_TRACES_DIR": str(work / "traces"),
            "DATA_ENGINE_DB_PATH": str(work / "traces/data_engine.db"),
            "ARTEMIS_FAKE_LLM": "0",
            "PYTHONPATH": str(ROOT / "scripts/lmstudio-runtime") + os.pathsep + checkout,
            "PYTHONUNBUFFERED": "1",
            "LLM_PAUSE_TIMEOUT_SECONDS": "30",
            "OBJECT_DETECTOR_TIMEOUT": "120",
        }
    )
    os.chdir(work)
    os.execve(
        python,
        [str(python), "-m", "artemis", "ui", "--host", "127.0.0.1", "--port", "8001", "--no-open"],
        env,
    )


if __name__ == "__main__":
    main()
