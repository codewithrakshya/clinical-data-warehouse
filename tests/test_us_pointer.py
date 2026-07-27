import tempfile
import unittest
from pathlib import Path

from clinical_dw.us_pointer import (
    PARTICIPANTS,
    PUBLICATION_URL,
    load_us_pointer_evidence,
)


class UsPointerEvidenceTests(unittest.TestCase):
    def test_published_primary_outcome_is_preserved(self) -> None:
        evidence = load_us_pointer_evidence()
        primary = evidence.loc[evidence["outcome_role"] == "Primary"].iloc[0]

        self.assertEqual(PARTICIPANTS, 2111)
        self.assertEqual(primary["difference"], 0.029)
        self.assertEqual(primary["difference_ci_low"], 0.008)
        self.assertEqual(primary["difference_ci_high"], 0.050)
        self.assertEqual(primary["p_value"], 0.008)
        self.assertTrue(primary["ci_excludes_zero"])

    def test_secondary_outcomes_keep_statistical_uncertainty(self) -> None:
        evidence = load_us_pointer_evidence().set_index("outcome")

        self.assertTrue(evidence.loc["Executive function", "ci_excludes_zero"])
        self.assertFalse(evidence.loc["Episodic memory", "ci_excludes_zero"])
        self.assertFalse(evidence.loc["Processing speed", "ci_excludes_zero"])

    def test_unexpected_publication_source_fails_validation(self) -> None:
        evidence = load_us_pointer_evidence()
        evidence.loc[0, "publication_url"] = "https://example.com"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.csv"
            evidence.drop(columns=["ci_excludes_zero", "evidence_design"]).to_csv(
                path, index=False
            )

            with self.assertRaisesRegex(ValueError, "unexpected publication source"):
                load_us_pointer_evidence(path)

        self.assertTrue(evidence.loc[1:, "publication_url"].eq(PUBLICATION_URL).all())


if __name__ == "__main__":
    unittest.main()
