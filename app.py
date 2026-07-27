"""Problem-focused Streamlit interface for the clinical data warehouse."""

import html
import os

import pandas as pd
import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from clinical_dw.cdc_aging import fetch_cdc_aging_with_fallback
from clinical_dw.quality import run_quality_checks
from clinical_dw.us_pointer import (
    FOLLOW_UP_YEARS,
    PARTICIPANTS,
    PUBLICATION_URL,
    SELF_GUIDED_PARTICIPANTS,
    STRUCTURED_PARTICIPANTS,
    TRIAL_REGISTRATION,
    YEAR_2_COMPLETION_PERCENT,
    load_us_pointer_evidence,
)


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
      .product-card {
        height: 100%;
        padding: 1.35rem 1.4rem;
        border-radius: 20px;
        border: 1px solid #d7e4df;
        background: linear-gradient(145deg, #ffffff, #f1f8f5);
        box-shadow: 0 10px 28px rgba(31, 66, 57, .07);
      }
      .product-card .product-number {
        color: #1e7c64;
        font-size: .75rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
      }
      .product-card h3 { color: #174f42; margin: .45rem 0 .55rem; }
      .product-card p { color: #5b6f68; line-height: 1.55; margin: 0 0 .8rem; }
      .product-card strong { color: #29483f; }
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
      .evidence-label {
        display: inline-block;
        padding: .35rem .65rem;
        margin-bottom: .65rem;
        border-radius: 999px;
        font-size: .75rem;
        font-weight: 800;
        letter-spacing: .04em;
        text-transform: uppercase;
      }
      .evidence-rct { background: #dff5ed; color: #135946; }
      .evidence-observational { background: #e8effa; color: #31547e; }
      .evidence-card {
        height: 100%;
        padding: 1.1rem 1.2rem;
        border: 1px solid #dfe8e4;
        border-radius: 18px;
        background: rgba(255,255,255,.9);
      }
      .evidence-card h4 { margin: .15rem 0 .5rem; color: #174f42; }
      .evidence-card p { margin: 0; color: #5b6f68; line-height: 1.55; }
      .stTabs [role="tablist"] {
        display: flex;
        flex-wrap: wrap;
        gap: .45rem;
        height: auto;
        background: #e7eeea;
        padding: .45rem;
        border-radius: 14px;
      }
      .stTabs [role="tab"] {
        flex: 0 1 auto;
        min-height: 2.65rem;
        border-radius: 10px;
        padding: .55rem .85rem;
        background: #ffffff;
        color: #29483f !important;
        border: 1px solid #d6e2dd;
        font-weight: 700;
      }
      .stTabs [role="tab"] p,
      .stTabs [role="tab"] span {
        color: inherit !important;
        opacity: 1 !important;
      }
      .stTabs [role="tab"]:hover {
        background: #f3faf7;
        color: #125b48 !important;
        border-color: #9fcdbd;
      }
      .stTabs [role="tab"]:focus-visible {
        outline: 3px solid rgba(30, 124, 100, .28);
        outline-offset: 2px;
      }
      .stTabs [aria-selected="true"] {
        background: #176b57;
        color: #ffffff !important;
        border-color: #176b57;
        box-shadow: 0 3px 10px rgba(29, 63, 54, .08);
      }
      .stTabs [data-baseweb="tab-highlight"] {
        display: none;
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


@st.cache_data(ttl=3600)
def cognitive_decline_data() -> tuple[pd.DataFrame, str]:
    return fetch_cdc_aging_with_fallback(where="class='Cognitive Decline'")


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
            AS loaded_at,
          current_setting('transaction_read_only') AS transaction_read_only
        """
    ).iloc[0]
except psycopg.Error as exc:
    st.error(
        "The dashboard cannot reach the warehouse. Start PostgreSQL and run the "
        "pipeline before opening the interface."
    )
    st.code(str(exc))
    st.stop()

source_label = "Unknown source" if pd.isna(counts["source_label"]) else str(counts["source_label"])
source_version = "" if pd.isna(counts["source_version"]) else str(counts["source_version"]).strip()
is_synthetic = True if pd.isna(counts["is_synthetic"]) else bool(counts["is_synthetic"])
source_display = f"{source_label} v{source_version}" if source_version else source_label
database_is_read_only = str(counts["transaction_read_only"]).lower() == "on"

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

st.markdown("### Choose your starting point")
st.markdown(
    '<p class="section-note">This project has two connected products. Start with '
    "patient-level data engineering or explore population and intervention evidence.</p>",
    unsafe_allow_html=True,
)
product_columns = st.columns(2)
product_cards = (
    (
        "Product 01",
        "Clinical Data Warehouse",
        "Turn incompatible clinical files into a validated, reusable research cohort.",
        "Use: cohort builder, clinical patterns, quality checks, and pipeline provenance.",
    ),
    (
        "Product 02",
        "Brain Health Evidence Explorer",
        "Compare published randomized evidence with CDC population-surveillance patterns.",
        "Use: US-POINTER outcomes, demographic comparisons, geography, and uncertainty.",
    ),
)
for column, (number, title, body, use) in zip(product_columns, product_cards, strict=True):
    with column:
        st.markdown(
            f"""
            <div class="product-card">
              <span class="product-number">{number}</span>
              <h3>{title}</h3>
              <p>{body}</p>
              <strong>{use}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")
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
story_tab, cohort_tab, patterns_tab, brain_tab, trust_tab, runs_tab = st.tabs(
    [
        "How it solves the problem",
        "Build a cohort",
        "Explore clinical patterns",
        "Brain health evidence",
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
        (
            "03",
            "Prove quality",
            "Parity, relationships, date ordering, and ETL failures are measured.",
        ),
        (
            "04",
            "Build cohorts",
            "Researchers filter connected patient histories and export results.",
        ),
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
    sex_options = filter_values.loc[filter_values["filter_name"] == "sex", "value"].tolist()
    race_options = filter_values.loc[filter_values["filter_name"] == "race", "value"].tolist()
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

with brain_tab:
    st.subheader("What can improve brain health—and where is the population burden?")
    st.markdown(
        '<p class="section-note">Two evidence layers answer different questions. '
        "The randomized trial estimates an intervention effect; CDC surveillance "
        "describes population patterns. They are displayed together but never "
        "treated as the same type of evidence.</p>",
        unsafe_allow_html=True,
    )

    trial_column, surveillance_column = st.columns(2)
    with trial_column:
        st.markdown(
            """
            <div class="evidence-card">
              <span class="evidence-label evidence-rct">Randomized evidence</span>
              <h4>US-POINTER</h4>
              <p>
                Tests whether a structured, multidomain lifestyle program improves
                cognitive trajectory relative to a lower-intensity self-guided program.
                Random assignment supports a causal comparison between these two groups.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with surveillance_column:
        st.markdown(
            """
            <div class="evidence-card">
              <span class="evidence-label evidence-observational">
                Observational surveillance
              </span>
              <h4>CDC Healthy Aging / BRFSS</h4>
              <p>
                Describes self-reported cognitive decline across places and population
                groups. It identifies patterns and inequities, but cannot establish that
                a risk factor or intervention caused an outcome.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    trial_tab, population_tab, methods_tab = st.tabs(
        ["US-POINTER results", "CDC population patterns", "How to interpret"]
    )

    with trial_tab:
        evidence = load_us_pointer_evidence()
        primary = evidence.loc[evidence["outcome_role"] == "Primary"].iloc[0]

        st.markdown(
            '<span class="evidence-label evidence-rct">Randomized clinical trial</span>',
            unsafe_allow_html=True,
        )
        trial_metrics = st.columns(4)
        trial_metrics[0].metric("Participants randomized", format_count(PARTICIPANTS))
        trial_metrics[1].metric("Follow-up", f"{FOLLOW_UP_YEARS} years")
        trial_metrics[2].metric(
            "Primary difference",
            f"{primary['difference']:.3f} SD/year",
            help="Structured minus self-guided annual change in global cognition.",
        )
        trial_metrics[3].metric(
            "95% confidence interval",
            f"{primary['difference_ci_low']:.3f} to {primary['difference_ci_high']:.3f}",
        )

        st.markdown(
            f"""
            The structured group included **{STRUCTURED_PARTICIPANTS:,}** participants
            and the self-guided group included **{SELF_GUIDED_PARTICIPANTS:,}**.
            **{YEAR_2_COMPLETION_PERCENT:.0f}%** completed the year-two assessment.
            Both groups improved on the global cognitive composite; the structured
            intervention improved more rapidly by **0.029 SD per year**.
            """
        )

        slope_chart = evidence.set_index("outcome")[
            ["structured_slope", "self_guided_slope"]
        ].rename(
            columns={
                "structured_slope": "Structured",
                "self_guided_slope": "Self-guided",
            }
        )
        st.markdown("#### Annual cognitive-score change")
        st.bar_chart(
            slope_chart,
            color=["#176b57", "#8aa9c5"],
            y_label="Adjusted change (SD per year)",
        )

        result_table = evidence[
            [
                "outcome",
                "outcome_role",
                "difference",
                "difference_ci_low",
                "difference_ci_high",
                "ci_excludes_zero",
            ]
        ].copy()
        result_table["interpretation"] = result_table["ci_excludes_zero"].map(
            {
                True: "95% CI excludes zero",
                False: "95% CI includes zero",
            }
        )
        st.dataframe(
            result_table.drop(columns="ci_excludes_zero"),
            width="stretch",
            hide_index=True,
            column_config={
                "outcome": "Cognitive outcome",
                "outcome_role": "Analysis role",
                "difference": st.column_config.NumberColumn(
                    "Structured − self-guided", format="%.3f"
                ),
                "difference_ci_low": st.column_config.NumberColumn("95% CI low", format="%.3f"),
                "difference_ci_high": st.column_config.NumberColumn("95% CI high", format="%.3f"),
                "interpretation": "Uncertainty",
            },
        )
        st.markdown(
            f"""
            [Read the peer-reviewed JAMA report]({PUBLICATION_URL}) ·
            Trial registration: [{TRIAL_REGISTRATION}](
            https://clinicaltrials.gov/study/{TRIAL_REGISTRATION})
            """
        )
        st.markdown(
            '<p class="trust-note"><strong>What this does not prove:</strong> '
            "The result does not show that either program prevents Alzheimer disease, "
            "nor does the standardized cognitive-score difference directly state how "
            "many dementia cases were prevented. Longer follow-up is needed to assess "
            "clinical significance and durability.</p>",
            unsafe_allow_html=True,
        )

    with population_tab:
        st.markdown(
            '<span class="evidence-label evidence-observational">'
            "Observational population surveillance</span>",
            unsafe_allow_html=True,
        )
        try:
            cdc, cdc_source = cognitive_decline_data()
        except (OSError, ValueError, FileNotFoundError) as exc:
            st.warning(
                "Neither the live CDC API nor the versioned fallback snapshot is "
                "available. US-POINTER evidence remains accessible."
            )
            st.caption(str(exc))
        else:
            if cdc_source == "Live CDC API":
                st.success("Data source: live CDC API", icon="●")
            else:
                st.info(
                    "The CDC API is temporarily unavailable. Showing the committed "
                    "cognitive-decline snapshot downloaded July 27, 2026.",
                    icon="↻",
                )

            available_questions = sorted(cdc["question"].dropna().unique())
            default_question_index = next(
                (
                    index
                    for index, question in enumerate(available_questions)
                    if "happening more often or is getting worse" in question.lower()
                ),
                0,
            )
            selected_question = st.selectbox(
                "Population indicator",
                available_questions,
                index=default_question_index,
            )
            question_data = cdc.loc[cdc["question"] == selected_question].copy()

            years = sorted(
                question_data["year_end"].dropna().astype(int).unique(),
                reverse=True,
            )
            filter_year, filter_geography, filter_age = st.columns(3)
            selected_year = filter_year.selectbox("Reporting year", years)
            year_data = question_data.loc[question_data["year_end"] == selected_year].copy()

            geography_types = {
                "States and territories": r"[A-Z]{2}",
                "Census regions": r"NRE|MDW|SOU|WEST",
                "National": r"US",
            }
            selected_geography_type = filter_geography.selectbox(
                "Geographic level",
                list(geography_types),
            )
            geography_mask = year_data["location_abbr"].str.fullmatch(
                geography_types[selected_geography_type],
                na=False,
            )
            if selected_geography_type == "States and territories":
                geography_mask &= ~year_data["location_abbr"].eq("US")
            geography_data = year_data.loc[geography_mask].copy()
            geography_options = sorted(geography_data["location"].dropna().unique())
            selected_locations = st.multiselect(
                "State, territory, or region",
                geography_options,
                placeholder="All available locations",
                help="Leave empty to compare every available location at this geographic level.",
            )
            if selected_locations:
                geography_data = geography_data.loc[
                    geography_data["location"].isin(selected_locations)
                ]

            age_options = sorted(
                value
                for value in geography_data["stratification_1"].dropna().unique()
                if value != "Overall"
            )
            selected_ages = filter_age.multiselect(
                "Age group",
                age_options,
                default=age_options,
            )
            if selected_ages:
                geography_data = geography_data.loc[
                    geography_data["stratification_1"].isin(selected_ages)
                ]

            demographic_column, group_column = st.columns(2)
            demographic_label = demographic_column.selectbox(
                "Demographic comparison",
                ["Overall", "Sex", "Race and ethnicity"],
            )
            category_map = {
                "Sex": "Sex",
                "Race and ethnicity": "Race/Ethnicity",
            }
            if demographic_label == "Overall":
                demographic_data = geography_data.loc[
                    geography_data["stratification_category_2"].isna()
                    | geography_data["stratification_2"].eq("Overall")
                ].copy()
                selected_groups: list[str] = []
                group_column.caption(
                    "Overall compares age groups and geography without a sex or "
                    "race/ethnicity stratum."
                )
            else:
                demographic_category = category_map[demographic_label]
                demographic_data = geography_data.loc[
                    geography_data["stratification_category_2"].eq(demographic_category)
                ].copy()
                group_options = sorted(demographic_data["stratification_2"].dropna().unique())
                selected_groups = group_column.multiselect(
                    demographic_label,
                    group_options,
                    default=group_options,
                )
                if selected_groups:
                    demographic_data = demographic_data.loc[
                        demographic_data["stratification_2"].isin(selected_groups)
                    ]

            available_widths = demographic_data["confidence_width"].dropna()
            if available_widths.empty:
                width_data = demographic_data.copy()
            else:
                width_min = float(available_widths.min())
                width_max = float(available_widths.max())
                selected_width = st.slider(
                    "Maximum 95% confidence-interval width",
                    min_value=width_min,
                    max_value=width_max,
                    value=width_max,
                    help="Narrower intervals represent more precise survey estimates.",
                )
                width_data = demographic_data.loc[
                    demographic_data["confidence_width"].le(selected_width)
                    | demographic_data["confidence_width"].isna()
                ].copy()

            comparison_data = width_data.loc[width_data["estimate_available"]].copy()
            comparison_data["population_group"] = comparison_data["stratification_2"].fillna(
                "Overall"
            )
            comparison_data["comparison"] = (
                comparison_data["location"].fillna("Unknown")
                + " · "
                + comparison_data["stratification_1"].fillna("Overall")
                + " · "
                + comparison_data["population_group"]
            )
            comparison_data = comparison_data.drop_duplicates(
                ["location_abbr", "stratification_1", "population_group"]
            )

            population_metrics = st.columns(3)
            population_metrics[0].metric(
                "Comparable estimates",
                format_count(len(comparison_data)),
            )
            population_metrics[1].metric(
                "Locations represented",
                format_count(int(comparison_data["location_abbr"].nunique())),
            )
            population_metrics[2].metric(
                "Median CI width",
                (
                    f"{comparison_data['confidence_width'].median():.1f}"
                    if comparison_data["confidence_width"].notna().any()
                    else "Unavailable"
                ),
                help="Width of the published 95% confidence interval; narrower is more precise.",
            )

            if comparison_data.empty:
                st.info(
                    "No estimates match this combination. Broaden the geography, "
                    "demographic, age, or confidence-width filters."
                )
            else:
                st.markdown("#### Highest reported estimates in this comparison")
                top_comparisons = (
                    comparison_data.nlargest(25, "estimate")
                    .set_index("comparison")[["estimate"]]
                    .rename(columns={"estimate": "Reported estimate"})
                )
                st.bar_chart(
                    top_comparisons,
                    color="#5885b8",
                    horizontal=True,
                    x_label=str(comparison_data["value_unit"].dropna().iloc[0]),
                )
                st.dataframe(
                    comparison_data[
                        [
                            "location",
                            "stratification_1",
                            "population_group",
                            "estimate",
                            "confidence_low",
                            "confidence_high",
                            "confidence_width",
                            "value_unit",
                        ]
                    ].sort_values("estimate", ascending=False),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "location": "Location",
                        "stratification_1": "Age group",
                        "population_group": demographic_label,
                        "estimate": "Estimate",
                        "confidence_low": "95% CI low",
                        "confidence_high": "95% CI high",
                        "confidence_width": "CI width",
                        "value_unit": "Unit",
                    },
                )

            st.caption(
                "Source: CDC Alzheimer's Disease and Healthy Aging Data, derived "
                "primarily from BRFSS. Estimates are self-reported survey measures, "
                "not clinical Alzheimer diagnoses."
            )

    with methods_tab:
        comparison = pd.DataFrame(
            [
                (
                    "US-POINTER",
                    "Randomized clinical trial",
                    "Does the structured program outperform the self-guided program?",
                    "Causal comparison between randomized groups",
                    "Does not directly establish dementia prevention",
                ),
                (
                    "CDC Healthy Aging / BRFSS",
                    "Observational surveillance",
                    "Where and among whom is cognitive decline reported?",
                    "Population patterns, disparities, and uncertainty",
                    "Self-report; associations are not causal or diagnostic",
                ),
            ],
            columns=[
                "Evidence source",
                "Design",
                "Question answered",
                "Strongest inference",
                "Critical limitation",
            ],
        )
        st.dataframe(comparison, width="stretch", hide_index=True)
        st.markdown(
            """
            **Why the separation matters:** randomized assignment balances many
            competing explanations between intervention groups. A surveillance survey
            observes existing people and circumstances, so differences can reflect
            age, health, access, socioeconomic conditions, measurement, or other
            confounding factors. The two sources complement one another, but their
            numbers should not be pooled into a single effect estimate.
            """
        )

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
        st.markdown("#### Deployment safety")
        if database_is_read_only:
            st.success("Dashboard database session is read-only.")
        else:
            st.warning(
                "Dashboard database session is not read-only. Replace the Streamlit "
                "secret with the streamlit_reader connection string."
            )
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
