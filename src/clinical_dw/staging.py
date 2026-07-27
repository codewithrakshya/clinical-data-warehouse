"""Transactional loading of normalized source records into PostgreSQL staging."""

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from psycopg import Connection, sql

from clinical_dw.contracts import SYNTHEA_CONTRACTS
from clinical_dw.mimic import MIMIC_STAGING_ROWS
from clinical_dw.source_io import open_source_text
from clinical_dw.validation import validate_directory


@dataclass(frozen=True)
class StagingSpec:
    contract_name: str
    table: str
    source_columns: tuple[str, ...]
    target_columns: tuple[str, ...]


STAGING_SPECS = (
    StagingSpec(
        "patients",
        "patients",
        ("Id", "BIRTHDATE", "DEATHDATE", "GENDER", "RACE", "ETHNICITY", "CITY", "STATE", "ZIP"),
        ("id", "birthdate", "deathdate", "gender", "race", "ethnicity", "city", "state", "zip"),
    ),
    StagingSpec(
        "encounters",
        "encounters",
        (
            "Id",
            "START",
            "STOP",
            "PATIENT",
            "ENCOUNTERCLASS",
            "DESCRIPTION",
            "BASE_ENCOUNTER_COST",
            "TOTAL_CLAIM_COST",
        ),
        (
            "id",
            "start_at",
            "stop_at",
            "patient",
            "encounter_class",
            "description",
            "base_encounter_cost",
            "total_claim_cost",
        ),
    ),
    StagingSpec(
        "conditions",
        "conditions",
        ("START", "STOP", "PATIENT", "ENCOUNTER", "SYSTEM", "CODE", "DESCRIPTION"),
        ("start_date", "stop_date", "patient", "encounter", "system", "code", "description"),
    ),
    StagingSpec(
        "observations",
        "observations",
        (
            "DATE",
            "PATIENT",
            "ENCOUNTER",
            "CATEGORY",
            "CODE",
            "DESCRIPTION",
            "VALUE",
            "UNITS",
            "TYPE",
        ),
        (
            "observed_at",
            "patient",
            "encounter",
            "category",
            "code",
            "description",
            "value",
            "units",
            "observation_type",
        ),
    ),
)


def iter_source_rows(path: Path, columns: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    """Yield selected values in a deterministic order without transforming them."""
    with open_source_text(path) as stream:
        for row in csv.DictReader(stream):
            yield tuple(row[column] for column in columns)


def _source_rows(
    input_dir: Path,
    source: str,
    spec: StagingSpec,
) -> Iterator[tuple[str, ...]]:
    if source == "synthea":
        path = input_dir / SYNTHEA_CONTRACTS[spec.contract_name].filename
        yield from iter_source_rows(path, spec.source_columns)
        return
    if source == "mimic":
        yield from MIMIC_STAGING_ROWS[spec.table](input_dir)
        return
    raise ValueError(f"unsupported source: {source}")


def load_staging(
    input_dir: Path,
    connection: Connection,
    source: str = "synthea",
) -> dict[str, int]:
    """Replace all staging tables atomically with validated source rows."""
    results = validate_directory(input_dir, source=source)
    errors = [error for result in results for error in result.errors]
    if errors:
        raise ValueError("source validation failed: " + "; ".join(errors))

    counts: dict[str, int] = {}
    table_identifiers = [sql.Identifier("staging", spec.table) for spec in STAGING_SPECS]

    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(table_identifiers)))

        for spec in STAGING_SPECS:
            statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
                sql.Identifier("staging", spec.table),
                sql.SQL(", ").join(map(sql.Identifier, spec.target_columns)),
            )
            row_count = 0
            with cursor.copy(statement) as copy:
                for row in _source_rows(input_dir, source, spec):
                    copy.write_row(row)
                    row_count += 1
            counts[spec.table] = row_count

    return counts
