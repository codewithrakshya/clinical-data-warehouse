# MIMIC-IV Clinical Database Demo source

The [MIMIC-IV Clinical Database Demo
v2.2](https://physionet.org/content/mimic-iv-demo/2.2/) is an openly
available subset of 100 deidentified patients from MIMIC-IV. It is derived
from real electronic health records at Beth Israel Deaconess Medical Center,
but identifiers and dates have been transformed to protect privacy. Free-text
clinical notes are excluded.

The files are distributed by PhysioNet under the Open Data Commons Open
Database License v1.0. Do not treat the demo as identified clinical data or
interpret dashboard summaries as clinical findings.

## Download

Download version 2.2 from PhysioNet and extract it locally:

```bash
curl -fL \
  -o /tmp/mimic-iv-demo-2.2.zip \
  https://physionet.org/content/mimic-iv-demo/get-zip/2.2/

mkdir -p data/mimic/hosp
unzip -j /tmp/mimic-iv-demo-2.2.zip \
  'mimic-iv-clinical-database-demo-2.2/hosp/*' \
  -d data/mimic/hosp
```

`data/mimic/` is ignored by Git. The source files should not be added to this
repository.

## Files used

| MIMIC file | Common staging entity | Warehouse target |
| --- | --- | --- |
| `patients.csv.gz` | patients | `dim_patient` |
| `admissions.csv.gz` | encounters | `fact_encounter` |
| `diagnoses_icd.csv.gz` + dictionary | conditions | `dim_code`, `fact_condition` |
| `labevents.csv.gz` + dictionary | observations | `dim_code`, `fact_observation` |

The adapter adds stable `mimic:` prefixes to patient and admission identifiers
before they enter staging. Diagnosis descriptions and laboratory labels are
resolved from the corresponding MIMIC dictionaries.

MIMIC supplies an age anchored to a deidentified year rather than a direct
birth date. The adapter derives January 1 of `anchor_year - anchor_age` as an
approximate birth date because the compact learning schema requires a date.
This value must not be interpreted as an actual birth date. Diagnoses do not
have independent onset dates, so the admission date is used as the warehouse
onset date.

Laboratory rows without either a numeric or textual result are excluded during
normalization. The staging and warehouse parity check is performed after that
documented normalization.

## Run

```bash
clinical-dw validate --source mimic --input-dir data/mimic
clinical-dw run --source mimic --input-dir data/mimic
```

Running a complete pipeline replaces the active warehouse dataset. Use
`--source synthea` with `data/raw` to restore the deterministic Synthea test
dataset.

## Citation

Johnson, A., Bulgarelli, L., Pollard, T., Horng, S., Celi, L. A., & Mark, R.
(2023). *MIMIC-IV Clinical Database Demo* (version 2.2). PhysioNet.
https://doi.org/10.13026/dp1f-ex47
