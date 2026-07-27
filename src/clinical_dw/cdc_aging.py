"""Ingest and summarize the CDC Alzheimer's Disease and Healthy Aging dataset.

This source contains aggregate public-health estimates, not patient records. It
therefore has its own analysis model instead of being forced into the clinical
patient/encounter warehouse.
"""

from __future__ import annotations

import csv
import io
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

import certifi
import pandas as pd

DATASET_ID = "hfr9-rurv"
API_URL = f"https://data.cdc.gov/resource/{DATASET_ID}.csv"
PAGE_SIZE = 50_000

REQUIRED_COLUMNS = {
    "rowid",
    "yearstart",
    "yearend",
    "locationabbr",
    "locationdesc",
    "datasource",
    "class",
    "topic",
    "question",
    "data_value_unit",
    "data_value_type",
    "data_value",
    "low_confidence_limit",
    "high_confidence_limit",
    "stratificationcategory1",
    "stratification1",
}

OUTPUT_COLUMNS = [
    "row_id",
    "year_start",
    "year_end",
    "location_abbr",
    "location",
    "data_source",
    "indicator_class",
    "topic",
    "question",
    "value_unit",
    "value_type",
    "estimate",
    "confidence_low",
    "confidence_high",
    "stratification_category_1",
    "stratification_1",
    "stratification_category_2",
    "stratification_2",
    "class_id",
    "topic_id",
    "question_id",
    "location_id",
]

COLUMN_MAP = {
    "rowid": "row_id",
    "yearstart": "year_start",
    "yearend": "year_end",
    "locationabbr": "location_abbr",
    "locationdesc": "location",
    "datasource": "data_source",
    "class": "indicator_class",
    "data_value_unit": "value_unit",
    "data_value_type": "value_type",
    "data_value": "estimate",
    "low_confidence_limit": "confidence_low",
    "high_confidence_limit": "confidence_high",
    "stratificationcategory1": "stratification_category_1",
    "stratification1": "stratification_1",
    "stratificationcategory2": "stratification_category_2",
    "stratification2": "stratification_2",
    "classid": "class_id",
    "topicid": "topic_id",
    "questionid": "question_id",
    "locationid": "location_id",
}


def _download_page(
    offset: int,
    limit: int,
    timeout: int = 60,
    where: str | None = None,
) -> pd.DataFrame:
    parameters: dict[str, str | int] = {
        "$limit": limit,
        "$offset": offset,
        "$order": "rowid",
    }
    if where:
        parameters["$where"] = where
    query = urllib.parse.urlencode(parameters)
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "clinical-data-trust-lab/0.1"},
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=ssl_context,
    ) as response:
        content = response.read().decode("utf-8")
    return pd.read_csv(io.StringIO(content), dtype=str)


def fetch_cdc_aging_frame(
    *,
    where: str | None = None,
    max_rows: int | None = None,
    page_size: int = PAGE_SIZE,
) -> pd.DataFrame:
    """Fetch and normalize a filtered CDC dataset for interactive analysis."""
    pages: list[pd.DataFrame] = []
    offset = 0
    while max_rows is None or offset < max_rows:
        requested = page_size
        if max_rows is not None:
            requested = min(requested, max_rows - offset)
        page = _download_page(offset, requested, where=where)
        if page.empty:
            break
        pages.append(page)
        offset += len(page)
        if len(page) < requested:
            break

    if not pages:
        raise ValueError("CDC API returned no rows for the selected query")
    return normalize_cdc_aging(pd.concat(pages, ignore_index=True))


def download_cdc_aging(
    output_path: Path,
    *,
    max_rows: int | None = None,
    page_size: int = PAGE_SIZE,
) -> int:
    """Download the public CDC dataset deterministically and return its row count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    wrote_header = False

    with output_path.open("w", encoding="utf-8", newline="") as stream:
        while max_rows is None or offset < max_rows:
            requested = page_size
            if max_rows is not None:
                requested = min(requested, max_rows - offset)
            page = _download_page(offset, requested)
            if page.empty:
                break
            page.to_csv(
                stream,
                index=False,
                header=not wrote_header,
                quoting=csv.QUOTE_MINIMAL,
            )
            wrote_header = True
            offset += len(page)
            if len(page) < requested:
                break

    if not wrote_header:
        raise ValueError("CDC API returned no rows")
    return offset


def normalize_cdc_aging(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize raw CDC columns into analysis-friendly names/types."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"CDC Healthy Aging data is missing columns: {', '.join(missing)}")

    normalized = frame.rename(columns=COLUMN_MAP).copy()
    for optional in OUTPUT_COLUMNS:
        if optional not in normalized:
            normalized[optional] = pd.NA

    for column in ("year_start", "year_end"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce").astype("Int64")
    for column in ("estimate", "confidence_low", "confidence_high"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["confidence_width"] = normalized["confidence_high"] - normalized["confidence_low"]
    normalized["estimate_available"] = normalized["estimate"].notna()
    return normalized[[*OUTPUT_COLUMNS, "confidence_width", "estimate_available"]]


def build_topic_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Create a transparent coverage/quality summary, not a causal analysis."""
    return (
        frame.groupby(["indicator_class", "topic"], dropna=False)
        .agg(
            observations=("row_id", "size"),
            locations=("location_abbr", "nunique"),
            first_year=("year_start", "min"),
            last_year=("year_end", "max"),
            estimates_available=("estimate_available", "sum"),
            median_confidence_width=("confidence_width", "median"),
        )
        .reset_index()
        .sort_values(["indicator_class", "topic"], ignore_index=True)
    )


def prepare_cdc_aging(input_path: Path, output_dir: Path) -> tuple[int, int]:
    """Normalize raw data and write analysis-ready observations and a summary."""
    raw = pd.read_csv(input_path, dtype=str, low_memory=False)
    normalized = normalize_cdc_aging(raw)
    summary = build_topic_summary(normalized)

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output_dir / "cdc_healthy_aging_observations.csv", index=False)
    summary.to_csv(output_dir / "cdc_healthy_aging_topic_summary.csv", index=False)
    return len(normalized), len(summary)
