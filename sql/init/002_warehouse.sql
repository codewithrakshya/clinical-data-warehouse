CREATE TABLE IF NOT EXISTS warehouse.etl_run (
    etl_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    rows_read BIGINT NOT NULL DEFAULT 0 CHECK (rows_read >= 0),
    rows_loaded BIGINT NOT NULL DEFAULT 0 CHECK (rows_loaded >= 0),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS warehouse.dim_patient (
    patient_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_patient_id TEXT NOT NULL UNIQUE,
    birth_date DATE NOT NULL,
    death_date DATE,
    sex_at_birth TEXT,
    race TEXT,
    ethnicity TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    CONSTRAINT death_not_before_birth
      CHECK (death_date IS NULL OR death_date >= birth_date)
);

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    calendar_year SMALLINT NOT NULL,
    calendar_month SMALLINT NOT NULL CHECK (calendar_month BETWEEN 1 AND 12),
    day_of_month SMALLINT NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7)
);

CREATE TABLE IF NOT EXISTS warehouse.dim_code (
    code_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code_system TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT,
    UNIQUE (code_system, code)
);

CREATE TABLE IF NOT EXISTS warehouse.fact_encounter (
    encounter_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_encounter_id TEXT NOT NULL UNIQUE,
    patient_key BIGINT NOT NULL REFERENCES warehouse.dim_patient(patient_key),
    start_at TIMESTAMPTZ NOT NULL,
    stop_at TIMESTAMPTZ,
    encounter_class TEXT,
    description TEXT,
    base_cost NUMERIC(14, 2),
    total_claim_cost NUMERIC(14, 2),
    CONSTRAINT encounter_stop_after_start
      CHECK (stop_at IS NULL OR stop_at >= start_at)
);

CREATE TABLE IF NOT EXISTS warehouse.fact_condition (
    condition_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_key BIGINT NOT NULL REFERENCES warehouse.dim_patient(patient_key),
    encounter_key BIGINT REFERENCES warehouse.fact_encounter(encounter_key),
    code_key BIGINT NOT NULL REFERENCES warehouse.dim_code(code_key),
    onset_date DATE NOT NULL,
    resolved_date DATE,
    CONSTRAINT resolution_after_onset
      CHECK (resolved_date IS NULL OR resolved_date >= onset_date)
);

CREATE TABLE IF NOT EXISTS warehouse.fact_observation (
    observation_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    patient_key BIGINT NOT NULL REFERENCES warehouse.dim_patient(patient_key),
    encounter_key BIGINT REFERENCES warehouse.fact_encounter(encounter_key),
    code_key BIGINT NOT NULL REFERENCES warehouse.dim_code(code_key),
    observed_at TIMESTAMPTZ NOT NULL,
    value_numeric NUMERIC,
    value_text TEXT,
    unit TEXT,
    CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_encounter_patient
  ON warehouse.fact_encounter(patient_key);
CREATE INDEX IF NOT EXISTS idx_condition_patient
  ON warehouse.fact_condition(patient_key);
CREATE INDEX IF NOT EXISTS idx_observation_patient
  ON warehouse.fact_observation(patient_key);
CREATE INDEX IF NOT EXISTS idx_observation_date
  ON warehouse.fact_observation(observed_at);
