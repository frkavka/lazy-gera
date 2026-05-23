from models import ChunkResult
from converters.aozora import convert_to_aozora
from converters.kakuyomu import convert_to_kakuyomu
from converters.narou import convert_to_narou
from converters.tales import convert_to_tales
from converters.kdp import convert_to_kdp


# プラットフォーム名 → 変換関数のマッピング
#
# グループ①（青空系）  : ｜漢字《ルビ》 / 傍点→太字代替
# グループ②（カクヨム系）: |漢字《ルビ》  / 傍点→《《text》》
# グループ③（なろう系）  : |漢字《ルビ》  / 傍点→｜文《・》｜字《・》
# グループ④（TALESハイブリッド）: ｜漢字《ルビ》 / 傍点→《《text》》
_CONVERTERS = {
    # グループ①
    "aozora":   convert_to_aozora,
    "note":     convert_to_aozora,
    # グループ②
    "kakuyomu": convert_to_kakuyomu,
    "evesta":   convert_to_kakuyomu,   # エブリスタ
    "hameln":   convert_to_kakuyomu,   # ハーメルン
    # グループ③
    "narou":    convert_to_narou,
    # グループ④
    "tales":    convert_to_tales,
    # KDP（EPUB HTML）
    "kdp":      convert_to_kdp,
}


def convert_to_platform(results: list[ChunkResult], target: str) -> str:
    """
    全チャンクを指定プラットフォーム形式に変換して結合する。
    needs_review のチャンクは原文をフォールバックとして使用する。
    """
    converter = _CONVERTERS.get(target)
    if converter is None:
        raise ValueError(
            f"未対応のプラットフォーム: '{target}' "
            f"（対応: {', '.join(_CONVERTERS.keys())}）"
        )

    parts = []
    for result in results:
        text = result.transformed if result.status == "validated" else result.original
        parts.append(converter(text))

    return "\n\n".join(parts)
