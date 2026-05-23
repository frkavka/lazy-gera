from dataclasses import dataclass
from typing import Literal


@dataclass
class Chunk:
    chunk_id: int
    text: str
    start: int  # 原文中の開始位置（文字インデックス）
    end: int    # 原文中の終了位置


@dataclass
class DiffHunk:
    type: Literal["replace", "insert", "delete"]
    original: str       # 原文側の文字列
    ai_output: str      # AI出力（タグ除去後）側の文字列
    original_pos: int   # 原文中の文字位置（UI表示用）


@dataclass
class DiffInfo:
    original: str       # 原文チャンク
    transformed: str    # AI出力（内部フォーマット付き・ユーザー編集対象）
    stripped: str       # タグ除去後（比較用）
    hunks: list[DiffHunk]
    summary: str        # UI & リトライプロンプト兼用の人間向け説明


@dataclass
class ChunkResult:
    chunk_id: int
    original: str
    transformed: str | None
    status: Literal["validated", "needs_review"]
    retry_count: int
    diff_info: DiffInfo | None  # needs_review のときのみセット
