from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .market_universe import append_market_universe_columns
from .theme_taxonomy import enrich_theme_structure


@dataclass(frozen=True)
class RotationModel:
    as_of: str
    sector_frame: pd.DataFrame
    family_frame: pd.DataFrame
    trail_frame: pd.DataFrame
    leaders_frame: pd.DataFrame
    market_state: str
    summary: dict[str, Any]


def clean_stock_code(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"\.0$", "", regex=True).str.replace(r"\D", "", regex=True)
    return cleaned.str.zfill(6)


def classify_phase(relative_strength: float, momentum: float) -> str:
    if relative_strength >= 0 and momentum >= 0:
        return "领涨"
    if relative_strength < 0 and momentum >= 0:
        return "修复"
    if relative_strength >= 0 and momentum < 0:
        return "走弱"
    return "退潮"


def direction_label(dx: float, dy: float) -> str:
    if dx >= 0 and dy >= 0:
        return "右上加速"
    if dx < 0 <= dy:
        return "左上修复"
    if dx >= 0 > dy:
        return "右下降温"
    return "左下退潮"


def _rank_score(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)
    return (numeric.rank(pct=True) * 100).fillna(0.0)


def _safe_pct_change(frame: pd.DataFrame, periods: int) -> pd.Series:
    if len(frame.index) <= periods:
        return pd.Series(0.0, index=frame.columns)
    return ((frame.iloc[-1] / frame.iloc[-1 - periods]) - 1.0) * 100.0


def _prepare_inputs(stock_daily: pd.DataFrame, stock_industry: pd.DataFrame, as_of: str | None) -> pd.DataFrame:
    daily = stock_daily.copy()
    industry = stock_industry.copy()

    for required in ["代码", "日期", "收盘", "涨跌幅", "成交额"]:
        if required not in daily.columns:
            raise ValueError(f"stock_daily 缺少字段: {required}")
    for required in ["代码", "行业名称"]:
        if required not in industry.columns:
            raise ValueError(f"stock_industry 缺少字段: {required}")

    if "名称" not in industry.columns:
        industry["名称"] = industry.get("股票名称", industry["代码"])

    daily["代码"] = clean_stock_code(daily["代码"])
    industry["代码"] = clean_stock_code(industry["代码"])
    daily["日期"] = pd.to_datetime(daily["日期"], errors="coerce")
    if as_of:
        daily = daily[daily["日期"] <= pd.to_datetime(as_of)]

    for column in ["收盘", "涨跌幅", "成交额"]:
        daily[column] = pd.to_numeric(daily[column], errors="coerce")

    daily = daily.dropna(subset=["代码", "日期", "收盘", "涨跌幅"])
    merged = pd.merge(daily, industry[["代码", "名称", "行业名称"]], on="代码", how="inner")
    merged = merged[merged["代码"].str.match(r"^\d{6}$", na=False)].copy()
    merged = append_market_universe_columns(merged)
    if merged.empty:
        raise ValueError("股票日线与板块映射合并后为空，请检查数据库。")
    return merged


def _build_sector_daily(merged: pd.DataFrame) -> pd.DataFrame:
    grouped = merged.groupby(["日期", "行业名称"], as_index=False).agg(
        板块日涨幅=("涨跌幅", "mean"),
        上涨占比=("涨跌幅", lambda s: float((s > 0).mean())),
        涨停数=("涨跌幅", lambda s: int((s >= 9.8).sum())),
        成交额=("成交额", "sum"),
        成分数=("代码", "nunique"),
    )
    grouped["日期"] = pd.to_datetime(grouped["日期"])
    return grouped.sort_values(["日期", "行业名称"]).reset_index(drop=True)


def _unique_stock_daily(merged: pd.DataFrame) -> pd.DataFrame:
    return merged.drop_duplicates(["日期", "代码"]).copy()


def _build_market_benchmark(merged: pd.DataFrame) -> pd.Series:
    unique_daily = _unique_stock_daily(merged)
    market_returns = unique_daily.groupby("日期")["涨跌幅"].mean().sort_index().fillna(0.0)
    return (1.0 + market_returns / 100.0).cumprod() * 1000.0


