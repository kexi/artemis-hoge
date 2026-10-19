"""Artemis の実験用プロセスと子プロセスにだけ適用するローカルモデル接続。"""

import json
import os
import sys
from urllib.parse import urlsplit


def configure_local_models() -> None:
    model = os.environ.get("ARTEMIS_LOCAL_MODEL", "")
    is_experiment = bool(model)
    if not is_experiment:
        return

    base_url = os.environ["OPENAI_BASE_URL"]
    parsed = urlsplit(base_url)
    is_loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    is_http = parsed.scheme in {"http", "https"}
    is_local_endpoint = is_loopback and is_http
    if not is_local_endpoint:
        raise RuntimeError("LM Studio 実験の接続先は localhost に限定しています。")

    from artemis.config.settings import settings
    from artemis.llm.router import ModelFactory, ModelProvider

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
        os.environ[key] = ""
        setattr(settings, key, None)

    original = ModelFactory.create_model.__func__

    def create_local_model(cls, endpoint):
        # 上流の要約処理が provider=google を直接指定するため、設定ファイルだけでは切り替わらない。
        local = endpoint.model_copy(
            update={
                "provider": ModelProvider.OPENAI,
                "model_name": model,
                "api_base": base_url,
                "api_key": os.environ["OPENAI_API_KEY"],
                "thinking_budget": None,
                "thinking_level": None,
                "reasoning_effort": None,
                "include_thoughts": None,
                "enable_grounding": False,
                "timeout_seconds": 600,
            }
        )
        print(
            json.dumps(
                {
                    "event": "local_model_route",
                    "requested_model": endpoint.model_name,
                    "model": model,
                    "base_url": base_url,
                }
            ),
            flush=True,
        )
        return original(cls, local)

    ModelFactory.create_model = classmethod(create_local_model)


try:
    configure_local_models()
except Exception as error:  # noqa: BLE001
    # sitecustomize の例外は通常握りつぶされるため、そのままクラウド設定で起動させない。
    print(f"Local model setup failed: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
    os._exit(1)
