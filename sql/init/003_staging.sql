CREATE TABLE IF NOT EXISTS staging.patients (
    id TEXT,
    birthdate TEXT,
    deathdate TEXT,
    gender TEXT,
    race TEXT,
    ethnicity TEXT,
    city TEXT,
    state TEXT,
    zip TEXT
);

CREATE TABLE IF NOT EXISTS staging.encounters (
    id TEXT,
    start_at TEXT,
    stop_at TEXT,
    patient TEXT,
    encounter_class TEXT,
    description TEXT,
    base_encounter_cost TEXT,
    total_claim_cost TEXT
);

CREATE TABLE IF NOT EXISTS staging.conditions (
    start_date TEXT,
    stop_date TEXT,
    patient TEXT,
    encounter TEXT,
    system TEXT,
    code TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS staging.observations (
    observed_at TEXT,
    patient TEXT,
    encounter TEXT,
    category TEXT,
    code TEXT,
    description TEXT,
    value TEXT,
    units TEXT,
    observation_type TEXT
);

COMMENT ON TABLE staging.patients IS
  'Validated Synthea patient values preserved as source text.';
COMMENT ON TABLE staging.encounters IS
  'Validated Synthea encounter values preserved as source text.';
COMMENT ON TABLE staging.conditions IS
  'Validated Synthea condition values preserved as source text.';
COMMENT ON TABLE staging.observations IS
  'Validated Synthea observation values preserved as source text.';