def _build_index_reference_daily(merged: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("全A等权指数", None, 9.8),
        ("沪深主板指数", "沪深主板", 9.8),
        ("创业板指数", "创业板", 19.5),
        ("科创板指数", "科创板", 19.5),
    ]
    unique_daily = _unique_stock_daily(merged)
    records: list[pd.DataFrame] = []
    for label, segment, limit_up_threshold in specs:
        subset = unique_daily.copy() if segment is None else unique_daily[unique_daily["证券板块"] == segment].copy()
        if subset.empty:
            continue
        grouped = subset.groupby("日期", as_index=False).agg(
            板块日涨幅=("涨跌幅", "mean"),
            上涨占比=("涨跌幅", lambda s: float((s > 0).mean())),
            涨停数=("涨跌幅", lambda s: int((s >= limit_up_threshold).sum())),
            成交额=("成交额", "sum"),
            成分数=("代码", "nunique"),
        )
        grouped["行业名称"] = label
        records.append(grouped)
    if not records:
        return pd.DataFrame(columns=["日期", "行业名称", "板块日涨幅", "上涨占比", "涨停数", "成交额", "成分数"])
    result = pd.concat(records, ignore_index=True)
    result["日期"] = pd.to_datetime(result["日期"])
    return result[["日期", "行业名称", "板块日涨幅", "上涨占比", "涨停数", "成交额", "成分数"]].sort_values(
        ["日期", "行业名称"]
    )


