"""
System Capacity & Care Load Analytics — Premium Streamlit Dashboard
Unaccompanied Alien Children (UAC) Program

Run with:  streamlit run dashboard/streamlit_app.py
(run from the project root so the relative data path and the
`theme` / `components` / `src.metrics` imports all resolve)

Note on scope: Streamlit is a server-rendered Python app, not a
client-side SPA. True URL routing, localStorage, and JS page
transitions aren't natively available -- this file uses the closest
Streamlit-native equivalents (session_state view switching, query-param
theme persistence, CSS-only tooltips/animations) rather than faking
them with brittle workarounds.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from theme import inject_css, get_theme, toggle_theme, palette
from components import (
    kpi_card, kpi_skeleton_row, trend_line_chart, comparison_bar_chart,
    donut_chart, area_chart, data_table, activity_feed, insights_list,
)
from src.metrics import load_and_prepare, resample_to, early_late_comparison


# =================================================================
# Page setup
# =================================================================
st.set_page_config(page_title="UAC Capacity Analytics", page_icon="🛡️", layout="wide")
inject_css()
p = palette()

NAV_ITEMS = [
    ("Dashboard", "🏠", "Overview of system load, KPIs, and current status."),
    ("Analytics", "📊", "Deeper trend, comparison, and volatility analysis."),
    ("Data", "🗂️", "Search, sort, and export the underlying daily records."),
    ("Reports", "📄", "Early vs. late period comparison and summary export."),
    ("Activity", "🕒", "Timeline of strain-window and load-state events."),
    ("Settings", "⚙️", "Theme and display preferences."),
]
if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"


# =================================================================
# Sidebar navigation
# =================================================================
with st.sidebar:
    st.markdown("### 🛡️ UAC Analytics")
    st.caption("Capacity & care load monitoring")
    st.write("")
    for name, icon, desc in NAV_ITEMS:
        active = st.session_state.nav == name
        if st.button(
            f"{icon}  {name}", key=f"nav_{name}", use_container_width=True,
            type="primary" if active else "secondary", help=desc,
        ):
            st.session_state.nav = name
            st.rerun()
    st.write("")
    st.divider()
    st.caption("Data: HHS UAC Program daily reporting")

page = st.session_state.nav


# =================================================================
# Header
# =================================================================
head_l, head_r = st.columns([5, 1])
with head_l:
    st.markdown(f"## {dict((n, i) for n, i, _ in NAV_ITEMS)[page]}  {page}")
with head_r:
    st.write("")
    if st.button(
        "🌙 Dark" if get_theme() == "light" else "☀️ Light",
        use_container_width=True, help="Switch between light and dark mode. Your choice is saved in the page URL.",
    ):
        toggle_theme()
        st.rerun()

st.markdown(
    """
    <div class="uac-intro">
        <div class="eyebrow">What this dashboard does</div>
        <div style="font-weight:700; font-size:1.05rem; margin-bottom:6px;">
            System Capacity and Care Load Analytics for the Unaccompanied Alien
            Children (UAC) Program: A Data-Driven Framework for Healthcare
            Pipeline Monitoring
        </div>
        The Unaccompanied Alien Children (UAC) Program is a federally mandated
        pipeline in which minors apprehended by U.S. Customs and Border
        Protection (CBP) are transferred into the care of the Department of
        Health and Human Services (HHS) for shelter, medical screening, and
        eventual placement with sponsors. This dashboard translates daily
        CBP–HHS reporting data into four capacity indicators — Total System
        Load, Net Daily Flow, Care Load Volatility, and the Discharge Offset
        Ratio — and uses rolling-window analysis to identify sustained periods
        of capacity strain, supporting situational awareness for staffing and
        shelter planning.
    </div>
    """,
    unsafe_allow_html=True,
)


# =================================================================
# Data loading (cached; skeleton shown only on the true first load)
# =================================================================
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cleaned_data" / "sorted_data.csv"


@st.cache_data
def get_data(path):
    return load_and_prepare(path)


if not DATA_PATH.exists():
    st.error(f"Couldn't find the data file at `{DATA_PATH}`.")
    st.stop()

if "warm" not in st.session_state:
    kpi_skeleton_row(5)
    time.sleep(0.35)  # first-load only; subsequent reruns hit the cache instantly
    st.session_state.warm = True

try:
    df = get_data(DATA_PATH)
except Exception as e:
    st.error(f"Failed to load or process the data file: {e}")
    st.stop()


# =================================================================
# Global filters (shown on every page except Settings)
# =================================================================
if page != "Settings":
    f1, f2, f3 = st.columns([2, 1.4, 2])
    with f1:
        min_date, max_date = df.index.min().date(), df.index.max().date()
        date_range = st.date_input("Date range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)
    with f2:
        granularity = st.radio("Granularity", ["Daily", "Weekly", "Monthly"], horizontal=True)
    with f3:
        st.write("")

    if len(date_range) == 2:
        start, end = date_range
        filtered = df[(df.index.date >= start) & (df.index.date <= end)]
    else:
        st.info("Pick an end date to apply the range filter.")
        filtered = df.copy()

    if filtered.empty:
        st.warning("No data in the selected range. Widen it above.")
        st.stop()

    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}
    resampled = resample_to(filtered, freq_map[granularity])
    monthly = resample_to(filtered, "ME")
    st.divider()


# =================================================================
# PAGE: Dashboard
# =================================================================
if page == "Dashboard":
    cols = st.columns(5)
    avg_load = filtered["total_system_load"].mean()
    strain_days = int(filtered["in_strain_window"].sum())
    transferred = filtered["transferred_out"].sum()
    offset_ratio = filtered["discharged"].sum() / transferred if transferred > 0 else float("nan")
    growth = filtered["hhs_load_growth_rate"].mean()
    active_backlog = filtered["hhs_backlog_accum"].iloc[-1]

    with cols[0]:
        kpi_card("Total Records", f"{len(filtered):,}", "Number of daily records in the selected range.")
    with cols[1]:
        kpi_card("Active Users", f"{filtered['hhs_load'].iloc[-1]:,.0f}",
                  "Children currently active in HHS care as of the last day in range.")
    with cols[2]:
        kpi_card("Performance", f"{offset_ratio:.2f}",
                  "Discharge Offset Ratio: discharged ÷ transferred-in. ≥1.0 means the system kept pace.",
                  delta=f"{'Above' if offset_ratio >= 1 else 'Below'} break-even", delta_good=offset_ratio >= 1)
    with cols[3]:
        kpi_card("Growth", f"{growth:+.2f}%",
                  "Average day-over-day % change in HHS care load over the selected range.",
                  delta="rising" if growth > 0 else "falling", delta_good=growth <= 0)
    with cols[4]:
        kpi_card("Recent Activity", f"{strain_days} strain days",
                  "Days inside a sustained strain window (5+ consecutive days of positive net intake).",
                  delta=f"backlog {active_backlog:,.0f}", delta_good=active_backlog == 0)

    st.write("")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.plotly_chart(
            trend_line_chart(resampled, "total_system_load", "Total System Load — Trend", p["accent"]),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            donut_chart(
                ["CBP Custody", "HHS Care"],
                [resampled["cbp_load"].mean(), resampled["hhs_load"].mean()],
                "Load Distribution", [p["warning"], p["accent"]],
            ),
            use_container_width=True,
        )

    st.write("")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("##### Insights")
        insights_list(filtered, monthly)
    with c4:
        st.markdown("##### Recent Activity")
        activity_feed(filtered)


# =================================================================
# PAGE: Analytics
# =================================================================
elif page == "Analytics":
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            trend_line_chart(resampled, "hhs_load", "HHS Care Load", p["accent"]),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            trend_line_chart(resampled, "cbp_load", "CBP Custody Load", p["warning"]),
            use_container_width=True,
        )

    if granularity == "Monthly" and "discharge_offset_ratio" in resampled.columns:
        st.plotly_chart(
            comparison_bar_chart(resampled, "discharge_offset_ratio",
                                  "Monthly Discharge Offset Ratio", threshold=1.0),
            use_container_width=True,
        )
    else:
        st.info("Switch to Monthly granularity to see the Discharge Offset Ratio comparison chart.")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(
            area_chart(resampled, "hhs_backlog_accum", "Backlog Accumulation", p["danger"]),
            use_container_width=True,
        )
    with c4:
        st.plotly_chart(
            trend_line_chart(filtered.resample("W").mean(numeric_only=True), "hhs_load_volatility",
                              "Care Load Volatility (weekly avg)", p["success"]),
            use_container_width=True,
        )


# =================================================================
# PAGE: Data
# =================================================================
elif page == "Data":
    st.markdown("##### Daily Records")
    data_table(filtered, key_prefix="daily")


# =================================================================
# PAGE: Reports
# =================================================================
elif page == "Reports":
    st.markdown("##### Early vs. Late Period Comparison")
    if len(monthly) >= 4:
        comparison, early_label, late_label = early_late_comparison(monthly)
        st.caption(f"Early period: {early_label}  |  Late period: {late_label}")
        st.dataframe(comparison.style.format("{:.2f}"), use_container_width=True)
    else:
        st.info("Select a wider date range (at least a few months) to generate this report.")

    st.write("")
    st.download_button(
        "⬇️ Download filtered data as CSV",
        data=filtered.to_csv().encode("utf-8"),
        file_name="uac_filtered_data.csv",
        mime="text/csv",
    )


# =================================================================
# PAGE: Activity
# =================================================================
elif page == "Activity":
    st.markdown("##### Full Activity Timeline")
    activity_feed(filtered, max_items=30)


# =================================================================
# PAGE: Settings
# =================================================================
elif page == "Settings":
    st.markdown("##### Display Preferences")
    st.write(f"Current theme: **{get_theme().title()}**")
    st.caption(
        "Theme is stored in this page's URL (`?theme=...`), so bookmarking or "
        "refreshing the same link keeps your preference. Streamlit apps don't "
        "have access to the browser's localStorage without a custom JS component."
    )
    if st.button("Toggle theme"):
        toggle_theme()
        st.rerun()

    st.write("")
    st.markdown("##### About")
    st.caption(
        "UAC System Capacity & Care Load Analytics — built on a shared "
        "`src/metrics.py` module so the dashboard, notebooks, and any future "
        "reports stay numerically consistent."
    )


st.divider()
st.caption(
    "Net intake convention: inflow − outflow (positive = pressure/stress, negative = relief). "
    "Sample UI data derived directly from the HHS reporting dataset — no synthetic records."
)