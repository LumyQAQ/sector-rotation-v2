# 板块轮动图 V2

每日收盘后生成一套 A 股板块轮动复盘图：

- `rotation_report.html`: 可交互 HTML 复盘页
- `rotation_snapshot.png`: 适合发微信/小红书的长图
- `rotation_data.csv`: 当日板块轮动明细
- `rotation_family.csv`: 主线家族强度、共振度、子题材数量
- `rotation_leaders.csv`: 板块内 1 日先锋、3 日动能、5 日趋势、核心中军

Streamlit 交互页提供两种观察视角：

- `行业板块轮动`: 使用数据库 `stock_industry` 的行业/板块映射，适合观察中期行业风格与资金轮动。
- `开盘啦概念轮动`: 使用 `data/kpl_concept_library/concept_stock_map.csv` 的开盘啦概念池，一只股票可归属多个炒作概念，适合观察短线题材发酵、扩散和退潮。

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
- 主线家族：按现有 `行业名称` 的题材词归并到医药医疗、新能源电力、AI数字经济、半导体电子等家族。
- 题材地位：结合个体活跃分、家族强度、家族共振度和家族内排名，标记为主线核心、主线扩散、独立异动、修复观察、高位降温等。
- 指数参考：基于现有股票行情合成 `全A等权指数`、`沪深主板指数`、`创业板指数`、`科创板指数` 四个参考点；RRG 相对强弱基准使用全 A 唯一股票按日等权收益，确保全部个股进入轮动参考。
- 开盘啦概念轮动：概念池按股票名称匹配行情代码后单独建模，不追加创业板/科创板指数点，避免多概念股票重复加权指数。
- ST 处理：板块/概念轮动指标保留全市场样本，包括名称含 `ST` 或 `退` 的股票，使板块方向参考更完整。
- 个股穿透：1 日先锋、3 日动能、5 日趋势、核心中军推荐中排除 ST 和退市风险股。
- 活跃分：先综合 5 日涨幅、动量、相对强弱、上涨占比、涨停数、成交额变化，再叠加主线家族强度和共振度。

## 目录结构

```text
rotation_v2/
  data_loader.py   # 读取 SQLite 数据
  kpl_concepts.py  # 开盘啦概念池加载、股票名匹配、多标签概念模型
  market_universe.py # ST、沪深主板、创业板、科创板等市场范围识别
  metrics.py       # 轮动指标、市场状态、个股穿透
  theme_taxonomy.py # 主线家族归并、共振度、题材地位
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
