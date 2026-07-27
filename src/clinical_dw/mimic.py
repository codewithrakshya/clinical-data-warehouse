"""Normalize the open-access MIMIC-IV Demo into the common staging shape."""

import csv
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from clinical_dw.contracts import MIMIC_CONTRACTS
from clinical_dw.source_io import open_source_text


def _rows(input_dir: Path, contract_name: str) -> Iterator[dict[str, str]]:
    path = input_dir / MIMIC_CONTRACTS[contract_name].filename
    with open_source_text(path) as stream:
        yield from csv.DictReader(stream)


def _prefixed(kind: str, value: str) -> str:
    return f"mimic:{kind}:{value}"


def _admission_lookup(input_dir: Path) -> dict[str, dict[str, str]]:
    return {row["hadm_id"]: row for row in _rows(input_dir, "admissions")}


def iter_mimic_patients(input_dir: Path) -> Iterator[tuple[str, ...]]:
    """Map MIMIC patients and their first recorded admission race."""
    first_race: dict[str, str] = {}
    for admission in _rows(input_dir, "admissions"):
        first_race.setdefault(admission["subject_id"], admission["race"])

    for row in _rows(input_dir, "patients"):
        anchor_year = int(row["anchor_year"])
        anchor_age = int(row["anchor_age"])
        approximate_birth_date = date(anchor_year - anchor_age, 1, 1).isoformat()
        yield (
            _prefixed("patient", row["subject_id"]),
            approximate_birth_date,
            row["dod"],
            row["gender"],
            first_race.get(row["subject_id"], ""),
            "",
            "",
            "",
            "",
        )


def iter_mimic_encounters(input_dir: Path) -> Iterator[tuple[str, ...]]:
    """Map hospital admissions to the common encounter staging grain."""
    for row in _rows(input_dir, "admissions"):
        location = row["admission_location"].strip()
        description = f"Hospital admission from {location}" if location else "Hospital admission"
        yield (
            _prefixed("encounter", row["hadm_id"]),
            row["admittime"],
            row["dischtime"],
            _prefixed("patient", row["subject_id"]),
            row["admission_type"],
            description,
            "",
            "",
        )


def iter_mimic_conditions(input_dir: Path) -> Iterator[tuple[str, ...]]:
    """Map admission diagnoses to condition episodes using admission dates."""
    admissions = _admission_lookup(input_dir)
    descriptions = {
        (row["icd_version"], row["icd_code"]): row["long_title"]
        for row in _rows(input_dir, "diagnosis_dictionary")
    }
    for row in _rows(input_dir, "diagnoses"):
        admission = admissions[row["hadm_id"]]
        version = row["icd_version"]
        code = row["icd_code"]
        yield (
            admission["admittime"][:10],
            "",
            _prefixed("patient", row["subject_id"]),
            _prefixed("encounter", row["hadm_id"]),
            f"urn:hl7-org:icd-{version}",
            code,
            descriptions.get((version, code), f"ICD-{version} {code}"),
        )


def iter_mimic_observations(input_dir: Path) -> Iterator[tuple[str, ...]]:
    """Map laboratory events to numeric or textual observations."""
    lab_items = {
        row["itemid"]: (row["label"], row["category"]) for row in _rows(input_dir, "lab_dictionary")
    }
    for row in _rows(input_dir, "labs"):
        label, category = lab_items.get(row["itemid"], (f"Lab item {row['itemid']}", "Laboratory"))
        numeric_value = row["valuenum"].strip()
        value = numeric_value or row["value"]
        if not value.strip():
            continue
        hadm_id = row["hadm_id"].strip()
        yield (
            row["charttime"],
            _prefixed("patient", row["subject_id"]),
            _prefixed("encounter", hadm_id) if hadm_id else "",
            category or "Laboratory",
            row["itemid"],
            label,
            value,
            row["valueuom"],
            "numeric" if numeric_value else "text",
        )


MIMIC_STAGING_ROWS = {
    "patients": iter_mimic_patients,
    "encounters": iter_mimic_encounters,
    "conditions": iter_mimic_conditions,
    "observations": iter_mimic_observations,
}
