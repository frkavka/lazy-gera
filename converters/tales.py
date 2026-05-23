import re


def convert_to_tales(text: str) -> str:
    """内部フォーマット → TALES 形式（グループ④ハイブリッド）
    ルビは青空系（全角｜）、傍点はカクヨム系（《《》》）
    """
    # ルビ: {宇宙|そら} → ｜宇宙《そら》（全角パイプ）
    text = re.sub(r'\{([^|{}]+)\|([^}]+)\}', r'｜\1《\2》', text)
    # 太字（**text** はそのまま）
    # 傍点: ^^text^^ → 《《text》》
    text = re.sub(r'\^\^(.+?)\^\^', r'《《\1》》', text)
    # 章区切り
    text = text.replace('===', '［＃改丁］')
    # セクション区切り（空行）
    text = re.sub(r'^---$', '', text, flags=re.MULTILINE)
    return text
