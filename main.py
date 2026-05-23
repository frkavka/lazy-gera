"""
使い方:
  python main.py <原文ファイル> [--targets aozora kdp ...] [--rulebook ルールブック.yaml]

ルールブック解決ルール:
  --rulebook 指定あり → そのファイルのみ使用（共通とのマージなし）
  --rulebook 指定なし →
    プロジェクトルート（CWD）の rulebook.yaml を共通ベースとして読み込み、
    入力ファイルと同じディレクトリに rulebook.yaml があれば作品固有として追加マージする

例:
  python main.py novel.txt
  python main.py 異世界転生もの/第1話.txt --targets aozora kdp
  python main.py novel.txt --rulebook custom_rulebook.yaml
"""

import argparse
from pathlib import Path

from pipeline import text_formatting_pipeline

# CWD で共通ルールブックを探す順序
_COMMON_CANDIDATES = ["rulebook.yaml", "rulebook_example.yaml"]


def _find_common_rulebook() -> Path | None:
    for name in _COMMON_CANDIDATES:
        p = Path(name)
        if p.exists():
            return p
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="AI テキストフォーマッター")
    parser.add_argument("input", help="原文テキストファイルのパス")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=["aozora"],
        choices=["aozora", "note", "kakuyomu", "evesta", "hameln", "narou", "tales", "kdp"],
        help="出力プラットフォーム（複数指定可）",
    )
    parser.add_argument(
        "--rulebook",
        default=None,
        help="ルールブックのパス（指定時は共通ルールブックとのマージなし）",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"原文ファイルが見つかりません: {input_path}")

    original_text = input_path.read_text(encoding="utf-8")

    # ─── ルールブックのパス解決 ─────────────────────────────────────
    if args.rulebook:
        # 明示指定 → そのファイルのみ（共通とのマージなし）
        common_path = Path(args.rulebook)
        work_path   = None
    else:
        # 自動解決: CWD の共通 ＋ 入力ファイルのディレクトリの作品固有
        common_path = _find_common_rulebook()

        candidate = input_path.parent / "rulebook.yaml"
        # 入力ファイルが CWD 直下の場合は共通と同じファイルになるので除外
        if candidate.exists() and candidate.resolve() != (common_path.resolve() if common_path else None):
            work_path = candidate
        else:
            work_path = None

        if common_path is None and work_path is None:
            raise FileNotFoundError(
                "ルールブックが見つかりません。"
                "CWD に rulebook.yaml を置くか --rulebook で指定してください。"
            )
    # ──────────────────────────────────────────────────────────────────

    outputs, results = text_formatting_pipeline(
        original_text=original_text,
        targets=args.targets,
        common_rulebook_path=common_path,
        work_rulebook_path=work_path,
    )

    stem = input_path.stem
    for target, text in outputs.items():
        if target == "viewer":
            out_path = input_path.parent / f"{stem}_viewer.html"
        else:
            out_path = input_path.parent / f"{stem}_{target}.txt"
        out_path.write_text(text, encoding="utf-8")
        print(f"出力: {out_path}")


if __name__ == "__main__":
    main()
