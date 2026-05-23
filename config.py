from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent / "config.yaml"

# ハードコードのデフォルト値（config.yaml が存在しない・項目がない場合に使用）
_DEFAULTS: dict = {
    "llm": {
        "provider": "gemini",
        "model": {
            "gemini": "gemini-2.5-flash",
            "anthropic": "claude-haiku-4-5-20251001",
        },
        "initial_temperature": 0.3,
        "temperature_step": 0.1,
        "max_retries": 3,
    }
}


def load_config() -> dict:
    """
    config.yaml を読み込み、デフォルト値にマージして返す。
    config.yaml が存在しない場合はデフォルト値のみ返す。
    """
    if not _CONFIG_PATH.exists():
        return _DEFAULTS

    with _CONFIG_PATH.open(encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}

    return _deep_merge(_DEFAULTS, user_config)


def _deep_merge(base: dict, override: dict) -> dict:
    """override の値で base を再帰的に上書きする。"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
