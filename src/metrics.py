"""
Core metric calculations for the UAC System Capacity & Care Load dashboard.
Kept separate from the Streamlit app so the same logic can be reused/tested
independently (and so it matches the analysis + EDA notebooks exactly).
"""

import pandas as pd


RAW_COLUMN_MAP = {
    'Children apprehended and placed in CBP custody*': 'apprehended',
    'total load on CBP': 'cbp_load',
    'Children transferred out of CBP custody': 'transferred_out',
    'total load on HHS': 'hhs_load',
    'Children discharged from HHS Care': 'discharged',
}


def load_and_prepare(csv_path):
    """Load the cleaned CSV and rebuild every derived column used across
    the project (same steps as the analysis notebook)."""
    df = pd.read_csv(csv_path, index_col=0)
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns=RAW_COLUMN_MAP)

    # Problem Statement 1: Total System Load
    df['total_system_load'] = df['cbp_load'] + df['hhs_load']

    # Problem Statement 2: Balance between inflow and outflow
    # Sign convention (matches project spec): Net Intake = inflow - outflow.
    # Positive  = intake outpacing outflow -> building pressure ("Stress").
    # Negative  = outflow outpacing intake -> load draining  ("Relief").
    df['cbp_net_intake'] = df['apprehended'] - df['transferred_out']
    df['hhs_net_intake'] = df['transferred_out'] - df['discharged']

    # Problem Statement 3: daily stress/relief status
    df['cbp_status'] = _daily_status(df['cbp_net_intake'])
    df['hhs_status'] = _daily_status(df['hhs_net_intake'])

    # Rolling averages & volatility
    df['hhs_load_7d_avg'] = df['hhs_load'].rolling(7, min_periods=1).mean()
    df['hhs_load_14d_avg'] = df['hhs_load'].rolling(14, min_periods=1).mean()
    df['hhs_load_volatility'] = df['hhs_load'].rolling(7, min_periods=1).std()

    # Care Load Growth Rate: day-over-day % change in HHS care load
    df['hhs_load_growth_rate'] = df['hhs_load'].pct_change() * 100

    # Sustained strain windows (5+ consecutive days of positive net intake,
    # i.e. intake consistently outpacing discharge)
    df['in_strain_window'] = _flag_runs(df['hhs_net_intake'] > 0, min_run_days=5)

    # Sustained high-load periods (75th percentile threshold, 5+ day run)
    threshold = df['hhs_load'].quantile(0.75)
    df['sustained_high_load'] = _flag_runs(df['hhs_load'] > threshold, min_run_days=5)

    # Backlog Accumulation: running total of positive net intake, reset to
    # zero every time the system returns to relief (net intake <= 0).
    # Captures HOW MUCH backlog has built up during the current pressure
    # streak, not just whether a streak is happening.
    positive_intake = df['hhs_net_intake'].where(df['hhs_net_intake'] > 0, 0.0)
    relief_reset = (df['hhs_net_intake'] <= 0).cumsum()
    df['hhs_backlog_accum'] = positive_intake.groupby(relief_reset).cumsum()

    return df


def _daily_status(net_series):
    """Relief / Stress / No Data per day, NaN-safe.
    net_series follows the intake-minus-outflow convention, so:
    positive = Stress (backlog building), negative/zero = Relief."""
    return net_series.apply(
        lambda v: "No Data" if pd.isna(v) else ("Stress" if v > 0 else "Relief")
    )


def _flag_runs(bool_series, min_run_days):
    """True only for rows that are part of an unbroken run of `True`
    at least `min_run_days` long. Used for both strain windows and
    sustained high-load periods."""
    run_id = (bool_series != bool_series.shift()).cumsum()
    run_lengths = bool_series.groupby(run_id).transform('sum')
    return bool_series & (run_lengths >= min_run_days)


def resample_to(df, freq):
    """freq: 'D' (daily/no resampling), 'W' (weekly), 'ME' (monthly)."""
    if freq == 'D':
        return df.copy()

    agg = df.resample(freq).agg({
        'apprehended': 'sum',
        'transferred_out': 'sum',
        'discharged': 'sum',
        'hhs_load': 'last',
        'cbp_load': 'last',
        'total_system_load': 'last',
        'hhs_net_intake': 'mean',
        'hhs_backlog_accum': 'last',
        'in_strain_window': 'sum',
        'sustained_high_load': 'sum',
    })
    agg['discharge_offset_ratio'] = agg['discharged'] / agg['transferred_out']
    return agg


def early_late_comparison(monthly_df):
    """Split a monthly-resampled dataframe in half and compare key KPIs."""
    midpoint = len(monthly_df) // 2
    early = monthly_df.iloc[:midpoint]
    late = monthly_df.iloc[midpoint:]

    comparison = pd.DataFrame({
        'Early period': [
            early['hhs_load'].mean(),
            early['discharge_offset_ratio'].mean(),
            early['in_strain_window'].mean(),
        ],
        'Late period': [
            late['hhs_load'].mean(),
            late['discharge_offset_ratio'].mean(),
            late['in_strain_window'].mean(),
        ],
    }, index=['Avg HHS Load', 'Avg Discharge Offset Ratio', 'Avg Strain Days/Month'])

    early_label = f"{early.index.min().date()} to {early.index.max().date()}"
    late_label = f"{late.index.min().date()} to {late.index.max().date()}"
    return comparison, early_label, late_label
