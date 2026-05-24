import hashlib
import re
from pathlib import Path

from models import Chunk, ChunkResult, DiffInfo
from chunker import split_into_chunks
from transformer import build_user_prompt, build_retry_prompt
from llm_client import call_llm
from validator import check_integrity, compute_diff, render_diff
from converters import convert_to_platform
from rulebook import load_merged_rulebook
from config import load_config
from markup_processor import preprocess_markup
from viewer_generator import generate_viewer


def text_formatting_pipeline(
    original_text: str,
    targets: list[str],
    common_rulebook_path: Path | None = None,
    work_rulebook_path: Path | None = None,
) -> tuple[dict[str, str], list[ChunkResult]]:
    """
    メインパイプライン。
    リトライ設定は config.yaml（または組み込みデフォルト）から取得する。

    Args:
        original_text:        原文テキスト（改変厳禁）
        targets:              出力プラットフォームのリスト（例: ["aozora", "kdp"]）
        common_rulebook_path: 共通ルールブックのパス
        work_rulebook_path:   作品固有ルールブックのパス（省略可）

    Returns:
        outputs: プラットフォームごとの出力テキスト
        results: 全チャンクの処理結果（レビューレポート用）
    """
    cfg = load_config()["llm"]
    max_retries: int        = cfg["max_retries"]
    initial_temperature: float = cfg["initial_temperature"]
    temperature_step: float    = cfg["temperature_step"]

    rulebook, rulebook_desc = load_merged_rulebook(common_rulebook_path, work_rulebook_path)
    print(f"ルールブック: {rulebook_desc}")

    # 1. 作者マークアップを内部形式に変換（【】→** / 〔〕→^^ など）
    working_text = preprocess_markup(original_text, rulebook)

    # 2. 原本をロック（変換後のテキストで取る）
    master_hash = hashlib.sha256(working_text.encode("utf-8")).hexdigest()

    # 3. チャンク分割
    chunks = split_into_chunks(working_text)

    # 4. 各チャンクを変換・検証
    results: list[ChunkResult] = []
    for chunk in chunks:
        result = _transform_and_validate(
            chunk, rulebook, max_retries, initial_temperature, temperature_step
        )
        results.append(result)

    # 5. first_time_only の後処理（ルビ重複除去）
    results = _deduplicate_rubies(results, rulebook)

    # 6. レビューサマリーをコンソール出力（needs_review があれば警告）
    _print_review_summary(results)

    # 7. プラットフォームごとに変換して出力
    outputs = {
        target: convert_to_platform(results, target)
        for target in targets
    }

    # 8. 比較ビューア HTML を生成（常に含める）
    outputs["viewer"] = generate_viewer(working_text, results)

    return outputs, results


def _transform_and_validate(
    chunk: Chunk,
    rulebook: dict,
    max_retries: int,
    initial_temperature: float,
    temperature_step: float,
) -> ChunkResult:
    temperature = initial_temperature
    last_transformed: str | None = None
    last_diff: DiffInfo | None = None

    for attempt in range(max_retries):
        # リトライ時は前回の差分をプロンプトに添える
        if attempt == 0:
            user_prompt = build_user_prompt(chunk.text, rulebook)
        else:
            user_prompt = build_retry_prompt(chunk.text, rulebook, last_diff)

        last_transformed = call_llm(user_prompt, temperature=temperature)

        if check_integrity(chunk.text, last_transformed):
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                original=chunk.text,
                transformed=last_transformed,
                status="validated",
                retry_count=attempt,
                diff_info=None,
            )

        # 失敗 → 差分を記録して温度を下げてリトライ
        last_diff = compute_diff(chunk.text, last_transformed)
        temperature = max(0.0, temperature - temperature_step)

    # 規定回数失敗 → needs_review フラグを立てて続行（中断しない）
    return ChunkResult(
        chunk_id=chunk.chunk_id,
        original=chunk.text,
        transformed=last_transformed,
        status="needs_review",
        retry_count=max_retries,
        diff_info=last_diff,
    )


