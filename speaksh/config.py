from __future__ import annotations


DEFAULT_MODEL_NAME = "mlx-community/MiniCPM5-1B-OptiQ-4bit"
DEFAULT_MODEL_BACKEND = "mlx"
DEFAULT_TRANSFORMERS_MODEL_NAME = "openbmb/MiniCPM5-1B"


def effective_model_name(model_name: str, model_backend: str) -> str:
    if model_backend == "transformers" and model_name == DEFAULT_MODEL_NAME:
        return DEFAULT_TRANSFORMERS_MODEL_NAME
    return model_name
