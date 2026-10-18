"""
Unit tests for core metric calculations, session modeling, and funnel progressions.
"""

import unittest
import pandas as pd
import numpy as np


def compute_session_metrics(df: pd.DataFrame):
    """
    Standardized canonical session-level aggregation.
    Ensures that multiple purchase events within one session only count as 1 converting session.
    """
    sess_id_col = 'session_id' if 'session_id' in df.columns else 'user_id'
    ev_col = 'event_name' if 'event_name' in df.columns else 'event_type'
    dev_col = 'device_category' if 'device_category' in df.columns else 'device'
    ch_col = 'traffic_medium' if 'traffic_medium' in df.columns else 'channel'
    rev_col = 'purchase_revenue' if 'purchase_revenue' in df.columns else 'amount'

    sessions = df.groupby(sess_id_col).agg(
        device=(dev_col, 'first'),
        channel=(ch_col, 'first'),
        has_purchase=(ev_col, lambda x: int((x == 'purchase').any())),
        purchase_count=(ev_col, lambda x: int((x == 'purchase').sum())),
        revenue=(rev_col, 'sum') if rev_col in df.columns else (ev_col, lambda x: 0.0)
    ).reset_index()

    total_sessions = len(sessions)
    converting_sessions = int(sessions['has_purchase'].sum())
    total_purchase_events = int(sessions['purchase_count'].sum())
    cvr = (converting_sessions / total_sessions * 100.0) if total_sessions > 0 else 0.0

    return {
        'total_sessions': total_sessions,
        'converting_sessions': converting_sessions,
        'total_purchase_events': total_purchase_events,
        'session_cvr': round(cvr, 2)
    }


def validate_funnel_timestamp_ordering(df: pd.DataFrame):
    """
    Checks chronological timestamp progression within each session.
    Returns (valid: bool, inversion_count: int, details: list).
    """
    if 'event_timestamp' not in df.columns:
        return True, 0, []

    df_sorted = df.copy()
    df_sorted['ts'] = pd.to_datetime(df_sorted['event_timestamp'])

    stage_weights = {
        'session_start': 1,
        'page_view': 2,
        'view_item': 3,
        'add_to_cart': 4,
        'begin_checkout': 5,
        'purchase': 6
    }

    inversions = 0
    for sess, group in df_sorted.groupby('session_id'):
        if len(group) <= 1:
            continue
        g = group.sort_values('ts')
        stages = [stage_weights.get(e, 0) for e in g['event_name'] if e in stage_weights]
        # check if strictly non-decreasing
        for i in range(len(stages) - 1):
            if stages[i] > stages[i + 1]:
                inversions += 1
                break

    return inversions == 0, inversions, []


class TestSessionMetrics(unittest.TestCase):
    def test_multi_purchase_per_session_does_not_inflate_cvr(self):
        """
        Critical test: If a session contains 3 purchase events,
        it must count as exactly 1 converting session, NOT 3 conversions!
        """
        data = [
            {'session_id': 's1', 'event_name': 'session_start', 'device_category': 'desktop', 'traffic_medium': 'organic', 'purchase_revenue': 0.0},
            {'session_id': 's1', 'event_name': 'view_item', 'device_category': 'desktop', 'traffic_medium': 'organic', 'purchase_revenue': 0.0},
            {'session_id': 's1', 'event_name': 'purchase', 'device_category': 'desktop', 'traffic_medium': 'organic', 'purchase_revenue': 50.0},
            {'session_id': 's1', 'event_name': 'purchase', 'device_category': 'desktop', 'traffic_medium': 'organic', 'purchase_revenue': 30.0},
            {'session_id': 's1', 'event_name': 'purchase', 'device_category': 'desktop', 'traffic_medium': 'organic', 'purchase_revenue': 20.0},
            {'session_id': 's2', 'event_name': 'session_start', 'device_category': 'mobile', 'traffic_medium': 'cpc', 'purchase_revenue': 0.0},
            {'session_id': 's2', 'event_name': 'view_item', 'device_category': 'mobile', 'traffic_medium': 'cpc', 'purchase_revenue': 0.0},
        ]
        df = pd.DataFrame(data)
        metrics = compute_session_metrics(df)

        self.assertEqual(metrics['total_sessions'], 2)
        self.assertEqual(metrics['total_purchase_events'], 3)
        self.assertEqual(metrics['converting_sessions'], 1)  # Only s1 converted
        self.assertEqual(metrics['session_cvr'], 50.0)  # 1/2 = 50%, NOT 3/2 = 150%!

    def test_timestamp_ordering_detection(self):
        # Valid chronological flow
        valid_data = [
            {'session_id': 's1', 'event_name': 'session_start', 'event_timestamp': '2025-01-01 10:00:00'},
            {'session_id': 's1', 'event_name': 'view_item', 'event_timestamp': '2025-01-01 10:02:00'},
            {'session_id': 's1', 'event_name': 'add_to_cart', 'event_timestamp': '2025-01-01 10:03:00'},
            {'session_id': 's1', 'event_name': 'purchase', 'event_timestamp': '2025-01-01 10:05:00'},
        ]
        is_valid, inv_count, _ = validate_funnel_timestamp_ordering(pd.DataFrame(valid_data))
        self.assertTrue(is_valid)
        self.assertEqual(inv_count, 0)

        # Inverted flow: purchase timestamp before add_to_cart timestamp
        inverted_data = [
            {'session_id': 's2', 'event_name': 'session_start', 'event_timestamp': '2025-01-01 10:00:00'},
            {'session_id': 's2', 'event_name': 'purchase', 'event_timestamp': '2025-01-01 10:02:00'},
            {'session_id': 's2', 'event_name': 'add_to_cart', 'event_timestamp': '2025-01-01 10:05:00'},
        ]
        is_valid, inv_count, _ = validate_funnel_timestamp_ordering(pd.DataFrame(inverted_data))
        self.assertFalse(is_valid)
        self.assertEqual(inv_count, 1)


if __name__ == '__main__':
    unittest.main()
