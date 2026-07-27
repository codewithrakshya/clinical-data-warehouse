import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from clinical_dw.cdc_aging import (
    build_topic_summary,
    fetch_cdc_aging_with_fallback,
    load_cdc_aging_snapshot,
    normalize_cdc_aging,
    prepare_cdc_aging,
)


def raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "rowid": "row-1",
                "yearstart": "2022",
                "yearend": "2022",
                "locationabbr": "CA",
                "locationdesc": "California",
                "datasource": "BRFSS",
                "class": "Cognitive Decline",
                "topic": "Subjective cognitive decline",
                "question": "Percentage of adults with subjective cognitive decline",
                "data_value_unit": "%",
                "data_value_type": "Percentage",
                "data_value": "12.5",
                "low_confidence_limit": "10.0",
                "high_confidence_limit": "15.0",
                "stratificationcategory1": "Age Group",
                "stratification1": "Overall",
                "stratificationcategory2": "Sex",
                "stratification2": "Overall",
                "classid": "C06",
                "topicid": "TCC01",
                "questionid": "Q01",
                "locationid": "06",
            },
            {
                "rowid": "row-2",
                "yearstart": "2022",
                "yearend": "2022",
                "locationabbr": "NV",
                "locationdesc": "Nevada",
                "datasource": "BRFSS",
                "class": "Cognitive Decline",
                "topic": "Subjective cognitive decline",
                "question": "Percentage of adults with subjective cognitive decline",
                "data_value_unit": "%",
                "data_value_type": "Percentage",
                "data_value": "",
                "low_confidence_limit": "",
                "high_confidence_limit": "",
                "stratificationcategory1": "Age Group",
                "stratification1": "Overall",
            },
        ]
    )


class CdcAgingTests(unittest.TestCase):
    def test_normalization_preserves_estimates_and_uncertainty(self) -> None:
        normalized = normalize_cdc_aging(raw_frame())

        self.assertEqual(normalized.loc[0, "estimate"], 12.5)
        self.assertEqual(normalized.loc[0, "confidence_width"], 5.0)
        self.assertTrue(normalized.loc[0, "estimate_available"])
        self.assertFalse(normalized.loc[1, "estimate_available"])

    def test_missing_required_columns_fail_with_clear_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing columns"):
            normalize_cdc_aging(pd.DataFrame({"rowid": ["row-1"]}))

    def test_topic_summary_reports_coverage_not_patient_counts(self) -> None:
        summary = build_topic_summary(normalize_cdc_aging(raw_frame()))

        self.assertEqual(summary.loc[0, "observations"], 2)
        self.assertEqual(summary.loc[0, "locations"], 2)
        self.assertEqual(summary.loc[0, "estimates_available"], 1)

    def test_prepare_writes_analysis_ready_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "raw.csv"
            output_dir = root / "processed"
            raw_frame().to_csv(input_path, index=False)

            observations, topics = prepare_cdc_aging(input_path, output_dir)

            self.assertEqual((observations, topics), (2, 1))
            self.assertTrue((output_dir / "cdc_healthy_aging_observations.csv").exists())
            self.assertTrue((output_dir / "cdc_healthy_aging_topic_summary.csv").exists())

    def test_normalized_snapshot_can_be_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "snapshot.csv"
            normalize_cdc_aging(raw_frame()).to_csv(snapshot_path, index=False)

            snapshot = load_cdc_aging_snapshot(snapshot_path)

            self.assertEqual(len(snapshot), 2)
            self.assertEqual(snapshot.loc[0, "confidence_width"], 5.0)

    def test_fallback_is_used_when_live_fetch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "snapshot.csv"
            normalize_cdc_aging(raw_frame()).to_csv(snapshot_path, index=False)

            with mock.patch(
                "clinical_dw.cdc_aging.fetch_cdc_aging_frame",
                side_effect=OSError("CDC unavailable"),
            ):
                frame, source = fetch_cdc_aging_with_fallback(snapshot_path=snapshot_path)

            self.assertEqual(len(frame), 2)
            self.assertEqual(source, "Versioned CDC fallback snapshot")


if __name__ == "__main__":
    unittest.main()
