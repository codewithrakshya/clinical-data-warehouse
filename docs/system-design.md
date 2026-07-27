# Clinical Data Trust Lab: system design

## Purpose of this document

This document explains the system as an engineering and research product:

- the problem it is designed to solve;
- the people and workflows it supports;
- the boundaries between its two analytical products;
- how data move from files and public evidence into the interface;
- why the database, pipeline, quality, security, and deployment layers are
  designed this way;
- what users may and may not infer from the results; and
- what would have to change before using the pattern with institutional data.

For installation commands, see the [README](../README.md). For a shorter
nontechnical explanation, see the [project overview](project-overview.md). For
planned work, see the [project roadmap](roadmap.md).

## Executive summary

The Clinical Data Trust Lab is a research-facing data platform with two
connected products:

1. **Clinical Data Warehouse** — validates differently structured clinical
   files, translates them into a common model, records provenance and quality
   evidence, and supports cohort feasibility exploration.
2. **Brain Health Evidence Explorer** — presents published randomized
   US-POINTER results alongside CDC population-surveillance estimates while
   preserving the different inference allowed by each evidence type.

The central design principle is **trust before analysis**. A chart or cohort
count is useful only when the user can identify its source, understand the
grain of the underlying data, review transformation assumptions, see quality
warnings, and recognize the limits of the evidence.

This is a research-scale software system and public demonstration. It is not an electronic
health record, clinical decision-support application, patient portal,
production OMOP implementation, or HIPAA-compliant data platform.

## The problem being solved

Clinical and public-health data are fragmented in two different ways.

### Structural fragmentation

Clinical sources represent the same concepts differently:

- patient identifiers may be named `Id`, `subject_id`, or something else;
- a visit may mean an outpatient encounter in one source and a hospital
  admission in another;
- diagnosis and laboratory descriptions may live in separate dictionaries;
- dates, missing values, numeric values, and codes may have incompatible
  formats; and
- relationships between patients, encounters, diagnoses, and observations may
  be incomplete.

Without a reusable data layer, every analysis begins with another set of
one-off cleaning scripts and joins.

### Evidence fragmentation

Evidence about brain health also comes from sources that answer different
questions:

- a randomized trial estimates the effect of an intervention comparison;
- a surveillance survey describes where and among whom a condition or concern
  is reported; and
- a clinical dataset describes the records captured by a healthcare system or
  demonstration database.

Displaying these sources together without labeling their designs can encourage
causal overinterpretation. The explorer therefore keeps randomized,
observational, and clinical-record evidence conceptually and technically
separate.

## Intended users and use cases

| User | Primary need | Supported workflow |
| --- | --- | --- |
| Biomedical researcher | Determine whether a dataset can express a proposed cohort | Filter demographics, encounters, diagnoses, and utilization; review counts |
| Clinical data analyst | Avoid rebuilding foundational joins | Query reusable patient, code, date, and event tables |
| Research data engineer | Add or evaluate a new source | Implement a source contract and adapter into common staging |
| Research lead | Understand whether results are trustworthy | Review parity, link integrity, ETL history, provenance, and limitations |
| Population-health researcher | Explore reported cognitive-decline patterns | Compare CDC estimates across geography and demographic strata |
| Student or trainee | Learn an end-to-end clinical data system | Trace a record from source file through validation, PostgreSQL, and Streamlit |
| Research collaborator | Evaluate whether the system fits a shared workflow | Inspect tested behavior, assumptions, provenance, and documentation |

### Supported use cases

- source validation and schema-drift detection;
- deterministic ETL into a compact analytical warehouse;
- preliminary cohort feasibility and deidentified summary export;
- structural data-quality review;
- source and pipeline provenance review;
- comparison of published US-POINTER outcomes;
- exploration of CDC estimates by year, location, age, sex, race/ethnicity,
  and confidence-interval width; and
- teaching clinical data modeling and evidence interpretation.

### Explicit non-use cases

The system must not be used for:

