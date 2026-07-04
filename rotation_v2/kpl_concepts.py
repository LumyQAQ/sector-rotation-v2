from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .data_loader import project_root
from .metrics import RotationModel, build_rotation_model, clean_stock_code


LOCAL_KPL_CONCEPT_PATH = Path("/Users/ziranfeng/Desktop/CMLM V4.0/kpl_concept_library/concept_stock_map.csv")


def default_kpl_concept_candidates() -> list[Path]:
    root = project_root()
    return [
        root / "data" / "kpl_concept_library" / "concept_stock_map.csv",
        LOCAL_KPL_CONCEPT_PATH,
        Path("/Users/ziranfeng/Desktop/nuwa-skill-main/outputs/kpl_concept_library_20260702/concept_stock_map.csv"),
    ]


def resolve_kpl_concept_path(path: str | Path | None = None) -> Path:
    if path:
        resolved = Path(path).expanduser()
        if resolved.exists():
            return resolved
        raise FileNotFoundError(f"找不到开盘啦概念池: {resolved}")

    for candidate in default_kpl_concept_candidates():
        if candidate.exists():
            return candidate
    searched = "\n".join(str(candidate) for candidate in default_kpl_concept_candidates())
    raise FileNotFoundError(f"找不到开盘啦概念池 concept_stock_map.csv，已检查:\n{searched}")


def normalize_stock_name(value: Any) -> str:
    return str(value or "").replace("\u3000", "").strip().replace(" ", "")


TRADE_NAME_PREFIXES = ("XD", "DR", "XR")


def strip_trade_name_prefix(value: Any) -> str:
    name = normalize_stock_name(value)
    for prefix in TRADE_NAME_PREFIXES:
        if name.startswith(prefix) and len(name) > len(prefix) + 1:
            return name[len(prefix) :]
    return name


def _has_trade_name_prefix(value: Any) -> bool:
    name = normalize_stock_name(value)
    return any(name.startswith(prefix) and len(name) > len(prefix) + 1 for prefix in TRADE_NAME_PREFIXES)


def _trade_alias_matches(concepts: pd.DataFrame, industry: pd.DataFrame, exact_row_ids: set[int]) -> pd.DataFrame:
    unmatched = concepts[~concepts["_concept_row"].isin(exact_row_ids)].copy()
    if unmatched.empty:
        return pd.DataFrame()

    prefixed = industry[industry["名称"].map(_has_trade_name_prefix)].copy()
    if prefixed.empty:
        return pd.DataFrame()
    prefixed["stock_name_alias"] = prefixed["名称"].map(strip_trade_name_prefix)
    prefixed = prefixed[prefixed["stock_name_alias"].str.len() >= 3]

    records: list[dict[str, Any]] = []
    for _, concept in unmatched.iterrows():
        key = normalize_stock_name(concept["stock_name"])
        if len(key) < 3:
            continue
        candidates = prefixed[
            prefixed["stock_name_alias"].map(lambda alias: key.startswith(alias) or alias.startswith(key))
        ]
        if candidates["代码"].nunique() != 1:
            continue
        for _, candidate in candidates.iterrows():
            record = concept.to_dict()
            record.update({"代码": candidate["代码"], "名称": candidate["名称"], "stock_name_norm": candidate["stock_name_norm"]})
            records.append(record)

    return pd.DataFrame(records)


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, dtype=str)


def load_kpl_concept_stock_map(path: str | Path | None = None) -> pd.DataFrame:
    source = resolve_kpl_concept_path(path)
    frame = _read_csv(source)
    required = {"concept_name", "stock_name"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"开盘啦概念池缺少字段: {', '.join(sorted(missing))}")

    result = frame.copy()
    result["concept_name"] = result["concept_name"].astype(str).str.strip()
    result["stock_name"] = result["stock_name"].map(normalize_stock_name)
    result = result[(result["concept_name"] != "") & (result["stock_name"] != "")]
    return result.drop_duplicates(["concept_name", "stock_name"]).reset_index(drop=True)


def build_kpl_concept_mapping(
    stock_industry: pd.DataFrame,
    concept_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    concepts = load_kpl_concept_stock_map(concept_path)
    industry = stock_industry.copy()
    for required in ["代码", "名称"]:
        if required not in industry.columns:
            raise ValueError(f"stock_industry 缺少字段: {required}")

    industry["代码"] = clean_stock_code(industry["代码"])
    industry["名称"] = industry["名称"].astype(str)
    industry["stock_name_norm"] = industry["名称"].map(normalize_stock_name)
    concepts = concepts.reset_index(drop=True).reset_index(names="_concept_row")
    concepts["stock_name_norm"] = concepts["stock_name"].map(normalize_stock_name)

    exact_matched = concepts.merge(
        industry[["代码", "名称", "stock_name_norm"]],
        on="stock_name_norm",
        how="inner",
    )
    alias_matched = _trade_alias_matches(concepts, industry, set(exact_matched["_concept_row"].astype(int)))
    matched = pd.concat([exact_matched, alias_matched], ignore_index=True)
    mapping = (
        matched.rename(columns={"concept_name": "行业名称"})[["代码", "名称", "行业名称"]]
        .drop_duplicates(["代码", "行业名称"])
        .reset_index(drop=True)
    )
    if mapping.empty:
        raise ValueError("开盘啦概念池与 stock_industry 未匹配到任何股票。")

    stats = {
        "概念池概念数": int(concepts["concept_name"].nunique()),
        "概念池股票数": int(concepts["stock_name"].nunique()),
        "概念匹配股票数": int(mapping["代码"].nunique()),
        "概念映射行数": int(len(mapping)),
    }
    return mapping, stats


def build_kpl_concept_model(
    stock_daily: pd.DataFrame,
    stock_industry: pd.DataFrame,
    concept_path: str | Path | None = None,
    *,
    as_of: str | None = None,
    tail_days: int = 20,
    rs_window: int = 20,
    momentum_window: int = 5,
    smooth_window: int = 3,
) -> RotationModel:
    concept_mapping, stats = build_kpl_concept_mapping(stock_industry, concept_path)
    model = build_rotation_model(
        stock_daily,
        concept_mapping,
        as_of=as_of,
        tail_days=tail_days,
        rs_window=rs_window,
        momentum_window=momentum_window,
        smooth_window=smooth_window,
        include_growth_indices=False,
    )
    model.summary.update(stats)
    return model
