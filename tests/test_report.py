import unittest

import pandas as pd

from rotation_v2.metrics import build_rotation_model
from rotation_v2.report import build_sector_focus_figure, select_sector_view
from tests.test_metrics import make_toy_data


class RotationReportTests(unittest.TestCase):
    def test_select_sector_view_keeps_focus_sector_outside_top_n(self):
        sectors = pd.DataFrame(
            [
                {"行业名称": "AI算力", "阶段": "领涨", "活跃分": 95.0},
                {"行业名称": "创新药", "阶段": "修复", "活跃分": 88.0},
                {"行业名称": "机器人", "阶段": "领涨", "活跃分": 76.0},
                {"行业名称": "传统消费", "阶段": "退潮", "活跃分": 12.0},
            ]
        )

        view = select_sector_view(sectors, max_sectors=2, focus_sector="传统消费")

        self.assertEqual(set(view["行业名称"]), {"AI算力", "创新药", "传统消费"})
        self.assertEqual(view.iloc[0]["行业名称"], "传统消费")

    def test_build_sector_focus_figure_only_uses_selected_sector_trail(self):
        stock_daily, stock_industry = make_toy_data()
        model = build_rotation_model(stock_daily, stock_industry, tail_days=12)

        fig = build_sector_focus_figure(model, "AI算力")

        self.assertIn("AI算力", fig.layout.title.text)
        self.assertEqual(len(fig.data), 2)
        self.assertEqual({trace.name for trace in fig.data}, {"相对强弱", "动量"})
        for trace in fig.data:
            self.assertEqual(len(trace.x), 12)


if __name__ == "__main__":
    unittest.main()
