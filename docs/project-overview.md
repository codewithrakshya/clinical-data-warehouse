# Clinical Data Trust Lab: project overview

## One-sentence explanation

The Clinical Data Trust Lab turns differently structured clinical datasets
into one validated, auditable warehouse so researchers can define cohorts and
explore the available data without rebuilding source-specific cleaning and
joining logic for every question. Its connected Brain Health Evidence Explorer
also places randomized US-POINTER findings beside CDC surveillance patterns
without treating the two evidence designs as interchangeable.

## What problem does it solve?

Clinical data rarely arrive ready for analysis. One source may call a patient
`Id`, another may use `subject_id`, and another may use a completely different
identifier. Diagnoses, laboratory measurements, visits, dates, and missing
values can also be represented differently.

Before answering a research question, a team therefore has to determine:

- Which files and columns are required?
- What does one row represent?
- How are patients, encounters, diagnoses, and observations connected?
- Which codes describe a diagnosis or laboratory test?
- Are dates and numeric values valid?
- Did any records disappear or lose their relationships during transformation?
- Can another analyst reproduce the same cohort?

That preparation is often repeated in notebooks or one-off scripts. The result
may work for a single analysis but be difficult to audit, reuse, or adapt to a
second dataset.

This project moves that repeated work into a tested pipeline and a common
warehouse model.

## Why was it made?

The project was made to demonstrate an end-to-end approach to trustworthy
clinical data engineering:

1. Accept more than one source format.
2. Validate each source before changing the database.
3. Normalize source-specific fields into shared clinical concepts.
4. Preserve provenance and ETL history.
5. Test row parity, relationships, and date logic.
6. Give researchers an interactive way to define and export a cohort.
7. State privacy and interpretation limitations directly in the interface.

It is both a working portfolio project and a learning environment for clinical
data modeling, PostgreSQL, ETL design, data quality, reproducibility, and
research-facing application development.

## What is distinctive about it?

The project does **not** claim to invent a new database theory, clinical
standard, or cohort algorithm. Its contribution is the integration of several
good practices into a small, inspectable system.

### 1. One analytical model, multiple source adapters

Synthea and MIMIC-IV Demo have different file structures. Separate adapters
translate both into the same patient, encounter, condition, observation, code,
and date concepts. The downstream quality checks and dashboard queries do not
need to be rewritten for each source.

### 2. Trust is part of the product

The application does not present charts as if loading data were automatically
successful. It exposes row parity, broken relationships, duplicate warnings,
invalid date ordering, and failed ETL runs. Warnings remain visible instead of
being silently removed.

### 3. Cohort discovery is connected to the warehouse

Users can filter across demographics, encounter types, diagnosis descriptions,
and utilization thresholds. The cohort metrics and export are generated from
connected warehouse facts rather than from isolated source files.

### 4. Provenance and limitations travel with the analysis

The active dataset, source version, load time, citation, and known limitations
appear in the application. MIMIC's shifted dates and the project's derived date
assumptions are stated explicitly.

### 5. The implementation is deliberately understandable

The schema is smaller than OMOP CDM or a complete FHIR platform. That makes the
source mappings, transformations, SQL tables, quality checks, and interface
practical to inspect from end to end.

### 6. Different evidence types remain different products

Patient-level clinical records populate the warehouse. CDC surveillance
estimates and US-POINTER publication-level outcomes remain in separate
aggregate evidence services. The interface labels randomized versus
observational evidence and states what each source can support.

## Who is it for?

### Biomedical and population-health researchers

Researchers can inspect what data are available, define a preliminary cohort,
review quality evidence, and export a deidentified patient-level summary before
writing a full statistical analysis.

### Bioinformaticians and clinical data analysts

Analysts can reuse normalized identifiers, coded concepts, dates, and
relationships instead of repeating foundational cleaning and joining work.

### Research software and data engineers

