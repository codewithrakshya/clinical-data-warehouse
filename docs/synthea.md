# Synthea source data

[Synthea](https://synthea.mitre.org/) generates realistic but synthetic patient
histories. Its records are not associated with real people, which makes it
appropriate for a public learning repository.

## Recommended first dataset

Start with 100 synthetic patients. That is large enough to exercise joins and
quality checks, but small enough to inspect manually.

You can either:

1. Run Synthea locally and request CSV output.
2. Download a published sample export from the Synthea project.

Place the extracted CSV files in `data/raw/`. The directory is ignored by Git
to prevent large generated datasets from being committed.

## Files used in milestone 1

- `patients.csv`
- `encounters.csv`
- `conditions.csv`
- `observations.csv`

Later milestones can add medications, procedures, allergies, immunizations,
claims, and payer data.

## Questions to ask while inspecting a source file

1. What does one row represent (the **grain**)?
2. Which columns uniquely identify that row?
3. Which values link it to another file?
4. Which fields are dates, timestamps, numeric measures, or coded concepts?
5. How are missing values represented?
6. Can a source record arrive twice?

These questions drive both database design and data-quality tests.
