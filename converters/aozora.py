import re


def convert_to_aozora(text: str) -> str:
    """内部フォーマット → 青空文庫・note・TALES 形式"""
    # ルビ: {宇宙|そら} → ｜宇宙《そら》
    text = re.sub(r'\{([^|{}]+)\|([^}]+)\}', r'｜\1《\2》', text)
    # 太字
    text = re.sub(r'\*\*(.+?)\*\*', r'**\1**', text)
    # 傍点 → 太字で代替（青空文庫注記形式はウェブ貼り付けで描画されないため）
    text = re.sub(r'\^\^(.+?)\^\^', r'**\1**', text)
    # 章区切り
    text = text.replace('===', '［＃改丁］')
    # セクション区切り（空行に戻す）
    text = re.sub(r'^---$', '', text, flags=re.MULTILINE)
    return text
