"""Reusable data-quality checks for the clinical warehouse and dashboard."""

from dataclasses import asdict, dataclass

from psycopg import Connection


@dataclass(frozen=True)
class QualityCheck:
    check: str
    status: str
    value: int
    expected: str
    detail: str

    def as_dict(self) -> dict[str, str | int]:
        return asdict(self)


def _scalar(connection: Connection, statement: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(statement)
        return int(cursor.fetchone()[0] or 0)


def run_quality_checks(connection: Connection) -> list[QualityCheck]:
    """Run compact structural and relationship checks against the local warehouse."""
    checks: list[QualityCheck] = []
    parity_tables = (
        ("patients", "dim_patient"),
        ("encounters", "fact_encounter"),
        ("conditions", "fact_condition"),
        ("observations", "fact_observation"),
    )
    for staging_table, warehouse_table in parity_tables:
        source_count = _scalar(connection, f"SELECT COUNT(*) FROM staging.{staging_table}")
        warehouse_count = _scalar(connection, f"SELECT COUNT(*) FROM warehouse.{warehouse_table}")
        checks.append(
            QualityCheck(
                check=f"{staging_table.title()} row parity",
                status="PASS" if source_count == warehouse_count else "FAIL",
                value=warehouse_count,
                expected=f"{source_count} staged rows",
                detail=f"warehouse.{warehouse_table} should match its validated source.",
            )
        )

    broken_links = _scalar(
        connection,
        """
        SELECT
            (SELECT COUNT(*) FROM warehouse.fact_encounter e
             LEFT JOIN warehouse.dim_patient p ON p.patient_key = e.patient_key
             WHERE p.patient_key IS NULL)
          + (SELECT COUNT(*) FROM warehouse.fact_condition f
             LEFT JOIN warehouse.dim_patient p ON p.patient_key = f.patient_key
             LEFT JOIN warehouse.dim_code c ON c.code_key = f.code_key
             WHERE p.patient_key IS NULL OR c.code_key IS NULL)
          + (SELECT COUNT(*) FROM warehouse.fact_observation f
             LEFT JOIN warehouse.dim_patient p ON p.patient_key = f.patient_key
             LEFT JOIN warehouse.dim_code c ON c.code_key = f.code_key
             WHERE p.patient_key IS NULL OR c.code_key IS NULL)
          + (SELECT COUNT(*) FROM warehouse.fact_encounter f
             LEFT JOIN warehouse.dim_date d ON d.date_key = f.start_date_key
             WHERE d.date_key IS NULL)
          + (SELECT COUNT(*) FROM warehouse.fact_condition f
             LEFT JOIN warehouse.dim_date d ON d.date_key = f.onset_date_key
             WHERE d.date_key IS NULL)
          + (SELECT COUNT(*) FROM warehouse.fact_observation f
             LEFT JOIN warehouse.dim_date d ON d.date_key = f.observation_date_key
             WHERE d.date_key IS NULL)
        """,
    )
    checks.append(
        QualityCheck(
            check="Broken warehouse links",
            status="PASS" if broken_links == 0 else "FAIL",
            value=broken_links,
            expected="0",
            detail="Every fact must resolve to its required patient, code, and date dimensions.",
        )
    )

    failed_runs = _scalar(
        connection,
        "SELECT COUNT(*) FROM warehouse.etl_run WHERE status = 'failed'",
    )
    checks.append(
        QualityCheck(
            check="Failed ETL runs",
            status="PASS" if failed_runs == 0 else "WARN",
            value=failed_runs,
            expected="0",
            detail="Failures remain visible for operational troubleshooting.",
        )
    )

    duplicate_observations = _scalar(
        connection,
        """
        SELECT COALESCE(SUM(row_count - 1), 0)
        FROM (
            SELECT COUNT(*) AS row_count
            FROM staging.observations
            GROUP BY observed_at, patient, encounter, category, code,
                     description, value, units, observation_type
            HAVING COUNT(*) > 1
        ) duplicates
        """,
    )
    checks.append(
        QualityCheck(
            check="Exact source observation duplicates",
            status="PASS" if duplicate_observations == 0 else "WARN",
            value=duplicate_observations,
            expected="0 preferred",
            detail="Duplicates are preserved for traceability and flagged for review.",
        )
    )

    invalid_date_order = _scalar(
        connection,
        """
        SELECT
            (SELECT COUNT(*) FROM warehouse.dim_patient
             WHERE death_date IS NOT NULL AND death_date < birth_date)
          + (SELECT COUNT(*) FROM warehouse.fact_encounter
             WHERE stop_at IS NOT NULL AND stop_at < start_at)
          + (SELECT COUNT(*) FROM warehouse.fact_condition
             WHERE resolved_date IS NOT NULL AND resolved_date < onset_date)
        """,
    )
    checks.append(
        QualityCheck(
            check="Invalid date ordering",
            status="PASS" if invalid_date_order == 0 else "FAIL",
            value=invalid_date_order,
            expected="0",
            detail="Deaths, encounter stops, and resolutions cannot precede their starts.",
        )
    )

    return checks