def _deduplicate_rubies(results: list[ChunkResult], rulebook: dict) -> list[ChunkResult]:
    """
    first_time_only=true のルビをドキュメント全体で初出のみに絞る後処理。

    - fixed_rubys / context_dependent_rubys の各エントリに first_time_only: true
    - auto_ruby.first_time_only: true → 自動検出ルビ全体に適用
    """
    # 手動ルール: first_time_only 対象語を収集
    first_time_words: set[str] = set()
    for entry in rulebook.get("fixed_rubys", []):
        if entry.get("first_time_only", False):
            first_time_words.add(entry["word"])
    for entry in rulebook.get("context_dependent_rubys", []):
        if entry.get("first_time_only", False):
            first_time_words.add(entry["word"])

    auto_first_time: bool = rulebook.get("auto_ruby", {}).get("first_time_only", False)

    if not first_time_words and not auto_first_time:
        return results

    # 手動ルールの全語（auto_ruby との区別に使う）
    manual_words: set[str] = (
        {e["word"] for e in rulebook.get("fixed_rubys", [])}
        | {e["word"] for e in rulebook.get("context_dependent_rubys", [])}
    )

    _RUBY_PAT = re.compile(r'\{([^|{}]+)\|[^}]+\}')

    # 手動ルールのパターンは全チャンク共通なので事前コンパイル
    precompiled: dict[str, re.Pattern] = {
        w: re.compile(r'\{' + re.escape(w) + r'\|[^}]+\}')
        for w in first_time_words
    }
    # auto_ruby で動的に発見した語のキャッシュ（同じ語を何度もコンパイルしない）
    pat_cache: dict[str, re.Pattern] = {}

    seen: set[str] = set()
    new_results: list[ChunkResult] = []

    for result in results:
        if result.status != "validated" or result.transformed is None:
            new_results.append(result)
            continue

        text = result.transformed

        # auto_ruby.first_time_only: このチャンクに出現する非手動ルビ語を対象に追加
        target_words = set(first_time_words)
        if auto_first_time:
            auto_words = {m.group(1) for m in _RUBY_PAT.finditer(text)} - manual_words
            target_words |= auto_words

        for word in target_words:
            if word in precompiled:
                pat = precompiled[word]
            elif word in pat_cache:
                pat = pat_cache[word]
            else:
                pat = re.compile(r'\{' + re.escape(word) + r'\|[^}]+\}')
                pat_cache[word] = pat
            matches = list(pat.finditer(text))
            if not matches:
                continue

            if word in seen:
                # 出現済み → 全ルビを除去
                text = pat.sub(word, text)
            else:
                # 初出 → チャンク内で最初の1件だけ残し、以降を除去
                for m in reversed(matches[1:]):
                    text = text[:m.start()] + word + text[m.end():]
                seen.add(word)

        new_results.append(ChunkResult(
            chunk_id=result.chunk_id,
            original=result.original,
            transformed=text,
            status=result.status,
            retry_count=result.retry_count,
            diff_info=result.diff_info,
        ))

    return new_results


_SEP = "─" * 52


def _print_review_summary(results: list[ChunkResult]) -> None:
    """処理結果をコンソールに出力する。needs_review は差分をインライン表示。"""
    flagged = [r for r in results if r.status == "needs_review"]
    total = len(results)

    print(f"\n=== 処理結果 ===")
    print(f"総チャンク数: {total}  /  検証OK: {total - len(flagged)}  /  要確認: {len(flagged)}")

    if not flagged:
        print("\n✓ すべてのチャンクで本文変更なしを確認しました。")
        return

    print("\n[要確認チャンク — AI が本文を変更しようとした箇所]")
    for r in flagged:
        print(f"\n{_SEP}")
        print(f"チャンク #{r.chunk_id}  ({r.retry_count} 回リトライ後も不一致)")
        print(render_diff(r.diff_info))

    print(f"\n{_SEP}")
    print("⚠ 上記チャンクは原文をそのまま出力しています（タグなし）。")
    print("  手動で確認・編集してください。")
