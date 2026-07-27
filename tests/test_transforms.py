import unittest
from decimal import Decimal

from clinical_dw.transforms import (
    clean_optional_text,
    parse_date,
    parse_decimal,
    parse_timestamp,
    split_observation_value,
)


class TransformTests(unittest.TestCase):
    def test_clean_optional_text_normalizes_blanks(self) -> None:
        self.assertEqual(clean_optional_text("  value  "), "value")
        self.assertIsNone(clean_optional_text("   "))
        self.assertIsNone(clean_optional_text(None))

    def test_parse_date_accepts_synthea_date(self) -> None:
        self.assertEqual(parse_date("1985-04-12").isoformat(), "1985-04-12")
        self.assertIsNone(parse_date(""))

    def test_parse_timestamp_accepts_utc_suffix(self) -> None:
        parsed = parse_timestamp("2025-01-02T03:04:05Z")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)

    def test_parse_decimal_is_exact(self) -> None:
        self.assertEqual(parse_decimal("12.30"), Decimal("12.30"))
        with self.assertRaisesRegex(ValueError, "not a valid decimal"):
            parse_decimal("not-a-number")

    def test_split_observation_value_preserves_numeric_and_text_types(self) -> None:
        self.assertEqual(
            split_observation_value("98.6", "numeric"),
            (Decimal("98.6"), None),
        )
        self.assertEqual(
            split_observation_value("Never smoker", "text"),
            (None, "Never smoker"),
        )


if __name__ == "__main__":
    unittest.main()
