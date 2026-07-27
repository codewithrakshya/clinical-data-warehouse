"""Transform validated staging rows into analytics-ready warehouse tables."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from psycopg import Connection

from clinical_dw.transforms import (
    clean_optional_text,
    parse_date,
    parse_decimal,
    parse_timestamp,
    split_observation_value,
)


@dataclass(frozen=True)
class PatientRecord:
    source_patient_id: str
    birth_date: date
    death_date: date | None
    sex_at_birth: str | None
    race: str | None
    ethnicity: str | None
    city: str | None
    state: str | None
    postal_code: str | None


@dataclass(frozen=True)
class EncounterRecord:
    source_encounter_id: str
    source_patient_id: str
    start_at: datetime
    stop_at: datetime | None
    encounter_class: str | None
    description: str | None
    base_cost: Decimal | None
    total_claim_cost: Decimal | None


@dataclass(frozen=True)
class ConditionRecord:
    source_patient_id: str
    source_encounter_id: str | None
    code_system: str
    code: str
    description: str | None
    onset_date: date
    resolved_date: date | None


@dataclass(frozen=True)
class ObservationRecord:
    source_patient_id: str
    source_encounter_id: str | None
    code_system: str
    code: str
    description: str | None
    observed_at: datetime
    value_numeric: Decimal | None
    value_text: str | None
    unit: str | None


def transform_patient(row: tuple[str | None, ...]) -> PatientRecord:
    """Convert one source-shaped patient row into validated warehouse values."""
    (
        source_patient_id,
        birthdate,
        deathdate,
        gender,
        race,
        ethnicity,
        city,
        state,
        postal_code,
    ) = row

    patient_id = clean_optional_text(source_patient_id)
    birth_date = parse_date(birthdate)
    death_date = parse_date(deathdate)

    if patient_id is None:
        raise ValueError("patient source ID is required")
    if birth_date is None:
        raise ValueError(f"birth date is required for patient {patient_id}")
    if death_date is not None and death_date < birth_date:
        raise ValueError(f"death date precedes birth date for patient {patient_id}")

    return PatientRecord(
        source_patient_id=patient_id,
        birth_date=birth_date,
        death_date=death_date,
        sex_at_birth=clean_optional_text(gender),
        race=clean_optional_text(race),
        ethnicity=clean_optional_text(ethnicity),
        city=clean_optional_text(city),
        state=clean_optional_text(state),
        postal_code=clean_optional_text(postal_code),
    )


def transform_encounter(row: tuple[str | None, ...]) -> EncounterRecord:
    """Convert one source-shaped encounter row into typed warehouse values."""
    (
        source_encounter_id,
        source_patient_id,
        start,
        stop,
        encounter_class,
        description,
        base_cost,
        total_claim_cost,
    ) = row

    encounter_id = clean_optional_text(source_encounter_id)
    patient_id = clean_optional_text(source_patient_id)
    start_at = parse_timestamp(start)
    stop_at = parse_timestamp(stop)

    if encounter_id is None:
        raise ValueError("encounter source ID is required")
    if patient_id is None:
        raise ValueError(f"patient source ID is required for encounter {encounter_id}")
    if start_at is None:
        raise ValueError(f"start timestamp is required for encounter {encounter_id}")
    if stop_at is not None and stop_at < start_at:
        raise ValueError(f"stop timestamp precedes start for encounter {encounter_id}")

    return EncounterRecord(
        source_encounter_id=encounter_id,
        source_patient_id=patient_id,
        start_at=start_at,
        stop_at=stop_at,
        encounter_class=clean_optional_text(encounter_class),
        description=clean_optional_text(description),
        base_cost=parse_decimal(base_cost),
        total_claim_cost=parse_decimal(total_claim_cost),
    )


def transform_condition(row: tuple[str | None, ...]) -> ConditionRecord:
    """Convert one source-shaped condition row into typed warehouse values."""
    (
        source_patient_id,
        source_encounter_id,
        code_system,
        code,
        description,
        onset,
        resolved,
    ) = row

    patient_id = clean_optional_text(source_patient_id)
    encounter_id = clean_optional_text(source_encounter_id)
    system = clean_optional_text(code_system)
    clinical_code = clean_optional_text(code)
    onset_date = parse_date(onset)
    resolved_date = parse_date(resolved)

    if patient_id is None:
        raise ValueError("patient source ID is required for condition")
    if system is None:
        raise ValueError(f"code system is required for patient {patient_id}")
    if clinical_code is None:
        raise ValueError(f"clinical code is required for patient {patient_id}")
    if onset_date is None:
        raise ValueError(f"onset date is required for patient {patient_id}")
    if resolved_date is not None and resolved_date < onset_date:
        raise ValueError(f"resolution precedes onset for patient {patient_id}")

    return ConditionRecord(
        source_patient_id=patient_id,
        source_encounter_id=encounter_id,
        code_system=system,
        code=clinical_code,
        description=clean_optional_text(description),
        onset_date=onset_date,
        resolved_date=resolved_date,
    )


def transform_observation(row: tuple[str | None, ...]) -> ObservationRecord:
    """Convert one source-shaped observation row into typed warehouse values."""
    (
        source_patient_id,
        source_encounter_id,
        category,
        code,
        description,
        observed,
        value,
        units,
        observation_type,
    ) = row

    patient_id = clean_optional_text(source_patient_id)
    encounter_id = clean_optional_text(source_encounter_id)
    category_name = clean_optional_text(category) or "uncategorized"
    clinical_code = clean_optional_text(code)
    observed_at = parse_timestamp(observed)
    value_numeric, value_text = split_observation_value(value, observation_type)

    if patient_id is None:
        raise ValueError("patient source ID is required for observation")
    if clinical_code is None:
        raise ValueError(f"clinical code is required for patient {patient_id}")
    if observed_at is None:
        raise ValueError(f"timestamp is required for patient {patient_id}")
    if value_numeric is None and value_text is None:
        raise ValueError(f"value is required for observation {clinical_code}")

    return ObservationRecord(
        source_patient_id=patient_id,
        source_encounter_id=encounter_id,
        code_system=f"urn:synthea:observation:{category_name}",
        code=clinical_code,
        description=clean_optional_text(description),
        observed_at=observed_at,
        value_numeric=value_numeric,
        value_text=value_text,
        unit=clean_optional_text(units),
    )


def load_patient_dimension(connection: Connection) -> tuple[int, int]:
    """Upsert staged patients and write a durable ETL audit record."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO warehouse.etl_run (source_name, status)
            VALUES ('staging.patients', 'running')
            RETURNING etl_run_id
            """
        )
        etl_run_id = cursor.fetchone()[0]
    connection.commit()

    try:
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, birthdate, deathdate, gender, race, ethnicity, city, state, zip
                FROM staging.patients
                ORDER BY id
                """
            )
            source_rows = cursor.fetchall()
            records = [transform_patient(row) for row in source_rows]

            cursor.executemany(
                """
                INSERT INTO warehouse.dim_patient (
                    source_patient_id,
                    birth_date,
                    death_date,
                    sex_at_birth,
                    race,
                    ethnicity,
                    city,
                    state,
                    postal_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_patient_id) DO UPDATE SET
                    birth_date = EXCLUDED.birth_date,
                    death_date = EXCLUDED.death_date,
                    sex_at_birth = EXCLUDED.sex_at_birth,
                    race = EXCLUDED.race,
                    ethnicity = EXCLUDED.ethnicity,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    postal_code = EXCLUDED.postal_code
                """,
                [
                    (
                        record.source_patient_id,
                        record.birth_date,
                        record.death_date,
                        record.sex_at_birth,
                        record.race,
                        record.ethnicity,
                        record.city,
                        record.state,
                        record.postal_code,
                    )
                    for record in records
                ],
            )
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'succeeded',
                    rows_read = %s,
                    rows_loaded = %s
                WHERE etl_run_id = %s
                """,
                (len(source_rows), len(records), etl_run_id),
            )
    except Exception as exc:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'failed',
                    error_message = %s
                WHERE etl_run_id = %s
                """,
                (str(exc)[:2000], etl_run_id),
            )
        connection.commit()
        raise

    return len(source_rows), len(records)


