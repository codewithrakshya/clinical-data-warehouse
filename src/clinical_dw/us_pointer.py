"""Published aggregate evidence from the US-POINTER randomized clinical trial."""

from pathlib import Path

import pandas as pd

TRIAL_TITLE = (
    "Structured vs Self-Guided Multidomain Lifestyle Interventions for Global Cognitive Function"
)
TRIAL_REGISTRATION = "NCT03688126"
PUBLICATION_URL = "https://jamanetwork.com/journals/jama/fullarticle/2837046"
PARTICIPANTS = 2_111
STRUCTURED_PARTICIPANTS = 1_056
SELF_GUIDED_PARTICIPANTS = 1_055
FOLLOW_UP_YEARS = 2
YEAR_2_COMPLETION_PERCENT = 89.0

REQUIRED_COLUMNS = {
    "outcome",
    "outcome_role",
    "structured_slope",
    "structured_ci_low",
    "structured_ci_high",
    "self_guided_slope",
    "self_guided_ci_low",
    "self_guided_ci_high",
    "difference",
    "difference_ci_low",
    "difference_ci_high",
    "p_value",
    "unit",
    "source_table",
    "publication_url",
}

NUMERIC_COLUMNS = [
    "structured_slope",
    "structured_ci_low",
    "structured_ci_high",
    "self_guided_slope",
    "self_guided_ci_low",
    "self_guided_ci_high",
    "difference",
    "difference_ci_low",
    "difference_ci_high",
    "p_value",
]


def default_evidence_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data/evidence/us_pointer_outcomes.csv"


def load_us_pointer_evidence(path: Path | None = None) -> pd.DataFrame:
    """Load validated, publication-level trial estimates."""
    evidence_path = path or default_evidence_path()
    frame = pd.read_csv(evidence_path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"US-POINTER evidence is missing columns: {', '.join(missing)}")

    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame["outcome"].duplicated().any():
        raise ValueError("US-POINTER evidence contains duplicate outcomes")
    if not frame["publication_url"].eq(PUBLICATION_URL).all():
        raise ValueError("US-POINTER evidence contains an unexpected publication source")
    if (frame["difference_ci_low"] > frame["difference_ci_high"]).any():
        raise ValueError("US-POINTER evidence contains reversed confidence limits")

    frame["ci_excludes_zero"] = (frame["difference_ci_low"] > 0) | (frame["difference_ci_high"] < 0)
    frame["evidence_design"] = "Randomized clinical trial"
    return frame
