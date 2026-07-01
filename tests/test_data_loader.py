import os
import tempfile
import unittest
from pathlib import Path

from rotation_v2.data_loader import database_signature


class DataLoaderTests(unittest.TestCase):
    def test_database_signature_changes_when_same_path_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "sample_data.db"
            db_path.write_bytes(b"old")
            first = database_signature(db_path)

            db_path.write_bytes(b"newer-content")
            os.utime(db_path, ns=(first[1] + 1_000_000, first[1] + 1_000_000))
            second = database_signature(db_path)

        self.assertEqual(first[0], second[0])
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
