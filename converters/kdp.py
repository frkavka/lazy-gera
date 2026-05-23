import re


def convert_to_kdp(text: str) -> str:
    """内部フォーマット → KDP (EPUB HTML) 形式"""
    # ルビ
    text = re.sub(
        r'\{([^|{}]+)\|([^}]+)\}',
        r'<ruby>\1<rt>\2</rt></ruby>',
        text,
    )
    # 太字
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 傍点（CSS で dot を当てる想定）
    text = re.sub(r'\^\^(.+?)\^\^', r'<em class="tenten">\1</em>', text)
    # 章区切り
    text = text.replace('===', '<mbp:pagebreak/>')
    # セクション区切り
    text = re.sub(r'^---$', '<hr/>', text, flags=re.MULTILINE)
    # 段落を <p> タグで囲む
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    text = '\n'.join(f'<p>{p}</p>' for p in paragraphs)
    return text