Engineers can use the project as a reference for source adapters,
transactional staging loads, dimensional modeling, ETL audit records, and
quality gates.

### Students and trainees

Learners can trace a clinical record from a compressed CSV through validation,
staging, transformation, warehouse keys, quality checks, SQL queries, and a
deployed interface.

### Laboratories evaluating a new dataset

A lab can adapt the pattern to assess the structure and feasibility of a new
deidentified dataset before investing in a larger analytical workflow.

## Who benefits?

| Stakeholder | Benefit |
| --- | --- |
| Researcher | Faster cohort feasibility checks and fewer repeated joins |
| Analyst | Consistent variables, codes, dates, and reusable SQL |
| Data engineer | Explicit contracts, source adapters, and auditable loads |
| Research lead | Visible quality evidence and clearer limitations |
| Collaborator | A reproducible shared model instead of a private notebook |
| Learner | An understandable example of a complete clinical data pipeline |

The patients represented in the source data do **not** interact with this
application. This is a research data-engineering tool, not a patient portal.

## Primary use cases

### Cohort feasibility

Example question:

> How many deidentified patients have a diagnosis containing “diabetes,” at
> least one admission, and laboratory observations available?

The cohort builder returns the matching patient count, share of the source
population, connected encounters, diagnoses, and observations. It can export a
patient-level summary for additional analysis.

### Source harmonization

A team can add another adapter that maps a new source's patient, encounter,
diagnosis, and observation fields into the common staging model.

### Data-quality review

The quality report checks whether normalized staging rows reached the
warehouse, whether required dimension links resolve, whether clinical dates
are ordered correctly, and whether ETL failures or exact duplicates require
review.

### Research onboarding

A new collaborator can use the interface and documentation to understand the
source, warehouse grain, available concepts, record counts, assumptions, and
limitations.

### Reproducible engineering demonstrations

The same repository supports local Docker PostgreSQL, hosted Neon PostgreSQL,
automated tests, and a public Streamlit interface.

## How does it work?

```text
Synthea CSVs ─────┐
                  │
MIMIC-IV CSVs ────┼──> Source contract validation
                  │
Future adapter ───┘
                          |
                          v
                 Common staging tables
              patients / encounters / conditions /
                       observations
                          |
                          v
                 Typed transformations
              identifiers / timestamps / numeric values /
                     clinical code dictionaries
                          |
                          v
                  PostgreSQL warehouse
              patient + date + code dimensions
              encounter + condition + observation facts
                          |
                  +-------+-------+
                  |               |
                  v               v
           Quality evidence   Cohort queries
                  |               |
                  +-------+-------+
                          |
                          v
                 Streamlit interface
```

### Step 1: Select a source

The CLI accepts either:

```bash
clinical-dw run --source synthea --input-dir data/raw
```

or:

```bash
clinical-dw run --source mimic --input-dir data/mimic
```

### Step 2: Validate source contracts

The pipeline confirms that every required file exists, required columns are
present, and the files contain data. If validation fails, staging tables are
not replaced.

### Step 3: Normalize into common staging tables

Source adapters translate the original column names and structures into four
common staging entities:

- patients
- encounters
- conditions
- observations

MIMIC diagnosis and laboratory dictionaries provide human-readable
descriptions. Source identifiers receive stable prefixes to retain provenance.

### Step 4: Build warehouse dimensions and facts

Python transformations convert source text into typed dates, timestamps,
numeric values, and optional values. PostgreSQL keys connect:

- encounters to patients;
- diagnoses to patients, encounters, and codes;
- observations to patients, optional encounters, and codes; and
- clinical events to a shared date dimension.

### Step 5: Record operational history

Each entity load writes an `etl_run` record containing status, start and
completion times, rows read, rows loaded, and any error message.

### Step 6: Run quality checks

The pipeline checks:

- staging-to-warehouse row parity;
- broken patient, encounter, code, and date relationships;
- failed ETL runs;
- exact source observation duplicates; and
- invalid date ordering.

