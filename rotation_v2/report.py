from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from .metrics import RotationModel


PHASE_COLORS = {
    "领涨": "#d62728",
    "修复": "#ff9f1c",
    "走弱": "#4c78a8",
    "退潮": "#2ca02c",
}


def select_sector_view(
    sector_frame: pd.DataFrame,
    *,
    phases: list[str] | tuple[str, ...] | None = None,
    max_sectors: int | None = None,
    focus_sector: str | None = None,
) -> pd.DataFrame:
    """Return the sectors shown in the crowded RRG view.

    The focused sector is kept even when it falls outside the phase filter or
    Top N cutoff, because focus should never disappear while the user analyzes it.
    """
    if sector_frame.empty:
        return sector_frame.copy()

    base = sector_frame.copy()
    view = base
    if phases is not None:
        phase_set = {phase for phase in phases if phase}
        view = base[base["阶段"].isin(phase_set)].copy() if phase_set else base.iloc[0:0].copy()

    if max_sectors is not None:
        limit = max(0, int(max_sectors))
        view = view.nlargest(min(limit, len(view)), "活跃分") if limit else view.iloc[0:0].copy()
    else:
        view = view.copy()

    if focus_sector and focus_sector in set(base["行业名称"]):
        focus_row = base[base["行业名称"] == focus_sector]
        view = pd.concat([focus_row, view], ignore_index=True).drop_duplicates("行业名称", keep="first")

    view["_聚焦"] = view["行业名称"].eq(focus_sector)
    sort_columns = ["_聚焦"]
    ascending = [False]
    for column in ["活跃分", "5日涨幅"]:
        if column in view.columns:
            sort_columns.append(column)
            ascending.append(False)
    return view.sort_values(sort_columns, ascending=ascending).drop(columns="_聚焦").reset_index(drop=True)


def _leader_lookup(model: RotationModel) -> dict[str, str]:
    if model.leaders_frame.empty:
        return {}
    lines: dict[str, list[str]] = {}
    for (sector, leader_type), group in model.leaders_frame.groupby(["行业名称", "类型"]):
        leaders = " / ".join(group.sort_values("排名").head(3)["展示"].astype(str))
        lines.setdefault(sector, []).append(f"{leader_type}: {leaders}")
    return {sector: "<br>".join(parts) for sector, parts in lines.items()}


def _rrg_hover_template() -> str:
    return (
        "<b>%{customdata[0]}</b><br>"
        "阶段: %{customdata[1]} / %{customdata[2]}<br>"
        "相对强弱: %{x:.2f} | 动量: %{y:.2f}<br>"
        "活跃分: %{customdata[3]:.1f}<br>"
        "1日: %{customdata[4]:+.2f}% | 3日: %{customdata[5]:+.2f}% | 5日: %{customdata[6]:+.2f}%<br>"
        "上涨占比: %{customdata[7]:.0%} | 涨停数: %{customdata[8]}<br><br>"
        "%{customdata[9]}<extra></extra>"
    )


def _empty_rrg_figure(model: RotationModel) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        text="当前筛选没有可显示的板块",
        showarrow=False,
        font=dict(size=18, color="#6b7280"),
    )
    fig.update_layout(
        title=f"{model.as_of} 板块轮动地图 | {model.market_state}",
        template="plotly_white",
        height=680,
        margin=dict(l=34, r=24, t=70, b=42),
        xaxis=dict(title="相对强弱: 越右越强", gridcolor="#edf2f7"),
        yaxis=dict(title="动量: 越上越在加速", gridcolor="#edf2f7"),
    )
    return fig


