"""
Statistical helpers for the Product Growth Intelligence Platform.
Dev Chahar | Manipal University Jaipur
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Tuple, Optional


def conversion_rate_ci(
    conversions: int,
    trials: int,
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Wilson score confidence interval for a binomial proportion.

    Parameters
    ----------
    conversions : int  — number of successes
    trials      : int  — total observations
    confidence  : float — e.g. 0.95 for 95% CI

    Returns
    -------
    (rate, lower, upper)
    """
    if trials == 0:
        return 0.0, 0.0, 0.0
    p = conversions / trials
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    denom = 1 + z**2 / trials
    centre_adj = p + z**2 / (2 * trials)
    margin = z * np.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2))
    lower = (centre_adj - margin) / denom
    upper = (centre_adj + margin) / denom
    return round(p, 4), round(lower, 4), round(upper, 4)


def two_prop_z_test(
    conv_a: int, n_a: int,
    conv_b: int, n_b: int,
    alpha: float = 0.05
) -> dict:
    """
    Two-proportion z-test (A vs B).
    Suitable for A/B test conversion comparison.

    Returns a dict with p_value, z_stat, significant, lift_pct.
    """
    p_a = conv_a / n_a
    p_b = conv_b / n_b
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n_a + 1/n_b))
    if se == 0:
        return {'z_stat': 0, 'p_value': 1.0, 'significant': False, 'lift_pct': 0.0}
    z = (p_b - p_a) / se
    p_value = 2 * stats.norm.sf(abs(z))  # two-tailed
    lift = round(100 * (p_b - p_a) / p_a, 2) if p_a > 0 else None
    return {
        'cvr_a': round(p_a, 4),
        'cvr_b': round(p_b, 4),
        'z_stat': round(z, 3),
        'p_value': round(p_value, 5),
        'significant': p_value < alpha,
        'lift_pct': lift
    }


def sample_size_for_proportion(
    baseline_cvr: float,
    min_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.80
) -> int:
    """
    Required sample size per variant for a two-proportion test.

    Parameters
    ----------
    baseline_cvr          : control conversion rate (e.g. 0.03)
    min_detectable_effect : relative lift you want to detect (e.g. 0.10 = 10%)
    alpha                 : significance level (default 0.05)
    power                 : statistical power (default 0.80)

    Returns
    -------
    Sample size per variant (int)
    """
    p1 = baseline_cvr
    p2 = p1 * (1 + min_detectable_effect)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta  = stats.norm.ppf(power)
    p_bar   = (p1 + p2) / 2
    n = ((z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) +
          z_beta  * np.sqrt(p1*(1-p1) + p2*(1-p2))) ** 2) / (p2 - p1)**2
    return int(np.ceil(n))


def bootstrap_ci(
    data: np.ndarray,
    statistic=np.mean,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    random_state: int = 42
) -> Tuple[float, float, float]:
    """
    Bootstrap confidence interval for any statistic.

    Returns (observed_stat, lower_ci, upper_ci)
    """
    rng = np.random.default_rng(random_state)
    boot_stats = [statistic(rng.choice(data, size=len(data), replace=True))
                  for _ in range(n_bootstrap)]
    alpha = (1 - confidence) / 2
    lower = np.quantile(boot_stats, alpha)
    upper = np.quantile(boot_stats, 1 - alpha)
    return round(statistic(data), 4), round(lower, 4), round(upper, 4)


def detect_outliers_iqr(
    series: pd.Series,
    iqr_multiplier: float = 1.5
) -> pd.Series:
    """
    Flag outliers using IQR method. Returns boolean Series.
    """
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < q1 - iqr_multiplier * iqr) | (series > q3 + iqr_multiplier * iqr)


if __name__ == '__main__':
    # Quick sanity check
    rate, lo, hi = conversion_rate_ci(150, 5000)
    print(f'CVR: {rate:.2%}  95% CI: [{lo:.2%}, {hi:.2%}]')

    result = two_prop_z_test(150, 5000, 180, 5000)
    print('A/B test result:', result)

    n = sample_size_for_proportion(0.03, 0.10)
    print(f'Required sample per variant: {n:,}')
