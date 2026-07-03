from __future__ import annotations

import inspect
from dataclasses import replace

import streamlit as st

from rotation_v2.data_loader import available_dates, load_sqlite_data, resolve_db_path
from rotation_v2.freshness import LATEST_MANIFEST_URL, freshness_status, load_remote_latest_manifest
from rotation_v2.kpl_concepts import build_kpl_concept_model, resolve_kpl_concept_path
from rotation_v2.metrics import build_rotation_model
from rotation_v2.model_compat import normalize_rotation_model
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
st.caption("收盘后复盘: 行业板块轮动、开盘啦炒作概念轮动、RRG 强弱动量、个股穿透。")

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
    st.header("观察视角")
    view_mode = st.radio("视角", ["行业板块轮动", "开盘啦概念轮动"], horizontal=True)
    concept_path = None
    if view_mode == "开盘啦概念轮动":
        try:
            concept_default_path = str(resolve_kpl_concept_path(None))
        except FileNotFoundError:
            concept_default_path = ""
        concept_path = st.text_input("开盘啦概念池", value=concept_default_path)

status, freshness_message = freshness_status(latest_loaded_date, remote_latest)
if status == "stale" and freshness_message:
    st.warning(freshness_message)

if view_mode == "开盘啦概念轮动":
    if not concept_path:
        st.error("找不到开盘啦概念池 concept_stock_map.csv。")
        st.stop()
    model = normalize_rotation_model(
        build_kpl_concept_model(stock_daily, stock_industry, concept_path, as_of=selected_date, tail_days=tail_days)
    )
    object_label = "概念"
    family_label = "概念家族"
    focus_label = "聚焦概念"
    main_tab_label = "概念热度榜"
else:
    model = normalize_rotation_model(build_rotation_model(stock_daily, stock_industry, as_of=selected_date, tail_days=tail_days))
    object_label = "板块"
    family_label = "主线家族"
    focus_label = "聚焦板块"
    main_tab_label = "主线榜"

name_column_label = f"{object_label}名称"


def display_columns(frame, columns):
    available = [column for column in columns if column in frame.columns]
    return frame.loc[:, available].rename(columns={"行业名称": name_column_label, "主线家族": family_label})


def helper_accepts_family(helper) -> bool:
    return "families" in inspect.signature(helper).parameters


def filter_by_family(frame, families):
    if families is None or "主线家族" not in frame.columns:
        return frame
    family_set = {family for family in families if family}
    return frame[frame["主线家族"].isin(family_set)].copy() if family_set else frame.iloc[0:0].copy()


def select_sector_view_safe(frame, *, phases, families, max_sectors, focus_sector):
    if helper_accepts_family(select_sector_view):
        return select_sector_view(
            frame,
            phases=phases,
            families=families,
            max_sectors=max_sectors,
            focus_sector=focus_sector,
        )
    return select_sector_view(
        filter_by_family(frame, families),
        phases=phases,
        max_sectors=max_sectors,
        focus_sector=focus_sector,
    )


def build_rrg_figure_safe(model, *, label_limit, phases, families, max_sectors, focus_sector):
    if helper_accepts_family(build_rrg_figure):
        return build_rrg_figure(
            model,
            label_limit=label_limit,
            phases=phases,
            families=families,
            max_sectors=max_sectors,
            focus_sector=focus_sector,
        )
    filtered_model = model
    if families is not None:
        sector_frame = filter_by_family(model.sector_frame, families)
        sector_names = set(sector_frame["行业名称"]) if "行业名称" in sector_frame.columns else set()
        trail_frame = model.trail_frame
        if "行业名称" in trail_frame.columns:
            trail_frame = trail_frame[trail_frame["行业名称"].isin(sector_names)].copy()
        filtered_model = replace(model, sector_frame=sector_frame, trail_frame=trail_frame)
    return build_rrg_figure(
        filtered_model,
        label_limit=label_limit,
        phases=phases,
        max_sectors=max_sectors,
        focus_sector=focus_sector,
    )


with st.sidebar:
    st.header("口径")
    if view_mode == "开盘啦概念轮动":
        st.caption(f"概念池概念: {model.summary.get('概念池概念数', 0)} 个")
        st.caption(f"匹配股票: {model.summary.get('概念匹配股票数', 0)} 只")
        st.caption("同一股票可属于多个炒作概念")
    else:
        st.caption("指数参考: 全A等权 / 沪深主板 / 创业板 / 科创板")
        st.caption(f"全A基准股票: {model.summary.get('指数基准股票数', 0)} 只")
    st.caption(f"轮动指标包含 ST 样本: {model.summary.get('ST样本数', 0)} 只")
    st.caption(f"个股穿透排除 ST 后: {model.summary.get('可推荐非ST数', 0)} 只")
    st.header("视图")
    density_options = ["精选", "扩展", "全部"]
    if hasattr(st, "segmented_control"):
        density = st.segmented_control("气泡密度", density_options, default="精选")
    else:
        density = st.radio("气泡密度", density_options, index=0, horizontal=True)
    max_sector_map = {"精选": 32, "扩展": 55, "全部": None}
    selected_phases = st.multiselect("阶段", list(PHASE_COLORS.keys()), default=list(PHASE_COLORS.keys()))
    family_options = model.family_frame["主线家族"].tolist()
    family_choice = st.selectbox(family_label, [f"全部{family_label}"] + family_options, index=0)
    selected_families = None if family_choice == f"全部{family_label}" else [family_choice]
    label_limit = st.slider("标签数量", 0, 36, 14)
    focus_universe = model.sector_frame
    if selected_families:
        focus_universe = focus_universe[focus_universe["主线家族"].isin(selected_families)]
    focus_options = ["不聚焦"] + focus_universe["行业名称"].tolist()
    focus_choice = st.selectbox(focus_label, focus_options, index=0)
    focus_sector = None if focus_choice == "不聚焦" else focus_choice

