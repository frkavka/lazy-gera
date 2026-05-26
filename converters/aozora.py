import re


def _emphasis_to_narou(text: str) -> str:
    """^^text^^ → ｜文《・》｜字《・》（なろう式の傍点: 1文字ずつルビで代替）"""

    def to_dot_ruby(m: re.Match) -> str:
        return "".join(f"｜{ch}《・》" for ch in m.group(1))

    return re.sub(r"\^\^(.+?)\^\^", to_dot_ruby, text)


def convert_to_aozora(text: str) -> str:
    """内部フォーマット → 青空文庫・note・TALES 形式"""
    # ルビ: {宇宙|そら} → ｜宇宙《そら》
    text = re.sub(r"\{([^|{}]+)\|([^}]+)\}", r"｜\1《\2》", text)
    # 太字: **text** のまま（青空文庫/note は Markdown 太字が有効）
    # 傍点: ^^text^^ → なろう同様にドットルビで代替
    text = _emphasis_to_narou(text)
    # 章区切り（多分要らない）
    # text = text.replace("===", "［＃改丁］")
    # セクション区切り（空行に戻す）
    text = re.sub(r"^---$", "", text, flags=re.MULTILINE)
    return text
