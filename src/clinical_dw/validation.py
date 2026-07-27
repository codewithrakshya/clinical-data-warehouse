"""Validation of incoming synthetic CSV files before database loading."""

import csv
from dataclasses import dataclass
from pathlib import Path

from clinical_dw.contracts import CONTRACTS


@dataclass(frozen=True)
class ValidationResult:
    filename: str
    valid: bool
    row_count: int
    errors: tuple[str, ...]


def validate_csv(input_dir: Path, contract_name: str) -> ValidationResult:
    contract = CONTRACTS[contract_name]
    path = input_dir / contract.filename

    if not path.exists():
        return ValidationResult(contract.filename, False, 0, ("file is missing",))

    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        actual_columns = set(reader.fieldnames or [])
        missing = sorted(contract.required_columns - actual_columns)
        errors = [f"missing required column: {column}" for column in missing]
        row_count = sum(1 for _ in reader)

    if row_count == 0:
        errors.append("file contains no data rows")

    return ValidationResult(
        filename=contract.filename,
        valid=not errors,
        row_count=row_count,
        errors=tuple(errors),
    )


def validate_directory(input_dir: Path) -> list[ValidationResult]:
    return [validate_csv(input_dir, name) for name in CONTRACTS]