- patient care, diagnosis, treatment, or risk communication;
- clinical decision support;
- uploading protected health information or direct identifiers;
- estimating hospital or national prevalence from MIMIC-IV Demo;
- treating shifted MIMIC dates as real calendar trends;
- claiming that CDC surveillance differences are causal;
- claiming that the modeled US-POINTER publication table is participant-level
  trial data; or
- claiming that US-POINTER proves prevention of Alzheimer disease or dementia.

## System context

```text
                         DEVELOPMENT AND LOAD PATH

  Synthea CSVs ─┐
                ├─> contracts ─> source adapters ─> common staging
  MIMIC files ──┘                                      |
                                                       v
                                              typed transformations
                                                       |
                                                       v
                                                Neon PostgreSQL
                                          staging + warehouse schemas
                                                       |
                         PUBLIC READ PATH              | SELECT only
                                                       v
  US-POINTER CSV ───────────────────────────────> Streamlit application
                                                       ^
  CDC API ──> normalized response ─────────────────────┤
     └─────> versioned fallback snapshot ──────────────┘
```

GitHub stores source code, tests, documentation, the small published
US-POINTER evidence table, and the compressed CDC fallback. GitHub Actions
tests the code. Streamlit Community Cloud runs the interface. Neon hosts the
PostgreSQL warehouse.

The ETL writer and public dashboard deliberately use different database
credentials:

- `neondb_owner` is used temporarily by the developer to initialize and load
  data; and
- `streamlit_reader` is used by the deployed application and can only read the
  required schemas.

## Major components

| Component | Location | Responsibility |
| --- | --- | --- |
| CLI | `src/clinical_dw/cli.py` | Exposes validation, loading, quality, and CDC preparation commands |
| Source contracts | `src/clinical_dw/contracts.py` | Defines required files and columns |
| Source I/O | `src/clinical_dw/source_io.py` | Reads plain or compressed source files |
| Synthea mapping | `src/clinical_dw/staging.py` | Maps standard Synthea exports into common staging |
| MIMIC adapter | `src/clinical_dw/mimic.py` | Maps MIMIC Demo tables and dictionaries into common staging |
| Transformations | `src/clinical_dw/transforms.py`, `warehouse.py` | Converts source text into typed analytical records |
| Pipeline orchestration | `src/clinical_dw/pipeline.py` | Runs initialization and loads entities in dependency order |
| Database definition | `sql/init/` | Creates schemas, tables, constraints, and indexes |
| Quality service | `src/clinical_dw/quality.py` | Evaluates parity, relationships, ETL status, duplicates, and dates |
| CDC service | `src/clinical_dw/cdc_aging.py` | Retrieves, normalizes, summarizes, and falls back to a snapshot |
| US-POINTER service | `src/clinical_dw/us_pointer.py` | Validates the locally modeled publication-level outcomes |
| Interface | `app.py` | Provides cohort, patterns, evidence, quality, and provenance views |
| Tests | `tests/` | Verify contracts, adapters, transformations, loading, quality, and evidence |

## Why the system has two analytical products

The products share a mission—making biomedical evidence easier to inspect—but
they do not share one data model.

### Product 1: Clinical Data Warehouse

This product works with patient-level, deidentified or synthetic clinical
records. Its unit of analysis may be a patient, encounter, diagnosis episode,
or observation.

It supports questions such as:

> Does this source contain patients with a diabetes-related diagnosis, at
> least one encounter, and laboratory observations?

### Product 2: Brain Health Evidence Explorer

This product works with aggregate evidence.

- US-POINTER rows represent outcomes reported in a publication.
- CDC rows represent survey estimates for a location, period, question, and
  population stratum.

It supports questions such as:

> What did the randomized intervention comparison report, and how do reported
> cognitive-decline estimates vary across public-health strata?

The CDC and US-POINTER records are not loaded into the clinical fact tables.
This prevents aggregate estimates from being mistaken for patient events and
prevents incompatible evidence types from being pooled accidentally.

## Clinical ingestion design

### 1. Source contracts

Every supported source declares required files and columns. Validation happens
before staging tables are changed. A missing file, missing column, or empty
required input fails early with a source-specific message.

