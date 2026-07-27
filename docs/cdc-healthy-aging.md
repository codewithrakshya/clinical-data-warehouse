# CDC Alzheimer's Disease and Healthy Aging data

## Why this source comes first

The CDC dataset is unrestricted public-health data that can be downloaded without
a research application. It provides published estimates about cognitive decline,
caregiving, health, and aging across locations and population strata.

It does **not** contain patient records or Alzheimer disease diagnoses. Most source
observations are BRFSS survey estimates, and subjective cognitive decline is
self-reported. The pipeline therefore keeps these records in a separate analytical
model instead of placing them in clinical encounter tables.

## Reproduce the local preparation

Download a small learning sample:

```bash
clinical-dw fetch-cdc-aging \
  --output data/brain_health/raw/cdc_healthy_aging.csv \
  --max-rows 10000
```

Omit `--max-rows` to retrieve the complete dataset:

```bash
clinical-dw fetch-cdc-aging \
  --output data/brain_health/raw/cdc_healthy_aging.csv
```

Validate, normalize, and summarize it:

```bash
clinical-dw prepare-cdc-aging \
  --input data/brain_health/raw/cdc_healthy_aging.csv \
  --output-dir data/brain_health/processed
```

The command produces:

- `cdc_healthy_aging_observations.csv`: standardized estimates and confidence limits.
- `cdc_healthy_aging_topic_summary.csv`: topic coverage, year range, location coverage,
  estimate availability, and median confidence-interval width.

## Interpretation boundary

These data can describe population patterns and associations. They cannot establish
that a lifestyle factor caused cognitive decline, diagnose an individual, or reproduce
the causal estimate from the randomized US-POINTER trial.

US-POINTER evidence will be modeled separately as published trial-level evidence so
that randomized findings are never blended with observational survey estimates.

Source: <https://data.cdc.gov/Healthy-Aging/Alzheimer-s-Disease-and-Healthy-Aging-Data/hfr9-rurv>
