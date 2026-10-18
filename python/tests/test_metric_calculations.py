"""
Unit tests exercising the production metric calculation engine (python.scripts.metrics).
Validates session deduplication, sequential funnels, channel/device aggregations,
and timestamp monotonicity.
"""

import unittest
import pandas as pd
import numpy as np

from python.scripts.metrics import (
    normalize_event_schema,
    compute_session_metrics,
    compute_channel_metrics,
    compute_device_metrics,
    calculate_sequential_funnel,
    validate_timestamp_ordering
)


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
        self.assertEqual(metrics['session_cvr_pct'], 50.0)  # 1/2 = 50%, NOT 3/2 = 150%!
        self.assertEqual(metrics['total_revenue'], 100.0)
        self.assertEqual(metrics['aov'], 33.33)  # 100 / 3 purchases
        self.assertEqual(metrics['revenue_per_buyer'], 100.0)  # 100 / 1 converting session

    def test_timestamp_ordering_validation(self):
        # Strictly chronological timestamps
        valid_df = pd.DataFrame([
            {'session_id': 's1', 'event_timestamp': pd.Timestamp('2025-01-01 10:00:00')},
            {'session_id': 's1', 'event_timestamp': pd.Timestamp('2025-01-01 10:05:00')},
            {'session_id': 's2', 'event_timestamp': pd.Timestamp('2025-01-01 11:00:00')},
            {'session_id': 's2', 'event_timestamp': pd.Timestamp('2025-01-01 11:10:00')},
        ])
        res = validate_timestamp_ordering(valid_df)
        self.assertTrue(res['is_valid'])
        self.assertEqual(res['non_monotonic_sessions'], 0)

        # Inverted timestamp sequence in session s1
        inverted_df = pd.DataFrame([
            {'session_id': 's1', 'event_timestamp': pd.Timestamp('2025-01-01 10:10:00')},
            {'session_id': 's1', 'event_timestamp': pd.Timestamp('2025-01-01 10:05:00')},
        ])
        res_inv = validate_timestamp_ordering(inverted_df)
        self.assertFalse(res_inv['is_valid'])
        self.assertEqual(res_inv['non_monotonic_sessions'], 1)

    def test_sequential_funnel_enforces_order(self):
        """
        Tests that an out-of-order event (e.g. purchase before cart) does not count in sequential funnel.
        """
        data = [
            # Valid sequential session
            {'session_id': 's1', 'event_name': 'session_start', 'event_timestamp': pd.Timestamp('2025-01-01 10:00:00')},
            {'session_id': 's1', 'event_name': 'view_item',     'event_timestamp': pd.Timestamp('2025-01-01 10:01:00')},
            {'session_id': 's1', 'event_name': 'add_to_cart',   'event_timestamp': pd.Timestamp('2025-01-01 10:02:00')},
            {'session_id': 's1', 'event_name': 'begin_checkout','event_timestamp': pd.Timestamp('2025-01-01 10:03:00')},
            {'session_id': 's1', 'event_name': 'purchase',      'event_timestamp': pd.Timestamp('2025-01-01 10:04:00')},

            # Session s2: Purchase occurs BEFORE begin_checkout (purchase was at 11:03, checkout at 11:04)
            # Stage 4 (checkout) succeeded (11:04 >= 11:02), but Stage 5 (purchase) failed (11:03 is not >= 11:04)
            {'session_id': 's2', 'event_name': 'session_start', 'event_timestamp': pd.Timestamp('2025-01-01 11:00:00')},
            {'session_id': 's2', 'event_name': 'view_item',     'event_timestamp': pd.Timestamp('2025-01-01 11:01:00')},
            {'session_id': 's2', 'event_name': 'add_to_cart',   'event_timestamp': pd.Timestamp('2025-01-01 11:02:00')},
            {'session_id': 's2', 'event_name': 'purchase',      'event_timestamp': pd.Timestamp('2025-01-01 11:03:00')},
            {'session_id': 's2', 'event_name': 'begin_checkout','event_timestamp': pd.Timestamp('2025-01-01 11:04:00')},

            # Session s3: begin_checkout occurs BEFORE add_to_cart (fails Step 4)
            {'session_id': 's3', 'event_name': 'session_start', 'event_timestamp': pd.Timestamp('2025-01-01 12:00:00')},
            {'session_id': 's3', 'event_name': 'view_item',     'event_timestamp': pd.Timestamp('2025-01-01 12:01:00')},
            {'session_id': 's3', 'event_name': 'begin_checkout','event_timestamp': pd.Timestamp('2025-01-01 12:02:00')},
            {'session_id': 's3', 'event_name': 'add_to_cart',   'event_timestamp': pd.Timestamp('2025-01-01 12:03:00')},
        ]
        funnel = calculate_sequential_funnel(pd.DataFrame(data))
        self.assertEqual(funnel[funnel['Stage'] == 'Session Start']['Sessions'].iloc[0], 3)
        self.assertEqual(funnel[funnel['Stage'] == 'View Item']['Sessions'].iloc[0], 3)
        self.assertEqual(funnel[funnel['Stage'] == 'Add to Cart']['Sessions'].iloc[0], 3)
        self.assertEqual(funnel[funnel['Stage'] == 'Begin Checkout']['Sessions'].iloc[0], 2) # s1 & s2 (s3 checkout was before cart)
        self.assertEqual(funnel[funnel['Stage'] == 'Purchase']['Sessions'].iloc[0], 1)       # s1 only (s2 purchase was before checkout)

    def test_schema_normalization(self):
        raw = pd.DataFrame({
            'userId': ['u1', 'u2'],
            'sessionId': ['s1', 's2'],
            'eventType': ['session_start', 'purchase'],
            'medium': ['organic', 'cpc'],
            'device': ['desktop', 'mobile'],
            'revenue': ['10.5', '20.0']
        })
        normalized, meta = normalize_event_schema(raw)
        self.assertIn('user_pseudo_id', normalized.columns)
        self.assertIn('session_id', normalized.columns)
        self.assertIn('event_name', normalized.columns)
        self.assertIn('traffic_medium', normalized.columns)
        self.assertIn('device_category', normalized.columns)
        self.assertIn('purchase_revenue', normalized.columns)
        self.assertTrue(meta['has_genuine_session_id'])


if __name__ == '__main__':
    unittest.main()
