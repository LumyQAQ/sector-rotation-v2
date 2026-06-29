# 板块轮动图 V2

每日收盘后生成一套 A 股板块轮动复盘图：

- `rotation_report.html`: 可交互 HTML 复盘页
- `rotation_snapshot.png`: 适合发微信/小红书的长图
- `rotation_data.csv`: 当日板块轮动明细
- `rotation_leaders.csv`: 板块内 1 日先锋、3 日动能、5 日趋势、核心中军

## 快速运行

```bash
cd /Users/ziranfeng/Desktop/洪攻略/CMLM/轮动图_v2
python3 run_daily.py
```

默认会优先读取项目根目录里的 `sample_data.db`。如果根目录没有数据库，会自动读取旁边旧版目录里的：

```text
/Users/ziranfeng/Desktop/洪攻略/CMLM/轮动图/sample_data.db
```

也可以手动指定数据库和交易日：

```bash
python3 run_daily.py \
  --db /Users/ziranfeng/Desktop/洪攻略/CMLM/轮动图/sample_data.db \
  --date 2026-04-30 \
  --out outputs
```

## 打开交互看板

```bash
streamlit run streamlit_app.py
```

## 图形口径

- X 轴：相对强弱，板块指数相对全市场等权基准的 20 日强弱偏离。
- Y 轴：动量，强弱指标相对 5 日前的变化。
- 阶段：
  - `领涨`: 强弱为正，动量为正。
  - `修复`: 强弱为负，动量为正。
  - `走弱`: 强弱为正，动量为负。
  - `退潮`: 强弱为负，动量为负。
- 活跃分：综合 5 日涨幅、动量、相对强弱、上涨占比、涨停数、成交额变化。

## 目录结构

```text
rotation_v2/
  data_loader.py   # 读取 SQLite 数据
  metrics.py       # 轮动指标、市场状态、个股穿透
  report.py        # Plotly HTML 交互报告
  snapshot.py      # Matplotlib 长图快照
run_daily.py       # 每日一键生成
streamlit_app.py   # 交互看板
tests/             # 核心指标测试
```

## 数据要求

SQLite 里需要两张表：

- `stock_daily`: `代码`, `日期`, `收盘`, `涨跌幅`, `成交额`
- `stock_industry`: `代码`, `名称`, `行业名称`

旧版 `sample_data.db` 已满足这些字段。

## GitHub Topics

建议给仓库添加这些主题：

```text
a-share, sector-rotation, rrg, streamlit, plotly, quantitative-finance, market-dashboard
```
