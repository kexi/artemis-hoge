import os
import subprocess
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "scripts/lmstudio-runtime/sitecustomize.py"


def test_cloud_endpoint_is_rejected_before_loading_artemis():
    env = os.environ | {
        "ARTEMIS_LOCAL_MODEL": "test-model",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
    }
    result = subprocess.run(
        [sys.executable, str(RUNTIME)], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert "localhost" in result.stderr


def test_normal_python_process_does_not_activate_local_model_routing():
    env = os.environ | {"ARTEMIS_LOCAL_MODEL": ""}
    result = subprocess.run(
        [sys.executable, str(RUNTIME)], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert result.stdout == ""
