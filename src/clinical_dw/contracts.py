"""Source-file contracts for each supported clinical dataset."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceContract:
    filename: str
    required_columns: frozenset[str]


SYNTHEA_CONTRACTS = {
    "patients": SourceContract(
        filename="patients.csv",
        required_columns=frozenset(
            {
                "Id",
                "BIRTHDATE",
                "DEATHDATE",
                "GENDER",
                "RACE",
                "ETHNICITY",
                "CITY",
                "STATE",
                "ZIP",
            }
        ),
    ),
    "encounters": SourceContract(
        filename="encounters.csv",
        required_columns=frozenset(
            {
                "Id",
                "START",
                "STOP",
                "PATIENT",
                "ENCOUNTERCLASS",
                "DESCRIPTION",
                "BASE_ENCOUNTER_COST",
                "TOTAL_CLAIM_COST",
            }
        ),
    ),
    "conditions": SourceContract(
        filename="conditions.csv",
        required_columns=frozenset(
            {"START", "STOP", "PATIENT", "ENCOUNTER", "SYSTEM", "CODE", "DESCRIPTION"}
        ),
    ),
    "observations": SourceContract(
        filename="observations.csv",
        required_columns=frozenset(
            {
                "DATE",
                "PATIENT",
                "ENCOUNTER",
                "CATEGORY",
                "CODE",
                "DESCRIPTION",
                "VALUE",
                "UNITS",
                "TYPE",
            }
        ),
    ),
}

MIMIC_CONTRACTS = {
    "patients": SourceContract(
        filename="hosp/patients.csv.gz",
        required_columns=frozenset(
            {"subject_id", "gender", "anchor_age", "anchor_year", "dod"}
        ),
    ),
    "admissions": SourceContract(
        filename="hosp/admissions.csv.gz",
        required_columns=frozenset(
            {
                "subject_id",
                "hadm_id",
                "admittime",
                "dischtime",
                "admission_type",
                "admission_location",
                "race",
            }
        ),
    ),
    "diagnoses": SourceContract(
        filename="hosp/diagnoses_icd.csv.gz",
        required_columns=frozenset(
            {"subject_id", "hadm_id", "icd_code", "icd_version"}
        ),
    ),
    "diagnosis_dictionary": SourceContract(
        filename="hosp/d_icd_diagnoses.csv.gz",
        required_columns=frozenset(
            {"icd_code", "icd_version", "long_title"}
        ),
    ),
    "labs": SourceContract(
        filename="hosp/labevents.csv.gz",
        required_columns=frozenset(
            {
                "subject_id",
                "hadm_id",
                "itemid",
                "charttime",
                "value",
                "valuenum",
                "valueuom",
            }
        ),
    ),
    "lab_dictionary": SourceContract(
        filename="hosp/d_labitems.csv.gz",
        required_columns=frozenset({"itemid", "label", "category"}),
    ),
}

# Backwards-compatible alias used by existing Synthea tests and callers.
CONTRACTS = SYNTHEA_CONTRACTS

SOURCE_CONTRACTS = {
    "synthea": SYNTHEA_CONTRACTS,
    "mimic": MIMIC_CONTRACTS,
}
