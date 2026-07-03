from __future__ import annotations

import os
from pathlib import Path

_cache_root = Path(os.environ.get("TMPDIR", "/tmp")) / "rotation_v2_matplotlib"
_cache_root.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_cache_root))
os.environ.setdefault("XDG_CACHE_HOME", str(_cache_root))

import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from .metrics import RotationModel


def configure_chinese_font() -> None:
    preferred = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Songti SC",
        "Arial Unicode MS",
        "Microsoft YaHei",
        "Noto Sans CJK SC",
    ]
    available = {font.name for font in fm.fontManager.ttflist}
    for name in preferred:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def _format_pct(value: float) -> str:
    return f"{value:+.1f}%"


def _board_lines(title: str, df: pd.DataFrame, value_col: str, n: int = 8) -> list[str]:
    lines = [title]
    if df.empty:
        return lines + ["暂无"]
    for i, (_, row) in enumerate(df.head(n).iterrows(), start=1):
        value = row[value_col]
        name = row["行业名称"]
        phase = row.get("阶段", "")
        status = row.get("题材地位", "")
        if isinstance(value, (int, float, np.floating)):
            value_text = _format_pct(float(value)) if "涨幅" in value_col or value_col in {"动量", "相对强弱"} else f"{value:.1f}"
        else:
            value_text = str(value)
        lines.append(f"{i:02d}. {name}  {value_text}  {phase}  {status}")
    return lines


def _draw_text_panel(ax, lines: list[str], accent: str) -> None:
    ax.set_axis_off()
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, color="white", ec="#e5e7eb", lw=1))
    for i, line in enumerate(lines):
        if i == 0:
            ax.text(0.04, 0.92, line, transform=ax.transAxes, fontsize=15, fontweight="bold", color=accent, va="top")
        else:
            ax.text(0.04, 0.92 - i * 0.095, line, transform=ax.transAxes, fontsize=10.5, color="#111827", va="top")


