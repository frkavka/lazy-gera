import re


def _emphasis_to_narou(text: str) -> str:
    """^^text^^ → ｜文《・》｜字《・》（なろう傍点: 1文字ずつルビで代替）"""
    def to_dot_ruby(m: re.Match) -> str:
        return ''.join(f'｜{ch}《・》' for ch in m.group(1))
    return re.sub(r'\^\^(.+?)\^\^', to_dot_ruby, text)


def convert_to_narou(text: str) -> str:
    """内部フォーマット → 小説家になろう形式（グループ③）"""
    # ルビ: {宇宙|そら} → |宇宙《そら》（半角パイプ）
    text = re.sub(r'\{([^|{}]+)\|([^}]+)\}', r'|\1《\2》', text)
    # 太字・傍点 → 1文字ずつドットルビで代替（なろうに太字記法なし）
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: ''.join(f'｜{ch}《・》' for ch in m.group(1)), text)
    text = _emphasis_to_narou(text)
    # 章区切り（区切り線）
    text = text.replace('===', '――――――――――')
    # セクション区切り（空行）
    text = re.sub(r'^---$', '', text, flags=re.MULTILINE)
    return text
