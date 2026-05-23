from models import DiffInfo
from auto_ruby import detect_candidates, get_skip_words, KANJI_SET_MAP
from kanji_sets import JOYO_KANJI, build_kyouiku_set


SYSTEM_PROMPT = """\
あなたは「ルールブックに基づく機械的なテキストタグ付けエンジン」です。
文章の意味を解釈したり、より良く書き換えたりする権限はありません。
与えられた文章に【ルビ・書式タグを追加する】だけがあなたの唯一の機能です。

## 絶対に守るルール（※違反は致命的なシステムエラーを引き起こします）
- 【完全一致】原文の文字を1文字も変えてはいけない（追加・削除・置換すべて禁止）
- 【校正禁止】明らかな誤字脱字、文法エラー、不自然な表現であっても絶対に修正しないこと
- 【書式維持】語尾・句読点・改行（\\n）・全角半角スペースも完全にそのまま保持する
- 【送り仮名】ルビを振る際は、漢字部分のみか、送り仮名を含むか、ルールブックの定義境界を厳格に守ること
- 【フェイルセーフ】ルールブックに載っていない語、または判断に迷う箇所は何もせず原文のまま出力する

## ルビ付与の厳守事項
ルビを振ってよいのは、ユーザープロンプトの「適用ルール」に明記された語のみ。
リストに載っていない語に自分の判断でルビを追加することは絶対に禁止。
「読みにくそう」「ふりがながあると親切」などの理由でリスト外にルビを振ってはならない。

## 文脈依存ルビについて
ルールブックの「文脈依存ルビ」に記載された語は、前後の文脈から読みを推論して選択してよい。
これは例外的に付与された判断権限であり、あくまでルビの読みの選択のみに適用される。
本文テキストを変更する権限は一切ない。

## 出力フォーマット（内部フォーマット）
- ルビ    : {本文|よみ}     例) {宇宙|そら}、{躊躇|ためら}う
- 太字    : **text**
- 傍点    : ^^text^^
- セクション区切り : ---
- 章区切り : ===

## 出力ルール
- 整形後のテキストのみを出力する
- 説明・コメント・前置きは一切不要
- Markdownのコードブロック（``` 等）で囲まないこと。プレーンテキストのみを返すこと。\
"""


def build_user_prompt(chunk: str, rulebook: dict) -> str:
    """チャンクに出現する語だけに絞ったルールをプロンプトに埋め込む。"""
    sections: list[str] = []

    # --- 固定ルビ ---
    fixed = [
        e for e in rulebook.get("fixed_rubys", [])
        if e["word"] in chunk
    ]
    if fixed:
        lines = "\n".join(
            f'- 「{e["word"]}」→ {{{e["word"]}|{e["reading"]}}}'
            for e in fixed
        )
        sections.append(f"### 固定ルビ（条件なし・必ず適用）\n{lines}")

    # --- 文脈依存ルビ ---
    context = [
        e for e in rulebook.get("context_dependent_rubys", [])
        if e["word"] in chunk
    ]
    if context:
        lines = []
        for e in context:
            readings = "\n".join(
                f'  - {{{e["word"]}|{r["reading"]}}} : {r["condition"]}'
                for r in e["readings"]
            )
            lines.append(f'- 「{e["word"]}」（文脈で判断）\n{readings}')
        sections.append(f"### 文脈依存ルビ（文脈を読んで適切な方を選択）\n" + "\n".join(lines))

    # --- 書式ルール ---
    fmt_rules = [
        r for r in rulebook.get("format_rules", [])
        if r["target_word"] in chunk
    ]
    if fmt_rules:
        _ACTION_LABEL = {"bold": "太字（** **）"}
        lines = "\n".join(
            f'- 「{r["target_word"]}」→ {_ACTION_LABEL.get(r["action"], r["action"])}'
            for r in fmt_rules
        )
        sections.append(f"### 書式ルール\n{lines}")

    # --- 自動ルビ（難読漢字） ---
    if rulebook.get("auto_ruby", {}).get("enabled", False):
        skip = get_skip_words(rulebook)
        auto_ruby_cfg = rulebook.get("auto_ruby", {})
        threshold = auto_ruby_cfg.get("threshold", "joyo")
        kanji_set = KANJI_SET_MAP.get(threshold, JOYO_KANJI)
        if threshold == "kyoiku" and "kyoiku_grade" in auto_ruby_cfg:
            kanji_set = build_kyouiku_set(int(auto_ruby_cfg["kyoiku_grade"]))
        extra = auto_ruby_cfg.get("extra_kanji", "")
        if extra:
            kanji_set = kanji_set | frozenset(extra)
        candidates = detect_candidates(chunk, skip, kanji_set)
        if candidates:
            lines = "\n".join(
                f'- 「{c["word"]}」（候補読み: {c["reading"]}）'
                for c in candidates
            )
            sections.append(
                "### 自動検出された難読漢字\n"
                "文脈から読みが確信できる場合のみルビを振ってください。\n"
                "候補読みが誤っている場合は正しい読みに直して振ってください。\n"
                "不確かな場合は何もしないでください。\n"
                f"{lines}"
            )

    rule_text = "\n\n".join(sections) if sections else "（このチャンクに該当するルールなし）"

    return (
        f"## 適用ルール\n{rule_text}\n\n"
        f"## 処理対象テキスト\n{chunk}"
    )


def build_retry_prompt(chunk: str, rulebook: dict, diff_info: DiffInfo) -> str:
    """リトライ時は前回の差分サマリーをプロンプトに追加する。"""
    base = build_user_prompt(chunk, rulebook)
    return (
        f"{base}\n\n"
        f"## 前回の出力に問題がありました\n"
        f"{diff_info.summary}\n"
        f"本文の変更は厳禁です。タグの追加のみ行ってください。"
    )


