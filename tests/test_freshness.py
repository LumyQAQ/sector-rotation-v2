import unittest

from rotation_v2.freshness import freshness_status, parse_latest_manifest


class FreshnessTests(unittest.TestCase):
    def test_freshness_status_detects_remote_newer_than_loaded_data(self):
        status, message = freshness_status(
            "2026-07-01",
            {"date": "2026-07-02", "stock_rows": 5527},
        )

        self.assertEqual(status, "stale")
        self.assertIn("2026-07-02", message)
        self.assertIn("2026-07-01", message)

    def test_freshness_status_accepts_matching_dates(self):
        status, message = freshness_status(
            "2026-07-01",
            {"date": "2026-07-01", "stock_rows": 5527},
        )

        self.assertEqual(status, "fresh")
        self.assertIsNone(message)

    def test_parse_latest_manifest_accepts_json_bytes(self):
        manifest = parse_latest_manifest(b'{"date":"2026-07-01","stock_rows":5527}')

        self.assertEqual(manifest["date"], "2026-07-01")
        self.assertEqual(manifest["stock_rows"], 5527)


if __name__ == "__main__":
    unittest.main()