This protects the existing database from partial replacement when an input
export is incomplete or its schema has drifted.

### 2. Source adapters

Adapters translate source-specific structures into four shared staging
entities:

- `patients`;
- `encounters`;
- `conditions`; and
- `observations`.

Synthea columns map directly from its CSV export. The MIMIC adapter performs
additional work:

- derives an approximate birth date from anchor year and anchor age;
- uses the first recorded admission race as the available patient race label;
- represents admissions as encounters;
- resolves ICD descriptions through the diagnosis dictionary;
- resolves laboratory labels and categories through the item dictionary; and
- prefixes source identifiers to preserve their namespace.

These are declared engineering assumptions, not hidden clinical facts.

### 3. Common staging

Staging columns remain text shaped. Their job is to preserve normalized source
values before analytical typing, not to pretend the values are already clean.

All four staging tables are truncated and replaced inside one transaction. If
validation or copying fails, PostgreSQL rolls back the staging replacement.

### 4. Typed transformations

Transformation functions convert and validate:

- required and optional text;
- dates and timestamps;
- decimal values;
- numeric versus textual observations;
- temporal ordering; and
- required identifiers and code values.

Invalid required values fail the relevant load. PostgreSQL constraints provide
a second layer of protection for temporal relationships and foreign keys.

### 5. Dependency-ordered warehouse loading

The complete pipeline loads:

```text
patients
   |
   v
encounters
   |
   +--------+
   v        v
conditions observations
   \        /
    \      /
     v    v
    date dimension and date keys
```

The active analytical dataset is replaced rather than appended. Historical
`etl_run` rows remain so failures and prior operations are still visible.

## Warehouse data model

The warehouse uses a small star-like model.

| Table | Grain | Natural/source identity | Important relationships |
| --- | --- | --- | --- |
| `dim_patient` | One row per source patient | `source_patient_id` | Parent of all clinical facts |
| `dim_code` | One row per coding system and code | `(code_system, code)` | Describes conditions and observations |
| `dim_date` | One row per calendar date | `full_date`, `YYYYMMDD date_key` | Shared calendar for event dates |
| `fact_encounter` | One row per source encounter/admission | `source_encounter_id` | Patient and start/stop dates |
| `fact_condition` | One diagnosis episode | Generated key | Patient, optional encounter, code, onset/resolution dates |
| `fact_observation` | One measured or textual result | Generated key | Patient, optional encounter, code, observation date |
| `dataset_metadata` | One row describing the active source | Fixed key `1` | Source label, version, synthetic flag, load time |
| `etl_run` | One attempted entity load | Generated run ID | Status, timing, row counts, error |

### Why a compact star schema?

It makes table grain, keys, mappings, and joins inspectable. A complete OMOP
CDM or FHIR platform would provide much broader interoperability, but would
also introduce terminology, governance, and implementation complexity beyond
the educational and research-demonstration purpose of this project.

### Important modeling boundaries

- A missing encounter link is permitted for conditions and observations when
  the source does not provide one.
- A patient, code, and date link is required for every applicable fact.
- Numeric and textual observation values are stored separately.
- A code is unique only within its code system.
- Only one clinical source populates the active warehouse at a time.
- The MIMIC-derived birth and diagnosis onset dates are approximations.

## Pipeline behavior and failure model

`clinical-dw run` performs:

1. idempotent schema initialization;
2. source validation;
3. atomic staging replacement;
4. active warehouse reset;
5. patient loading;
6. encounter loading;
7. condition loading;
8. observation loading;
9. date-dimension construction and fact-key attachment;
10. active-source metadata update; and
11. quality checks.

Each entity load writes a durable ETL record. A failed transformation updates
that run to `failed`, stores a bounded error message, rolls back the entity
transaction, and raises the exception.

### Current atomicity limitation

The complete multi-step run is not one database-wide transaction. Staging is
atomic and each entity load is transactional, but a failure late in the
pipeline can leave an incomplete active warehouse until the pipeline is run
again successfully. A production evolution should load into a versioned build
schema and publish it with an atomic swap.

## Data-quality design

