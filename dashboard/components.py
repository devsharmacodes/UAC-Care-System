"""
Reusable UI building blocks for the UAC dashboard: KPI cards, charts,
a searchable/sortable/paginated data table, an activity feed, and an
auto-generated insights list. Kept separate from streamlit_app.py so
each piece can be reused across pages / swapped for a real API later.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import palette, plotly_template, tooltip_icon


# ---------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------
def kpi_card(label: str, value: str, help_text: str, delta: str = None, delta_good: bool = True):
    delta_html = ""
    if delta:
        cls = "uac-up" if delta_good else "uac-down"
        arrow = "▲" if delta_good else "▼"
        delta_html = f'<div class="uac-kpi-delta {cls}">{arrow} {delta}</div>'

    st.markdown(
        f"""
        <div class="uac-card">
            <div class="uac-kpi-top">
                <span class="uac-kpi-label">{label}</span>
                {tooltip_icon(help_text)}
            </div>
            <div class="uac-kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_skeleton_row(n: int = 5):
    cols = st.columns(n)
    for c in cols:
        with c:
            st.markdown('<div class="uac-skel"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------
# Charts (Plotly, theme-aware)
# ---------------------------------------------------------------
def _style_fig(fig, title: str, height: int = 320):
    p = palette()
    fig.update_layout(
        template=plotly_template(),
        title=dict(text=title, font=dict(size=15)),
        height=height,
        margin=dict(l=10, r=10, t=45, b=10),
        paper_bgcolor=p["card"],
        plot_bgcolor=p["card"],
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        hovermode="x unified",
    )
    return fig


def trend_line_chart(df: pd.DataFrame, y_col: str, title: str, color: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df[y_col], mode="lines", line=dict(color=color, width=2.4),
        fill="tozeroy", fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba"),
        name=y_col,
    ))
    return _style_fig(fig, title)


def comparison_bar_chart(df: pd.DataFrame, y_col: str, title: str, threshold: float = None):
    p = palette()
    colors = [p["success"] if v >= (threshold or 0) else p["danger"] for v in df[y_col].fillna(0)]
    fig = go.Figure(go.Bar(x=df.index, y=df[y_col], marker_color=colors))
    if threshold is not None:
        fig.add_hline(y=threshold, line_dash="dot", line_color=p["text_muted"])
    return _style_fig(fig, title)


def donut_chart(labels: list, values: list, title: str, colors: list):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62, marker=dict(colors=colors),
        textinfo="label+percent",
    ))
    return _style_fig(fig, title, height=300)


def area_chart(df: pd.DataFrame, y_col: str, title: str, color: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df[y_col], mode="lines", line=dict(color=color, width=2),
        fill="tozeroy",
    ))
    return _style_fig(fig, title)


# ---------------------------------------------------------------
# Status badge helper
# ---------------------------------------------------------------
def status_badge_html(status: str) -> str:
    cls = {"Stress": "uac-badge-stress", "Relief": "uac-badge-relief"}.get(status, "uac-badge-nodata")
    return f'<span class="uac-badge {cls}">{status}</span>'