def render_snapshot_png(model: RotationModel, out_path: str | Path, label_limit: int = 26) -> Path:
    configure_chinese_font()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    df = model.sector_frame.copy()
    labels = set(df.nlargest(min(label_limit, len(df)), "活跃分")["行业名称"])
    cmap = LinearSegmentedColormap.from_list("cn_red_green", ["#009966", "#f1f5f9", "#d62728"])
    vmax = max(1.0, float(df["5日涨幅"].abs().quantile(0.95)))
    norm = TwoSlopeNorm(vcenter=0, vmin=-vmax, vmax=vmax)

    fig = plt.figure(figsize=(14, 18), dpi=150, facecolor="#f7f8fb")
    grid = fig.add_gridspec(12, 12, left=0.045, right=0.97, top=0.95, bottom=0.04, hspace=0.55, wspace=0.45)

    title_ax = fig.add_subplot(grid[0:1, :])
    title_ax.set_axis_off()
    title_ax.text(0, 0.72, f"{model.as_of} 板块轮动日报", fontsize=29, fontweight="bold", color="#111827")
    title_ax.text(0, 0.22, "RRG 强弱动量 + 主线家族 + 个股穿透", fontsize=13, color="#6b7280")
    title_ax.text(0.83, 0.62, model.market_state, fontsize=18, fontweight="bold", color="white",
                  bbox=dict(boxstyle="round,pad=0.42,rounding_size=0.08", fc="#111827", ec="#111827"))

    scatter_ax = fig.add_subplot(grid[1:8, 0:8])
    scatter_ax.set_facecolor("white")
    scatter_ax.axhline(0, color="#9ca3af", lw=1)
    scatter_ax.axvline(0, color="#9ca3af", lw=1)
    sizes = np.clip(df["活跃分"].to_numpy(), 8, 100) * 8
    scatter = scatter_ax.scatter(
        df["相对强弱"],
        df["动量"],
        s=sizes,
        c=df["5日涨幅"],
        cmap=cmap,
        norm=norm,
        alpha=0.86,
        edgecolors="white",
        linewidths=0.8,
    )
    for row in df.itertuples(index=False):
        if row.行业名称 in labels:
            scatter_ax.text(row.相对强弱, row.动量, row.行业名称, fontsize=8.2, color="#111827")
    scatter_ax.set_title("板块轮动地图", loc="left", fontsize=18, fontweight="bold", pad=12)
    scatter_ax.set_xlabel("相对强弱: 越右越强")
    scatter_ax.set_ylabel("动量: 越上越在加速")
    scatter_ax.grid(color="#eef2f7", linewidth=0.8)
    scatter_ax.text(0.98, 0.96, "领涨", transform=scatter_ax.transAxes, ha="right", va="top", color="#d62728", fontsize=15, fontweight="bold")
    scatter_ax.text(0.02, 0.96, "修复", transform=scatter_ax.transAxes, ha="left", va="top", color="#ff9f1c", fontsize=15, fontweight="bold")
    scatter_ax.text(0.98, 0.04, "走弱", transform=scatter_ax.transAxes, ha="right", va="bottom", color="#4c78a8", fontsize=15, fontweight="bold")
    scatter_ax.text(0.02, 0.04, "退潮", transform=scatter_ax.transAxes, ha="left", va="bottom", color="#009966", fontsize=15, fontweight="bold")
    cbar = fig.colorbar(scatter, ax=scatter_ax, fraction=0.035, pad=0.015)
    cbar.set_label("5日涨幅")

    summary_ax = fig.add_subplot(grid[1:3, 8:12])
    summary_ax.set_axis_off()
    summary_ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=summary_ax.transAxes, color="white", ec="#e5e7eb", lw=1))
    summary_items = list(model.summary.items())[:7]
    for i, (key, value) in enumerate(summary_items):
        x = 0.05 + (i % 2) * 0.47
        y = 0.86 - (i // 2) * 0.22
        summary_ax.text(x, y, str(key), transform=summary_ax.transAxes, fontsize=9.5, color="#6b7280")
        summary_ax.text(x, y - 0.1, str(value), transform=summary_ax.transAxes, fontsize=16, fontweight="bold", color="#111827")

    mainline = df.nlargest(8, "活跃分")
    improving = df[df["阶段"] == "修复"].nlargest(8, "动量")
    declining = df.nsmallest(8, "5日涨幅")
    risk = df[df["阶段"] == "走弱"].nlargest(8, "相对强弱")

    _draw_text_panel(fig.add_subplot(grid[3:6, 8:10]), _board_lines("主线榜", mainline, "活跃分"), "#d62728")
    _draw_text_panel(fig.add_subplot(grid[3:6, 10:12]), _board_lines("修复榜", improving, "动量"), "#ff9f1c")
    _draw_text_panel(fig.add_subplot(grid[6:9, 8:10]), _board_lines("退潮榜", declining, "5日涨幅"), "#009966")
    _draw_text_panel(fig.add_subplot(grid[6:9, 10:12]), _board_lines("高位降温", risk, "相对强弱"), "#4c78a8")

    leaders_ax = fig.add_subplot(grid[8:12, 0:12])
    leaders_ax.set_axis_off()
    leaders_ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=leaders_ax.transAxes, color="white", ec="#e5e7eb", lw=1))
    leaders_ax.text(0.02, 0.92, "强势板块个股穿透", transform=leaders_ax.transAxes, fontsize=18, fontweight="bold", color="#111827")
    top_sectors = df.nlargest(8, "活跃分")["行业名称"].tolist()
    leaders = model.leaders_frame[model.leaders_frame["行业名称"].isin(top_sectors)].copy()
    y = 0.78
    for sector in top_sectors:
        sector_leaders = leaders[leaders["行业名称"] == sector]
        one_day = "、".join(sector_leaders[sector_leaders["类型"] == "1日先锋"].sort_values("排名").head(2)["展示"].astype(str))
        trend = "、".join(sector_leaders[sector_leaders["类型"] == "5日趋势"].sort_values("排名").head(2)["展示"].astype(str))
        core = "、".join(sector_leaders[sector_leaders["类型"] == "核心中军"].sort_values("排名").head(2)["展示"].astype(str))
        text = f"{sector}:  1日 {one_day or '-'}   |   5日 {trend or '-'}   |   中军 {core or '-'}"
        leaders_ax.text(0.03, y, text, transform=leaders_ax.transAxes, fontsize=10.5, color="#111827")
        y -= 0.085

    fig.savefig(out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out
