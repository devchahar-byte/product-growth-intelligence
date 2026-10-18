"""
Production Metric Engine & Data Quality Validators
Product Growth Intelligence Platform
Dev Chahar | Manipal University Jaipur
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np


def normalize_event_schema(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Standardizes schema column names for GA4 / e-commerce event exports.
    Returns normalized DataFrame and a dict of validation metadata.
    """
    df = df.copy()
    col_mapping = {
        'user_id': 'user_pseudo_id',
        'userId': 'user_pseudo_id',
        'session': 'session_id',
        'sessionId': 'session_id',
        'event': 'event_name',
        'eventType': 'event_name',
        'medium': 'traffic_medium',
        'channel': 'traffic_medium',
        'device': 'device_category',
        'device_type': 'device_category',
        'revenue': 'purchase_revenue',
        'price': 'purchase_revenue',
        'timestamp': 'event_timestamp',
        'date': 'event_date'
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns and v not in df.columns})

    metadata = {
        'has_genuine_session_id': 'session_id' in df.columns or 'ga_session_id' in df.columns,
        'has_timestamps': 'event_timestamp' in df.columns,
        'has_revenue': 'purchase_revenue' in df.columns
    }

    # Session construction
    if 'session_id' not in df.columns:
        if 'ga_session_id' in df.columns and 'user_pseudo_id' in df.columns:
            df['session_id'] = df['user_pseudo_id'].astype(str) + '_' + df['ga_session_id'].astype(str)
        elif 'user_pseudo_id' in df.columns:
            # Explicitly mark synthetic fallback
            df['session_id'] = df['user_pseudo_id'].astype(str) + '_synthetic_session'
            metadata['session_id_fallback'] = True
        else:
            raise ValueError("Uploaded data must contain a 'session_id' or 'user_pseudo_id' column.")

    # Timestamps & dates
    if 'event_timestamp' in df.columns:
        df['event_timestamp'] = pd.to_datetime(df['event_timestamp'], errors='coerce')
    else:
        df['event_timestamp'] = pd.NaT

    if 'event_date' in df.columns:
        df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')
    elif df['event_timestamp'].notna().any():
        df['event_date'] = df['event_timestamp'].dt.floor('D')
    else:
        df['event_date'] = pd.Timestamp.now().floor('D')

    # Defaults
    if 'event_name' not in df.columns:
        raise ValueError("Data must contain an 'event_name' column indicating the event type.")
    if 'traffic_medium' not in df.columns:
        df['traffic_medium'] = '(none)'
    if 'device_category' not in df.columns:
        df['device_category'] = 'desktop'
    if 'purchase_revenue' not in df.columns:
        df['purchase_revenue'] = 0.0
    else:
        df['purchase_revenue'] = pd.to_numeric(df['purchase_revenue'], errors='coerce').fillna(0.0)

    return df, metadata


def compute_session_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes session-level conversion KPIs.
    Guarantees conversion is calculated as unique sessions with >= 1 purchase
    divided by total eligible sessions.
    """
    total_events = len(df)
    total_sessions = int(df['session_id'].nunique())
    unique_users = int(df['user_pseudo_id'].nunique()) if 'user_pseudo_id' in df.columns else total_sessions

    purchasing_session_ids = set(df[df['event_name'] == 'purchase']['session_id'].unique())
    converting_sessions = len(purchasing_session_ids)
    total_purchase_events = int((df['event_name'] == 'purchase').sum())
    total_revenue = float(df['purchase_revenue'].sum())

    session_cvr = (converting_sessions / total_sessions * 100.0) if total_sessions > 0 else 0.0
    aov = (total_revenue / total_purchase_events) if total_purchase_events > 0 else 0.0
    revenue_per_buyer = (total_revenue / converting_sessions) if converting_sessions > 0 else 0.0

    return {
        'total_events': total_events,
        'total_sessions': total_sessions,
        'unique_users': unique_users,
        'converting_sessions': converting_sessions,
        'total_purchase_events': total_purchase_events,
        'session_cvr_pct': round(session_cvr, 2),
        'total_revenue': round(total_revenue, 2),
        'aov': round(aov, 2),
        'revenue_per_buyer': round(revenue_per_buyer, 2)
    }


def compute_channel_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes acquisition channel volume and session conversion rates.
    """
    records = []
    for med, grp in df.groupby('traffic_medium'):
        s_count = grp['session_id'].nunique()
        c_count = grp[grp['event_name'] == 'purchase']['session_id'].nunique()
        p_events = int((grp['event_name'] == 'purchase').sum())
        rev = float(grp['purchase_revenue'].sum())
        cvr = round(100.0 * c_count / s_count, 2) if s_count > 0 else 0.0
        aov_val = round(rev / p_events, 2) if p_events > 0 else 0.0
        records.append({
            'traffic_medium': med,
            'sessions': s_count,
            'converting_sessions': c_count,
            'purchases': p_events,
            'revenue': round(rev, 2),
            'cvr_pct': cvr,
            'aov': aov_val
        })
    return pd.DataFrame(records).sort_values(by='sessions', ascending=False)


