"""
Statistical helpers for the Product Growth Intelligence Platform.
Author: Dev Chahar | Manipal University Jaipur
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Tuple, Optional, Dict, Any


def conversion_rate_ci(
    conversions: int,
    trials: int,
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Wilson score confidence interval for a binomial proportion.

    Parameters
    ----------
    conversions : int
        Number of successes. Must satisfy 0 <= conversions <= trials.
    trials : int
        Total observations. Must be > 0.
    confidence : float
        Confidence level (default: 0.95). Must be in (0, 1).

    Returns
    -------
    (rate, lower, upper) : Tuple[float, float, float]
        Point estimate, lower CI bound, and upper CI bound.

    Raises
    ------
    ValueError
        If trials <= 0, conversions < 0, conversions > trials, or confidence not in (0, 1).
    """
    if trials <= 0:
        raise ValueError(f"Sample size (trials) must be positive, got {trials}.")
    if conversions < 0 or conversions > trials:
        raise ValueError(
            f"Conversions ({conversions}) must satisfy 0 <= conversions <= trials ({trials})."
        )
    if not (0 < confidence < 1):
        raise ValueError(f"Confidence level must be strictly between 0 and 1, got {confidence}.")

    p = conversions / trials
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    denom = 1 + z**2 / trials
    centre_adj = p + z**2 / (2 * trials)
    margin = z * np.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2))
    lower = max(0.0, (centre_adj - margin) / denom)
    upper = min(1.0, (centre_adj + margin) / denom)
    return round(p, 4), round(lower, 4), round(upper, 4)


def two_prop_z_test(
    conv_a: int,
    n_a: int,
    conv_b: int,
    n_b: int,
    alpha: float = 0.05,
    confidence: float = 0.95
) -> Dict[str, Any]:
    """
    Two-proportion two-tailed z-test with Newcombe hybrid score confidence interval
    for the treatment-control difference (p_b - p_a).

    Parameters
    ----------
    conv_a : int
        Conversions in control group. Must satisfy 0 <= conv_a <= n_a.
    n_a : int
        Sample size of control group. Must be > 0.
    conv_b : int
        Conversions in treatment group. Must satisfy 0 <= conv_b <= n_b.
    n_b : int
        Sample size of treatment group. Must be > 0.
    alpha : float
        Significance level (default 0.05). Must be in (0, 1).
    confidence : float
        Confidence level for difference interval (default 0.95). Must be in (0, 1).

    Returns
    -------
    Dict containing:
        - cvr_a: Control conversion rate
        - cvr_b: Treatment conversion rate
        - diff: Absolute difference (p_b - p_a)
        - diff_ci_lower: Lower bound of difference CI (Newcombe hybrid score)
        - diff_ci_upper: Upper bound of difference CI (Newcombe hybrid score)
        - z_stat: Test statistic
        - p_value: Two-tailed p-value
        - significant: Boolean (p_value < alpha)
        - lift_pct: Relative lift % ((p_b - p_a) / p_a * 100), or None if p_a == 0

    Raises
    ------
    ValueError
        If sample sizes <= 0, conversions invalid, or alpha/confidence not in (0, 1).
    """
    if n_a <= 0 or n_b <= 0:
        raise ValueError(f"Sample sizes must be positive, got n_a={n_a}, n_b={n_b}.")
    if conv_a < 0 or conv_a > n_a:
        raise ValueError(f"conv_a ({conv_a}) must satisfy 0 <= conv_a <= n_a ({n_a}).")
    if conv_b < 0 or conv_b > n_b:
        raise ValueError(f"conv_b ({conv_b}) must satisfy 0 <= conv_b <= n_b ({n_b}).")
    if not (0 < alpha < 1):
        raise ValueError(f"alpha must be strictly between 0 and 1, got {alpha}.")
    if not (0 < confidence < 1):
        raise ValueError(f"confidence must be strictly between 0 and 1, got {confidence}.")

    p_a = conv_a / n_a
    p_b = conv_b / n_b
    diff = p_b - p_a

    # Pooled variance for hypothesis test
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))

    if se == 0:
        z = 0.0
        p_value = 1.0
    else:
        z = diff / se
        p_value = float(2 * stats.norm.sf(abs(z)))

    # Relative lift %: undefined (None) if control baseline is zero
    lift = round(100.0 * diff / p_a, 2) if p_a > 0 else None

    # Newcombe Hybrid Score Interval for (p_b - p_a)
    _, l_a, u_a = conversion_rate_ci(conv_a, n_a, confidence)
    _, l_b, u_b = conversion_rate_ci(conv_b, n_b, confidence)

    diff_ci_lower = max(-1.0, diff - np.sqrt((p_b - l_b)**2 + (u_a - p_a)**2))
    diff_ci_upper = min(1.0, diff + np.sqrt((u_b - p_b)**2 + (p_a - l_a)**2))

    return {
        'cvr_a': round(p_a, 4),
        'cvr_b': round(p_b, 4),
        'diff': round(diff, 4),
        'diff_ci_lower': round(float(diff_ci_lower), 4),
        'diff_ci_upper': round(float(diff_ci_upper), 4),
        'z_stat': round(float(z), 3),
        'p_value': round(p_value, 5),
        'significant': bool(p_value < alpha),
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
    baseline_cvr : float
        Control conversion rate (e.g. 0.02 for 2%). Must be in (0, 1).
    min_detectable_effect : float
        Relative lift to detect (e.g. 0.10 for 10% lift). Must be > 0.
    alpha : float
        Significance level (default 0.05). Must be in (0, 1).
    power : float
        Statistical power (default 0.80). Must be in (0, 1).

    Returns
    -------
    int
        Required sample size per variant.

    Raises
    ------
    ValueError
        If any input parameters are out of their valid mathematical domains.
    """
    if not (0 < baseline_cvr < 1):
        raise ValueError(f"baseline_cvr must be in (0, 1), got {baseline_cvr}.")
    if min_detectable_effect <= 0:
        raise ValueError(f"min_detectable_effect must be > 0, got {min_detectable_effect}.")
    if not (0 < alpha < 1):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}.")
    if not (0 < power < 1):
        raise ValueError(f"power must be in (0, 1), got {power}.")

    p1 = baseline_cvr
    p2 = p1 * (1 + min_detectable_effect)
    if p2 >= 1.0:
        raise ValueError(
            f"Treatment conversion rate p2 = {p2:.4f} exceeds 1.0. Lower min_detectable_effect."
        )

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    p_bar = (p1 + p2) / 2
    n = ((z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) +
          z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (p2 - p1)**2
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
    if len(data) == 0:
        raise ValueError("Data array cannot be empty.")
    if not (0 < confidence < 1):
        raise ValueError("confidence must be in (0, 1).")

    rng = np.random.default_rng(random_state)
    boot_stats = [statistic(rng.choice(data, size=len(data), replace=True))
                  for _ in range(n_bootstrap)]
    alpha = (1 - confidence) / 2
    lower = np.quantile(boot_stats, alpha)
    upper = np.quantile(boot_stats, 1 - alpha)
    return round(float(statistic(data)), 4), round(float(lower), 4), round(float(upper), 4)


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
