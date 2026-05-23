"""
難読漢字の自動ルビ候補を検出するモジュール。
pykakasi で読みを取得し、指定した漢字セットでフィルタリングする。
"""

from pykakasi import kakasi

from kanji_sets import JOYO_KANJI, KYOUIKU_KANJI, JIS_LEVEL_1_KANJI

# kakasi インスタンスはモジュールレベルで一度だけ生成（呼び出しのたびに作ると遅い）
_kks = kakasi()

# threshold 文字列 → 漢字セットのマッピング
KANJI_SET_MAP: dict[str, frozenset[str]] = {
    "jis_1":  JIS_LEVEL_1_KANJI,
    "joyo":   JOYO_KANJI,
    "kyoiku": KYOUIKU_KANJI,
}


def _is_kanji(ch: str) -> bool:
    return '一' <= ch <= '鿿'


def _strip_okurigana(word: str, reading: str) -> tuple[str, str]:
    """
    末尾の送り仮名を word と reading から除去する。

    最後の漢字より後ろの文字列を送り仮名とみなし、
    reading がその送り仮名で終わっている場合のみ除去する。

    例:
      「焦っ」+「あせっ」 → 「焦」+「あせ」
      「憎たらしい」+「にくたらしい」 → 「憎」+「にく」
      「別の」+「べつの」 → 「別」+「べつ」
      「宇宙」+「うちゅう」 → そのまま（送り仮名なし）
    """
    last_kanji = max((i for i, ch in enumerate(word) if _is_kanji(ch)), default=-1)
    if last_kanji == -1:
        return word, reading

    okurigana = word[last_kanji + 1:]
    if okurigana and reading.endswith(okurigana):
        return word[:last_kanji + 1], reading[:-len(okurigana)]

    return word, reading


def detect_candidates(
    chunk: str,
    skip_words: set[str],
    kanji_set: frozenset[str] = JOYO_KANJI,
) -> list[dict]:
    """
    チャンクから難読漢字候補を検出して返す。

    フィルタリング優先順位:
      1. skip_words に登録済みの語 → スキップ（fixed_rubys / context_dependent_rubys で処理）
      2. 全文字が kanji_set に含まれる語 → スキップ（読者が読めると見なす範囲）
      3. 残り → 候補として返す（読みは pykakasi の提案値）

    Args:
        chunk:      処理対象のテキスト
        skip_words: ルールブック登録済みの語セット（除外対象）
        kanji_set:  「読めて当然」とみなす漢字セット（JOYO_KANJI or KYOUIKU_KANJI）

    Returns:
        [{"word": "邂逅", "reading": "かいこう"}, ...]
    """
    result = _kks.convert(chunk)

    candidates: list[dict] = []
    seen: set[str] = set()

    for item in result:
        orig: str = item["orig"]
        reading: str = item.get("hira", "")

        # 漢字を含まない → スキップ
        if not any(_is_kanji(ch) for ch in orig):
            continue

        # 読みが取得できなかった → スキップ
        if not reading:
            continue

        # 送り仮名を除去（例: 「焦っ|あせっ」→「焦|あせ」）
        word, reading = _strip_okurigana(orig, reading)

        # ルールブック登録済み → スキップ（除去前後どちらでもヒットしたら除外）
        if word in skip_words or orig in skip_words:
            continue

        # 全文字が kanji_set 内 → スキップ（読者が読めると見なす）
        if all(not _is_kanji(ch) or ch in kanji_set for ch in word):
            continue

        # 同一語の重複除去（送り仮名除去後の語で判定）
        if word in seen:
            continue
        seen.add(word)

        candidates.append({"word": word, "reading": reading})

    return candidates


def get_skip_words(rulebook: dict) -> set[str]:
    """ルールブック登録済みの語をセットで返す。"""
    words: set[str] = set()
    for e in rulebook.get("fixed_rubys", []):
        words.add(e["word"])
    for e in rulebook.get("context_dependent_rubys", []):
        words.add(e["word"])
    return words
