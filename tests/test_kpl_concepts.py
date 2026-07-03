import tempfile
import unittest
from pathlib import Path

import pandas as pd

from rotation_v2.kpl_concepts import build_kpl_concept_mapping, build_kpl_concept_model
from tests.test_metrics import make_universe_data


class KplConceptTests(unittest.TestCase):
    def _write_concept_csv(self) -> Path:
        rows = [
            {"concept_order": 1, "concept_name": "AI硬件", "stock_seq": 1, "stock_name": "主板核心"},
            {"concept_order": 1, "concept_name": "AI硬件", "stock_seq": 2, "stock_name": "创业样本"},
            {"concept_order": 2, "concept_name": "半导体设备", "stock_seq": 1, "stock_name": "科创样本"},
            {"concept_order": 3, "concept_name": "噪声概念", "stock_seq": 1, "stock_name": "*ST噪声"},
            {"concept_order": 4, "concept_name": "未匹配概念", "stock_seq": 1, "stock_name": "不存在股票"},
        ]
        temp = tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8-sig", delete=False)
        pd.DataFrame(rows).to_csv(temp.name, index=False)
        temp.close()
        return Path(temp.name)

    def test_build_kpl_concept_mapping_matches_stock_names_to_codes(self):
        _stock_daily, stock_industry = make_universe_data()
        concept_csv = self._write_concept_csv()

        mapping, stats = build_kpl_concept_mapping(stock_industry, concept_csv)

        self.assertEqual(stats["概念池概念数"], 4)
        self.assertEqual(stats["概念池股票数"], 5)
        self.assertEqual(stats["概念匹配股票数"], 4)
        self.assertEqual(set(mapping["行业名称"]), {"AI硬件", "半导体设备", "噪声概念"})
        self.assertIn("300001", set(mapping["代码"].astype(str).str.zfill(6)))
        self.assertIn("688001", set(mapping["代码"].astype(str).str.zfill(6)))

    def test_build_kpl_concept_model_uses_concepts_without_growth_indices(self):
        stock_daily, stock_industry = make_universe_data()
        concept_csv = self._write_concept_csv()

        model = build_kpl_concept_model(stock_daily, stock_industry, concept_csv, tail_days=12)

        sectors = set(model.sector_frame["行业名称"])
        self.assertIn("AI硬件", sectors)
        self.assertIn("半导体设备", sectors)
        self.assertNotIn("创业板指数", sectors)
        self.assertNotIn("科创板指数", sectors)
        self.assertGreaterEqual(model.summary["概念池概念数"], 4)
        self.assertGreaterEqual(model.summary["概念匹配股票数"], 4)
        recommended_names = set(model.leaders_frame["股票名称"].astype(str))
        self.assertNotIn("*ST噪声", recommended_names)


if __name__ == "__main__":
    unittest.main()
