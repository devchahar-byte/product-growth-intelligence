"""
Unit tests for statistical helpers in stats_helpers.py.
Uses unittest for zero-dependency test execution, fully compatible with pytest.
"""

import unittest
import numpy as np
from python.scripts.stats_helpers import (
    conversion_rate_ci,
    two_prop_z_test,
    sample_size_for_proportion,
    bootstrap_ci,
    detect_outliers_iqr
)


class TestConversionRateCI(unittest.TestCase):
    def test_valid_ci(self):
        rate, lower, upper = conversion_rate_ci(150, 5000)
        self.assertEqual(rate, 0.03)
        self.assertTrue(0.0 < lower < rate < upper < 1.0)
        self.assertEqual(round(lower, 4), 0.0256)
        self.assertEqual(round(upper, 4), 0.0351)

    def test_zero_conversions(self):
        rate, lower, upper = conversion_rate_ci(0, 100)
        self.assertEqual(rate, 0.0)
        self.assertEqual(lower, 0.0)
        self.assertTrue(upper > 0.0)

    def test_all_conversions(self):
        rate, lower, upper = conversion_rate_ci(100, 100)
        self.assertEqual(rate, 1.0)
        self.assertTrue(lower < 1.0)
        self.assertEqual(upper, 1.0)

    def test_zero_sample_size_raises(self):
        with self.assertRaises(ValueError):
            conversion_rate_ci(0, 0)

    def test_negative_trials_raises(self):
        with self.assertRaises(ValueError):
            conversion_rate_ci(5, -10)

    def test_conversions_greater_than_trials_raises(self):
        with self.assertRaises(ValueError):
            conversion_rate_ci(10, 5)

    def test_negative_conversions_raises(self):
        with self.assertRaises(ValueError):
            conversion_rate_ci(-1, 50)

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            conversion_rate_ci(10, 100, confidence=1.5)
        with self.assertRaises(ValueError):
            conversion_rate_ci(10, 100, confidence=0.0)


class TestTwoPropZTest(unittest.TestCase):
    def test_valid_test_with_lift_and_ci(self):
        res = two_prop_z_test(conv_a=100, n_a=5000, conv_b=150, n_b=5000)
        self.assertEqual(res['cvr_a'], 0.02)
        self.assertEqual(res['cvr_b'], 0.03)
        self.assertEqual(res['diff'], 0.01)
        self.assertTrue(res['significant'])
        self.assertEqual(res['lift_pct'], 50.0)
        self.assertTrue(res['diff_ci_lower'] < res['diff'] < res['diff_ci_upper'])
        self.assertTrue(res['diff_ci_lower'] > 0)  # Statistically significant positive lift

    def test_zero_baseline_returns_none_lift(self):
        res = two_prop_z_test(conv_a=0, n_a=1000, conv_b=10, n_b=1000)
        self.assertEqual(res['cvr_a'], 0.0)
        self.assertEqual(res['cvr_b'], 0.01)
        self.assertIsNone(res['lift_pct'])  # Undefined lift, must be None
        self.assertTrue(res['significant'])
        self.assertTrue(res['diff_ci_lower'] < res['diff'] < res['diff_ci_upper'])

    def test_zero_sample_size_raises(self):
        with self.assertRaises(ValueError):
            two_prop_z_test(0, 0, 10, 100)
        with self.assertRaises(ValueError):
            two_prop_z_test(10, 100, 5, 0)

    def test_conversions_exceeding_sample_raises(self):
        with self.assertRaises(ValueError):
            two_prop_z_test(150, 100, 10, 100)
        with self.assertRaises(ValueError):
            two_prop_z_test(10, 100, 200, 100)

    def test_invalid_alpha_raises(self):
        with self.assertRaises(ValueError):
            two_prop_z_test(10, 100, 15, 100, alpha=1.2)


class TestSampleSizeForProportion(unittest.TestCase):
    def test_valid_sample_size(self):
        n = sample_size_for_proportion(baseline_cvr=0.02, min_detectable_effect=0.10)
        self.assertTrue(n > 10000)
        self.assertIsInstance(n, int)

    def test_exact_sample_size_calculation(self):
        # Mobile experiment baseline: 0.81% CVR
        n_20 = sample_size_for_proportion(baseline_cvr=0.0081, min_detectable_effect=0.20, alpha=0.05, power=0.80)
        n_10 = sample_size_for_proportion(baseline_cvr=0.0081, min_detectable_effect=0.10, alpha=0.05, power=0.80)
        self.assertEqual(n_20, 52819)
        self.assertEqual(n_10, 201758)

    def test_invalid_baseline_raises(self):
        with self.assertRaises(ValueError):
            sample_size_for_proportion(baseline_cvr=0.0, min_detectable_effect=0.10)
        with self.assertRaises(ValueError):
            sample_size_for_proportion(baseline_cvr=1.2, min_detectable_effect=0.10)

    def test_invalid_mde_raises(self):
        with self.assertRaises(ValueError):
            sample_size_for_proportion(baseline_cvr=0.02, min_detectable_effect=-0.05)


class TestBootstrapCI(unittest.TestCase):
    def test_bootstrap_mean(self):
        data = np.array([10.0, 12.0, 15.0, 14.0, 13.0, 11.0, 12.5])
        stat, lower, upper = bootstrap_ci(data, statistic=np.mean)
        self.assertTrue(lower < stat < upper)

    def test_empty_data_raises(self):
        with self.assertRaises(ValueError):
            bootstrap_ci(np.array([]))


if __name__ == '__main__':
    unittest.main()
