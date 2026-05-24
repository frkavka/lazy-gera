import os
import time

from dotenv import load_dotenv

from transformer import SYSTEM_PROMPT
from config import load_config

load_dotenv()

# 503 リトライ設定
_SERVICE_UNAVAILABLE_RETRIES = 3
_SERVICE_UNAVAILABLE_WAIT    = 10  # 秒（リトライごとに 2 倍）


def call_llm(user_prompt: str, temperature: float = 0.3) -> str:
    """
    LLM API を呼び出して変換後テキストを返す。
    使用プロバイダーは config.yaml の llm.provider で切り替える。
    """
    cfg = load_config()
    provider = cfg["llm"]["provider"]

    if provider == "gemini":
        return _call_gemini(user_prompt, temperature, cfg)
    elif provider == "anthropic":
        return _call_anthropic(user_prompt, temperature, cfg)
    else:
        raise ValueError(
            f"未対応のLLMプロバイダー: '{provider}' "
            f"（config.yaml の llm.provider を確認してください）"
        )


def _call_gemini(user_prompt: str, temperature: float, cfg: dict) -> str:
    from google import genai
    from google.genai import types
    from google.api_core.exceptions import ServiceUnavailable

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY が .env に設定されていません")

    client = genai.Client(api_key=api_key)
    wait = _SERVICE_UNAVAILABLE_WAIT

    for attempt in range(_SERVICE_UNAVAILABLE_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=cfg["llm"]["model"]["gemini"],
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=temperature,
                ),
            )
            return response.text
        except ServiceUnavailable:
            if attempt >= _SERVICE_UNAVAILABLE_RETRIES:
                raise
            print(f"  [503] Gemini サービス一時停止。{wait} 秒後にリトライ ({attempt + 1}/{_SERVICE_UNAVAILABLE_RETRIES})...")
            time.sleep(wait)
            wait *= 2


def _call_anthropic(user_prompt: str, temperature: float, cfg: dict) -> str:
    # 将来対応予定。枠だけ用意しておく。
    raise NotImplementedError(
        "Anthropicプロバイダーは未実装です。"
        "config.yaml の llm.provider を 'gemini' にしてください。"
    )
