# 漢字セット定義
# データソース: kanji-data サブモジュール (mimneko/kanji-data)
#
# auto_ruby の threshold 設定で使い分ける:
#   "jis_1"  → JIS第1水準漢字外にルビ候補（小説慣れした層向け）
#   "joyo"   → 常用漢字外にルビ候補（一般読者向け）
#   "kyoiku" → 教育漢字外にルビ候補（子ども・ライト読者向け、学年指定可）

import csv
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "kanji-data"


# ── JIS第1水準（EUC-JPから計算生成） ─────────────────────────────────────────

def _generate_jis_level_1() -> frozenset[str]:
    """JIS X 0208 第1水準漢字（16区〜47区51点）をEUC-JPから生成する。"""
    kanji_set: set[str] = set()
    for ku in range(16, 48):
        for ten in range(1, 95):
            if ku == 47 and ten > 51:
                break
            try:
                char = bytes([ku + 0xA0, ten + 0xA0]).decode("euc_jp")
                kanji_set.add(char)
            except UnicodeDecodeError:
                continue
    return frozenset(kanji_set)


JIS_LEVEL_1_KANJI: frozenset[str] = _generate_jis_level_1()


# ── 常用漢字（kanji-data/常用漢字.csv） ──────────────────────────────────────

def _load_joyo() -> frozenset[str]:
    path = _DATA_DIR / "常用漢字.csv"
    with path.open(encoding="utf-8-sig") as f:
        return frozenset(row["漢字"] for row in csv.DictReader(f))


JOYO_KANJI: frozenset[str] = _load_joyo()


# ── 教育漢字（kanji-data/教育漢字.csv、学年フィルタリング対応） ───────────────

def build_kyouiku_set(max_grade: int = 6) -> frozenset[str]:
    """
    指定学年以下の教育漢字セットを返す。

    Args:
        max_grade: 含める最大学年（1〜6）。デフォルトは6（全学年）。
                   例: 3 → 小学3年生までに習う漢字のみ含む

    Returns:
        max_grade 以下の学年の漢字の frozenset
    """
    path = _DATA_DIR / "教育漢字.csv"
    with path.open(encoding="utf-8-sig") as f:
        return frozenset(
            row["漢字"] for row in csv.DictReader(f)
            if int(row["学年"]) <= max_grade
        )


KYOUIKU_KANJI: frozenset[str] = build_kyouiku_set()  # デフォルト: 全学年（6年分）
