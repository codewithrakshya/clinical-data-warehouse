# Clinical Data Warehouse

A portfolio-scale clinical data warehouse built with synthetic
[Synthea](https://synthea.mitre.org/) records, PostgreSQL, and Python.

> This project uses synthetic data only. Never commit protected health
> information (PHI), credentials, or exports from a clinical system.

## What this project demonstrates

- Modeling clinical data for analytics
- Loading messy source CSVs through a reproducible ETL pipeline
- Separating raw/staging data from curated warehouse tables
- Data-quality testing and audit logging
- Containerized local development with PostgreSQL
- Healthcare analytics without exposing real patient information

## Architecture

```text
Synthea CSV files
        |
        v
Python validation and transformation
        |
        v
staging schema (source-shaped tables)
        |
        v
warehouse schema (dimensions + facts)
        |
        v
SQL analytics / future dashboard
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

### 3. Download synthetic Synthea CSV data

Generate or download a Synthea CSV export and place these files under
`data/raw/`:

```text
patients.csv
encounters.csv
conditions.csv
observations.csv
```

See [docs/synthea.md](docs/synthea.md) for options.

### 4. Validate source files

```bash
clinical-dw validate --input-dir data/raw
```

The first milestone implements validation and deterministic transformations.
Database loading is the next milestone.

### 5. Run tests

```bash
pytest
```

## Learning path

1. **Source contracts:** inspect `src/clinical_dw/contracts.py`.
2. **Transformations:** inspect `src/clinical_dw/transforms.py`.
3. **Warehouse grain:** read `sql/init/002_warehouse.sql`.
4. **Quality checks:** run `pytest -v`.
5. **Next milestone:** load validated rows into staging and populate facts and
   dimensions transactionally.

## Repository layout

```text
.
├── data/                  # Local synthetic inputs (ignored by Git)
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
- [x] Add unit-tested transformation helpers
- [ ] Load CSVs into staging tables
- [ ] Build dimensions and facts transactionally
- [ ] Add end-to-end data-quality tests
- [ ] Add analytical SQL examples
- [ ] Add a Streamlit dashboard
- [ ] Add GitHub Actions CI
