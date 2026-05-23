import re
import warnings

from models import Chunk

# 文末として認識する文字
_SENTENCE_END = re.compile(r'[。！？]')


def split_into_chunks(text: str, max_chars: int = 5000) -> list[Chunk]:
    """
    原文を意味の塊で分割してChunkリストを返す。

    分割優先順位:
      1. \\n\\n（空行）  ← 段落の区切り
      2. 。！？（句点・感嘆符・疑問符）← max_chars 超過時のみ
         ただし「」『』内は分割しない

    単文が max_chars を超える場合は強制分割せずそのまま渡す。
    """
    paragraphs = _split_paragraphs(text)

    chunks: list[Chunk] = []
    chunk_id = 0

    for para_text, para_start in paragraphs:
        if len(para_text) <= max_chars:
            # 段落がmax_chars以内 → そのまま1チャンク
            chunks.append(Chunk(
                chunk_id=chunk_id,
                text=para_text,
                start=para_start,
                end=para_start + len(para_text),
            ))
            chunk_id += 1
        else:
            # 段落が長すぎる → 句点で再分割してグループ化
            sentences = _split_by_sentence(para_text, para_start)
            for sub_text, sub_start, sub_end in _group_sentences(sentences, max_chars):
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=sub_text,
                    start=sub_start,
                    end=sub_end,
                ))
                chunk_id += 1

    if not chunks:
        # 空行も句点もない場合は全文を1チャンク
        chunks.append(Chunk(chunk_id=0, text=text, start=0, end=len(text)))

    return chunks


def _split_paragraphs(text: str) -> list[tuple[str, int]]:
    """空行（\\n\\n）で段落分割し、(テキスト, 開始位置) のリストを返す。"""
    paragraphs = []
    pos = 0
    for para in text.split('\n\n'):
        if para.strip():  # 空白・改行のみの段落はスキップ
            paragraphs.append((para, pos))
        pos += len(para) + 2  # \n\n の分
    return paragraphs


# 開き括弧 → 閉じ括弧 の対応表
_OPEN_BRACKETS  = ('「', '『', '（')
_CLOSE_BRACKETS = ('」', '』', '）')
_BRACKET_PAIRS  = dict(zip(_CLOSE_BRACKETS, _OPEN_BRACKETS))


def _split_by_sentence(text: str, base_offset: int) -> list[tuple[str, int, int]]:
    """
    句点（。！？）で文を分割し、(テキスト, 開始位置, 終了位置) のリストを返す。
    「」『』（）の内部では分割しない。ネストも考慮する。
    閉じ括弧が不一致の場合は警告を出す（処理は続行）。
    """
    sentences = []
    depth = 0
    current_start = 0

    for i, ch in enumerate(text):
        if ch in _OPEN_BRACKETS:
            depth += 1
        elif ch in _CLOSE_BRACKETS:
            if depth == 0:
                # 閉じ括弧が多い（原文の不一致）→ 警告のみで続行
                warnings.warn(
                    f"閉じ括弧の不一致: 位置 {base_offset + i} 付近 "
                    f"「{text[max(0,i-5):i+5]}」",
                    stacklevel=3,
                )
            else:
                depth -= 1
        elif _SENTENCE_END.match(ch) and depth == 0:
            sentence = text[current_start:i + 1]
            sentences.append((
                sentence,
                base_offset + current_start,
                base_offset + i + 1,
            ))
            current_start = i + 1

    # 末尾に句点がないテキスト（台詞・地の文の残り等）
    if current_start < len(text):
        sentences.append((
            text[current_start:],
            base_offset + current_start,
            base_offset + len(text),
        ))

    # 末尾まで括弧が閉じていない場合も警告
    if depth > 0:
        warnings.warn(
            f"開き括弧が閉じられていません（depth={depth}）: "
            f"末尾付近 「{text[-20:]}」",
            stacklevel=2,
        )

    return sentences


def _group_sentences(
    sentences: list[tuple[str, int, int]],
    max_chars: int,
) -> list[tuple[str, int, int]]:
    """
    文をmax_chars以内のグループに結合する。
    単文がmax_charsを超える場合はそのまま1グループとする（強制分割しない）。
    """
    groups = []
    buffer: list[str] = []
    buffer_start: int | None = None
    buffer_len = 0

    for text, start, end in sentences:
        if buffer_start is None:
            buffer_start = start

        if buffer and buffer_len + len(text) > max_chars:
            # バッファを確定してリセット
            groups.append((''.join(buffer), buffer_start, start))
            buffer = [text]
            buffer_start = start
            buffer_len = len(text)
        else:
            buffer.append(text)
            buffer_len += len(text)

    if buffer:
        groups.append((''.join(buffer), buffer_start, sentences[-1][2]))

    return groups