def load_encounter_fact(connection: Connection) -> tuple[int, int]:
    """Upsert staged encounters after resolving warehouse patient keys."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO warehouse.etl_run (source_name, status)
            VALUES ('staging.encounters', 'running')
            RETURNING etl_run_id
            """
        )
        etl_run_id = cursor.fetchone()[0]
    connection.commit()

    try:
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, patient, start_at, stop_at, encounter_class, description,
                       base_encounter_cost, total_claim_cost
                FROM staging.encounters
                ORDER BY id
                """
            )
            source_rows = cursor.fetchall()
            records = [transform_encounter(row) for row in source_rows]

            cursor.execute("SELECT source_patient_id, patient_key FROM warehouse.dim_patient")
            patient_keys = dict(cursor.fetchall())
            missing_patient_ids = {
                record.source_patient_id
                for record in records
                if record.source_patient_id not in patient_keys
            }
            if missing_patient_ids:
                raise ValueError(
                    f"{len(missing_patient_ids)} encounter patient IDs are absent "
                    "from warehouse.dim_patient"
                )

            cursor.executemany(
                """
                INSERT INTO warehouse.fact_encounter (
                    source_encounter_id,
                    patient_key,
                    start_at,
                    stop_at,
                    encounter_class,
                    description,
                    base_cost,
                    total_claim_cost
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_encounter_id) DO UPDATE SET
                    patient_key = EXCLUDED.patient_key,
                    start_at = EXCLUDED.start_at,
                    stop_at = EXCLUDED.stop_at,
                    encounter_class = EXCLUDED.encounter_class,
                    description = EXCLUDED.description,
                    base_cost = EXCLUDED.base_cost,
                    total_claim_cost = EXCLUDED.total_claim_cost
                """,
                [
                    (
                        record.source_encounter_id,
                        patient_keys[record.source_patient_id],
                        record.start_at,
                        record.stop_at,
                        record.encounter_class,
                        record.description,
                        record.base_cost,
                        record.total_claim_cost,
                    )
                    for record in records
                ],
            )
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'succeeded',
                    rows_read = %s,
                    rows_loaded = %s
                WHERE etl_run_id = %s
                """,
                (len(source_rows), len(records), etl_run_id),
            )
    except Exception as exc:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'failed',
                    error_message = %s
                WHERE etl_run_id = %s
                """,
                (str(exc)[:2000], etl_run_id),
            )
        connection.commit()
        raise

    return len(source_rows), len(records)


def load_condition_fact(connection: Connection) -> tuple[int, int]:
    """Rebuild condition facts after resolving patient, encounter, and code keys."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO warehouse.etl_run (source_name, status)
            VALUES ('staging.conditions', 'running')
            RETURNING etl_run_id
            """
        )
        etl_run_id = cursor.fetchone()[0]
    connection.commit()

    try:
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT patient, encounter, system, code, description, start_date, stop_date
                FROM staging.conditions
                ORDER BY patient, start_date, code
                """
            )
            source_rows = cursor.fetchall()
            records = [transform_condition(row) for row in source_rows]

            cursor.execute("SELECT source_patient_id, patient_key FROM warehouse.dim_patient")
            patient_keys = dict(cursor.fetchall())
            cursor.execute(
                "SELECT source_encounter_id, encounter_key FROM warehouse.fact_encounter"
            )
            encounter_keys = dict(cursor.fetchall())

            missing_patient_ids = {
                record.source_patient_id
                for record in records
                if record.source_patient_id not in patient_keys
            }
            missing_encounter_ids = {
                record.source_encounter_id
                for record in records
                if record.source_encounter_id is not None
                and record.source_encounter_id not in encounter_keys
            }
            if missing_patient_ids:
                raise ValueError(
                    f"{len(missing_patient_ids)} condition patient IDs are absent "
                    "from warehouse.dim_patient"
                )
            if missing_encounter_ids:
                raise ValueError(
                    f"{len(missing_encounter_ids)} condition encounter IDs are absent "
                    "from warehouse.fact_encounter"
                )

            codes = {(record.code_system, record.code): record.description for record in records}
            cursor.executemany(
                """
                INSERT INTO warehouse.dim_code (code_system, code, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (code_system, code) DO UPDATE SET
                    description = EXCLUDED.description
                """,
                [
                    (system, code, description)
                    for (system, code), description in sorted(codes.items())
                ],
            )
            cursor.execute("SELECT code_system, code, code_key FROM warehouse.dim_code")
            code_keys = {(system, code): code_key for system, code, code_key in cursor.fetchall()}

            cursor.execute("TRUNCATE warehouse.fact_condition RESTART IDENTITY")
            cursor.executemany(
                """
                INSERT INTO warehouse.fact_condition (
                    patient_key,
                    encounter_key,
                    code_key,
                    onset_date,
                    resolved_date
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (
                        patient_keys[record.source_patient_id],
                        encounter_keys.get(record.source_encounter_id),
                        code_keys[(record.code_system, record.code)],
                        record.onset_date,
                        record.resolved_date,
                    )
                    for record in records
                ],
            )
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'succeeded',
                    rows_read = %s,
                    rows_loaded = %s
                WHERE etl_run_id = %s
                """,
                (len(source_rows), len(records), etl_run_id),
            )
    except Exception as exc:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'failed',
                    error_message = %s
                WHERE etl_run_id = %s
                """,
                (str(exc)[:2000], etl_run_id),
            )
        connection.commit()
        raise

    return len(source_rows), len(records)


def load_observation_fact(connection: Connection) -> tuple[int, int]:
    """Rebuild observation facts after resolving patient, encounter, and code keys."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO warehouse.etl_run (source_name, status)
            VALUES ('staging.observations', 'running')
            RETURNING etl_run_id
            """
        )
        etl_run_id = cursor.fetchone()[0]
    connection.commit()

    try:
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT patient, encounter, category, code, description, observed_at,
                       value, units, observation_type
                FROM staging.observations
                ORDER BY patient, observed_at, code
                """
            )
            source_rows = cursor.fetchall()
            records = [transform_observation(row) for row in source_rows]

            cursor.execute("SELECT source_patient_id, patient_key FROM warehouse.dim_patient")
            patient_keys = dict(cursor.fetchall())
            cursor.execute(
                "SELECT source_encounter_id, encounter_key FROM warehouse.fact_encounter"
            )
            encounter_keys = dict(cursor.fetchall())

            missing_patient_ids = {
                record.source_patient_id
                for record in records
                if record.source_patient_id not in patient_keys
            }
            missing_encounter_ids = {
                record.source_encounter_id
                for record in records
                if record.source_encounter_id is not None
                and record.source_encounter_id not in encounter_keys
            }
            if missing_patient_ids:
                raise ValueError(
                    f"{len(missing_patient_ids)} observation patient IDs are absent "
                    "from warehouse.dim_patient"
                )
            if missing_encounter_ids:
                raise ValueError(
                    f"{len(missing_encounter_ids)} observation encounter IDs are absent "
                    "from warehouse.fact_encounter"
                )

            codes = {(record.code_system, record.code): record.description for record in records}
            cursor.executemany(
                """
                INSERT INTO warehouse.dim_code (code_system, code, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (code_system, code) DO UPDATE SET
                    description = EXCLUDED.description
                """,
                [
                    (system, code, description)
                    for (system, code), description in sorted(codes.items())
                ],
            )
            cursor.execute("SELECT code_system, code, code_key FROM warehouse.dim_code")
            code_keys = {(system, code): code_key for system, code, code_key in cursor.fetchall()}

            cursor.execute("TRUNCATE warehouse.fact_observation RESTART IDENTITY")
            cursor.executemany(
                """
                INSERT INTO warehouse.fact_observation (
                    patient_key,
                    encounter_key,
                    code_key,
                    observed_at,
                    value_numeric,
                    value_text,
                    unit
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        patient_keys[record.source_patient_id],
                        encounter_keys.get(record.source_encounter_id),
                        code_keys[(record.code_system, record.code)],
                        record.observed_at,
                        record.value_numeric,
                        record.value_text,
                        record.unit,
                    )
                    for record in records
                ],
            )
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'succeeded',
                    rows_read = %s,
                    rows_loaded = %s
                WHERE etl_run_id = %s
                """,
                (len(source_rows), len(records), etl_run_id),
            )
    except Exception as exc:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE warehouse.etl_run
                SET completed_at = NOW(),
                    status = 'failed',
                    error_message = %s
                WHERE etl_run_id = %s
                """,
                (str(exc)[:2000], etl_run_id),
            )
        connection.commit()
        raise

    return len(source_rows), len(records)