def _build_leaders(merged: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    recommendable = merged[merged["可推荐龙头"]].copy() if "可推荐龙头" in merged.columns else merged.copy()
    latest = recommendable[recommendable["日期"] == as_of].copy()
    if latest.empty:
        return pd.DataFrame(columns=["行业名称", "类型", "排名", "股票名称", "代码", "数值", "展示"])
    close_pivot = recommendable.pivot_table(index="日期", columns="代码", values="收盘", aggfunc="last").sort_index()
    latest["3日涨幅"] = latest["代码"].map(_safe_pct_change(close_pivot, 3)).fillna(0.0)
    latest["5日涨幅"] = latest["代码"].map(_safe_pct_change(close_pivot, 5)).fillna(0.0)

    records: list[dict[str, Any]] = []
    leader_specs = [
        ("1日先锋", "涨跌幅", "%"),
        ("3日动能", "3日涨幅", "%"),
        ("5日趋势", "5日涨幅", "%"),
        ("核心中军", "成交额", "亿"),
    ]
    for sector, group in latest.groupby("行业名称"):
        for leader_type, metric, unit in leader_specs:
            top = group.sort_values(metric, ascending=False).head(3)
            for rank, (_, row) in enumerate(top.iterrows(), start=1):
                value = float(row[metric]) if pd.notna(row[metric]) else 0.0
                display_value = f"{value / 100000000:.1f}亿" if unit == "亿" else f"{value:+.1f}%"
                records.append(
                    {
                        "行业名称": sector,
                        "类型": leader_type,
                        "排名": rank,
                        "股票名称": row["名称"],
                        "代码": row["代码"],
                        "数值": value,
                        "展示": f"{row['名称']} {display_value}",
                    }
                )
    return pd.DataFrame(records)


def _infer_market_state(sector_frame: pd.DataFrame, family_frame: pd.DataFrame | None = None) -> tuple[str, dict[str, Any]]:
    phase_counts = sector_frame["阶段"].value_counts().to_dict()
    positive_share = float((sector_frame["1日涨幅"] > 0).mean())
    median_5d = float(sector_frame["5日涨幅"].median())
    top10 = sector_frame.nlargest(min(10, len(sector_frame)), "活跃分")
    top5_return = float(top10.head(5)["5日涨幅"].mean()) if not top10.empty else 0.0
    leading_count = int(phase_counts.get("领涨", 0))
    improving_count = int(phase_counts.get("修复", 0))
    avg_abs_momentum = float(sector_frame["动量"].abs().mean())

    if median_5d < -1.0 and positive_share < 0.42:
        state = "退潮防守"
    elif leading_count >= max(4, len(sector_frame) * 0.08) and top5_return > 1.5:
        state = "主线抱团"
    elif avg_abs_momentum > 2.0 or improving_count >= max(5, len(sector_frame) * 0.12):
        state = "快速轮动"
    else:
        state = "修复试探"

    summary = {
        "领涨板块数": leading_count,
        "修复板块数": improving_count,
        "走弱板块数": int(phase_counts.get("走弱", 0)),
        "退潮板块数": int(phase_counts.get("退潮", 0)),
        "上涨板块占比": round(positive_share * 100, 1),
        "板块5日涨幅中位数": round(median_5d, 2),
        "Top5平均5日涨幅": round(top5_return, 2),
    }
    if family_frame is not None and not family_frame.empty:
        summary["最强主线"] = str(family_frame.iloc[0]["主线家族"])
        summary["Top3主线共振"] = round(float(family_frame.head(3)["家族共振度"].mean()), 1)
        summary["主线家族数"] = int(len(family_frame))
    return state, summary


def build_rotation_model(
    stock_daily: pd.DataFrame,
    stock_industry: pd.DataFrame,
    *,
    as_of: str | None = None,
    tail_days: int = 20,
    rs_window: int = 20,
    momentum_window: int = 5,
    smooth_window: int = 3,
    include_growth_indices: bool = True,
) -> RotationModel:
    merged = _prepare_inputs(stock_daily, stock_industry, as_of)
    st_count = int(stock_industry["名称"].astype(str).str.upper().str.contains("ST|退", regex=True, na=False).sum())
    recommendable_count = int(merged[merged["可推荐龙头"]]["代码"].nunique()) if "可推荐龙头" in merged.columns else int(merged["代码"].nunique())
    daily_frames = [_build_sector_daily(merged)]
    if include_growth_indices:
        daily_frames.append(_build_index_reference_daily(merged))
    sector_daily = pd.concat([frame for frame in daily_frames if not frame.empty], ignore_index=True)

    returns = (
        sector_daily.pivot(index="日期", columns="行业名称", values="板块日涨幅")
        .sort_index()
        .fillna(0.0)
    )
    sector_index = (1.0 + returns / 100.0).cumprod() * 1000.0
    benchmark = _build_market_benchmark(merged).reindex(sector_index.index).ffill().bfill()

    min_periods = max(5, min(rs_window // 2, len(sector_index)))
    rs = sector_index.div(benchmark, axis=0)
    strength = ((rs / rs.rolling(rs_window, min_periods=min_periods).mean()) - 1.0) * 100.0
    strength = strength.rolling(smooth_window, min_periods=1).mean()
    momentum = (strength - strength.shift(momentum_window)).rolling(smooth_window, min_periods=1).mean()

    metric_dates = strength.dropna(how="all").index.intersection(momentum.dropna(how="all").index)
    if metric_dates.empty:
        raise ValueError("历史数据不足，无法计算轮动指标。建议至少准备 25 个交易日。")

    as_of_ts = pd.to_datetime(as_of) if as_of else metric_dates.max()
    if as_of_ts not in metric_dates:
        as_of_ts = metric_dates[metric_dates <= as_of_ts].max()
    benchmark_stock_count = int(_unique_stock_daily(merged).loc[lambda df: df["日期"] == as_of_ts, "代码"].nunique())

    latest_strength = strength.loc[as_of_ts].fillna(0.0)
    latest_momentum = momentum.loc[as_of_ts].fillna(0.0)
    prev_idx = max(0, list(strength.index).index(as_of_ts) - 1)
    prev_date = strength.index[prev_idx]
    prev_strength = strength.loc[prev_date].reindex(latest_strength.index).fillna(0.0)
    prev_momentum = momentum.loc[prev_date].reindex(latest_momentum.index).fillna(0.0)

    latest_sector_stats = sector_daily[sector_daily["日期"] == as_of_ts].set_index("行业名称")
    turnover_pivot = sector_daily.pivot(index="日期", columns="行业名称", values="成交额").sort_index().fillna(0.0).infer_objects(copy=False)
    turnover_base = turnover_pivot.rolling(10, min_periods=3).mean()
    turnover_chg = ((turnover_pivot.loc[as_of_ts] / turnover_base.loc[as_of_ts]) - 1.0).replace([np.inf, -np.inf], 0.0)

    sector_frame = pd.DataFrame(
        {
            "行业名称": latest_strength.index,
            "相对强弱": latest_strength.values,
            "动量": latest_momentum.reindex(latest_strength.index).values,
            "1日涨幅": returns.loc[as_of_ts].reindex(latest_strength.index).fillna(0.0).values,
            "3日涨幅": _safe_pct_change(sector_index, 3).reindex(latest_strength.index).fillna(0.0).values,
            "5日涨幅": _safe_pct_change(sector_index, 5).reindex(latest_strength.index).fillna(0.0).values,
            "10日涨幅": _safe_pct_change(sector_index, 10).reindex(latest_strength.index).fillna(0.0).values,
            "上涨占比": latest_sector_stats["上涨占比"].reindex(latest_strength.index).fillna(0.0).values,
            "涨停数": pd.to_numeric(latest_sector_stats["涨停数"].reindex(latest_strength.index), errors="coerce").fillna(0).astype(int).values,
            "成交额": pd.to_numeric(latest_sector_stats["成交额"].reindex(latest_strength.index), errors="coerce").fillna(0.0).values,
            "成分数": pd.to_numeric(latest_sector_stats["成分数"].reindex(latest_strength.index), errors="coerce").fillna(0).astype(int).values,
            "成交额变化": turnover_chg.reindex(latest_strength.index).fillna(0.0).values,
        }
    )
    sector_frame["阶段"] = [classify_phase(x, y) for x, y in zip(sector_frame["相对强弱"], sector_frame["动量"])]
    dx = latest_strength - prev_strength
    dy = latest_momentum - prev_momentum
    sector_frame["方向"] = [direction_label(float(dx[s]), float(dy[s])) for s in sector_frame["行业名称"]]
    sector_frame["活跃分"] = (
        _rank_score(sector_frame["5日涨幅"]) * 0.26
        + _rank_score(sector_frame["动量"]) * 0.24
        + _rank_score(sector_frame["相对强弱"]) * 0.18
        + _rank_score(sector_frame["上涨占比"]) * 0.14
        + _rank_score(sector_frame["涨停数"]) * 0.10
        + _rank_score(sector_frame["成交额变化"]) * 0.08
    ).round(1)

    sector_frame, family_frame = enrich_theme_structure(sector_frame)
    sector_frame = sector_frame.sort_values(["活跃分", "5日涨幅"], ascending=False).reset_index(drop=True)
    market_state, summary = _infer_market_state(sector_frame, family_frame)

    trail_dates = list(metric_dates[metric_dates <= as_of_ts])[-tail_days:]
    trail_records: list[dict[str, Any]] = []
    for order, date in enumerate(trail_dates, start=1):
        for sector in latest_strength.index:
            trail_records.append(
                {
                    "日期": pd.to_datetime(date).strftime("%Y-%m-%d"),
                    "行业名称": sector,
                    "相对强弱": float(strength.loc[date, sector]) if pd.notna(strength.loc[date, sector]) else 0.0,
                    "动量": float(momentum.loc[date, sector]) if pd.notna(momentum.loc[date, sector]) else 0.0,
                    "序号": order,
                }
            )
    trail_frame = pd.DataFrame(trail_records)
    leaders_frame = _build_leaders(merged, as_of_ts)

    summary["样本板块数"] = int(len(sector_frame))
    summary["样本股票数"] = int(merged[merged["日期"] == as_of_ts]["代码"].nunique())
    summary["指数基准股票数"] = benchmark_stock_count
    summary["ST样本数"] = st_count
    summary["可推荐非ST数"] = recommendable_count
    summary["指数参考数"] = int(sector_frame["题材层级"].eq("指数参考").sum())

    return RotationModel(
        as_of=pd.to_datetime(as_of_ts).strftime("%Y-%m-%d"),
        sector_frame=sector_frame,
        family_frame=family_frame,
        trail_frame=trail_frame,
        leaders_frame=leaders_frame,
        market_state=market_state,
        summary=summary,
    )