The quality layer currently distinguishes:

- **PASS** — the structural expectation is satisfied;
- **WARN** — analysis may proceed only after reviewing a visible issue; and
- **FAIL** — the warehouse should not be treated as analysis ready.

Checks cover:

| Check | Why it matters | Current severity |
| --- | --- | --- |
| Staging-to-warehouse row parity | Detects records lost during transformation | Fail |
| Broken dimension relationships | Prevents orphan clinical facts | Fail |
| Failed ETL history | Preserves operational problems | Warning |
| Exact source observation duplicates | Avoids silently hiding questionable source rows | Warning |
| Invalid date ordering | Prevents impossible temporal sequences | Fail |

Passing these checks establishes structural consistency. It does **not**
establish clinical correctness, absence of bias, fitness for a specific
scientific question, or correctness of source coding.

## Cohort-query design

The cohort builder queries normalized warehouse entities rather than source
files. Filters may combine:

- sex at birth;
- source race label;
- encounter/admission type;
- minimum encounter count; and
- diagnosis-description text.

The output is a deidentified patient-level feasibility summary with connected
encounter, diagnosis, and observation counts. It is not a statistical analysis
dataset and does not adjust for censoring, repeated measures, confounding,
selection bias, or survey design.

All variable user inputs are passed as database parameters. They are not
interpolated into SQL values.

## Brain-health evidence design

### US-POINTER

The repository contains a small, validated table transcribed from the
peer-reviewed publication. Validation confirms expected columns, numeric
types, unique outcomes, source URL, and ordered confidence limits.

The interface labels this as randomized evidence and reports the comparison
described by the publication. It does not claim access to participant-level
US-POINTER data.

### CDC Healthy Aging

The CDC service:

1. requests Cognitive Decline records from the public Socrata API;
2. normalizes column names and numeric types;
3. retains unavailable or suppressed estimates as a quality signal;
4. calculates confidence-interval width; and
5. supports comparisons by indicator, year, geography, age, sex, and
   race/ethnicity.

These are aggregate surveillance estimates, derived primarily from BRFSS. They
are observational, self-reported, and subject to survey-design and
nonresponse considerations.

### CDC resilience

The deployed app prefers the live API. If the request fails, it loads the
compressed, versioned Cognitive Decline snapshot stored in the repository. The
interface visibly identifies whether it is using the live API or the fallback.

The fallback improves availability; it does not replace a formal data-version
policy. Its retrieval date and source filter are stored in adjacent metadata.

## Runtime and deployment design

```text
Developer machine
  ├── Docker PostgreSQL for local learning and tests
  └── owner connection for intentional cloud ETL

GitHub
  ├── source control
  ├── CI tests
  └── deployment source for Streamlit

Streamlit Community Cloud
  ├── executes app.py
  ├── stores DATABASE_URL as a secret
  └── connects with streamlit_reader

Neon PostgreSQL
  ├── staging schema
  ├── warehouse schema
  └── read-only public application role
```

The dashboard caches database queries briefly and CDC API results for longer.
This reduces repeated work while keeping operational and evidence views
reasonably current.

## Security and privacy design

### Current safeguards

- The public warehouse uses MIMIC-IV Demo, not an institutional EHR extract.
- Synthea remains available for synthetic testing.
- Raw local data and secrets are excluded from source control.
- Streamlit uses `streamlit_reader`, which has schema usage and table `SELECT`
  privileges only.
- The read-only role also defaults sessions to read-only as defense in depth.
- The app displays whether its current database session is read-only.
- ETL owner credentials are not stored in Streamlit.
- The CDC and US-POINTER components contain aggregate evidence, not patient
  records.

### Trust boundaries

| Boundary | Trusted action | Prohibited or untrusted action |
| --- | --- | --- |
| Source input | Open, synthetic, or approved deidentified data | PHI or private institutional exports |
| ETL connection | Temporary owner-level load by the developer | Owner credential in a public app |
| Streamlit connection | Parameterized read-only queries | DDL, writes, or unrestricted credentials |
| Cohort export | Deidentified demo summary | Direct identifiers or unsuppressed institutional cohorts |
| Evidence interpretation | Labeled descriptive or randomized evidence | Unlabeled causal or clinical claims |