### Step 7: Explore and export a cohort

The application queries the warehouse to apply patient and clinical filters.
It recalculates cohort size and event counts and generates a deidentified CSV
summary for downstream research work.

## Example user journey

1. A researcher opens the public application.
2. The landing page explains the data harmonization problem and identifies the
   active source.
3. The researcher reviews how source tables map into the warehouse.
4. In **Build a cohort**, the researcher enters `diabetes`.
5. The application searches normalized diagnosis descriptions and returns the
   matching patients with connected encounter and observation counts.
6. The researcher adds demographic or encounter filters.
7. The researcher downloads the resulting deidentified cohort summary.
8. Before interpreting it, the researcher reviews **Trust & provenance** for
   warnings, source details, and known limitations.

## Data sources

### MIMIC-IV Clinical Database Demo v2.2

The active public deployment uses the openly available MIMIC-IV Demo, a
deidentified subset of 100 patients derived from electronic health records.
Identifiers and dates have been transformed, and free-text clinical notes are
excluded.

The project uses:

- patients;
- hospital admissions;
- ICD diagnoses and their dictionary; and
- laboratory events and their dictionary.

See [MIMIC source documentation](mimic-iv-demo.md).

### Synthea

Synthea generates realistic but synthetic patient histories. It remains the
deterministic test and teaching source for the pipeline.

See [Synthea source documentation](synthea.md).

### CDC Alzheimer's Disease and Healthy Aging

The explorer uses unrestricted aggregate Cognitive Decline estimates from the
CDC dataset, primarily derived from BRFSS. Users can compare available
estimates by year, state or region, age, sex, race/ethnicity, and confidence
interval width. The deployed app uses a visibly labeled versioned fallback if
the live CDC API is unavailable.

See [CDC source documentation](cdc-healthy-aging.md).

### Published US-POINTER evidence

The explorer models selected aggregate outcomes reported in the peer-reviewed
US-POINTER publication. These are publication-level randomized trial results,
not participant-level trial data available through this repository.

See [US-POINTER evidence documentation](us-pointer-evidence.md).

## What can users safely conclude?

Users can evaluate:

- whether the pipeline loaded and connected records correctly;
- which data concepts and code descriptions are represented;
- whether a proposed cohort can be expressed with the available fields;
- whether quality warnings require investigation; and
- how the same warehouse pattern can support multiple sources.

Users should **not** conclude:

- that dashboard summaries represent a hospital or general population;
- that an association is clinically meaningful;
- that shifted dates describe real calendar trends;
- that derived birth or diagnosis dates are exact;
- that the application supports clinical decisions; or
- that the system is approved for identifiable or protected health
  information.

## Privacy and security boundary

- The public deployment contains only synthetic or openly available
  deidentified demo data.
- Raw source files and credentials are ignored by Git.
- Database credentials belong in environment variables or Streamlit secrets.
- The project is not a HIPAA-compliant clinical system.
- It should not receive PHI, direct identifiers, clinical notes, or private
  institutional exports.

## What would be required for institutional use?

Using the pattern with institutional data would require work beyond this
portfolio project, including:

- institutional approval and a data-use agreement;
- secure infrastructure and access controls;
- a read-only application database role;
- encryption, logging, monitoring, backups, and incident procedures;
- formal terminology and source-to-standard mappings;
- validation with clinical and domain experts;
- versioned schema migrations;
- more extensive data-quality rules;
- privacy review and suppression policies; and
- governance for cohort exports.

## Short project description

> The Clinical Data Trust Lab is a multi-source clinical data warehouse and
> interactive cohort explorer. It validates Synthea and MIMIC-IV Demo files,
> harmonizes patients, encounters, diagnoses, laboratory observations, codes,
> and dates into a shared PostgreSQL model, exposes quality and provenance
> evidence, and lets researchers define and export deidentified cohorts.
