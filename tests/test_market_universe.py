import unittest

from rotation_v2.market_universe import board_segment, is_leader_recommendable, is_main_board_tradable, is_st_name


class MarketUniverseTests(unittest.TestCase):
    def test_detects_st_names(self):
        self.assertTrue(is_st_name("*ST铖昌"))
        self.assertTrue(is_st_name("ST亚光"))
        self.assertTrue(is_st_name("退市未来"))
        self.assertFalse(is_st_name("中国卫星"))

    def test_classifies_board_segments(self):
        self.assertEqual(board_segment("300001"), "创业板")
        self.assertEqual(board_segment("301001"), "创业板")
        self.assertEqual(board_segment("688001"), "科创板")
        self.assertEqual(board_segment("920001"), "北交所")
        self.assertEqual(board_segment("600001"), "沪深主板")
        self.assertEqual(board_segment("002001"), "沪深主板")

    def test_main_board_tradable_excludes_st_and_non_main_boards(self):
        self.assertTrue(is_main_board_tradable("600001", "主板票"))
        self.assertTrue(is_main_board_tradable("002001", "深主板票"))
        self.assertFalse(is_main_board_tradable("300001", "创业票"))
        self.assertFalse(is_main_board_tradable("688001", "科创票"))
        self.assertFalse(is_main_board_tradable("600001", "*ST主板"))

    def test_leader_recommendable_only_excludes_st(self):
        self.assertTrue(is_leader_recommendable("600001", "主板票"))
        self.assertTrue(is_leader_recommendable("300001", "创业票"))
        self.assertTrue(is_leader_recommendable("688001", "科创票"))
        self.assertFalse(is_leader_recommendable("600001", "*ST主板"))


if __name__ == "__main__":
    unittest.main()
