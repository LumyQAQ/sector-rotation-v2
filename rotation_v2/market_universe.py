from __future__ import annotations

from typing import Any

import pandas as pd


MAIN_BOARD_PREFIXES = ("000", "001", "002", "003", "600", "601", "603", "605")
CHINEXT_PREFIXES = ("300", "301")
STAR_PREFIXES = ("688", "689")
BSE_PREFIXES = ("4", "8", "9")


def clean_code(value: Any) -> str:
    return str(value or "").replace(".0", "").strip().zfill(6)


def is_st_name(value: Any) -> bool:
    name = str(value or "").upper().replace("＊", "*").strip()
    return "ST" in name or "退" in name


def board_segment(code: Any) -> str:
    cleaned = clean_code(code)
    if cleaned.startswith(CHINEXT_PREFIXES):
        return "创业板"
    if cleaned.startswith(STAR_PREFIXES):
        return "科创板"
    if cleaned.startswith(MAIN_BOARD_PREFIXES):
        return "沪深主板"
    if cleaned.startswith(BSE_PREFIXES):
        return "北交所"
    return "其他"


def is_main_board_tradable(code: Any, name: Any = "") -> bool:
    return board_segment(code) == "沪深主板" and not is_st_name(name)


def is_leader_recommendable(code: Any, name: Any = "") -> bool:
    return not is_st_name(name)


def append_market_universe_columns(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["证券板块"] = enriched["代码"].map(board_segment)
    enriched["是否ST"] = enriched["名称"].map(is_st_name) if "名称" in enriched.columns else False
    enriched["可推荐龙头"] = [
        is_leader_recommendable(code, name)
        for code, name in zip(enriched["代码"], enriched["名称"] if "名称" in enriched.columns else [""] * len(enriched))
    ]
    enriched["主板可推荐"] = [
        is_main_board_tradable(code, name)
        for code, name in zip(enriched["代码"], enriched["名称"] if "名称" in enriched.columns else [""] * len(enriched))
    ]
    return enriched
