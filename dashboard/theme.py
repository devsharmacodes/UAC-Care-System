"""
Theme system for the UAC System Capacity & Care Load dashboard.

Handles the light/dark palette and all custom CSS (cards, badges,
hover tooltips, nav states, skeleton loaders). Streamlit has no native
localStorage access, so the active theme is persisted in the page's
URL query string (?theme=dark) -- it survives a refresh of the same
tab/bookmark, which is the closest equivalent available in Streamlit
without shipping a custom JS component.
"""

import streamlit as st

LIGHT = {
    "bg": "#f6f7fb",
    "bg_secondary": "#ffffff",
    "card": "#ffffff",
    "border": "#e6e8ef",
    "text": "#0f172a",
    "text_muted": "#64748b",
    "accent": "#4f46e5",
    "accent_soft": "#eef0ff",
    "success": "#16a34a",
    "success_soft": "#e9f9ee",
    "danger": "#dc2626",
    "danger_soft": "#fdecec",
    "warning": "#d97706",
    "warning_soft": "#fef4e6",
    "shadow": "0 1px 2px rgba(15,23,42,.06), 0 1px 3px rgba(15,23,42,.08)",
}

DARK = {
    "bg": "#0b0e14",
    "bg_secondary": "#10141d",
    "card": "#141926",
    "border": "#242b3d",
    "text": "#e7eaf2",
    "text_muted": "#8d95ab",
    "accent": "#818cf8",
    "accent_soft": "#1c2040",
    "success": "#4ade80",
    "success_soft": "#132a1c",
    "danger": "#f87171",
    "danger_soft": "#2c1616",
    "warning": "#fbbf24",
    "warning_soft": "#2c2312",
    "shadow": "0 1px 2px rgba(0,0,0,.4), 0 2px 10px rgba(0,0,0,.35)",
}


def get_theme() -> str:
    """Active theme name, seeded from the URL query param on first load."""
    if "theme" not in st.session_state:
        st.session_state.theme = st.query_params.get("theme", "light")
    return st.session_state.theme


def toggle_theme():
    st.session_state.theme = "dark" if get_theme() == "light" else "light"
    st.query_params["theme"] = st.session_state.theme


def palette() -> dict:
    return DARK if get_theme() == "dark" else LIGHT


def plotly_template() -> str:
    return "plotly_dark" if get_theme() == "dark" else "plotly_white"


