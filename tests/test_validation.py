import csv
import tempfile
import unittest
from pathlib import Path

from clinical_dw.contracts import CONTRACTS
from clinical_dw.validation import validate_csv


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_validation_reports_missing_file(self) -> None:
        result = validate_csv(self.input_dir, "patients")
        self.assertFalse(result.valid)
        self.assertEqual(result.errors, ("file is missing",))

    def test_validation_reports_missing_columns(self) -> None:
        write_csv(
            self.input_dir / "patients.csv",
            ["Id"],
            [{"Id": "patient-1"}],
        )
        result = validate_csv(self.input_dir, "patients")
        self.assertFalse(result.valid)
        self.assertTrue(any("BIRTHDATE" in error for error in result.errors))

    def test_validation_accepts_complete_contract(self) -> None:
        columns = sorted(CONTRACTS["patients"].required_columns)
        write_csv(
            self.input_dir / "patients.csv",
            columns,
            [{column: f"value-{column}" for column in columns}],
        )
        result = validate_csv(self.input_dir, "patients")
        self.assertTrue(result.valid)
        self.assertEqual(result.row_count, 1)


if __name__ == "__main__":
    unittest.main()
