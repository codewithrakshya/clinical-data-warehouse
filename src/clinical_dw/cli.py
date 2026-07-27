"""Command-line interface for learning and running the ETL pipeline."""

import argparse
import os
from pathlib import Path

import psycopg

from clinical_dw.staging import load_staging
from clinical_dw.validation import validate_directory
from clinical_dw.warehouse import load_encounter_fact, load_patient_dimension

DEFAULT_DATABASE_URL = "postgresql://clinical_dw:clinical_dw_dev@localhost:5432/clinical_dw"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clinical-dw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate Synthea source CSVs")
    validate.add_argument("--input-dir", type=Path, required=True)

    load = subparsers.add_parser(
        "load-staging", help="validate and replace PostgreSQL staging tables"
    )
    load.add_argument("--input-dir", type=Path, required=True)
    load.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    patients = subparsers.add_parser(
        "load-patients", help="transform staged patients into the warehouse"
    )
    patients.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    encounters = subparsers.add_parser(
        "load-encounters", help="transform staged encounters into the warehouse"
    )
    encounters.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
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

    if args.command == "load-staging":
        with psycopg.connect(args.database_url) as connection:
            counts = load_staging(args.input_dir, connection)
        for table, count in counts.items():
            print(f"LOADED staging.{table:15} rows={count}")
        return 0

    if args.command == "load-patients":
        with psycopg.connect(args.database_url) as connection:
            rows_read, rows_loaded = load_patient_dimension(connection)
        print(f"LOADED warehouse.dim_patient rows_read={rows_read} rows_loaded={rows_loaded}")
        return 0

    if args.command == "load-encounters":
        with psycopg.connect(args.database_url) as connection:
            rows_read, rows_loaded = load_encounter_fact(connection)
        print(f"LOADED warehouse.fact_encounter rows_read={rows_read} rows_loaded={rows_loaded}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
