"""Streamlit interface for the local synthetic clinical data warehouse."""

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
    page_title="Clinical Warehouse Explorer",
    page_icon="🧬",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp { background: #f5f7f6; }
      [data-testid="stHeader"] { background: transparent; }
      .hero {
        padding: 2rem 2.2rem;
        border-radius: 22px;
        color: #f7fffc;
        background:
          radial-gradient(circle at 85% 20%, rgba(97, 214, 181, .35), transparent 28%),
          linear-gradient(125deg, #12372f 0%, #185b4c 58%, #247a66 100%);
        box-shadow: 0 16px 38px rgba(21, 75, 63, .18);
        margin-bottom: 1.2rem;
      }
      .hero-kicker {
        color: #a8ead6;
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .14em;
        text-transform: uppercase;
      }
      .hero h1 {
        font-size: clamp(2rem, 5vw, 3.6rem);
        letter-spacing: -.045em;
        line-height: 1;
        margin: .55rem 0 .8rem;
      }
      .hero p { color: #d9f4ea; max-width: 760px; margin: 0; }
      [data-testid="stMetric"] {
        background: white;
        border: 1px solid #dde7e3;
        border-radius: 16px;
        padding: 1rem 1.1rem;
        box-shadow: 0 6px 20px rgba(26, 60, 52, .05);
      }
      [data-testid="stMetricValue"] { color: #164f43; }
      .section-note {
        color: #526a63;
        font-size: .92rem;
        margin-top: -.5rem;
        margin-bottom: 1rem;
      }
      .synthetic-note {
        border-left: 4px solid #e4a853;
        background: #fff8eb;
        padding: .8rem 1rem;
        border-radius: 0 10px 10px 0;
        color: #6f5329;
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
def quality_results() -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL) as connection:
        return pd.DataFrame(check.as_dict() for check in run_quality_checks(connection))


def format_count(value: int) -> str:
    return f"{value:,}"


st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Synthetic clinical analytics</div>
      <h1>Clinical Warehouse Explorer</h1>
      <p>
        Follow validated Synthea records from source-shaped staging tables to
        connected, analytics-ready patient, encounter, condition, and observation facts.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    counts = query(
        """
        SELECT
          (SELECT COUNT(*) FROM warehouse.dim_patient) AS patients,
          (SELECT COUNT(*) FROM warehouse.fact_encounter) AS encounters,
          (SELECT COUNT(*) FROM warehouse.fact_condition) AS conditions,
          (SELECT COUNT(*) FROM warehouse.fact_observation) AS observations
        """
    ).iloc[0]
except psycopg.Error as exc:
    st.error(
        "The dashboard cannot reach the local warehouse. Start Docker and run the "
        "warehouse loading commands before opening the interface."
    )
    st.code(str(exc))
    st.stop()

metric_columns = st.columns(4)
metric_columns[0].metric("Patients", format_count(int(counts["patients"])))
metric_columns[1].metric("Encounters", format_count(int(counts["encounters"])))
metric_columns[2].metric("Condition episodes", format_count(int(counts["conditions"])))
metric_columns[3].metric("Observations", format_count(int(counts["observations"])))

st.markdown(
    '<p class="synthetic-note">This interface contains synthetic Synthea data only. '
    "Its summaries demonstrate engineering and analytical behavior—not conclusions "
    "about a real population.</p>",
    unsafe_allow_html=True,
)

overview_tab, condition_tab, observation_tab, quality_tab, pipeline_tab = st.tabs(
    ["Overview", "Conditions", "Observations", "Data quality", "Pipeline"]
)

with overview_tab:
    left, right = st.columns((1.15, 1))
    with left:
        st.subheader("Healthcare utilization")
        st.markdown(
            '<p class="section-note">Encounter volume by source-defined visit class.</p>',
            unsafe_allow_html=True,
        )
        encounter_classes = query(
            """
            SELECT encounter_class, COUNT(*) AS encounters
            FROM warehouse.fact_encounter
            GROUP BY encounter_class
            ORDER BY encounters DESC
            """
        )
        st.bar_chart(
            encounter_classes.set_index("encounter_class"),
            color="#247a66",
            horizontal=True,
        )

    with right:
        st.subheader("Patient coverage")
        st.markdown(
            '<p class="section-note">Synthetic demographics represented in the warehouse.</p>',
            unsafe_allow_html=True,
        )
        demographics = query(
            """
            SELECT
              COALESCE(race, 'Unknown') AS race,
              COUNT(*) AS patients
            FROM warehouse.dim_patient
            GROUP BY COALESCE(race, 'Unknown')
            ORDER BY patients DESC
            """
        )
        st.bar_chart(demographics.set_index("race"), color="#e4a853")

    st.subheader("Encounter duration and cost")
    utilization = query(
        """
        SELECT
          encounter_class,
          COUNT(*) AS encounters,
          ROUND(AVG(EXTRACT(EPOCH FROM (stop_at - start_at)) / 60)::numeric, 1)
            AS average_minutes,
          ROUND(SUM(total_claim_cost), 2) AS total_claim_cost
        FROM warehouse.fact_encounter
        GROUP BY encounter_class
        ORDER BY encounters DESC
        """
    )
    st.dataframe(
        utilization,
        width="stretch",
        hide_index=True,
        column_config={
            "encounter_class": "Encounter class",
            "encounters": st.column_config.NumberColumn("Encounters", format="%d"),
            "average_minutes": st.column_config.NumberColumn("Average minutes", format="%.1f"),
            "total_claim_cost": st.column_config.NumberColumn(
                "Synthetic claim cost", format="$%.2f"
            ),
        },
    )

with condition_tab:
    st.subheader("Most prevalent coded conditions and findings")
    st.markdown(
        '<p class="section-note">Ranked by distinct synthetic patients, not raw rows.</p>',
        unsafe_allow_html=True,
    )
    conditions = query(
        """
        SELECT
          c.description,
          c.code,
          COUNT(*) AS episodes,
          COUNT(DISTINCT f.patient_key) AS patients,
          COUNT(*) FILTER (WHERE f.resolved_date IS NULL) AS unresolved
        FROM warehouse.fact_condition f
        JOIN warehouse.dim_code c ON c.code_key = f.code_key
        GROUP BY c.description, c.code
        ORDER BY patients DESC, episodes DESC
        LIMIT 25
        """
    )
    st.bar_chart(
        conditions.head(12).set_index("description")[["patients"]],
        color="#247a66",
        horizontal=True,
    )
    st.dataframe(conditions, width="stretch", hide_index=True)

with observation_tab:
    category_column, measure_column = st.columns((0.9, 1.4))
    with category_column:
        st.subheader("Observation mix")
        categories = query(
            """
            SELECT
              REPLACE(c.code_system, 'urn:synthea:observation:', '') AS category,
              COUNT(*) AS observations
            FROM warehouse.fact_observation f
            JOIN warehouse.dim_code c ON c.code_key = f.code_key
            GROUP BY category
            ORDER BY observations DESC
            """
        )
        st.bar_chart(
            categories.set_index("category"),
            color="#5c8fc4",
            horizontal=True,
        )

    with measure_column:
        st.subheader("Most frequent numeric measurements")
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
        st.dataframe(measurements, width="stretch", hide_index=True)

    st.subheader("Observation timeline")
    monthly = query(
        """
        SELECT
          DATE_TRUNC('year', observed_at)::date AS year,
          COUNT(*) AS observations
        FROM warehouse.fact_observation
        GROUP BY year
        ORDER BY year
        """
    )
    st.line_chart(monthly.set_index("year"), color="#247a66")

with quality_tab:
    st.subheader("Data-quality report")
    st.markdown(
        '<p class="section-note">Structural checks run directly against staging and '
        "warehouse tables. Warnings remain visible rather than being silently removed.</p>",
        unsafe_allow_html=True,
    )
    quality = quality_results()
    status_counts = quality["status"].value_counts()
    status_columns = st.columns(3)
    status_columns[0].metric("Passed", int(status_counts.get("PASS", 0)))
    status_columns[1].metric("Warnings", int(status_counts.get("WARN", 0)))
    status_columns[2].metric("Failures", int(status_counts.get("FAIL", 0)))
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

with pipeline_tab:
    st.subheader("ETL run history")
    st.markdown(
        '<p class="section-note">A durable audit trail of each warehouse transformation.</p>',
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

st.sidebar.caption("Local PostgreSQL • Synthetic data only")
