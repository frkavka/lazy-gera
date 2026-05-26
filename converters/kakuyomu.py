import re


def convert_to_kakuyomu(text: str) -> str:
    """内部フォーマット → カクヨム・エブリスタ・ハーメルン形式（グループ②）"""
    # ルビ: {宇宙|そら} → |宇宙《そら》（半角パイプ）
    text = re.sub(r'\{([^|{}]+)\|([^}]+)\}', r'|\1《\2》', text)
    # 太字・傍点 → 《《text》》（カクヨム/エブリスタに太字記法なし）
    text = re.sub(r'\*\*(.+?)\*\*', r'《《\1》》', text)
    text = re.sub(r'\^\^(.+?)\^\^', r'《《\1》》', text)
    # 章区切り（区切り線）
    text = text.replace('===', '――――――――――')
    # セクション区切り（空行）
    text = re.sub(r'^---$', '', text, flags=re.MULTILINE)
    return text