### Not a compliance claim

These controls are appropriate for the current public demonstration. They do
not make the system HIPAA compliant or ready to receive regulated data.

## Reliability and observability

Current reliability mechanisms include:

- transactional staging replacement;
- transaction-scoped entity loads;
- database constraints and foreign keys;
- ETL audit records;
- visible quality checks;
- unit and integration tests;
- GitHub Actions;
- CDC API caching and fallback; and
- visible source, version, load time, and read-only status.

Current observability is intentionally simple. There is no centralized log
aggregation, alerting, uptime objective, query tracing, or automated rollback.
Streamlit and Neon platform logs remain the primary operational diagnostic
sources.

## Research and interpretation safeguards

Before presenting a result, ask:

1. What is the unit of observation?
2. Is the source synthetic, deidentified clinical data, observational survey
   evidence, or randomized evidence?
3. Does the metric describe records, people, survey respondents, or a
   publication-level effect?
4. Are dates exact, shifted, or derived?
5. Are missing and suppressed values visible?
6. Does the confidence interval describe survey uncertainty or a randomized
   treatment comparison?
7. Is the proposed statement descriptive, associative, or causal?
8. Is the source population suitable for the intended inference?

The interface supports evidence exploration. Final scientific claims require a
prespecified analysis plan, appropriate statistical methods, source-specific
domain review, and reproducible analysis code.

## Important technical limitations

- The public MIMIC demo contains only 100 patients.
- Only one patient-level source is active in the warehouse at a time.
- Full pipeline publication is not atomic across all entities.
- The schema is not a complete clinical common data model.
- Terminology mapping is source preserving rather than standardized to a
  single vocabulary.
- Diagnosis text search is simple case-insensitive substring matching.
- Cohort export has no institutional suppression or disclosure-control policy.
- CDC exploration does not currently reproduce BRFSS survey-weighted
  inferential analyses.
- CDC fallback refresh is manual.
- Streamlit is a single application layer, not a separate API and frontend.
- Platform-level monitoring and automated recovery are limited.

## Evolution path for a production research platform

A production implementation would likely add:

- versioned database migrations;
- immutable dataset builds and atomic publication;
- separate development, staging, and production environments;
- role-based access control and identity management;
- encrypted backups, recovery testing, audit-log retention, and alerting;
- a terminology service and governed mappings;
- formal data contracts with schema versions;
- orchestration with retries, idempotency, scheduling, and lineage;
- privacy review, minimum-cell suppression, and controlled cohort export;
- validated statistical pipelines;
- an application API separate from the presentation layer; and
- institutional security, legal, and scientific governance.

## Design decisions worth preserving

1. **Validate before mutation.**
2. **Keep source-specific logic in adapters.**
3. **Preserve a stable downstream model.**
4. **Make table grain explicit.**
5. **Separate aggregate evidence from patient facts.**
6. **Show quality warnings rather than silently cleaning them away.**
7. **Label evidence design and inference limits next to results.**
8. **Use least-privilege credentials for public applications.**
9. **Keep provenance with every deployed analytical view.**
10. **Prefer a small system that can be understood end to end.**

## Glossary

| Term | Meaning in this project |
| --- | --- |
| Adapter | Source-specific code that translates an input dataset into common staging |
| Cohort | A set of deidentified patients meeting selected feasibility criteria |
| Contract | Required files and columns expected from a source |
| Dimension | A reusable descriptive entity such as patient, code, or date |
| Fact | An event or observation connected to dimensions |
| Grain | What exactly one row represents |
| ETL | Extract, transform, and load |
| Parity | Agreement between staged and warehouse row counts |
| Provenance | Information about source, version, timing, and transformations |
| Staging | Source-preserving normalized tables before analytical typing |
| Warehouse | Curated relational tables designed for repeatable analysis |
| Observational evidence | Describes patterns without randomized exposure assignment |
| Randomized evidence | Compares groups assigned by a random process |
