from __future__ import annotations

from typing import Any

import pandas as pd


INDEX_REFERENCE_NAMES = {"全A等权指数", "沪深主板指数", "创业板指数", "科创板指数"}


FAMILY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("医药医疗", ("医药", "医疗", "生物制品", "血液", "诊断", "医美", "美容医疗")),
    ("新能源电力", ("光伏", "风电", "风力", "电池", "储能", "电网", "输变电", "配电", "电力", "发电", "火电", "蓄电")),
    ("AI数字经济", ("AI", "算力", "人工智能", "软件", "计算机", "IT服务", "数字", "数据", "云", "互联网", "游戏", "传媒", "媒体", "通信", "电信", "门户网站")),
    ("半导体电子", ("半导体", "电子", "元件", "面板", "光学", "消费电子", "印制电路板", "PCB", "芯片")),
    ("汽车机器人", ("汽车", "乘用车", "商用车", "载货车", "底盘", "发动机", "摩托", "机器人")),
    ("高端制造军工", ("军工", "航天", "航空", "航海", "兵装", "机械", "设备", "仪器仪表", "轨交", "重型设备", "楼宇")),
    ("大消费", ("食品", "饮料", "白酒", "啤酒", "家电", "家用电器", "电器", "厨卫", "厨房", "冰洗", "彩电", "卫浴", "家居", "服饰", "纺织", "辅料", "零食", "调味", "宠物", "旅游", "景区", "酒店", "餐饮", "商贸", "零售", "电商", "超市", "贸易", "社会服务", "人力资源", "会展", "连锁", "美容护理", "个护", "洗护", "饰品", "文化用品", "教育出版", "造纸", "用纸", "包装", "肉制品", "粮油")),
    ("地产基建", ("房地产", "地产", "建筑", "建材", "基建", "工程", "水泥", "玻璃", "钢结构")),
    ("资源化工", ("化工", "化学", "石油", "石化", "油气", "油服", "煤", "钢铁", "钢", "有色", "金属", "贵金属", "小金属", "白银", "铜", "镍", "钼", "铅锌", "钛白粉", "磷", "氮肥", "钾肥", "肥", "焦", "纯碱", "玻纤", "橡胶", "助剂", "有机硅", "涤纶", "印染", "涂料", "塑料", "聚氨酯", "改性")),
    ("金融", ("银行", "保险", "证券", "非银", "信托", "金融")),
    ("农业养殖", ("农业", "农林牧渔", "农产品", "养殖", "饲料", "种植", "食用菌", "动保", "动物保健")),
    ("交通物流", ("交通", "运输", "快递", "物流", "航运", "港口", "机场", "公交")),
    ("环保公用", ("环保", "固废", "公用事业")),
)


BROAD_SECTOR_NAMES = {
    "医药生物",
    "计算机",
    "电子",
    "汽车",
    "电力设备",
    "基础化工",
    "机械设备",
    "国防军工",
    "传媒",
    "通信",
    "食品饮料",
    "家用电器",
    "房地产",
    "非银金融",
    "银行Ⅱ",
    "交通运输",
    "环保",
    "农林牧渔",
    "建筑装饰",
    "建筑材料",
    "煤炭",
    "有色金属",
    "钢铁",
    "石油石化",
    "公用事业",
    "社会服务",
    "商贸零售",
    "轻工制造",
    "纺织服饰",
}


def classify_theme_family(sector_name: Any) -> str:
    name = str(sector_name or "").strip()
    if name in INDEX_REFERENCE_NAMES:
        return "市场指数"
    for family, keywords in FAMILY_RULES:
        if any(keyword in name for keyword in keywords):
            return family
    return "其他主题"


def infer_theme_level(sector_name: Any, component_count: Any) -> str:
    name = str(sector_name or "").strip()
    if name in INDEX_REFERENCE_NAMES:
        return "指数参考"
    count = pd.to_numeric(pd.Series([component_count]), errors="coerce").fillna(0).iloc[0]
    if name in BROAD_SECTOR_NAMES or count >= 80:
        return "宽基主线"
    if count <= 5:
        return "微型题材"
    return "细分题材"


def _rank_score(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)
    return (numeric.rank(pct=True) * 100).fillna(0.0)


