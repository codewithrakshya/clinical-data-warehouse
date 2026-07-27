import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from clinical_dw.mimic import (
    iter_mimic_conditions,
    iter_mimic_encounters,
    iter_mimic_observations,
    iter_mimic_patients,
)


def write_gzip_csv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, mode="wt", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


class MimicAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name)

        write_gzip_csv(
            self.input_dir / "hosp/patients.csv.gz",
            ["subject_id", "gender", "anchor_age", "anchor_year", "dod"],
            [
                {
                    "subject_id": "1001",
                    "gender": "F",
                    "anchor_age": "41",
                    "anchor_year": "2020",
                    "dod": "",
                }
            ],
        )
        write_gzip_csv(
            self.input_dir / "hosp/admissions.csv.gz",
            [
                "subject_id",
                "hadm_id",
                "admittime",
                "dischtime",
                "admission_type",
                "admission_location",
                "race",
            ],
            [
                {
                    "subject_id": "1001",
                    "hadm_id": "2001",
                    "admittime": "2020-03-01 10:00:00",
                    "dischtime": "2020-03-03 14:00:00",
                    "admission_type": "URGENT",
                    "admission_location": "TRANSFER FROM HOSPITAL",
                    "race": "ASIAN",
                }
            ],
        )
        write_gzip_csv(
            self.input_dir / "hosp/diagnoses_icd.csv.gz",
            ["subject_id", "hadm_id", "icd_code", "icd_version"],
            [
                {
                    "subject_id": "1001",
                    "hadm_id": "2001",
                    "icd_code": "E119",
                    "icd_version": "10",
                }
            ],
        )
        write_gzip_csv(
            self.input_dir / "hosp/d_icd_diagnoses.csv.gz",
            ["icd_code", "icd_version", "long_title"],
            [
                {
                    "icd_code": "E119",
                    "icd_version": "10",
                    "long_title": "Type 2 diabetes mellitus without complications",
                }
            ],
        )
        write_gzip_csv(
            self.input_dir / "hosp/labevents.csv.gz",
            [
                "subject_id",
                "hadm_id",
                "itemid",
                "charttime",
                "value",
                "valuenum",
                "valueuom",
            ],
            [
                {
                    "subject_id": "1001",
                    "hadm_id": "2001",
                    "itemid": "50931",
                    "charttime": "2020-03-01 11:00:00",
                    "value": "120",
                    "valuenum": "120",
                    "valueuom": "mg/dL",
                }
            ],
        )
        write_gzip_csv(
            self.input_dir / "hosp/d_labitems.csv.gz",
            ["itemid", "label", "category"],
            [{"itemid": "50931", "label": "Glucose", "category": "Chemistry"}],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_patient_mapping_derives_approximate_birth_year_and_race(self) -> None:
        row = next(iter_mimic_patients(self.input_dir))

        self.assertEqual(row[0], "mimic:patient:1001")
        self.assertEqual(row[1], "1979-01-01")
        self.assertEqual(row[3], "F")
        self.assertEqual(row[4], "ASIAN")

    def test_admission_mapping_creates_common_encounter_shape(self) -> None:
        row = next(iter_mimic_encounters(self.input_dir))

        self.assertEqual(row[0], "mimic:encounter:2001")
        self.assertEqual(row[3], "mimic:patient:1001")
        self.assertEqual(row[4], "URGENT")

    def test_diagnosis_mapping_uses_dictionary_and_admission_date(self) -> None:
        row = next(iter_mimic_conditions(self.input_dir))

        self.assertEqual(row[0], "2020-03-01")
        self.assertEqual(row[4], "urn:hl7-org:icd-10")
        self.assertEqual(row[6], "Type 2 diabetes mellitus without complications")

    def test_lab_mapping_preserves_numeric_value_and_units(self) -> None:
        row = next(iter_mimic_observations(self.input_dir))

        self.assertEqual(row[3], "Chemistry")
        self.assertEqual(row[5], "Glucose")
        self.assertEqual(row[6], "120")
        self.assertEqual(row[7], "mg/dL")
        self.assertEqual(row[8], "numeric")


if __name__ == "__main__":
    unittest.main()
