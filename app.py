"""Problem-focused Streamlit interface for the clinical data warehouse."""

import html
import os

import pandas as pd
import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from clinical_dw.quality import run_quality_checks


def database_url() -> str:
    if configured_url := os.getenv("DATABASE_URL"):
        return configured_url
    try:
        return str(st.secrets["DATABASE_URL"])
    except (KeyError, StreamlitSecretNotFoundError):
        return "postgresql://clinical_dw:clinical_dw_dev@localhost:5432/clinical_dw"


DATABASE_URL = database_url()

st.set_page_config(
    page_title="Clinical Data Trust Lab",
    page_icon="🧬",
    layout="wide",
)

st.markdown(
    """
    <style>
      :root {
        --ink: #14211d;
        --muted: #5c6f68;
        --green: #176b57;
        --mint: #72d6b5;
        --cream: #f6f3ec;
        --amber: #f2b84b;
      }
      .stApp {
        background:
          radial-gradient(circle at 100% 0%, rgba(114, 214, 181, .13), transparent 28rem),
          #f7f8f6;
        color: var(--ink);
      }
      [data-testid="stHeader"] { background: transparent; }
      .block-container { max-width: 1280px; padding-top: 1.4rem; }
      .hero {
        position: relative;
        overflow: hidden;
        padding: clamp(2rem, 5vw, 4.5rem);
        border-radius: 30px;
        color: #f7fffc;
        background:
          radial-gradient(circle at 86% 16%, rgba(114, 214, 181, .38), transparent 25%),
          radial-gradient(circle at 75% 110%, rgba(242, 184, 75, .22), transparent 34%),
          linear-gradient(135deg, #102c25 0%, #145342 54%, #1e7c64 100%);
        box-shadow: 0 24px 64px rgba(20, 68, 56, .2);
        margin-bottom: 1.4rem;
      }
      .hero::after {
        content: "";
        position: absolute;
        width: 240px;
        height: 240px;
        right: -80px;
        bottom: -110px;
        border: 1px solid rgba(255,255,255,.22);
        border-radius: 50%;
        box-shadow: 0 0 0 32px rgba(255,255,255,.04), 0 0 0 64px rgba(255,255,255,.03);
      }
      .eyebrow {
        color: #9fe7d0;
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .16em;
        text-transform: uppercase;
      }
      .hero h1 {
        max-width: 900px;
        font-size: clamp(2.4rem, 6vw, 5rem);
        letter-spacing: -.055em;
        line-height: .98;
        margin: .8rem 0 1.15rem;
      }
      .hero p {
        color: #d9f4eb;
        font-size: 1.08rem;
        line-height: 1.65;
        max-width: 780px;
        margin: 0;
      }
      .source-pill {
        display: inline-block;
        margin-top: 1.4rem;
        padding: .48rem .75rem;
        border: 1px solid rgba(255,255,255,.25);
        background: rgba(255,255,255,.1);
        border-radius: 999px;
        color: #effff9;
        font-size: .82rem;
      }
      [data-testid="stMetric"] {
        background: rgba(255,255,255,.92);
        border: 1px solid #dfe8e4;
        border-radius: 18px;
        padding: 1rem 1.15rem;
        box-shadow: 0 8px 24px rgba(31, 66, 57, .06);
      }
      [data-testid="stMetricLabel"] { color: #60736c; }
      [data-testid="stMetricValue"] { color: #124f40; }
      .problem-card, .flow-card {
        height: 100%;
        padding: 1.15rem 1.2rem;
        border-radius: 18px;
        border: 1px solid #dde6e2;
        background: rgba(255,255,255,.88);
      }
      .problem-card strong, .flow-card strong {
        display: block;
        color: #174f42;
        margin-bottom: .35rem;
      }
      .problem-card p, .flow-card p {
        color: #5b6f68;
        font-size: .9rem;
        line-height: 1.55;
        margin: 0;
      }
      .flow-number {
        display: inline-flex;
        width: 1.85rem;
        height: 1.85rem;
        align-items: center;
        justify-content: center;
        margin-bottom: .7rem;
        border-radius: 50%;
        background: #dff5ed;
        color: #16604e;
        font-weight: 800;
      }
      .section-note {
        color: #60736c;
        font-size: .93rem;
        margin-top: -.45rem;
        margin-bottom: 1rem;
      }
      .trust-note {
        border-left: 4px solid var(--amber);
        background: #fff8e9;
        padding: .9rem 1.05rem;
        border-radius: 0 12px 12px 0;
        color: #674d20;
      }
      .stTabs [data-baseweb="tab-list"] {
        gap: .4rem;
        background: #edf2ef;
        padding: .35rem;
        border-radius: 14px;
      }
      .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: .45rem .8rem;
      }
      .stTabs [aria-selected="true"] {
        background: white;
        box-shadow: 0 3px 10px rgba(29, 63, 54, .08);
      }
      div[data-testid="stDataFrame"] {
        border: 1px solid #dfe8e4;
        border-radius: 14px;
        overflow: hidden;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def query(statement: str) -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(statement)
        columns = [column.name for column in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)


@st.cache_data(ttl=30)
def query_with_params(statement: str, params: tuple[object, ...]) -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(statement, params)
        columns = [column.name for column in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)


@st.cache_data(ttl=30)
def quality_results() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL) as connection:
        return pd.DataFrame(check.as_dict() for check in run_quality_checks(connection))


def format_count(value: int) -> str:
    return f"{value:,}"


try:
    counts = query(
        """
        SELECT
          (SELECT COUNT(*) FROM staging.patients)
            + (SELECT COUNT(*) FROM staging.encounters)
            + (SELECT COUNT(*) FROM staging.conditions)
            + (SELECT COUNT(*) FROM staging.observations) AS normalized_source_rows,
          (SELECT COUNT(*) FROM warehouse.dim_patient) AS patients,
          (SELECT COUNT(*) FROM warehouse.fact_encounter) AS encounters,
          (SELECT COUNT(*) FROM warehouse.fact_condition) AS conditions,
          (SELECT COUNT(*) FROM warehouse.fact_observation) AS observations,
          (SELECT COUNT(*) FROM warehouse.dim_code) AS codes,
          (SELECT source_label FROM warehouse.dataset_metadata WHERE metadata_id = 1)
            AS source_label,
          (SELECT source_version FROM warehouse.dataset_metadata WHERE metadata_id = 1)
            AS source_version,
          (SELECT is_synthetic FROM warehouse.dataset_metadata WHERE metadata_id = 1)
            AS is_synthetic,
          (SELECT loaded_at FROM warehouse.dataset_metadata WHERE metadata_id = 1)
            AS loaded_at
        """
    ).iloc[0]
except psycopg.Error as exc:
    st.error(
        "The dashboard cannot reach the warehouse. Start PostgreSQL and run the "
        "pipeline before opening the interface."
    )
    st.code(str(exc))
    st.stop()

source_label = (
    "Unknown source" if pd.isna(counts["source_label"]) else str(counts["source_label"])
)
source_version = (
    "" if pd.isna(counts["source_version"]) else str(counts["source_version"]).strip()
)
is_synthetic = (
    True if pd.isna(counts["is_synthetic"]) else bool(counts["is_synthetic"])
)
source_display = f"{source_label} v{source_version}" if source_version else source_label

st.markdown(
    f"""
    <div class="hero">
      <div class="eyebrow">Clinical data engineering • trust before analysis</div>
      <h1>From fragmented clinical files to a trustworthy research cohort.</h1>
      <p>
        Clinical datasets arrive with incompatible identifiers, code systems,
        timestamps, and missing values. This platform validates and harmonizes them
        into one auditable warehouse—then lets researchers define cohorts without
        rebuilding every join from scratch.
      </p>
      <span class="source-pill">Active source · {html.escape(source_display)}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(4)
metric_columns[0].metric(
    "Normalized source rows",
    format_count(int(counts["normalized_source_rows"])),
    help="Rows that passed source-specific normalization and entered staging.",
)
metric_columns[1].metric("Linked patients", format_count(int(counts["patients"])))
metric_columns[2].metric(
    "Clinical events",
    format_count(
        int(counts["encounters"]) + int(counts["conditions"]) + int(counts["observations"])
    ),
)
metric_columns[3].metric("Standardized codes", format_count(int(counts["codes"])))

problem_columns = st.columns(3)
problem_cards = (
    (
        "The problem",
        "Clinical files use source-specific structures, so analysis begins with repeated cleaning, mapping, and fragile joins.",
    ),
    (
        "The intervention",
        "Adapters validate each source and normalize patients, encounters, diagnoses, labs, codes, and dates into one model.",
    ),
    (
        "The outcome",
        "Researchers get an auditable, quality-checked cohort layer that can be explored and exported consistently.",
    ),
)
for column, (title, body) in zip(problem_columns, problem_cards, strict=True):
    with column:
        st.markdown(
            f'<div class="problem-card"><strong>{title}</strong><p>{body}</p></div>',
            unsafe_allow_html=True,
        )

st.write("")
story_tab, cohort_tab, patterns_tab, trust_tab, runs_tab = st.tabs(
    [
        "How it solves the problem",
        "Build a cohort",
        "Explore clinical patterns",
        "Trust & provenance",
        "Pipeline runs",
    ]
)

with story_tab:
    st.subheader("One path from source complexity to reusable evidence")
    st.markdown(
        '<p class="section-note">The warehouse separates source-specific decisions '
        "from reusable analytical logic.</p>",
        unsafe_allow_html=True,
    )
    flow_columns = st.columns(4)
    flow_cards = (
        ("01", "Validate", "Required files and columns are checked before the database changes."),
        ("02", "Harmonize", "Source adapters translate identifiers, diagnoses, labs, and dates."),
        ("03", "Prove quality", "Parity, relationships, date ordering, and ETL failures are measured."),
        ("04", "Build cohorts", "Researchers filter connected patient histories and export results."),
    )
    for column, (number, title, body) in zip(flow_columns, flow_cards, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="flow-card">
                  <span class="flow-number">{number}</span>
                  <strong>{title}</strong>
                  <p>{body}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    left, right = st.columns((1.05, 1))
    with left:
        st.markdown("#### Source-to-warehouse mapping")
        if is_synthetic:
            mapping = pd.DataFrame(
                [
                    ("patients.csv", "Patients", "dim_patient"),
                    ("encounters.csv", "Encounters", "fact_encounter"),
                    ("conditions.csv", "Conditions + codes", "fact_condition"),
                    ("observations.csv", "Observations + codes", "fact_observation"),
                ],
                columns=["Source files", "Normalized concept", "Warehouse target"],
            )
        else:
            mapping = pd.DataFrame(
                [
                    ("patients", "Patient identity", "dim_patient"),
                    ("admissions", "Hospital encounters", "fact_encounter"),
                    ("diagnoses_icd + dictionary", "Coded diagnoses", "fact_condition"),
                    ("labevents + dictionary", "Laboratory results", "fact_observation"),
                ],
                columns=["MIMIC files", "Normalized concept", "Warehouse target"],
            )
        st.dataframe(mapping, width="stretch", hide_index=True)

    with right:
        st.markdown("#### What becomes reusable")
        st.markdown(
            """
            - Stable patient and encounter keys across every analysis
            - Descriptions resolved from ICD and laboratory dictionaries
            - Numeric and text results stored without mixing their meaning
            - A shared calendar for consistent time-based queries
            - Durable ETL history and visible quality warnings
            - The same downstream queries across Synthea and MIMIC
            """
        )

with cohort_tab:
    st.subheader("Define an analysis-ready cohort")
    st.markdown(
        '<p class="section-note">Filters operate across normalized demographics, '
        "admissions, diagnoses, and laboratory histories—not isolated CSV files.</p>",
        unsafe_allow_html=True,
    )

    filter_values = query(
        """
        SELECT 'sex' AS filter_name, COALESCE(sex_at_birth, 'Unknown') AS value
        FROM warehouse.dim_patient
        UNION
        SELECT 'race', COALESCE(race, 'Unknown')
        FROM warehouse.dim_patient
        UNION
        SELECT 'encounter_class', COALESCE(encounter_class, 'Unknown')
        FROM warehouse.fact_encounter
        ORDER BY filter_name, value
        """
    )
    sex_options = filter_values.loc[
        filter_values["filter_name"] == "sex", "value"
    ].tolist()
    race_options = filter_values.loc[
        filter_values["filter_name"] == "race", "value"
    ].tolist()
    encounter_options = filter_values.loc[
        filter_values["filter_name"] == "encounter_class", "value"
    ].tolist()

    filter_one, filter_two, filter_three = st.columns(3)
    selected_sexes = filter_one.multiselect("Sex", sex_options)
    selected_races = filter_two.multiselect("Race / ethnicity label", race_options)
    selected_encounters = filter_three.multiselect("Admission / encounter type", encounter_options)

    filter_four, filter_five = st.columns((1, 2))
    minimum_encounters = filter_four.number_input(
        "Minimum encounters",
        min_value=0,
        max_value=max(int(counts["encounters"]), 1),
        value=1,
        step=1,
    )
    diagnosis_search = filter_five.text_input(
        "Diagnosis contains",
        placeholder="Example: diabetes, heart failure, hypertension",
    ).strip()

    predicates = ["COALESCE(es.encounters, 0) >= %s"]
    params: list[object] = [int(minimum_encounters)]
    if selected_sexes:
        predicates.append("COALESCE(p.sex_at_birth, 'Unknown') = ANY(%s)")
        params.append(selected_sexes)
    if selected_races:
        predicates.append("COALESCE(p.race, 'Unknown') = ANY(%s)")
        params.append(selected_races)
    if selected_encounters:
        predicates.append(
            """
            EXISTS (
                SELECT 1
                FROM warehouse.fact_encounter selected_e
                WHERE selected_e.patient_key = p.patient_key
                  AND COALESCE(selected_e.encounter_class, 'Unknown') = ANY(%s)
            )
            """
        )
        params.append(selected_encounters)
    if diagnosis_search:
        predicates.append(
            """
            EXISTS (
                SELECT 1
                FROM warehouse.fact_condition selected_f
                JOIN warehouse.dim_code selected_c
                  ON selected_c.code_key = selected_f.code_key
                WHERE selected_f.patient_key = p.patient_key
                  AND selected_c.description ILIKE %s
            )
            """
        )
        params.append(f"%{diagnosis_search}%")

    cohort_statement = f"""
        WITH encounter_summary AS (
            SELECT
                patient_key,
                COUNT(*) AS encounters,
                MIN(start_at)::date AS first_encounter,
                MAX(start_at)::date AS last_encounter
            FROM warehouse.fact_encounter
            GROUP BY patient_key
        ),
        condition_summary AS (
            SELECT patient_key, COUNT(*) AS diagnoses
            FROM warehouse.fact_condition
            GROUP BY patient_key
        ),
        observation_summary AS (
            SELECT patient_key, COUNT(*) AS observations
            FROM warehouse.fact_observation
            GROUP BY patient_key
        )
        SELECT
            p.source_patient_id AS patient_id,
            COALESCE(p.sex_at_birth, 'Unknown') AS sex,
            COALESCE(p.race, 'Unknown') AS race,
            CASE
                WHEN es.first_encounter IS NULL THEN NULL
                ELSE DATE_PART('year', AGE(es.first_encounter, p.birth_date))::integer
            END AS approximate_age_at_first_encounter,
            COALESCE(es.encounters, 0) AS encounters,
            COALESCE(cs.diagnoses, 0) AS diagnoses,
            COALESCE(os.observations, 0) AS observations,
            es.first_encounter,
            es.last_encounter
        FROM warehouse.dim_patient p
        LEFT JOIN encounter_summary es USING (patient_key)
        LEFT JOIN condition_summary cs USING (patient_key)
        LEFT JOIN observation_summary os USING (patient_key)
        WHERE {" AND ".join(predicates)}
        ORDER BY encounters DESC, diagnoses DESC, patient_id
    """
    cohort = query_with_params(cohort_statement, tuple(params))

    cohort_metrics = st.columns(4)
    cohort_metrics[0].metric("Patients in cohort", format_count(len(cohort)))
    cohort_metrics[1].metric(
        "Share of source population",
        f"{(100 * len(cohort) / max(int(counts['patients']), 1)):.1f}%",
    )
    cohort_metrics[2].metric(
        "Admissions / encounters",
        format_count(int(cohort["encounters"].sum()) if not cohort.empty else 0),
    )
    cohort_metrics[3].metric(
        "Clinical observations",
        format_count(int(cohort["observations"].sum()) if not cohort.empty else 0),
    )

    if cohort.empty:
        st.info("No patients match this combination. Broaden one or more filters.")
    else:
        st.dataframe(
            cohort,
            width="stretch",
            hide_index=True,
            column_config={
                "patient_id": "Deidentified patient ID",
                "approximate_age_at_first_encounter": "Approx. age at first encounter",
                "first_encounter": "First encounter",
                "last_encounter": "Last encounter",
            },
        )
        st.download_button(
            "Download cohort CSV",
            cohort.to_csv(index=False).encode("utf-8"),
            file_name=f"{source_label.lower().replace(' ', '-')}-cohort.csv",
            mime="text/csv",
            help="Exports deidentified patient-level summaries from the selected cohort.",
        )

    st.markdown(
        '<p class="trust-note"><strong>Interpretation boundary:</strong> MIMIC dates '
        "are shifted and birth dates are approximated from anchor age. Use cohort "
        "results to evaluate data-engineering behavior, not calendar trends or "
        "clinical effectiveness.</p>",
        unsafe_allow_html=True,
    )

with patterns_tab:
    condition_column, lab_column = st.columns(2)
    with condition_column:
        st.subheader("Conditions represented")
        conditions = query(
            """
            SELECT
              c.description,
              c.code,
              COUNT(*) AS episodes,
              COUNT(DISTINCT f.patient_key) AS patients
            FROM warehouse.fact_condition f
            JOIN warehouse.dim_code c ON c.code_key = f.code_key
            GROUP BY c.description, c.code
            ORDER BY patients DESC, episodes DESC
            LIMIT 20
            """
        )
        st.bar_chart(
            conditions.head(10).set_index("description")[["patients"]],
            color="#1e7c64",
            horizontal=True,
        )
        st.dataframe(conditions, width="stretch", hide_index=True)

    with lab_column:
        st.subheader("Laboratory measurements represented")
        measurements = query(
            """
            SELECT
              c.description,
              f.unit,
              COUNT(*) AS measurements,
              ROUND(AVG(f.value_numeric), 2) AS mean,
              MIN(f.value_numeric) AS minimum,
              MAX(f.value_numeric) AS maximum
            FROM warehouse.fact_observation f
            JOIN warehouse.dim_code c ON c.code_key = f.code_key
            WHERE f.value_numeric IS NOT NULL
            GROUP BY c.description, f.unit
            ORDER BY measurements DESC
            LIMIT 20
            """
        )
        st.bar_chart(
            measurements.head(10).set_index("description")[["measurements"]],
            color="#5885b8",
            horizontal=True,
        )
        st.dataframe(measurements, width="stretch", hide_index=True)

    utilization_left, utilization_right = st.columns((1.1, 1))
    with utilization_left:
        st.subheader("Encounter mix")
        encounter_classes = query(
            """
            SELECT COALESCE(encounter_class, 'Unknown') AS encounter_class,
                   COUNT(*) AS encounters
            FROM warehouse.fact_encounter
            GROUP BY COALESCE(encounter_class, 'Unknown')
            ORDER BY encounters DESC
            """
        )
        st.bar_chart(
            encounter_classes.set_index("encounter_class"),
            color="#f2b84b",
            horizontal=True,
        )
    with utilization_right:
        st.subheader("Dataset coverage")
        demographics = query(
            """
            SELECT COALESCE(race, 'Unknown') AS race, COUNT(*) AS patients
            FROM warehouse.dim_patient
            GROUP BY COALESCE(race, 'Unknown')
            ORDER BY patients DESC
            """
        )
        st.bar_chart(demographics.set_index("race"), color="#72bda3")

with trust_tab:
    st.subheader("Evidence that the warehouse is safe to analyze")
    st.markdown(
        '<p class="section-note">Checks run against the live staging and warehouse '
        "tables. Warnings remain visible instead of being silently discarded.</p>",
        unsafe_allow_html=True,
    )
    quality = quality_results()
    status_counts = quality["status"].value_counts()
    status_columns = st.columns(3)
    status_columns[0].metric("Passed", int(status_counts.get("PASS", 0)))
    status_columns[1].metric("Warnings to review", int(status_counts.get("WARN", 0)))
    status_columns[2].metric("Blocking failures", int(status_counts.get("FAIL", 0)))
    st.dataframe(
        quality,
        width="stretch",
        hide_index=True,
        column_config={
            "check": "Check",
            "status": "Status",
            "value": st.column_config.NumberColumn("Observed", format="%d"),
            "expected": "Expected",
            "detail": "Why it matters",
        },
    )

    provenance_left, provenance_right = st.columns(2)
    with provenance_left:
        st.markdown("#### Provenance")
        st.write(f"**Active source:** {source_display}")
        st.write(f"**Last loaded:** {counts['loaded_at']}")
        if not is_synthetic:
            st.markdown(
                "**Citation:** Johnson et al. (2023), MIMIC-IV Clinical Database "
                "Demo v2.2, PhysioNet. DOI: 10.13026/dp1f-ex47."
            )
    with provenance_right:
        st.markdown("#### Known limitations")
        if is_synthetic:
            st.markdown(
                "- Generated records are not observations of real patients.\n"
                "- Findings demonstrate pipeline behavior, not population evidence."
            )
        else:
            st.markdown(
                "- The demo contains only 100 deidentified patients.\n"
                "- Dates are shifted and direct birth dates are unavailable.\n"
                "- Diagnosis onset is approximated from admission time.\n"
                "- Free-text clinical notes are not included."
            )

with runs_tab:
    st.subheader("Auditable transformation history")
    st.markdown(
        '<p class="section-note">Every warehouse entity records rows read, rows loaded, '
        "completion state, and failures for reproducibility.</p>",
        unsafe_allow_html=True,
    )
    runs = query(
        """
        SELECT
          etl_run_id,
          source_name,
          status,
          started_at,
          completed_at,
          rows_read,
          rows_loaded,
          error_message
        FROM warehouse.etl_run
        ORDER BY etl_run_id DESC
        LIMIT 50
        """
    )
    st.dataframe(runs, width="stretch", hide_index=True)

if st.sidebar.button("Refresh warehouse data", width="stretch"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("### Clinical Data Trust Lab")
st.sidebar.caption(f"Active source: {source_display}")
st.sidebar.caption("Validated • Harmonized • Auditable")
