import csv
import tempfile
import unittest
from pathlib import Path

from clinical_dw.staging import iter_source_rows


class StagingTests(unittest.TestCase):
    def test_iter_source_rows_preserves_text_and_column_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "patients.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["Id", "ZIP", "IGNORED"])
                writer.writeheader()
                writer.writerow({"Id": "patient-1", "ZIP": "02108", "IGNORED": "value"})

            rows = list(iter_source_rows(path, ("ZIP", "Id")))

        self.assertEqual(rows, [("02108", "patient-1")])


if __name__ == "__main__":
    unittest.main()
