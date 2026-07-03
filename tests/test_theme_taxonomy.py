import unittest

import pandas as pd

from rotation_v2.theme_taxonomy import classify_theme_family, enrich_theme_structure


class ThemeTaxonomyTests(unittest.TestCase):
    def test_classify_theme_family_uses_existing_sector_names(self):
        self.assertEqual(classify_theme_family("横向通用软件"), "AI数字经济")
        self.assertEqual(classify_theme_family("电池化学品"), "新能源电力")
        self.assertEqual(classify_theme_family("医药生物"), "医药医疗")
        self.assertEqual(classify_theme_family("快递"), "交通物流")
        self.assertEqual(classify_theme_family("家用电器"), "大消费")
        self.assertEqual(classify_theme_family("橡胶助剂"), "资源化工")
        self.assertEqual(classify_theme_family("白银"), "资源化工")
        self.assertEqual(classify_theme_family("动物保健Ⅲ"), "农业养殖")
        self.assertEqual(classify_theme_family("商用载货车"), "汽车机器人")

    def test_enrich_theme_structure_scores_family_resonance(self):
        sectors = pd.DataFrame(
            [
                {
                    "行业名称": "AI算力",
                    "相对强弱": 6.0,
                    "动量": 5.0,
                    "1日涨幅": 4.0,
                    "5日涨幅": 8.0,
                    "上涨占比": 0.9,
                    "涨停数": 2,
                    "成分数": 20,
                    "阶段": "领涨",
                    "活跃分": 86.0,
                },
                {
                    "行业名称": "横向通用软件",
                    "相对强弱": 3.0,
                    "动量": 4.0,
                    "1日涨幅": 2.5,
                    "5日涨幅": 5.0,
                    "上涨占比": 0.8,
                    "涨停数": 1,
                    "成分数": 35,
                    "阶段": "修复",
                    "活跃分": 78.0,
                },
                {
                    "行业名称": "传统消费",
                    "相对强弱": 4.0,
                    "动量": 3.5,
                    "1日涨幅": 4.5,
                    "5日涨幅": 7.0,
                    "上涨占比": 0.4,
                    "涨停数": 0,
                    "成分数": 18,
                    "阶段": "领涨",
                    "活跃分": 76.0,
                },
            ]
        )

        enriched, family_frame = enrich_theme_structure(sectors)
        enriched_by_name = enriched.set_index("行业名称")

        required_columns = {"主线家族", "题材层级", "家族强度", "家族共振度", "家族内排名", "题材地位", "个体活跃分"}
        self.assertTrue(required_columns.issubset(set(enriched.columns)))
        self.assertEqual(enriched_by_name.loc["AI算力", "主线家族"], "AI数字经济")
        self.assertEqual(enriched_by_name.loc["AI算力", "题材地位"], "主线核心")
        self.assertGreater(enriched_by_name.loc["AI算力", "家族共振度"], enriched_by_name.loc["传统消费", "家族共振度"])
        self.assertGreater(enriched_by_name.loc["AI算力", "活跃分"], enriched_by_name.loc["AI算力", "个体活跃分"])
        self.assertIn("AI数字经济", set(family_frame["主线家族"]))
        self.assertGreaterEqual(int(family_frame.set_index("主线家族").loc["AI数字经济", "子题材数"]), 2)

    def test_top_ranked_family_can_mark_core_with_moderate_resonance(self):
        sectors = pd.DataFrame(
            [
                {"行业名称": "家用电器", "相对强弱": 5.0, "动量": 4.0, "1日涨幅": 1.2, "5日涨幅": 5.0, "上涨占比": 0.7, "涨停数": 1, "成分数": 40, "阶段": "领涨", "活跃分": 90.0},
                {"行业名称": "厨卫电器", "相对强弱": 2.0, "动量": -1.0, "1日涨幅": -0.4, "5日涨幅": 3.0, "上涨占比": 0.4, "涨停数": 0, "成分数": 8, "阶段": "走弱", "活跃分": 82.0},
                {"行业名称": "冰洗", "相对强弱": -1.0, "动量": -2.0, "1日涨幅": -0.2, "5日涨幅": 2.0, "上涨占比": 0.5, "涨停数": 0, "成分数": 7, "阶段": "退潮", "活跃分": 75.0},
                {"行业名称": "AI算力", "相对强弱": -2.0, "动量": -2.0, "1日涨幅": -1.0, "5日涨幅": -2.0, "上涨占比": 0.2, "涨停数": 0, "成分数": 20, "阶段": "退潮", "活跃分": 60.0},
            ]
        )

        enriched, family_frame = enrich_theme_structure(sectors)
        consumer_family = family_frame.set_index("主线家族").loc["大消费"]
        consumer_leader = enriched.set_index("行业名称").loc["家用电器"]

        self.assertEqual(int(consumer_family["家族排名"]), 1)
        self.assertGreaterEqual(float(consumer_family["家族共振度"]), 40.0)
        self.assertEqual(consumer_leader["题材地位"], "主线核心")


if __name__ == "__main__":
    unittest.main()