def inject_css():
    p = palette()
    st.markdown(
        f"""
    <style>
    :root {{
        --bg: {p['bg']}; --bg-secondary: {p['bg_secondary']}; --card: {p['card']};
        --border: {p['border']}; --text: {p['text']}; --text-muted: {p['text_muted']};
        --accent: {p['accent']}; --accent-soft: {p['accent_soft']};
        --success: {p['success']}; --success-soft: {p['success_soft']};
        --danger: {p['danger']}; --danger-soft: {p['danger_soft']};
        --warning: {p['warning']}; --warning-soft: {p['warning_soft']};
        --shadow: {p['shadow']}; --radius: 14px;
    }}

    html, body, [data-testid="stAppViewContainer"], .main, [data-testid="stHeader"] {{
        background-color: var(--bg) !important;
        transition: background-color .25s ease;
    }}
    [data-testid="stHeader"] {{ background-color: transparent !important; }}
    [data-testid="stSidebar"] {{
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border);
    }}
    h1, h2, h3, h4, h5, p, span, label, li {{ color: var(--text); }}
    .block-container {{ padding-top: 1.6rem; max-width: 1300px; }}
    hr {{ border-color: var(--border) !important; }}

    /* ---- Cards ---- */
    .uac-card {{
        background: var(--card); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 1.05rem 1.2rem;
        box-shadow: var(--shadow); transition: transform .15s ease, box-shadow .15s ease;
        height: 100%;
    }}
    .uac-card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.12); }}

    .uac-kpi-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
    .uac-kpi-label {{
        font-size: .78rem; color: var(--text-muted); font-weight: 600;
        text-transform: uppercase; letter-spacing: .04em;
    }}
    .uac-kpi-value {{ font-size: 1.7rem; font-weight: 700; color: var(--text); margin-top: 3px; }}
    .uac-kpi-delta {{ font-size: .8rem; font-weight: 600; margin-top: 4px; }}
    .uac-up {{ color: var(--success); }}
    .uac-down {{ color: var(--danger); }}

    /* ---- Pure-CSS hover tooltip (no JS) ---- */
    .uac-tt {{ position: relative; display: inline-flex; cursor: help; }}
    .uac-tt .uac-tt-icon {{
        width: 16px; height: 16px; border-radius: 50%; background: var(--border);
        color: var(--text-muted); font-size: .68rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
    }}
    .uac-tt .uac-tt-bubble {{
        visibility: hidden; opacity: 0; position: absolute; z-index: 50;
        bottom: 135%; left: 50%; transform: translateX(-50%) translateY(4px);
        width: 220px; background: var(--text); color: var(--bg);
        font-size: .76rem; font-weight: 500; line-height: 1.35;
        padding: .5rem .65rem; border-radius: 8px;
        box-shadow: 0 8px 20px rgba(0,0,0,.25);
        transition: opacity .15s ease, transform .15s ease;
        pointer-events: none;
    }}
    .uac-tt:hover .uac-tt-bubble {{
        visibility: visible; opacity: 1; transform: translateX(-50%) translateY(0);
    }}

    /* ---- Badges ---- */
    .uac-badge {{
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: .72rem; font-weight: 700;
    }}
    .uac-badge-stress {{ background: var(--danger-soft); color: var(--danger); }}
    .uac-badge-relief {{ background: var(--success-soft); color: var(--success); }}
    .uac-badge-nodata {{ background: var(--border); color: var(--text-muted); }}

    /* ---- Intro banner ---- */
    .uac-intro {{
        background: linear-gradient(135deg, var(--accent-soft), transparent 70%);
        border: 1px solid var(--border); border-radius: var(--radius);
        padding: 1rem 1.3rem; margin-bottom: 1.3rem;
    }}
    .uac-intro .eyebrow {{
        font-size: .72rem; font-weight: 700; letter-spacing: .06em;
        text-transform: uppercase; color: var(--accent); margin-bottom: 4px;
    }}

    /* ---- Activity feed ---- */
    .uac-activity-item {{ display: flex; gap: .7rem; padding: .55rem 0; border-bottom: 1px solid var(--border); }}
    .uac-activity-item:last-child {{ border-bottom: none; }}
    .uac-dot {{ width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }}
    .uac-activity-time {{ color: var(--text-muted); font-size: .76rem; }}

    /* ---- Insights ---- */
    .uac-insight {{
        display: flex; gap: .6rem; align-items: flex-start;
        padding: .6rem .1rem; border-bottom: 1px dashed var(--border);
    }}
    .uac-insight:last-child {{ border-bottom: none; }}

    /* ---- Skeleton loader ---- */
    .uac-skel {{
        background: linear-gradient(90deg, var(--border) 25%, var(--bg-secondary) 37%, var(--border) 63%);
        background-size: 400% 100%; animation: uac-shimmer 1.3s ease infinite;
        border-radius: var(--radius); height: 92px;
    }}
    @keyframes uac-shimmer {{ 0% {{ background-position: 100% 50%; }} 100% {{ background-position: 0 50%; }} }}

    /* ---- Data table ---- */
    .uac-table {{ width: 100%; border-collapse: collapse; font-size: .86rem; }}
    .uac-table th {{
        text-align: left; padding: .55rem .7rem; color: var(--text-muted);
        font-size: .72rem; text-transform: uppercase; letter-spacing: .03em;
        border-bottom: 1px solid var(--border);
    }}
    .uac-table td {{ padding: .55rem .7rem; border-bottom: 1px solid var(--border); color: var(--text); }}
    .uac-table tr:hover td {{ background: var(--accent-soft); }}

    /* ---- Buttons ---- */
    button[kind="primary"] {{ border-radius: 9px !important; font-weight: 600 !important; }}
    button[kind="secondary"] {{ border-radius: 9px !important; }}
    div[data-testid="stButton"] button {{ transition: transform .12s ease; }}
    div[data-testid="stButton"] button:hover {{ transform: translateY(-1px); }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def tooltip_icon(text: str) -> str:
    """Small '?' badge that reveals `text` in a floating bubble on hover.
    Returns raw HTML -- embed inline next to a label with unsafe_allow_html."""
    return (
        f'<span class="uac-tt"><span class="uac-tt-icon">?</span>'
        f'<span class="uac-tt-bubble">{text}</span></span>'
    )
