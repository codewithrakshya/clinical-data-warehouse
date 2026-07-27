import unittest
from datetime import date

from clinical_dw.warehouse import (
    build_date_records,
    date_key,
    transform_condition,
    transform_encounter,
    transform_observation,
    transform_patient,
)


class WarehouseTests(unittest.TestCase):
    def test_date_key_uses_yyyymmdd_format(self) -> None:
        self.assertEqual(date_key(date(2026, 1, 2)), 20260102)

    def test_build_date_records_includes_range_boundaries(self) -> None:
        records = build_date_records(date(2025, 12, 31), date(2026, 1, 2))

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].date_key, 20251231)
        self.assertEqual(records[-1].date_key, 20260102)
        self.assertEqual(records[-1].day_of_week, 5)

    def test_build_date_records_rejects_reversed_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "end must not precede start"):
            build_date_records(date(2026, 1, 2), date(2026, 1, 1))

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

    def test_transform_condition_converts_dates_and_blank_resolution(self) -> None:
        record = transform_condition(
            (
                "patient-1",
                "encounter-1",
                "http://snomed.info/sct",
                "44054006",
                "Diabetes mellitus type 2",
                "2020-04-12",
                "",
            )
        )

        self.assertEqual(record.onset_date, date(2020, 4, 12))
        self.assertIsNone(record.resolved_date)
        self.assertEqual(record.code, "44054006")

    def test_transform_condition_rejects_resolution_before_onset(self) -> None:
        with self.assertRaisesRegex(ValueError, "precedes onset"):
            transform_condition(
                (
                    "patient-1",
                    "encounter-1",
                    "http://snomed.info/sct",
                    "44054006",
                    "Diabetes mellitus type 2",
                    "2020-04-12",
                    "2020-04-11",
                )
            )

    def test_transform_condition_requires_code_system(self) -> None:
        with self.assertRaisesRegex(ValueError, "code system is required"):
            transform_condition(
                (
                    "patient-1",
                    "encounter-1",
                    "",
                    "44054006",
                    "",
                    "2020-04-12",
                    "",
                )
            )

    def test_transform_observation_splits_numeric_value(self) -> None:
        record = transform_observation(
            (
                "patient-1",
                "encounter-1",
                "vital-signs",
                "8867-4",
                "Heart rate",
                "2026-01-02T10:00:00Z",
                "72.5",
                "beats/min",
                "numeric",
            )
        )

        self.assertEqual(str(record.value_numeric), "72.5")
        self.assertIsNone(record.value_text)
        self.assertEqual(record.code_system, "urn:synthea:observation:vital-signs")

    def test_transform_observation_preserves_text_value(self) -> None:
        record = transform_observation(
            (
                "patient-1",
                "",
                "",
                "72166-2",
                "Tobacco smoking status",
                "2026-01-02T10:00:00Z",
                "Never smoker",
                "",
                "text",
            )
        )

        self.assertIsNone(record.source_encounter_id)
        self.assertEqual(record.value_text, "Never smoker")
        self.assertEqual(record.code_system, "urn:synthea:observation:uncategorized")

    def test_transform_observation_requires_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "value is required"):
            transform_observation(
                (
                    "patient-1",
                    "",
                    "survey",
                    "72166-2",
                    "",
                    "2026-01-02T10:00:00Z",
                    "",
                    "",
                    "text",
                )
            )


if __name__ == "__main__":
    unittest.main()
