# Clinical Data Warehouse

A portfolio-scale, multi-source clinical data warehouse built with Python,
PostgreSQL, [Synthea](https://synthea.mitre.org/), and the openly available
[MIMIC-IV Clinical Database Demo](https://physionet.org/content/mimic-iv-demo/2.2/).

The project is also beginning a separate brain-health evidence track using the
unrestricted [CDC Alzheimer's Disease and Healthy Aging Data](https://data.cdc.gov/Healthy-Aging/Alzheimer-s-Disease-and-Healthy-Aging-Data/hfr9-rurv).
These aggregate estimates are deliberately kept separate from patient-level
clinical facts. See [the CDC source guide](docs/cdc-healthy-aging.md).

The brain-health evidence view also models published aggregate outcomes from
the US-POINTER randomized clinical trial. See
[the US-POINTER evidence guide](docs/us-pointer-evidence.md).

[**Explore the live Clinical Warehouse dashboard →**](https://rakshya-clinical-warehouse.streamlit.app/)

**New to the project?** Read
[what it solves, why it exists, who it benefits, and how it works](docs/project-overview.md).

> The live project uses the deidentified MIMIC-IV Demo. It is not designed or
> approved for protected health information (PHI). Never commit credentials or
> exports from a clinical system.

## Project highlights

- Normalizes either deterministic Synthea fixtures or the MIMIC-IV Demo into
  one analytics-ready warehouse model through explicit source adapters.
- Processes 100 deidentified MIMIC demo patients, 275 admissions, 4,506
  diagnoses, and 98,139 laboratory results in the real-world-data path.
- Models analytics-ready patient and code dimensions with encounter, condition,
  and observation facts in PostgreSQL.
- Preserves source-shaped staging data, validates schema drift, resolves
  warehouse relationships, and records durable ETL audit history.
- Publishes structural quality checks that distinguish failures from reviewable
  warnings instead of silently discarding questionable source records.
- Provides an interactive cohort builder across demographics, encounter types,
  diagnosis text, and utilization thresholds with deidentified CSV export.
- Runs locally with Docker and in the cloud with Neon PostgreSQL, Streamlit
  Community Cloud, and GitHub Actions CI.

## What this project demonstrates

- Modeling clinical data for analytics
- Loading messy source CSVs through a reproducible ETL pipeline
- Separating raw/staging data from curated warehouse tables
- Data-quality testing and audit logging
- Containerized local development with PostgreSQL
- Deidentified healthcare analytics with explicit provenance and limitations

## Architecture

```text
Synthea CSVs ─┐
              ├─> source adapters + validation
MIMIC CSVs ───┘
        |
        v
common staging schema
        |
        v
warehouse schema (dimensions + facts)
        |
        v
Streamlit analytics dashboard
```

The deployed application uses the same warehouse model:

```text
GitHub source + CI
        |
        v
Streamlit Community Cloud
        |
        v
Neon PostgreSQL
        |
        v
staging + warehouse + ETL audit schemas
```

### Why two database schemas?

The `staging` schema stays close to the source format. It gives us a place to
inspect and validate incoming data without pretending it is already analytics
ready.

The `warehouse` schema contains stable dimensions and fact tables. Analysts can
query these tables without repeatedly cleaning identifiers, dates, codes, and
numeric values.

## Warehouse model

| Table | Grain | Purpose |
| --- | --- | --- |
| `dim_patient` | One row per patient | Demographics and patient identity |
| `dim_date` | One row per calendar date | Consistent time-based analysis |
| `dim_code` | One row per coding-system/code pair | Diagnoses and observations |
| `fact_encounter` | One row per encounter | Visit utilization and duration |
| `fact_condition` | One row per patient condition | Diagnosis history |
| `fact_observation` | One row per clinical observation | Labs, vitals, and results |
| `etl_run` | One row per pipeline run | Operational audit trail |
| `dataset_metadata` | One row for the active source | Provenance and dashboard labeling |

This is a deliberately small star schema. It is easier to learn and test than a
full OMOP or FHIR implementation, while preserving the same core modeling
ideas.

## Quick start

### 1. Start PostgreSQL

```bash
cp .env.example .env
docker compose up -d db
```

The database initializes itself from [`sql/init`](sql/init).

### 2. Create a Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Choose a source dataset

Generate or download a Synthea CSV export and place these files under
`data/raw/`:

```text
patients.csv
encounters.csv
conditions.csv
observations.csv
```

See [docs/synthea.md](docs/synthea.md) for options.

For the deidentified MIMIC-IV Demo, follow
[docs/mimic-iv-demo.md](docs/mimic-iv-demo.md) and extract the files under
`data/mimic/`.

### 4. Validate source files

```bash
clinical-dw validate --input-dir data/raw
```

For MIMIC:

```bash
clinical-dw validate --source mimic --input-dir data/mimic
```

### 5. Load normalized staging tables

```bash
clinical-dw load-staging --input-dir data/raw
```

Use `--source mimic --input-dir data/mimic` for MIMIC. Each adapter validates
its required files before replacing the common staging tables in one database
transaction.

### 6. Run tests

```bash
pytest
```

### 7. Build the patient dimension

```bash
clinical-dw load-patients
```

This converts staged text into typed patient records, upserts them by source
patient ID, and writes the outcome to `warehouse.etl_run`.

### 8. Build the encounter fact

```bash
clinical-dw load-encounters
```

This converts encounter timestamps and costs, resolves every source patient ID
to a warehouse patient key, and records one fact row per healthcare visit.

### 9. Build the code dimension and condition fact

```bash
clinical-dw load-conditions
```

This upserts reusable clinical concepts into `dim_code`, resolves patient and
encounter keys, converts onset and resolution dates, and transactionally
rebuilds one condition fact per source diagnosis episode.

### 10. Build observation facts

```bash
clinical-dw load-observations
```

Numeric measurements and text responses are stored separately, optional
encounter links remain nullable, and source-specific coding namespaces are
retained.

### 11. Run the data-quality report

```bash
clinical-dw quality
```

### 12. Open the dashboard

```bash
streamlit run app.py
```

Streamlit opens the local Clinical Warehouse Explorer with utilization,
condition, observation, data-quality, and ETL audit views.

The public dashboard is available at
[rakshya-clinical-warehouse.streamlit.app](https://rakshya-clinical-warehouse.streamlit.app/).

## Run the complete pipeline

After PostgreSQL is available, run either source through the complete build:

```bash
clinical-dw run --input-dir data/raw

clinical-dw run --source mimic --input-dir data/mimic
```

The command initializes the database, replaces the active dataset, loads
dimensions and facts in dependency order, records source provenance, and
finishes with the data-quality report.

## Cloud deployment

The recommended portfolio deployment keeps source control, the application,
and the database separate:

```text
GitHub repository
├── Streamlit Community Cloud: app.py
└── Neon PostgreSQL: staging and warehouse schemas
```

1. Create a Neon PostgreSQL project and copy its pooled connection string.
2. From this local checkout, load the selected dataset into Neon:

   ```bash
   DATABASE_URL='your-neon-connection-string' \
     clinical-dw run --source mimic --input-dir data/mimic
   ```

3. Push the repository to GitHub.
4. In Streamlit Community Cloud, deploy `app.py` from the `main` branch.
5. Add the connection string in Streamlit Advanced settings:

   ```toml
   DATABASE_URL = "your-neon-connection-string"
   ```

Never commit the hosted connection string or `.streamlit/secrets.toml`.
`requirements.txt` installs this project and its dashboard dependencies in
Streamlit Community Cloud.

### Secure the deployed dashboard with a read-only Neon role

The ETL pipeline needs the owner account because it creates and replaces tables.
The public Streamlit dashboard only runs `SELECT` queries and must use a separate
least-privilege account.

1. Open the Neon SQL Editor as `neondb_owner`.
2. Open [`sql/security/create_streamlit_reader.sql`](sql/security/create_streamlit_reader.sql).
3. Replace the example password with a long, unique generated password and run
   the statements once.
4. In Streamlit Community Cloud, open the app's **Settings → Secrets**.
5. Replace `DATABASE_URL` with the Neon connection string using
   `streamlit_reader` and its new password.
6. Reboot the app. Under **Trust & provenance → Deployment safety**, confirm
   that the dashboard reports a read-only database session.

Keep the owner connection string only in a local environment variable when
running ETL. Never place it in Streamlit Secrets.

### Resilient CDC access

The brain-health explorer prefers the live CDC API. If the API times out or is
unavailable, it automatically uses the committed, compressed cognitive-decline
snapshot and displays a visible fallback label. Snapshot provenance is recorded
in
[`data/brain_health/cdc_cognitive_decline_snapshot.metadata.json`](data/brain_health/cdc_cognitive_decline_snapshot.metadata.json).

## Data-quality interpretation

Both adapters validate source schemas before normalization. The MIMIC demo load
passes normalized row parity, relationship integrity, date ordering, and ETL
run checks. Source duplicates remain visible as a warning rather than being
silently removed.

## Scope and limitations

- The supported adapters target Synthea CSV exports and MIMIC-IV Demo v2.2.
- MIMIC identifiers and dates are deidentified; derived birth dates and
  diagnosis onset dates are documented approximations.
- The project is not designed or approved for protected health information.
- Dashboard summaries demonstrate engineering behavior and must not be
  interpreted as findings about a real patient population.
- This learning-scale star schema is intentionally smaller than production
  standards such as OMOP CDM or FHIR-based clinical platforms.

## Learning path

1. **Source contracts:** inspect `src/clinical_dw/contracts.py`.
2. **Source adapters:** compare `src/clinical_dw/mimic.py` with the Synthea
   staging specifications in `src/clinical_dw/staging.py`.
3. **Transformations:** inspect `src/clinical_dw/transforms.py`.
4. **Warehouse grain:** read `sql/init/002_warehouse.sql`.
5. **Quality checks:** run `pytest -v`.
6. **Calendar analysis:** inspect `load_date_dimension` in
   `src/clinical_dw/warehouse.py` to see how event dates receive reusable
   `YYYYMMDD` keys.

## Repository layout

```text
.
├── data/                  # Local source inputs (ignored by Git)
├── docs/                  # Learning notes and architecture decisions
├── sql/init/              # PostgreSQL initialization scripts
├── src/clinical_dw/       # Python validation and ETL code
├── tests/                 # Unit tests
├── compose.yaml           # Local PostgreSQL service
└── pyproject.toml         # Python package and tooling
```

## Roadmap

- [x] Define architecture and warehouse grain
- [x] Create PostgreSQL staging and warehouse schemas
- [x] Add Synthea source contracts and validation
- [x] Add a MIMIC-IV Demo adapter and dataset provenance
- [x] Add unit-tested transformation helpers
- [x] Load CSVs into staging tables
- [x] Build dimensions and facts transactionally
  - [x] Patient dimension
  - [x] Code dimension
  - [x] Date dimension
  - [x] Encounter fact
  - [x] Condition fact
  - [x] Observation fact
- [x] Add end-to-end data-quality reports
- [x] Add problem-focused analytics and an interactive cohort explorer
- [x] Add a Streamlit dashboard
- [x] Add GitHub Actions CI
- [x] Add a reproducible CDC Healthy Aging downloader and preparation workflow
- [x] Model public US-POINTER results as trial-level evidence
- [x] Add a brain-health evidence view to the Streamlit interface
