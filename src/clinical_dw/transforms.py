"""Small, deterministic transformations shared by future ETL loaders."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def parse_date(value: str | None) -> date | None:
    cleaned = clean_optional_text(value)
    return date.fromisoformat(cleaned) if cleaned else None


def parse_timestamp(value: str | None) -> datetime | None:
    cleaned = clean_optional_text(value)
    if not cleaned:
        return None
    return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))


def parse_decimal(value: str | None) -> Decimal | None:
    cleaned = clean_optional_text(value)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"not a valid decimal: {value!r}") from exc


def split_observation_value(
    value: str | None, observation_type: str | None
) -> tuple[Decimal | None, str | None]:
    cleaned = clean_optional_text(value)
    if cleaned is None:
        return None, None
    if (observation_type or "").strip().lower() == "numeric":
        return parse_decimal(cleaned), None
    return None, cleaned
