"""
System Capacity & Care Load Analytics — Streamlit Dashboard
Unaccompanied Alien Children (UAC) Program

Run with:  streamlit run dashboard/streamlit_app.py
(run this command from the project root, so the relative data path resolves)
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow importing src/metrics.py when running from the app/ folder
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.metrics import load_and_prepare, resample_to, early_late_comparison


# ---------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------
st.set_page_config(
    page_title="UAC System Capacity & Care Load Analytics",
    layout="wide",
)

st.title("System Capacity & Care Load Analytics")
st.caption("Unaccompanied Alien Children (UAC) Program — CBP & HHS pipeline")


# ---------------------------------------------------------------
# Data loading (cached so it doesn't reload on every interaction)
# ---------------------------------------------------------------
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cleaned_data" / "sorted_data.csv"


@st.cache_data
def get_data(path):
    return load_and_prepare(path)


if not DATA_PATH.exists():
    st.error(
        f"Couldn't find the data file at `{DATA_PATH}`. "
        "Make sure `cleaned_data.csv` is in `data/cleaned_data/` at the project root."
    )
    st.stop()

df = get_data(DATA_PATH)


# ---------------------------------------------------------------
# Sidebar — user controls
# ---------------------------------------------------------------
st.sidebar.header("Filters")

min_date, max_date = df.index.min().date(), df.index.max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

granularity = st.sidebar.radio(
    "Time granularity",
    options=["Daily", "Weekly", "Monthly"],
    index=0,
)
freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}

metric_options = st.sidebar.multiselect(
    "Metrics to show on the load chart",
    options=["CBP Custody load", "HHS Care load", "Total System Load"],
    default=["HHS Care load", "CBP Custody load"],
)

show_strain = st.sidebar.checkbox("Highlight sustained strain windows", value=True)

# Apply date filter
if len(date_range) == 2:
    start, end = date_range
    filtered = df[(df.index.date >= start) & (df.index.date <= end)]
else:
    filtered = df.copy()

resampled = resample_to(filtered, freq_map[granularity])


# ---------------------------------------------------------------
# KPI Summary Cards
# ---------------------------------------------------------------
st.subheader("KPI Summary")

col1, col2, col3, col4 = st.columns(4)

avg_total_load = filtered['total_system_load'].mean()
strain_days = int(filtered['in_strain_window'].sum())
strain_pct = filtered['in_strain_window'].mean() * 100 if len(filtered) else 0
avg_offset_ratio = (
    filtered['discharged'].sum() / filtered['transferred_out'].sum()
    if filtered['transferred_out'].sum() > 0 else float('nan')
)
avg_volatility = filtered['hhs_load_volatility'].mean()

col1.metric("Avg Total System Load", f"{avg_total_load:,.0f}")
col2.metric("Strain Days", f"{strain_days:,}", help="Days inside a sustained strain window (5+ consecutive stress days)")
col3.metric("Discharge Offset Ratio", f"{avg_offset_ratio:.2f}", help="Discharged ÷ Transferred-in. ≥1.0 means the system kept pace.")
col4.metric("Avg Care Load Volatility", f"{avg_volatility:,.1f}", help="7-day rolling standard deviation of HHS load")


# ---------------------------------------------------------------
# System Load Overview Pane
# ---------------------------------------------------------------
st.subheader("System Load Overview")

chart_df = pd.DataFrame(index=resampled.index)
if "CBP Custody load" in metric_options:
    chart_df["CBP Custody load"] = resampled["cbp_load"]
if "HHS Care load" in metric_options:
    chart_df["HHS Care load"] = resampled["hhs_load"]
if "Total System Load" in metric_options:
    chart_df["Total System Load"] = resampled["total_system_load"]

if not chart_df.empty:
    st.line_chart(chart_df)
else:
    st.info("Select at least one metric in the sidebar to show the chart.")

if show_strain and granularity == "Daily":
    strain_days_list = filtered.index[filtered['in_strain_window']]
    if len(strain_days_list) > 0:
        st.caption(
            f"⚠️ {len(strain_days_list)} day(s) in the selected range fall inside a sustained strain window "
            f"(first: {strain_days_list.min().date()}, last: {strain_days_list.max().date()})."
        )
    else:
        st.caption("✅ No sustained strain windows in the selected range.")


# ---------------------------------------------------------------
# CBP vs HHS Load Comparison
# ---------------------------------------------------------------
st.subheader("CBP vs HHS Load Comparison")
st.line_chart(resampled[["cbp_load", "hhs_load"]].rename(
    columns={"cbp_load": "CBP Custody", "hhs_load": "HHS Care"}
))


# ---------------------------------------------------------------
# Net Intake & Backlog Trends
# ---------------------------------------------------------------
st.subheader("Net Intake & Backlog Trends")

left, right = st.columns(2)

with left:
    st.markdown("**Discharge Offset Ratio** (discharged ÷ transferred-in)")
    if granularity == "Monthly" and "discharge_offset_ratio" in resampled.columns:
        st.bar_chart(resampled["discharge_offset_ratio"])
        st.caption("Values ≥ 1.0 mean discharges kept pace with arrivals that period.")
    else:
        st.info("Switch to Monthly granularity in the sidebar to see the Discharge Offset Ratio trend.")

with right:
    st.markdown("**Sustained strain days per period**")
    if "in_strain_window" in resampled.columns:
        st.bar_chart(resampled["in_strain_window"])
    else:
        st.line_chart(filtered["in_strain_window"].astype(int))


# ---------------------------------------------------------------
# Early vs Late comparison (only meaningful with enough monthly data)
# ---------------------------------------------------------------
st.subheader("Early vs Late Period Comparison")

monthly_full = resample_to(filtered, "ME")
if len(monthly_full) >= 4:
    comparison, early_label, late_label = early_late_comparison(monthly_full)
    st.caption(f"Early period: {early_label}  |  Late period: {late_label}")
    st.dataframe(comparison.style.format("{:.2f}"), use_container_width=True)
else:
    st.info("Select a wider date range (at least a few months) to see the early vs. late comparison.")


st.divider()
st.caption(
    "Data source: HHS Unaccompanied Alien Children Program daily reporting. "
    "Net flow convention: outflow − inflow (negative = stress, positive = relief)."
)