# ---------------------------------------------------------------
# Searchable / sortable / paginated data table
# ---------------------------------------------------------------
def data_table(df: pd.DataFrame, key_prefix: str, page_size: int = 12):
    display_df = df.reset_index().rename(columns={"index": "date"})
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    top = st.columns([2, 1.3, 1])
    with top[0]:
        query = st.text_input("Search by date (YYYY-MM-DD)", key=f"{key_prefix}_q", placeholder="e.g. 2024-04")
    with top[1]:
        sort_col = st.selectbox(
            "Sort by", options=["date", "hhs_load", "cbp_load", "total_system_load", "hhs_status"],
            key=f"{key_prefix}_sort",
        )
    with top[2]:
        ascending = st.checkbox("Ascending", value=False, key=f"{key_prefix}_asc")

    if query:
        display_df = display_df[display_df["date"].str.contains(query)]

    display_df = display_df.sort_values(sort_col, ascending=ascending)

    total_rows = len(display_df)
    n_pages = max(1, -(-total_rows // page_size))
    page = st.number_input(
        "Page", min_value=1, max_value=n_pages, value=1, step=1, key=f"{key_prefix}_page"
    )
    start, end = (page - 1) * page_size, page * page_size
    page_df = display_df.iloc[start:end].copy()
    page_df["hhs_status"] = page_df["hhs_status"].apply(status_badge_html)

    st.markdown(
        page_df[["date", "cbp_load", "hhs_load", "total_system_load", "hhs_status"]]
        .rename(columns={
            "date": "Date", "cbp_load": "CBP Load", "hhs_load": "HHS Load",
            "total_system_load": "Total Load", "hhs_status": "Status",
        })
        .to_html(escape=False, index=False, classes="uac-table", border=0),
        unsafe_allow_html=True,
    )
    st.caption(f"Showing {min(end, total_rows) - start} of {total_rows} rows · page {page} of {n_pages}")


# ---------------------------------------------------------------
# Activity feed (derived from strain / high-load state transitions)
# ---------------------------------------------------------------
def activity_feed(df: pd.DataFrame, max_items: int = 8):
    p = palette()
    events = []
    strain_starts = df.index[(df["in_strain_window"]) & (~df["in_strain_window"].shift(1, fill_value=False))]
    strain_ends = df.index[(~df["in_strain_window"]) & (df["in_strain_window"].shift(1, fill_value=False))]

    for d in strain_starts:
        events.append((d, "Sustained strain window began", "warning"))
    for d in strain_ends:
        events.append((d, "Sustained strain window ended", "success"))

    events.sort(key=lambda e: e[0], reverse=True)
    events = events[:max_items]

    if not events:
        st.info("No strain-window transitions in the selected range.")
        return

    color_map = {"warning": p["warning"], "success": p["success"], "danger": p["danger"]}
    html = ""
    for d, label, kind in events:
        html += (
            f'<div class="uac-activity-item">'
            f'<div class="uac-dot" style="background:{color_map[kind]}"></div>'
            f'<div><div>{label}</div>'
            f'<div class="uac-activity-time">{d.date()}</div></div></div>'
        )
    st.markdown(f'<div class="uac-card">{html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------
# Auto-generated insights
# ---------------------------------------------------------------
def insights_list(filtered: pd.DataFrame, resampled_monthly: pd.DataFrame):
    p = palette()
    insights = []

    if len(filtered) > 1:
        load_change = filtered["hhs_load"].iloc[-1] - filtered["hhs_load"].iloc[0]
        direction = "risen" if load_change > 0 else "fallen"
        insights.append(
            f"HHS care load has {direction} by {abs(load_change):,.0f} children "
            f"over the selected range."
        )

    strain_pct = filtered["in_strain_window"].mean() * 100 if len(filtered) else 0
    if strain_pct > 0:
        insights.append(f"{strain_pct:.1f}% of days in this range fall inside a sustained strain window.")
    else:
        insights.append("No sustained strain windows detected in this range.")

    if "discharge_offset_ratio" in resampled_monthly.columns and len(resampled_monthly):
        below_one = (resampled_monthly["discharge_offset_ratio"] < 1.0).sum()
        if below_one:
            insights.append(
                f"{below_one} month(s) in range had a Discharge Offset Ratio below 1.0 "
                f"— discharges fell behind arrivals."
            )

    if not insights:
        insights.append("Not enough data in the selected range to generate insights.")

    icons = ["📈", "⚠️", "🔁", "💡"]
    html = ""
    for i, text in enumerate(insights):
        html += f'<div class="uac-insight"><span>{icons[i % len(icons)]}</span><span>{text}</span></div>'
    st.markdown(f'<div class="uac-card">{html}</div>', unsafe_allow_html=True)
