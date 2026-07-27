"""Source-file contracts for the subset of Synthea CSVs used by the warehouse."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceContract:
    filename: str
    required_columns: frozenset[str]


CONTRACTS = {
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
                "SYSTEM",
                "CODE",
                "DESCRIPTION",
                "VALUE",
                "UNITS",
                "TYPE",
            }
        ),
    ),
}
