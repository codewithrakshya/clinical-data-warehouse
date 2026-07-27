# Project status and roadmap

## Purpose

This roadmap records what is complete, what remains valuable, and what should
stay outside the current scope. It is intentionally prioritized so the project
does not grow through unrelated features.

## Current release status

The project currently provides:

- Synthea and MIMIC-IV Demo source adapters;
- validated, transactional staging loads;
- patient, code, and date dimensions;
- encounter, condition, and observation facts;
- ETL audit history and structural quality checks;
- a Streamlit cohort builder and clinical-pattern explorer;
- a Brain Health Evidence Explorer;
- modeled publication-level US-POINTER results;
- interactive CDC comparisons across demographic and geographic strata;
- a versioned CDC API fallback;
- a read-only Neon role for the public dashboard;
- visible deployment-safety and provenance information;
- automated tests and GitHub Actions; and
- public Streamlit deployment.

This is a credible stopping point for the current engineering milestone.

## Immediate documentation milestone

- [x] Explain the problem, users, and use cases.
- [x] Document the end-to-end system design.
- [x] Define patient-level versus aggregate evidence boundaries.
- [x] Document the read-only deployment model.
- [x] Document the CDC fallback and evidence limitations.
- [x] Record remaining work in priority order.

## Next priority: publication-ready reproducibility

These tasks would add the most credibility without changing the product's
scope.

### 1. Create one reproducible case study

Add a notebook or scripted report that:

- states one narrow, descriptive research question;
- identifies the exact source and population;
- queries the warehouse reproducibly;
- includes a data dictionary for every selected variable;
- reports missingness and exclusions;
- generates one or two final tables or figures; and
- includes an interpretation and limitations section.

The case study should demonstrate the analytical value of the warehouse. It
should not claim a new clinical discovery from the 100-patient MIMIC demo.

### 2. Prepare a citable software release

- Add `CITATION.cff`.
- Pin or lock the release environment.
- Create a `v1.0.0` GitHub release.
- Archive the release through Zenodo for a DOI.
- Add the DOI and citation badge to the README.
- Record the exact deployed data versions.

### 3. Add a compact data dictionary

Document for each warehouse field:

- table and column;
- data type;
- row grain;
- source mapping;
- transformation or derivation;
- nullability; and
- interpretation limitation.

This is especially important for approximate MIMIC birth dates, diagnosis
onset dates, race labels, shifted dates, and code namespaces.

## Next engineering priority: safer dataset publication

### 4. Make complete warehouse builds atomic

The current pipeline resets and reloads the active warehouse in entity-sized
transactions. A late failure can leave the active warehouse incomplete.

A stronger design would:

1. create a versioned build schema or dataset version;
2. load and validate every entity there;
3. run all blocking quality checks;
4. publish the completed build with one atomic view or schema swap; and
5. retain or clean up the prior version according to policy.

### 5. Introduce schema migrations

Replace purely idempotent initialization with a migration tool or numbered
migration ledger. This would make structural changes reviewable, ordered, and
repeatable across local and hosted databases.

### 6. Strengthen CDC version management

- Add a documented snapshot refresh command.
- Validate snapshot metadata and checksum in tests.
- Record the CDC dataset update timestamp in the interface.
- Define when a snapshot should be refreshed.
- Compare a new snapshot with the prior version before replacement.

### 7. Add a deployed smoke test

Add a lightweight check that confirms:

- the public application starts;
- the landing page renders;
- the clinical warehouse query succeeds;
- the database session reports read-only;
- US-POINTER evidence loads; and
- either the live CDC API or fallback loads.

Do not place production credentials in pull-request workflows.

## Research-quality improvements

### 8. Expand data-quality semantics

Potential additions:

- missingness by field and source;
- orphan optional encounter-link rates;
- code-description coverage;
- numeric observation plausibility checks by code and unit;
- unexpected-unit distributions;
- duplicate classifications rather than one exact-duplicate count;
- encounter and observation temporal consistency;
- quality results tied to a specific dataset version; and
- explicit blocking versus advisory quality policies.

Clinical plausibility rules require domain review and should not be added as
universal truths without evidence.

### 9. Improve CDC statistical context

The dashboard can compare published estimates and confidence intervals, but it
does not perform a new BRFSS survey analysis. Useful improvements include:

- clearer sample-size and suppression metadata where available;
- more explanation of weighting and survey design;
- careful handling of non-comparable years or question definitions;
- region-versus-state comparison guidance; and
- downloadable filtered aggregate results with source metadata.

### 10. Improve cohort definition transparency

- Display the generated cohort criteria as plain language.
- Add an explicit inclusion/exclusion summary.
- Version or hash cohort definitions.
- Export provenance and criteria alongside the cohort CSV.
- Add exact code selection rather than diagnosis text search alone.
- Distinguish feasibility counts from an analysis-ready cohort dataset.

## Operational improvements

### 11. Add basic monitoring

- Document where Streamlit and Neon logs are found.
- Add a non-sensitive health check.
- Define what constitutes an outage.
- Record expected response behavior when CDC is unavailable.
- Consider alerting only if the project becomes actively maintained.

### 12. Improve secrets and access lifecycle

- Maintain separate ETL-owner and dashboard-reader credentials.
- Rotate both credentials periodically and after accidental exposure.
- Document reader-role recreation and revocation.
- Confirm default privileges whenever new schemas are introduced.
- Never use owner credentials in Streamlit or CI.

## Optional future extensions

These are worthwhile only after the reproducibility and release milestones.

- Add another unrestricted public-health source with a clearly distinct
  research question.
- Add an OMOP-inspired export or mapping demonstration.
- Separate the backend query layer from Streamlit.
- Add saved cohort definitions without storing sensitive patient data.
- Add accessibility and mobile-layout testing.
- Add a formal architecture decision record directory.

## Deliberately deferred

The following should not be treated as near-term tasks:

- requesting or ingesting controlled Alzheimer disease datasets;
- uploading institutional EHR data;
- supporting protected health information;
- building predictive clinical models from the 100-patient MIMIC demo;
- presenting individual risk scores;
- diagnosing cognitive decline;
- combining CDC and US-POINTER values into one effect estimate;
- replacing established standards such as OMOP or FHIR; or
- claiming production or regulatory readiness.

These directions require additional data rights, governance, statistical
design, clinical review, privacy controls, and institutional infrastructure.

## Recommended next milestone

The best next milestone is:

> **Publish a reproducible, descriptive case study and create a citable v1.0
> software release.**

This would strengthen the project more than adding another dashboard feature.
It would demonstrate that the platform can support a transparent analytical
workflow while preserving its data and inference boundaries.