def compute_device_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes device-category volume and session conversion rates.
    """
    records = []
    for dev, grp in df.groupby('device_category'):
        s_count = grp['session_id'].nunique()
        c_count = grp[grp['event_name'] == 'purchase']['session_id'].nunique()
        p_events = int((grp['event_name'] == 'purchase').sum())
        rev = float(grp['purchase_revenue'].sum())
        cvr = round(100.0 * c_count / s_count, 2) if s_count > 0 else 0.0
        records.append({
            'device_category': dev,
            'sessions': s_count,
            'converting_sessions': c_count,
            'purchases': p_events,
            'revenue': round(rev, 2),
            'cvr_pct': cvr
        })
    return pd.DataFrame(records).sort_values(by='sessions', ascending=False)


def calculate_sequential_funnel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates within-session sequential conversion funnel.
    Requires each stage transition to occur in chronological timestamp order:
    session_start <= view_item <= add_to_cart <= begin_checkout <= purchase.
    """
    stages = ['session_start', 'view_item', 'add_to_cart', 'begin_checkout', 'purchase']
    stage_labels = ['Session Start', 'View Item', 'Add to Cart', 'Begin Checkout', 'Purchase']

    # Extract earliest timestamp per session for each stage
    session_times = df.groupby('session_id').apply(
        lambda g: pd.Series({
            s: g[g['event_name'] == s]['event_timestamp'].min() for s in stages
        }),
        include_groups=False
    )

    t_sess = session_times['session_start']
    t_view = session_times['view_item']
    t_cart = session_times['add_to_cart']
    t_chk  = session_times['begin_checkout']
    t_pur  = session_times['purchase']

    s1 = t_sess.notna()
    s2 = s1 & t_view.notna() & (t_view >= t_sess)
    s3 = s2 & t_cart.notna() & (t_cart >= t_view)
    s4 = s3 & t_chk.notna() & (t_chk >= t_cart)
    s5 = s4 & t_pur.notna() & (t_pur >= t_chk)

    counts = [int(s1.sum()), int(s2.sum()), int(s3.sum()), int(s4.sum()), int(s5.sum())]
    top_n = counts[0] if counts[0] > 0 else 1

    pct_of_top = [round(100.0 * c / top_n, 2) for c in counts]
    drop_offs = [0.0]
    for i in range(1, len(counts)):
        prev = counts[i-1]
        curr = counts[i]
        drop = round(100.0 * (1 - curr / prev), 2) if prev > 0 else 0.0
        drop_offs.append(drop)

    return pd.DataFrame({
        'Stage': stage_labels,
        'Sessions': counts,
        '% of Top': pct_of_top,
        'Step Drop-off (%)': drop_offs
    })


def validate_timestamp_ordering(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates chronological monotonicity of event timestamps within multi-event sessions.
    """
    if 'event_timestamp' not in df.columns or df['event_timestamp'].isna().all():
        return {
            'applicable': False,
            'message': 'Timestamp ordering check skipped: Event timestamps are unavailable.'
        }

    # Group by session and evaluate monotonicity
    ts_checks = df.groupby('session_id')['event_timestamp'].agg(['count', lambda s: s.is_monotonic_increasing])
    ts_checks.columns = ['event_count', 'is_monotonic']
    multi_event_sessions = ts_checks[ts_checks['event_count'] > 1]
    total_multi_sessions = len(multi_event_sessions)
    non_monotonic_sessions = int((~multi_event_sessions['is_monotonic']).sum())

    return {
        'applicable': True,
        'total_multi_event_sessions': total_multi_sessions,
        'non_monotonic_sessions': non_monotonic_sessions,
        'is_valid': non_monotonic_sessions == 0
    }
