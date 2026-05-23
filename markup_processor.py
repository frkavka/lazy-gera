"""
作者が原稿に書いたマークアップ記号を内部形式に変換する前処理モジュール。

ルールブックの markup セクションで記号を定義する（省略時はデフォルト値を使用）:

  markup:
    bold:
      open: "【"
      close: "】"
    emphasis:
      open: "〔"
      close: "〕"

変換後の内部形式:
  太字: **text**
  傍点: ^^text^^

制約:
  開始・終了記号に以下を含めると内部処理と競合する可能性がある:
    ** ^^ { } | === ---
  競合が検出された場合は警告を表示するが処理は続行する。
"""

import re

# 内部形式で予約済みの文字列
_RESERVED = frozenset(["**", "^^", "{", "}", "|", "===", "---"])

_DEFAULT_MARKUP = {
    "bold":     {"open": "【", "close": "】"},
    "emphasis": {"open": "〔", "close": "〕"},
}


def _check_reserved(symbol: str, label: str) -> None:
    for r in _RESERVED:
        if r in symbol:
            print(f"⚠ markup.{label} に予約済み記号 '{r}' が含まれています（内部形式と競合する可能性）")
            return


def _apply(text: str, open_mark: str, close_mark: str,
           inner_open: str, inner_close: str) -> str:
    """open_mark〜close_mark で囲まれた範囲を内部形式に置換する。"""
    if open_mark == close_mark:
        # 開閉が同じ記号（例: ※text※）→ 偶数番目を閉じとみなす
        parts = re.split(re.escape(open_mark), text)
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                result.append(f"{inner_open}{part}{inner_close}")
            else:
                result.append(part)
        return "".join(result)
    else:
        pat = re.compile(
            re.escape(open_mark) + r"(.+?)" + re.escape(close_mark),
            re.DOTALL,
        )
        return pat.sub(lambda m: f"{inner_open}{m.group(1)}{inner_close}", text)


def preprocess_markup(text: str, rulebook: dict) -> str:
    """
    ルールブックの markup 定義に従い、作者記号を内部形式に変換する。

    Args:
        text:     原文テキスト
        rulebook: ロード済みルールブック

    Returns:
        作者記号を内部形式（** / ^^）に変換したテキスト
    """
    markup = rulebook.get("markup", {})

    for kind, (inner_open, inner_close) in [("bold", ("**", "**")), ("emphasis", ("^^", "^^"))]:
        cfg = {**_DEFAULT_MARKUP[kind], **markup.get(kind, {})}
        open_mark  = cfg["open"]
        close_mark = cfg["close"]

        # 記号の競合チェック
        _check_reserved(open_mark,  f"{kind}.open")
        _check_reserved(close_mark, f"{kind}.close")

        # 記号が実際に出現する場合のみ変換（無駄な処理をしない）
        if open_mark in text:
            text = _apply(text, open_mark, close_mark, inner_open, inner_close)

    return text
