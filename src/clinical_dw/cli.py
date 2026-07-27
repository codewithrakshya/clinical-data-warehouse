"""Command-line interface for learning and running the ETL pipeline."""

import argparse
from pathlib import Path

from clinical_dw.validation import validate_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clinical-dw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate Synthea source CSVs")
    validate.add_argument("--input-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "validate":
        results = validate_directory(args.input_dir)
        for result in results:
            status = "PASS" if result.valid else "FAIL"
            print(f"{status:4} {result.filename:20} rows={result.row_count}")
            for error in result.errors:
                print(f"     - {error}")
        return 0 if all(result.valid for result in results) else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
