from types import SimpleNamespace
import unittest

import pandas as pd

from rotation_v2.model_compat import normalize_rotation_model


class ModelCompatTests(unittest.TestCase):
    def test_normalize_rotation_model_adds_family_frame_for_legacy_model(self):
        legacy_model = SimpleNamespace(
            as_of="2026-07-02",
            sector_frame=pd.DataFrame(
                [
                    {
                        "行业名称": "家用电器",
                        "相对强弱": 3.0,
                        "动量": 2.0,
                        "1日涨幅": 1.2,
                        "5日涨幅": 4.0,
                        "上涨占比": 0.7,
                        "涨停数": 1,
                        "成分数": 40,
                        "阶段": "领涨",
                        "活跃分": 82.0,
                    },
                    {
                        "行业名称": "AI算力",
                        "相对强弱": -1.0,
                        "动量": -2.0,
                        "1日涨幅": -0.5,
                        "5日涨幅": -2.0,
                        "上涨占比": 0.3,
                        "涨停数": 0,
                        "成分数": 20,
                        "阶段": "退潮",
                        "活跃分": 45.0,
                    },
                ]
            ),
            trail_frame=pd.DataFrame(),
            leaders_frame=pd.DataFrame(),
            market_state="修复试探",
            summary={},
        )

        model = normalize_rotation_model(legacy_model)

        self.assertTrue(hasattr(model, "family_frame"))
        self.assertIn("主线家族", model.sector_frame.columns)
        self.assertIn("题材地位", model.sector_frame.columns)
        self.assertGreaterEqual(len(model.family_frame), 1)


if __name__ == "__main__":
    unittest.main()
