from copy import deepcopy
from pathlib import Path

import yaml


def load_rulebook(path: str | Path) -> dict:
    """YAMLルールブックを読み込む。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ルールブックが見つかりません: {path}")
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"ルールブックが空です: {path}")
    return data


def merge_rulebooks(base: dict, override: dict) -> dict:
    """
    共通ルールブック（base）に作品固有ルールブック（override）をマージする。

    - リスト系ルール（fixed_rubys / context_dependent_rubys / format_rules）:
        同じキーの語は override が優先、新規語は追加
    - 辞書系設定（auto_ruby / markup / safety_settings）:
        override の値で上書き（shallow merge）
    """
    result = deepcopy(base)

    # リスト系：語をキーとして override が優先
    LIST_RULES: dict[str, str] = {
        "fixed_rubys":             "word",
        "context_dependent_rubys": "word",
        "format_rules":            "target_word",
    }
    for section, key_field in LIST_RULES.items():
        if section not in override:
            continue
        override_list: list[dict] = override[section]
        override_keys = {e[key_field] for e in override_list if key_field in e}
        # base から重複キーを除き、override を末尾に追加
        base_list = [e for e in result.get(section, []) if e.get(key_field) not in override_keys]
        result[section] = base_list + override_list

    # 辞書系：override で上書き
    for section in ("auto_ruby", "markup", "safety_settings"):
        if section not in override:
            continue
        if isinstance(result.get(section), dict) and isinstance(override[section], dict):
            result[section] = {**result[section], **override[section]}
        else:
            result[section] = override[section]

    return result


def load_merged_rulebook(
    common_path: Path | None,
    work_path: Path | None,
) -> tuple[dict, str]:
    """
    共通ルールブックと作品固有ルールブックをマージして返す。

    Returns:
        (merged_dict, 読み込み状況の説明文)
    """
    if common_path is None and work_path is None:
        raise ValueError("ルールブックが1つも指定されていません")

    if common_path is not None and work_path is not None:
        base     = load_rulebook(common_path)
        override = load_rulebook(work_path)
        desc = f"{common_path} ＋ {work_path}（作品固有）"
        return merge_rulebooks(base, override), desc

    if common_path is not None:
        return load_rulebook(common_path), str(common_path)

    return load_rulebook(work_path), str(work_path)   # type: ignore[arg-type]
