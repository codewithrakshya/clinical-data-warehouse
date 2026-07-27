"""End-to-end orchestration for a validated clinical warehouse build."""

from dataclasses import dataclass
from pathlib import Path

from psycopg import Connection

from clinical_dw.database import initialize_database
from clinical_dw.quality import QualityCheck, run_quality_checks
from clinical_dw.staging import load_staging
from clinical_dw.warehouse import (
    load_condition_fact,
    load_date_dimension,
    load_encounter_fact,
    load_observation_fact,
    load_patient_dimension,
    reset_warehouse_data,
    set_dataset_metadata,
)


@dataclass(frozen=True)
class PipelineResult:
    staging_counts: dict[str, int]
    warehouse_counts: dict[str, int]
    quality_checks: list[QualityCheck]


def run_pipeline(
    input_dir: Path,
    connection: Connection,
    source: str = "synthea",
) -> PipelineResult:
    """Initialize schemas and load all warehouse entities in dependency order."""
    initialize_database(connection)
    staging_counts = load_staging(input_dir, connection, source=source)
    reset_warehouse_data(connection)

    warehouse_counts = {}
    _, warehouse_counts["dim_patient"] = load_patient_dimension(connection)
    _, warehouse_counts["fact_encounter"] = load_encounter_fact(connection)
    _, warehouse_counts["fact_condition"] = load_condition_fact(connection)
    _, warehouse_counts["fact_observation"] = load_observation_fact(connection)
    _, warehouse_counts["dim_date"] = load_date_dimension(connection)
    set_dataset_metadata(connection, source)

    return PipelineResult(
        staging_counts=staging_counts,
        warehouse_counts=warehouse_counts,
        quality_checks=run_quality_checks(connection),
    )