def _numeric_column(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def build_family_frame(sector_frame: pd.DataFrame) -> pd.DataFrame:
    if sector_frame.empty:
        return pd.DataFrame(
            columns=[
                "主线家族",
                "子题材数",
                "宽基主线数",
                "个体活跃均分",
                "Top3个体活跃均分",
                "5日涨幅均值",
                "涨停数",
                "题材扩散率",
                "成分上涨均值",
                "家族强度",
                "家族共振度",
                "家族排名",
            ]
        )

    records: list[dict[str, Any]] = []
    for family, group in sector_frame.groupby("主线家族", sort=False):
        individual_score = _numeric_column(group, "个体活跃分")
        top3 = individual_score.nlargest(min(3, len(individual_score)))
        up_component_mean = _numeric_column(group, "上涨占比").mean() * 100.0
        active_theme_share = (
            (group["阶段"].isin(["领涨", "修复"]) & (_numeric_column(group, "1日涨幅") > 0)).mean() * 100.0
            if "阶段" in group.columns
            else 0.0
        )
        records.append(
            {
                "主线家族": family,
                "子题材数": int(len(group)),
                "宽基主线数": int((group.get("题材层级") == "宽基主线").sum()) if "题材层级" in group.columns else 0,
                "个体活跃均分": float(individual_score.mean()),
                "Top3个体活跃均分": float(top3.mean()) if not top3.empty else 0.0,
                "5日涨幅均值": float(_numeric_column(group, "5日涨幅").mean()),
                "涨停数": int(_numeric_column(group, "涨停数").sum()),
                "题材扩散率": float(active_theme_share),
                "成分上涨均值": float(up_component_mean),
            }
        )

    family_frame = pd.DataFrame(records)
    family_frame["家族强度"] = (
        family_frame["Top3个体活跃均分"] * 0.50
        + family_frame["个体活跃均分"] * 0.25
        + _rank_score(family_frame["5日涨幅均值"]) * 0.15
        + _rank_score(family_frame["涨停数"]) * 0.10
    ).clip(0, 100).round(1)
    size_factor = (0.65 + family_frame["子题材数"].clip(upper=3) * 0.12).clip(upper=1.0)
    family_frame["家族共振度"] = (
        (family_frame["题材扩散率"] * 0.55 + family_frame["成分上涨均值"] * 0.45) * size_factor
    ).clip(0, 100).round(1)
    family_frame["家族排名"] = family_frame["家族强度"].rank(method="dense", ascending=False).astype(int)
    return family_frame.sort_values(["家族强度", "家族共振度"], ascending=False).reset_index(drop=True)


def _theme_status(row: pd.Series) -> str:
    if row.get("题材层级") == "指数参考":
        return "指数参考"
    individual_score = float(row.get("个体活跃分", 0.0))
    family_strength = float(row.get("家族强度", 0.0))
    family_resonance = float(row.get("家族共振度", 0.0))
    family_rank = int(row.get("家族排名", 99))
    within_rank = int(row.get("家族内排名", 99))
    phase = str(row.get("阶段", ""))
    momentum = float(row.get("动量", 0.0))
    five_day = float(row.get("5日涨幅", 0.0))

    if family_rank <= 3 and family_strength >= 75 and family_resonance >= 40 and within_rank <= 3 and individual_score >= 75:
        return "主线核心"
    if family_rank <= 5 and family_strength >= 66 and family_resonance >= 38 and within_rank <= 8:
        return "主线扩散"
    if individual_score >= 78 and (family_resonance < 38 or family_rank > 6):
        return "独立异动"
    if phase == "修复" and momentum > 0:
        return "修复观察"
    if phase == "走弱":
        return "高位降温"
    if phase == "退潮" or five_day <= -3:
        return "退潮防守"
    return "轮动跟随"


def enrich_theme_structure(sector_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if sector_frame.empty:
        family_frame = build_family_frame(sector_frame.copy())
        return sector_frame.copy(), family_frame

    enriched = sector_frame.copy()
    enriched["主线家族"] = enriched["行业名称"].map(classify_theme_family)
    enriched["题材层级"] = [
        infer_theme_level(name, count)
        for name, count in zip(enriched["行业名称"], _numeric_column(enriched, "成分数"))
    ]
    enriched["个体活跃分"] = _numeric_column(enriched, "活跃分")

    family_frame = build_family_frame(enriched)
    family_metrics = family_frame.set_index("主线家族")[["家族强度", "家族共振度", "家族排名"]]
    enriched = enriched.join(family_metrics, on="主线家族")
    enriched[["家族强度", "家族共振度", "家族排名"]] = enriched[["家族强度", "家族共振度", "家族排名"]].fillna(
        {"家族强度": 50.0, "家族共振度": 0.0, "家族排名": 99}
    )
    enriched["家族内排名"] = (
        enriched.groupby("主线家族")["个体活跃分"].rank(method="first", ascending=False).astype(int)
    )
    enriched["题材地位"] = enriched.apply(_theme_status, axis=1)

    status_bonus = enriched["题材地位"].map({"主线核心": 3.0, "主线扩散": 1.5, "独立异动": -2.0}).fillna(0.0)
    enriched["活跃分"] = (
        enriched["个体活跃分"] * 0.72
        + enriched["家族强度"] * 0.18
        + enriched["家族共振度"] * 0.10
        + status_bonus
    ).clip(0, 100).round(1)

    return enriched, family_frame
