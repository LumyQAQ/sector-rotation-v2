from __future__ import annotations

import streamlit as st

from rotation_v2.data_loader import available_dates, load_sqlite_data, resolve_db_path
from rotation_v2.metrics import build_rotation_model
from rotation_v2.report import build_rrg_figure


st.set_page_config(page_title="板块轮动图 V2", layout="wide")


@st.cache_data(show_spinner=False)
def cached_load(db_path: str):
    daily, industry, resolved = load_sqlite_data(db_path or None)
    return daily, industry, str(resolved)


st.title("板块轮动图 V2")
st.caption("收盘后复盘: RRG 强弱动量、主线榜、修复榜、退潮榜、个股穿透。")

with st.sidebar:
    st.header("数据")
    default_path = str(resolve_db_path(None))
    db_path = st.text_input("SQLite 数据库", value=default_path)
    stock_daily, stock_industry, resolved_db = cached_load(db_path)
    dates = available_dates(stock_daily)
    selected_date = st.selectbox("交易日", dates, index=len(dates) - 1)
    tail_days = st.slider("轨迹回看", 8, 35, 18)

model = build_rotation_model(stock_daily, stock_industry, as_of=selected_date, tail_days=tail_days)

top_cols = st.columns(7)
for col, (key, value) in zip(top_cols, model.summary.items()):
    col.metric(key, value)

st.subheader(f"{model.as_of} | {model.market_state}")
st.plotly_chart(build_rrg_figure(model), use_container_width=True)

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
