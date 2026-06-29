import unittest

import pandas as pd

from rotation_v2.metrics import build_rotation_model, classify_phase


def make_toy_data():
    dates = pd.date_range("2026-01-01", periods=35, freq="B")
    stock_industry = pd.DataFrame(
        [
            {"代码": "000001", "名称": "强势一号", "行业名称": "AI算力"},
            {"代码": "000002", "名称": "强势二号", "行业名称": "AI算力"},
            {"代码": "000003", "名称": "弱势一号", "行业名称": "传统消费"},
            {"代码": "000004", "名称": "弱势二号", "行业名称": "传统消费"},
        ]
    )

    rows = []
    for i, date in enumerate(dates):
        profiles = {
            "000001": 10 + i * 1.2,
            "000002": 9 + i * 1.0,
            "000003": 30 - i * 0.35,
            "000004": 28 - i * 0.25,
        }
        previous = {
            "000001": 10 + max(i - 1, 0) * 1.2,
            "000002": 9 + max(i - 1, 0) * 1.0,
            "000003": 30 - max(i - 1, 0) * 0.35,
            "000004": 28 - max(i - 1, 0) * 0.25,
        }
        for code, close in profiles.items():
            prev = previous[code]
            pct = 0.0 if i == 0 else (close / prev - 1) * 100
            rows.append(
                {
                    "代码": code,
                    "日期": date.strftime("%Y-%m-%d"),
                    "收盘": close,
                    "涨跌幅": pct,
                    "成交额": 100_000_000 + i * 1_000_000 + int(code[-1]) * 10_000,
                }
            )
    return pd.DataFrame(rows), stock_industry


class RotationMetricTests(unittest.TestCase):
    def test_classify_phase_uses_rrg_quadrants(self):
        self.assertEqual(classify_phase(1.0, 1.0), "领涨")
        self.assertEqual(classify_phase(-1.0, 1.0), "修复")
        self.assertEqual(classify_phase(1.0, -1.0), "走弱")
        self.assertEqual(classify_phase(-1.0, -1.0), "退潮")

    def test_build_rotation_model_returns_snapshot_trails_and_leaders(self):
        stock_daily, stock_industry = make_toy_data()

        model = build_rotation_model(stock_daily, stock_industry, tail_days=12)

        self.assertEqual(model.as_of, "2026-02-18")
        self.assertIn(model.market_state, {"主线抱团", "快速轮动", "修复试探", "退潮防守"})
        self.assertGreaterEqual(len(model.sector_frame), 2)
        self.assertGreaterEqual(len(model.trail_frame), 20)
        self.assertGreaterEqual(len(model.leaders_frame), 8)

        required_sector_cols = {
            "行业名称",
            "相对强弱",
            "动量",
            "1日涨幅",
            "3日涨幅",
            "5日涨幅",
            "活跃分",
            "阶段",
            "方向",
        }
        self.assertTrue(required_sector_cols.issubset(set(model.sector_frame.columns)))

        ai_row = model.sector_frame.set_index("行业名称").loc["AI算力"]
        weak_row = model.sector_frame.set_index("行业名称").loc["传统消费"]
        self.assertGreater(ai_row["5日涨幅"], weak_row["5日涨幅"])
        self.assertIn(ai_row["阶段"], {"领涨", "修复", "走弱", "退潮"})

        leader_types = set(model.leaders_frame["类型"])
        self.assertTrue({"1日先锋", "3日动能", "5日趋势", "核心中军"}.issubset(leader_types))


if __name__ == "__main__":
    unittest.main()