visible_sectors = select_sector_view_safe(
    model.sector_frame,
    phases=selected_phases,
    families=selected_families,
    max_sectors=max_sector_map[density],
    focus_sector=focus_sector,
)

top_cols = st.columns(7)
for col, (key, value) in zip(top_cols, model.summary.items()):
    col.metric(key, value)

st.subheader(f"{view_mode} | {model.as_of} | {model.market_state}")
family_caption = f"全部{family_label}" if selected_families is None else selected_families[0]
st.caption(f"显示范围: {len(visible_sectors)} / {len(model.sector_frame)} 个{object_label} | {family_label}: {family_caption}")
rrg_figure = build_rrg_figure_safe(
    model,
    label_limit=label_limit,
    phases=selected_phases,
    families=selected_families,
    max_sectors=max_sector_map[density],
    focus_sector=focus_sector,
)
rrg_figure.update_layout(title=f"{model.as_of} {object_label}轮动地图 | {model.market_state}")
st.plotly_chart(rrg_figure, width="stretch")

if focus_sector:
    focus_row = model.sector_frame.set_index("行业名称").loc[focus_sector]
    st.subheader(f"{focus_label} | {focus_sector}")
    focus_cols = st.columns(8)
    focus_metrics = [
        ("主线", focus_row["主线家族"]),
        ("地位", focus_row["题材地位"]),
        ("阶段", focus_row["阶段"]),
        ("方向", focus_row["方向"]),
        ("活跃分", f"{focus_row['活跃分']:.1f}"),
        ("5日涨幅", f"{focus_row['5日涨幅']:+.2f}%"),
        ("家族强度", f"{focus_row['家族强度']:.1f}"),
        ("家族共振", f"{focus_row['家族共振度']:.1f}"),
        ("成交额", f"{focus_row['成交额'] / 100000000:.1f}亿"),
    ]
    for col, (label, value) in zip(focus_cols, focus_metrics):
        col.metric(label, value)

    focus_chart_col, focus_table_col = st.columns([1.35, 1])
    with focus_chart_col:
        st.plotly_chart(build_sector_focus_figure(model, focus_sector), width="stretch")
    with focus_table_col:
        focus_leaders = model.leaders_frame[model.leaders_frame["行业名称"] == focus_sector]
        st.dataframe(display_columns(focus_leaders, ["行业名称", "类型", "排名", "股票名称", "代码", "展示"]), use_container_width=True, height=360)

tab_family, tab_main, tab_fix, tab_down, tab_leaders, tab_raw = st.tabs([family_label, main_tab_label, "修复榜", "退潮榜", "个股穿透", "明细"])
with tab_family:
    st.dataframe(
        model.family_frame[
            ["主线家族", "家族排名", "家族强度", "家族共振度", "子题材数", "宽基主线数", "Top3个体活跃均分", "5日涨幅均值", "涨停数"]
        ].rename(columns={"主线家族": family_label}),
        use_container_width=True,
        height=560,
    )
with tab_main:
    st.dataframe(
        display_columns(
            model.sector_frame.nlargest(30, "活跃分"),
            ["主线家族", "行业名称", "题材地位", "题材层级", "阶段", "方向", "活跃分", "个体活跃分", "家族强度", "家族共振度", "1日涨幅", "3日涨幅", "5日涨幅", "上涨占比", "涨停数"],
        ),
        use_container_width=True,
        height=620,
    )
with tab_fix:
    st.dataframe(
        display_columns(
            model.sector_frame[model.sector_frame["阶段"] == "修复"].nlargest(30, "动量"),
            ["主线家族", "行业名称", "题材地位", "方向", "动量", "相对强弱", "3日涨幅", "5日涨幅", "活跃分"],
        ),
        use_container_width=True,
        height=620,
    )
with tab_down:
    st.dataframe(
        display_columns(
            model.sector_frame.nsmallest(35, "5日涨幅"),
            ["主线家族", "行业名称", "题材地位", "阶段", "方向", "1日涨幅", "3日涨幅", "5日涨幅", "活跃分"],
        ),
        use_container_width=True,
        height=620,
    )
with tab_leaders:
    st.dataframe(display_columns(model.leaders_frame, model.leaders_frame.columns.tolist()), use_container_width=True, height=720)
with tab_raw:
    st.dataframe(display_columns(model.sector_frame, model.sector_frame.columns.tolist()), use_container_width=True, height=720)
