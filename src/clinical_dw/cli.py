"""Command-line interface for learning and running the ETL pipeline."""

import argparse
import os
from pathlib import Path

import psycopg

from clinical_dw.cdc_aging import download_cdc_aging, prepare_cdc_aging
from clinical_dw.database import initialize_database
from clinical_dw.pipeline import run_pipeline
from clinical_dw.quality import run_quality_checks
from clinical_dw.staging import load_staging
from clinical_dw.validation import validate_directory
from clinical_dw.warehouse import (
    load_condition_fact,
    load_date_dimension,
    load_encounter_fact,
    load_observation_fact,
    load_patient_dimension,
)

DEFAULT_DATABASE_URL = "postgresql://clinical_dw:clinical_dw_dev@localhost:5432/clinical_dw"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clinical-dw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate source CSVs")
    validate.add_argument("--input-dir", type=Path, required=True)
    validate.add_argument(
        "--source",
        choices=("synthea", "mimic"),
        default="synthea",
    )

    load = subparsers.add_parser(
        "load-staging", help="validate and replace PostgreSQL staging tables"
    )
    load.add_argument("--input-dir", type=Path, required=True)
    load.add_argument(
        "--source",
        choices=("synthea", "mimic"),
        default="synthea",
    )
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

    conditions = subparsers.add_parser(
        "load-conditions", help="transform staged conditions into the warehouse"
    )
    conditions.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    observations = subparsers.add_parser(
        "load-observations", help="transform staged observations into the warehouse"
    )
    observations.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    dates = subparsers.add_parser(
        "load-dates", help="build the shared calendar and connect fact date keys"
    )
    dates.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    quality = subparsers.add_parser("quality", help="run structural warehouse data-quality checks")
    quality.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    init_db = subparsers.add_parser(
        "init-db", help="initialize schemas and tables in any PostgreSQL database"
    )
    init_db.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    pipeline = subparsers.add_parser("run", help="initialize and run the complete ETL pipeline")
    pipeline.add_argument("--input-dir", type=Path, required=True)
    pipeline.add_argument(
        "--source",
        choices=("synthea", "mimic"),
        default="synthea",
    )
    pipeline.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    )

    fetch_aging = subparsers.add_parser(
        "fetch-cdc-aging",
        help="download the unrestricted CDC Healthy Aging public dataset",
    )
    fetch_aging.add_argument("--output", type=Path, required=True)
    fetch_aging.add_argument(
        "--max-rows",
        type=int,
        help="optional row limit for a quick learning/test download",
    )

    prepare_aging = subparsers.add_parser(
        "prepare-cdc-aging",
        help="validate and prepare CDC Healthy Aging data for analysis",
    )
    prepare_aging.add_argument("--input", type=Path, required=True)
    prepare_aging.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "validate":
        results = validate_directory(args.input_dir, source=args.source)
        for result in results:
            status = "PASS" if result.valid else "FAIL"
            print(f"{status:4} {result.filename:20} rows={result.row_count}")
            for error in result.errors:
                print(f"     - {error}")
        return 0 if all(result.valid for result in results) else 1

    if args.command == "load-staging":
        with psycopg.connect(args.database_url) as connection:
            counts = load_staging(args.input_dir, connection, source=args.source)
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

    if args.command == "load-conditions":
        with psycopg.connect(args.database_url) as connection:
            rows_read, rows_loaded = load_condition_fact(connection)
        print(f"LOADED warehouse.fact_condition rows_read={rows_read} rows_loaded={rows_loaded}")
        return 0

    if args.command == "load-observations":
        with psycopg.connect(args.database_url) as connection:
            rows_read, rows_loaded = load_observation_fact(connection)
        print(f"LOADED warehouse.fact_observation rows_read={rows_read} rows_loaded={rows_loaded}")
        return 0

    if args.command == "load-dates":
        with psycopg.connect(args.database_url) as connection:
            rows_read, rows_loaded = load_date_dimension(connection)
        print(f"LOADED warehouse.dim_date rows_read={rows_read} rows_loaded={rows_loaded}")
        return 0

    if args.command == "quality":
        with psycopg.connect(args.database_url) as connection:
            checks = run_quality_checks(connection)
        for check in checks:
            print(
                f"{check.status:4} {check.check:36} value={check.value} expected={check.expected}"
            )
        return 1 if any(check.status == "FAIL" for check in checks) else 0

    if args.command == "init-db":
        with psycopg.connect(args.database_url) as connection:
            sql_files = initialize_database(connection)
        for filename in sql_files:
            print(f"APPLIED {filename}")
        return 0

    if args.command == "run":
        with psycopg.connect(args.database_url) as connection:
            result = run_pipeline(args.input_dir, connection, source=args.source)
        for table, count in result.warehouse_counts.items():
            print(f"LOADED warehouse.{table:15} rows={count}")
        for check in result.quality_checks:
            print(f"{check.status:4} {check.check}")
        return 1 if any(check.status == "FAIL" for check in result.quality_checks) else 0

    if args.command == "fetch-cdc-aging":
        count = download_cdc_aging(args.output, max_rows=args.max_rows)
        print(f"DOWNLOADED CDC Healthy Aging rows={count} path={args.output}")
        return 0

    if args.command == "prepare-cdc-aging":
        observations, topics = prepare_cdc_aging(args.input, args.output_dir)
        print(
            "PREPARED CDC Healthy Aging "
            f"observations={observations} topics={topics} output={args.output_dir}"
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
