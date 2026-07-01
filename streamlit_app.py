from __future__ import annotations

import streamlit as st

from rotation_v2.data_loader import available_dates, load_sqlite_data, resolve_db_path
from rotation_v2.freshness import LATEST_MANIFEST_URL, freshness_status, load_remote_latest_manifest
from rotation_v2.metrics import build_rotation_model
from rotation_v2.report import PHASE_COLORS, build_rrg_figure, build_sector_focus_figure, select_sector_view


st.set_page_config(page_title="板块轮动图 V2", layout="wide")


@st.cache_data(show_spinner=False)
def cached_load(db_path: str, db_mtime_ns: int, db_size: int):
    daily, industry, resolved = load_sqlite_data(db_path)
    return daily, industry, str(resolved)


def database_signature(db_path: str) -> tuple[str, int, int]:
    resolved = resolve_db_path(db_path or None)
    stat = resolved.stat()
    return str(resolved.resolve()), stat.st_mtime_ns, stat.st_size


@st.cache_data(show_spinner=False, ttl=300)
def cached_remote_latest_manifest(url: str):
    try:
        return load_remote_latest_manifest(url)
    except Exception:
        return {}


st.title("板块轮动图 V2")
st.caption("收盘后复盘: RRG 强弱动量、主线榜、修复榜、退潮榜、个股穿透。")

with st.sidebar:
    st.header("数据")
    default_path = str(resolve_db_path(None))
    db_path = st.text_input("SQLite 数据库", value=default_path)
    resolved_path, db_mtime_ns, db_size = database_signature(db_path)
    stock_daily, stock_industry, resolved_db = cached_load(resolved_path, db_mtime_ns, db_size)
    dates = available_dates(stock_daily)
    remote_latest = cached_remote_latest_manifest(LATEST_MANIFEST_URL)
    latest_loaded_date = dates[-1]
    remote_latest_date = remote_latest.get("date")
    st.caption(f"当前加载: {latest_loaded_date}")
    if remote_latest_date:
        st.caption(f"GitHub 最新: {remote_latest_date}")
    selected_date = st.selectbox("交易日", dates, index=len(dates) - 1)
    tail_days = st.slider("轨迹回看", 8, 35, 18)

status, freshness_message = freshness_status(latest_loaded_date, remote_latest)
if status == "stale" and freshness_message:
    st.warning(freshness_message)

model = build_rotation_model(stock_daily, stock_industry, as_of=selected_date, tail_days=tail_days)

with st.sidebar:
    st.header("视图")
    density_options = ["精选", "扩展", "全部"]
    if hasattr(st, "segmented_control"):
        density = st.segmented_control("气泡密度", density_options, default="精选")
    else:
        density = st.radio("气泡密度", density_options, index=0, horizontal=True)
    max_sector_map = {"精选": 32, "扩展": 55, "全部": None}
    selected_phases = st.multiselect("阶段", list(PHASE_COLORS.keys()), default=list(PHASE_COLORS.keys()))
    label_limit = st.slider("标签数量", 0, 36, 14)
    focus_options = ["不聚焦"] + model.sector_frame["行业名称"].tolist()
    focus_choice = st.selectbox("聚焦板块", focus_options, index=0)
    focus_sector = None if focus_choice == "不聚焦" else focus_choice

visible_sectors = select_sector_view(
    model.sector_frame,
    phases=selected_phases,
    max_sectors=max_sector_map[density],
    focus_sector=focus_sector,
)

top_cols = st.columns(7)
for col, (key, value) in zip(top_cols, model.summary.items()):
    col.metric(key, value)

st.subheader(f"{model.as_of} | {model.market_state}")
st.caption(f"显示范围: {len(visible_sectors)} / {len(model.sector_frame)} 个板块")
st.plotly_chart(
    build_rrg_figure(
        model,
        label_limit=label_limit,
        phases=selected_phases,
        max_sectors=max_sector_map[density],
        focus_sector=focus_sector,
    ),
    width="stretch",
)

if focus_sector:
    focus_row = model.sector_frame.set_index("行业名称").loc[focus_sector]
    st.subheader(f"聚焦 | {focus_sector}")
    focus_cols = st.columns(7)
    focus_metrics = [
        ("阶段", focus_row["阶段"]),
        ("方向", focus_row["方向"]),
        ("活跃分", f"{focus_row['活跃分']:.1f}"),
        ("1日涨幅", f"{focus_row['1日涨幅']:+.2f}%"),
        ("5日涨幅", f"{focus_row['5日涨幅']:+.2f}%"),
        ("上涨占比", f"{focus_row['上涨占比']:.0%}"),
        ("成交额", f"{focus_row['成交额'] / 100000000:.1f}亿"),
    ]
    for col, (label, value) in zip(focus_cols, focus_metrics):
        col.metric(label, value)

    focus_chart_col, focus_table_col = st.columns([1.35, 1])
    with focus_chart_col:
        st.plotly_chart(build_sector_focus_figure(model, focus_sector), width="stretch")
    with focus_table_col:
        focus_leaders = model.leaders_frame[model.leaders_frame["行业名称"] == focus_sector]
        st.dataframe(focus_leaders, use_container_width=True, height=360)

tab_main, tab_fix, tab_down, tab_leaders, tab_raw = st.tabs(["主线榜", "修复榜", "退潮榜", "个股穿透", "明细"])
with tab_main:
    st.dataframe(
        model.sector_frame.nlargest(30, "活跃分")[
            ["行业名称", "阶段", "方向", "活跃分", "1日涨幅", "3日涨幅", "5日涨幅", "上涨占比", "涨停数"]
        ],
        use_container_width=True,
        height=620,
    )
with tab_fix:
    st.dataframe(
        model.sector_frame[model.sector_frame["阶段"] == "修复"].nlargest(30, "动量")[
            ["行业名称", "方向", "动量", "相对强弱", "3日涨幅", "5日涨幅", "活跃分"]
        ],
        use_container_width=True,
        height=620,
    )
with tab_down:
    st.dataframe(
        model.sector_frame.nsmallest(35, "5日涨幅")[
            ["行业名称", "阶段", "方向", "1日涨幅", "3日涨幅", "5日涨幅", "活跃分"]
        ],
        use_container_width=True,
        height=620,
    )
with tab_leaders:
    st.dataframe(model.leaders_frame, use_container_width=True, height=720)
with tab_raw:
    st.dataframe(model.sector_frame, use_container_width=True, height=720)
