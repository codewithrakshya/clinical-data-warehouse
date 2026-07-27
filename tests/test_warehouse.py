import unittest
from datetime import date

from clinical_dw.warehouse import transform_encounter, transform_patient


class WarehouseTests(unittest.TestCase):
    def test_transform_patient_converts_dates_and_blank_optionals(self) -> None:
        record = transform_patient(
            (
                " patient-1 ",
                "1990-02-03",
                "",
                "F",
                "asian",
                "nonhispanic",
                "Boston",
                "Massachusetts",
                "02108",
            )
        )

        self.assertEqual(record.source_patient_id, "patient-1")
        self.assertEqual(record.birth_date, date(1990, 2, 3))
        self.assertIsNone(record.death_date)
        self.assertEqual(record.postal_code, "02108")

    def test_transform_patient_rejects_missing_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "source ID is required"):
            transform_patient(("", "1990-02-03", "", "", "", "", "", "", ""))

    def test_transform_patient_rejects_death_before_birth(self) -> None:
        with self.assertRaisesRegex(ValueError, "precedes birth"):
            transform_patient(("patient-1", "1990-02-03", "1989-01-01", "", "", "", "", "", ""))

    def test_transform_encounter_converts_timestamps_and_costs(self) -> None:
        record = transform_encounter(
            (
                "encounter-1",
                "patient-1",
                "2026-01-02T10:00:00Z",
                "2026-01-02T10:30:00Z",
                "ambulatory",
                "Office visit",
                "75.00",
                "125.50",
            )
        )

        self.assertEqual(record.start_at.isoformat(), "2026-01-02T10:00:00+00:00")
        self.assertEqual(str(record.base_cost), "75.00")
        self.assertEqual(str(record.total_claim_cost), "125.50")

    def test_transform_encounter_rejects_missing_patient(self) -> None:
        with self.assertRaisesRegex(ValueError, "patient source ID is required"):
            transform_encounter(
                (
                    "encounter-1",
                    "",
                    "2026-01-02T10:00:00Z",
                    "",
                    "",
                    "",
                    "",
                    "",
                )
            )

    def test_transform_encounter_rejects_stop_before_start(self) -> None:
        with self.assertRaisesRegex(ValueError, "precedes start"):
            transform_encounter(
                (
                    "encounter-1",
                    "patient-1",
                    "2026-01-02T10:00:00Z",
                    "2026-01-02T09:59:00Z",
                    "",
                    "",
                    "",
                    "",
                )
            )


if __name__ == "__main__":
    unittest.main()
