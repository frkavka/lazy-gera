import re
import unicodedata
import difflib

from models import DiffHunk, DiffInfo


def normalize(text: str) -> str:
    """Unicode NFC統一 + 改行コード統一。比較前に必ず通す。"""
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n")


def remove_tags(text: str) -> str:
    """内部フォーマットのタグをすべて除去して素のテキストに戻す。"""
    # ルビ: {宇宙|そら} → 宇宙
    text = re.sub(r'\{([^|{}]+)\|[^}]+\}', r'\1', text)
    # 太字: **text** → text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # 傍点: ^^text^^ → text
    text = re.sub(r'\^\^(.+?)\^\^', r'\1', text)
    # セクション区切り・章区切りは空行に戻す
    text = re.sub(r'^---$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^===$', '', text, flags=re.MULTILINE)
    return text


def check_integrity(original: str, transformed: str) -> bool:
    """タグ除去後の本文が原文と完全一致するか検証する。
    両辺からタグを除去して比較する（作者マークアップ変換後のタグも除去対象）。
    """
    return normalize(remove_tags(original)) == normalize(remove_tags(transformed))


def compute_diff(original: str, transformed: str) -> DiffInfo:
    """バリデーション失敗時の差分情報を生成する。UI & リトライプロンプト用。"""
    stripped_original   = normalize(remove_tags(original))
    stripped_transformed = normalize(remove_tags(transformed))

    # 文字単位で比較（日本語テキストに適切）
    matcher = difflib.SequenceMatcher(None, stripped_original, stripped_transformed, autojunk=False)

    hunks = []
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            continue
        hunks.append(DiffHunk(
            type=opcode,
            original=stripped_original[i1:i2],
            ai_output=stripped_transformed[j1:j2],
            original_pos=i1,
        ))

    return DiffInfo(
        original=stripped_original,   # タグ除去済みを渡す（render_diff のコンテキスト表示用）
        transformed=transformed,
        stripped=stripped_transformed,
        hunks=hunks,
        summary=_build_summary(hunks),
    )


def _build_summary(hunks: list[DiffHunk]) -> str:
    if not hunks:
        return "差分なし"

    parts = []
    for h in hunks:
        if h.type == "replace":
            parts.append(f"「{h.original}」→「{h.ai_output}」に変更")
        elif h.type == "delete":
            parts.append(f"「{h.original}」が削除された")
        elif h.type == "insert":
            parts.append(f"「{h.ai_output}」が挿入された")

    return f"{len(hunks)}箇所の変更検出: " + " / ".join(parts)


def render_diff(diff_info: DiffInfo, context_chars: int = 20) -> str:
    """
    git-diff 風のインライン差分表示を生成する。

    例:
        --- 原文
        +++ AI出力（タグ除去後）
        @@ 変更 1/2 @@
        -  …肉体を[敵]視した。…
        +  …肉体を[的]視した。…
    """
    norm_orig = normalize(diff_info.original)
    total = len(diff_info.hunks)

    lines = [
        "--- 原文",
        "+++ AI出力（タグ除去後）",
    ]

    for idx, hunk in enumerate(diff_info.hunks, 1):
        i1 = hunk.original_pos
        i2 = i1 + len(hunk.original)

        pre = norm_orig[max(0, i1 - context_chars):i1]
        suf = norm_orig[i2:min(len(norm_orig), i2 + context_chars)]

        if i1 - context_chars > 0:
            pre = "…" + pre
        if i2 + context_chars < len(norm_orig):
            suf = suf + "…"

        lines.append(f"\n@@ 変更 {idx}/{total} @@")

        if hunk.type == "replace":
            lines.append(f"-  {pre}[{hunk.original}]{suf}")
            lines.append(f"+  {pre}[{hunk.ai_output}]{suf}")
        elif hunk.type == "delete":
            lines.append(f"-  {pre}[{hunk.original}]{suf}")
            lines.append(f"+  {pre}[（削除）]{suf}")
        elif hunk.type == "insert":
            lines.append(f"-  {pre}[（挿入なし）]{suf}")
            lines.append(f"+  {pre}[{hunk.ai_output}]{suf}")

    return "\n".join(lines)