def build_rrg_figure(
    model: RotationModel,
    label_limit: int = 18,
    trail_limit: int = 10,
    *,
    phases: list[str] | tuple[str, ...] | None = None,
    max_sectors: int | None = None,
    focus_sector: str | None = None,
) -> go.Figure:
    df = select_sector_view(model.sector_frame, phases=phases, max_sectors=max_sectors, focus_sector=focus_sector)
    if df.empty:
        return _empty_rrg_figure(model)

    leaders = _leader_lookup(model)
    top_labels = set(df.nlargest(min(label_limit, len(df)), "活跃分")["行业名称"])
    if focus_sector:
        top_labels.discard(focus_sector)
    df["标签"] = df["行业名称"].where(df["行业名称"].isin(top_labels), "")
    df["穿透"] = df["行业名称"].map(leaders).fillna("暂无个股穿透")

    fig = go.Figure()
    top_trails = set(df.nlargest(min(trail_limit, len(df)), "活跃分")["行业名称"])
    if focus_sector and focus_sector in set(df["行业名称"]):
        top_trails.add(focus_sector)
    trail_df = model.trail_frame[model.trail_frame["行业名称"].isin(top_trails)].copy()
    for sector, group in trail_df.groupby("行业名称"):
        group = group.sort_values("序号")
        phase = df.loc[df["行业名称"] == sector, "阶段"].iloc[0]
        color = PHASE_COLORS.get(phase, "#666")
        is_focus = bool(focus_sector and sector == focus_sector)
        fig.add_trace(
            go.Scatter(
                x=group["相对强弱"],
                y=group["动量"],
                mode="lines+markers" if is_focus else "lines",
                name=f"{sector}轨迹" if is_focus else None,
                line=dict(color="#111827" if is_focus else color, width=3.4 if is_focus else 1.35),
                marker=dict(size=6, color="#111827") if is_focus else None,
                opacity=0.95 if is_focus else 0.22,
                hoverinfo="skip",
                showlegend=is_focus,
            )
        )

    for phase, group in df.groupby("阶段", sort=False):
        fig.add_trace(
            go.Scatter(
                x=group["相对强弱"],
                y=group["动量"],
                mode="markers+text",
                name=phase,
                text=group["标签"],
                textposition="top center",
                textfont=dict(size=11, color="#1f2937"),
                marker=dict(
                    size=(group["活跃分"].clip(lower=8) / 100 * 30 + 8),
                    color=group["5日涨幅"],
                    colorscale=[[0, "#009966"], [0.48, "#d8dee9"], [0.52, "#f0d5d5"], [1, "#d62728"]],
                    cmid=0,
                    line=dict(width=1, color="#ffffff"),
                    opacity=0.82,
                    showscale=phase == df["阶段"].iloc[0],
                    colorbar=dict(title="5日涨幅%", len=0.72),
                ),
                customdata=group[
                    ["行业名称", "阶段", "方向", "活跃分", "1日涨幅", "3日涨幅", "5日涨幅", "上涨占比", "涨停数", "穿透"]
                ],
                hovertemplate=_rrg_hover_template(),
            )
        )

    if focus_sector and focus_sector in set(df["行业名称"]):
        focus = df[df["行业名称"] == focus_sector].copy()
        fig.add_trace(
            go.Scatter(
                x=focus["相对强弱"],
                y=focus["动量"],
                mode="markers+text",
                name=f"聚焦: {focus_sector}",
                text=focus["行业名称"],
                textposition="middle right",
                textfont=dict(size=14, color="#111827"),
                marker=dict(
                    symbol="diamond",
                    size=(focus["活跃分"].clip(lower=8) / 100 * 34 + 16),
                    color=focus["5日涨幅"],
                    colorscale=[[0, "#009966"], [0.48, "#d8dee9"], [0.52, "#f0d5d5"], [1, "#d62728"]],
                    cmid=0,
                    line=dict(width=3, color="#111827"),
                    showscale=False,
                ),
                customdata=focus[
                    ["行业名称", "阶段", "方向", "活跃分", "1日涨幅", "3日涨幅", "5日涨幅", "上涨占比", "涨停数", "穿透"]
                ],
                hovertemplate=_rrg_hover_template(),
            )
        )

    fig.add_hline(y=0, line_color="#9ca3af", line_width=1)
    fig.add_vline(x=0, line_color="#9ca3af", line_width=1)
    fig.add_annotation(xref="paper", yref="paper", x=0.98, y=0.98, text="领涨", showarrow=False, font=dict(size=16, color="#d62728"))
    fig.add_annotation(xref="paper", yref="paper", x=0.02, y=0.98, text="修复", showarrow=False, font=dict(size=16, color="#ff9f1c"))
    fig.add_annotation(xref="paper", yref="paper", x=0.98, y=0.02, text="走弱", showarrow=False, font=dict(size=16, color="#4c78a8"))
    fig.add_annotation(xref="paper", yref="paper", x=0.02, y=0.02, text="退潮", showarrow=False, font=dict(size=16, color="#2ca02c"))

    fig.update_layout(
        title=f"{model.as_of} 板块轮动地图 | {model.market_state}",
        template="plotly_white",
        height=780,
        margin=dict(l=34, r=24, t=70, b=42),
        xaxis=dict(title="相对强弱: 越右越强", gridcolor="#edf2f7"),
        yaxis=dict(title="动量: 越上越在加速", gridcolor="#edf2f7"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#111827", font_color="white", align="left"),
    )
    return fig


def build_sector_focus_figure(model: RotationModel, sector: str) -> go.Figure:
    trail = model.trail_frame[model.trail_frame["行业名称"] == sector].sort_values("序号")
    fig = go.Figure()
    if trail.empty:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            text=f"{sector} 暂无轨迹数据",
            showarrow=False,
            font=dict(size=16, color="#6b7280"),
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=trail["日期"],
                y=trail["相对强弱"],
                mode="lines+markers",
                name="相对强弱",
                line=dict(color="#d62728", width=2.4),
                marker=dict(size=6),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=trail["日期"],
                y=trail["动量"],
                mode="lines+markers",
                name="动量",
                line=dict(color="#4c78a8", width=2.4),
                marker=dict(size=6),
            )
        )
        fig.add_hline(y=0, line_color="#9ca3af", line_width=1)

    fig.update_layout(
        title=f"{sector} | 强弱与动量轨迹",
        template="plotly_white",
        height=360,
        margin=dict(l=34, r=18, t=56, b=38),
        xaxis=dict(title="日期", gridcolor="#edf2f7"),
        yaxis=dict(title="指标值", gridcolor="#edf2f7"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#111827", font_color="white", align="left"),
    )
    return fig


def _table_html(df: pd.DataFrame, columns: list[str], rows: int = 10) -> str:
    if df.empty:
        return "<p class='muted'>暂无数据</p>"
    view = df.loc[:, columns].head(rows).copy()
    for column in view.columns:
        if pd.api.types.is_float_dtype(view[column]):
            view[column] = view[column].map(lambda x: f"{x:.2f}")
    return view.to_html(index=False, classes="data-table", escape=False)


def write_html_report(model: RotationModel, out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig_html = pio.to_html(build_rrg_figure(model), include_plotlyjs="cdn", full_html=False)

    df = model.sector_frame
    mainline = df.nlargest(12, "活跃分")
    improving = df[df["阶段"] == "修复"].nlargest(10, "动量")
    declining = df.nsmallest(10, "5日涨幅")
    risk = df[df["阶段"] == "走弱"].nlargest(10, "相对强弱")

    summary_cards = "\n".join(
        f"<div class='card'><div class='k'>{key}</div><div class='v'>{value}</div></div>"
        for key, value in model.summary.items()
    )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{model.as_of} 板块轮动日报</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Arial,sans-serif; color:#111827; background:#f7f8fb; }}
    .wrap {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
    .hero {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:18px; }}
    h1 {{ margin:0; font-size:34px; letter-spacing:0; }}
    .state {{ display:inline-block; padding:8px 14px; border-radius:6px; background:#111827; color:white; font-weight:700; }}
    .muted {{ color:#6b7280; }}
    .cards {{ display:grid; grid-template-columns: repeat(7, 1fr); gap:10px; margin: 16px 0 20px; }}
    .card {{ background:white; border:1px solid #e5e7eb; border-radius:8px; padding:12px; }}
    .card .k {{ color:#6b7280; font-size:12px; }}
    .card .v {{ font-size:20px; font-weight:750; margin-top:4px; }}
    .panel {{ background:white; border:1px solid #e5e7eb; border-radius:8px; padding:16px; margin-bottom:18px; }}
    .grid {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:14px; }}
    h2 {{ font-size:18px; margin:0 0 10px; }}
    .data-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    .data-table th {{ text-align:left; color:#4b5563; border-bottom:1px solid #e5e7eb; padding:7px 6px; }}
    .data-table td {{ border-bottom:1px solid #f0f2f5; padding:7px 6px; }}
    @media (max-width: 1000px) {{ .cards,.grid {{ grid-template-columns:1fr 1fr; }} .hero {{ display:block; }} }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div>
        <h1>{model.as_of} 板块轮动日报</h1>
        <p class="muted">盘后自动生成: RRG 强弱动量 + 主线榜 + 个股穿透</p>
      </div>
      <div class="state">{model.market_state}</div>
    </section>
    <section class="cards">{summary_cards}</section>
    <section class="panel">{fig_html}</section>
    <section class="grid">
      <div class="panel"><h2>主线榜</h2>{_table_html(mainline, ["行业名称", "阶段", "方向", "活跃分", "5日涨幅"], 12)}</div>
      <div class="panel"><h2>修复榜</h2>{_table_html(improving, ["行业名称", "方向", "动量", "3日涨幅", "活跃分"], 10)}</div>
      <div class="panel"><h2>退潮榜</h2>{_table_html(declining, ["行业名称", "阶段", "5日涨幅", "1日涨幅", "活跃分"], 10)}</div>
      <div class="panel"><h2>高位降温</h2>{_table_html(risk, ["行业名称", "相对强弱", "动量", "5日涨幅", "方向"], 10)}</div>
    </section>
    <section class="panel">
      <h2>个股穿透</h2>
      {_table_html(model.leaders_frame, ["行业名称", "类型", "排名", "股票名称", "代码", "展示"], 80)}
    </section>
  </main>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out
