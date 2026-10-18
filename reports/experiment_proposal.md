# Experiment Proposal: Mobile Checkout UX Improvement
## Product Growth Intelligence Platform — Causal Investigation

**Author:** Dev Chahar | B.Tech CSE | Manipal University Jaipur  
**Status:** Proposal (not yet run)  
**Priority:** P0

> [!IMPORTANT]
> This proposal demonstrates knowledge of A/B testing methodology.
> The historical GA4 dataset **cannot** establish causal effects.
> This experiment must be run on live traffic to generate causal evidence.

---

## 1. Problem Statement

**Observed (from historical data):** Mobile users account for ~60% of sessions but show a materially lower purchase conversion rate than desktop users.

**Hypothesis:** The mobile checkout flow introduces friction (too many steps, small tap targets, limited payment options) that causes users to abandon. Simplifying the checkout experience on mobile will increase purchase conversion rate.

**Causal claim (to be tested):** A streamlined mobile checkout → higher CVR on mobile.

---

## 2. Proposed Change (Treatment)

**Control (A):** Existing multi-step checkout flow on mobile.

**Treatment (B):** Simplified one-page checkout on mobile with:
- Guest checkout prominently featured (no forced account creation)
- Google Pay / Apple Pay as primary payment options
- Progress indicator reduced to 2 steps (address + payment)
- Auto-fill enabled for saved addresses
- Larger tap targets (min 44×44 px per Material Design guidelines)

---

## 3. Experiment Design

| Parameter | Value |
|---|---|
| Unit of randomisation | `user_pseudo_id` (session-level proxy) |
| Allocation | 50% Control / 50% Treatment |
| Traffic filter | Mobile device sessions only |
| Target market | All geographies (global) |
| Assignment method | Server-side feature flag (e.g., Firebase Remote Config) |
| Experiment duration | Minimum 14 days (2 full business cycles) |
| Minimum sample | See Section 4 |

### 3.1 Randomisation Note
Because `user_pseudo_id` is a proxy (not a true persistent user ID), there is a risk of the same physical user appearing in both groups across sessions. This introduces contamination. **Mitigate** by using a deterministic hash of `user_pseudo_id` for group assignment, ensuring consistent assignment within the experiment window.

---

## 4. Sample Size Calculation

**Inputs:**
- Baseline mobile CVR (from verified data): **0.81%** ($95\%\text{ CI: }[0.78\%, 0.84\%]$, $K = 2,340, N = 289,000$)
- Significance level: $\alpha = 0.05$ (two-tailed)
- Statistical power: $1 - \beta = 0.80$
- Minimum detectable effect (MDE):
  - Target 1 (Aggressive MDE = 20% relative lift; $0.81\% \to 0.97\%$): **48,342 sessions per variant**
  - Target 2 (Conservative MDE = 10% relative lift; $0.81\% \to 0.89\%$): **201,758 sessions per variant**

**Formula & Calculation:**

```python
from python.scripts.stats_helpers import sample_size_for_proportion

# Target 1: 20% relative lift
n_20 = sample_size_for_proportion(baseline_cvr=0.0081, min_detectable_effect=0.20, alpha=0.05, power=0.80)
print(f'Required (MDE 20%): {n_20:,} sessions per variant ({n_20*2:,} total)')
# Output: 48,342 sessions per variant (96,684 total)

# Target 2: 10% relative lift
n_10 = sample_size_for_proportion(baseline_cvr=0.0081, min_detectable_effect=0.10, alpha=0.05, power=0.80)
print(f'Required (MDE 10%): {n_10:,} sessions per variant ({n_10*2:,} total)')
# Output: 201,758 sessions per variant (403,516 total)
```

**Estimated Runtime:**
At the store's average mobile volume of $\approx 3,141$ sessions/day ($289,000 / 92$ days):
- **For MDE = 20%:** $\frac{96,684}{3,141} \approx 31$ days runtime.
- **For MDE = 10%:** $\frac{403,516}{3,141} \approx 128$ days runtime.
- **Recommendation:** Power the initial test for **MDE = 20%** with a scheduled runtime of 31–35 days to cover 4 full weekly business cycles.

---

## 5. Metrics

### 5.1 Primary Metric
| Metric | Definition | Direction |
|---|---|---|
| Mobile Session CVR | `converting_sessions / session_starts` on mobile | Increase |

### 5.2 Secondary Metrics
| Metric | Definition | Direction |
|---|---|---|
| Mobile Add-to-Cart Rate | `add_to_cart / session_starts` on mobile | Neutral or Increase |
| Checkout Completion Rate | `purchase / begin_checkout` on mobile | Increase |
| Average Order Value (mobile) | `revenue / purchases` on mobile | Non-inferior (≥ −5%) |

### 5.3 Guardrail Metrics (Must Not Degrade)
| Metric | Threshold |
|---|---|
| Overall site revenue | Must not decline >5% |
| Desktop CVR | Must not be affected (spillover check) |
| Page load time (mobile) | Must not increase >200ms (Core Web Vitals) |
| Return rate / refund rate | Must not increase |

---

## 6. Analysis Plan

1. **Pre-experiment SRM check:** Verify that group sizes are within 1% of expected 50/50 split. Sample Ratio Mismatch indicates randomisation error.
2. **Primary analysis:** Two-proportion z-test on CVR at experiment end.
3. **Sequential testing:** Use alpha spending (e.g., O'Brien-Fleming) if peeking during the experiment.
4. **Segment analysis:** Break results by country, OS, browser — check for heterogeneous treatment effects.
5. **Long-term effects:** Re-examine Day 7 vs Day 14 CVR to check for novelty effects.

```python
from python.scripts.stats_helpers import two_prop_z_test, conversion_rate_ci

# Example post-experiment analysis
result = two_prop_z_test(
    conv_a=control_purchases,  n_a=control_sessions,
    conv_b=treat_purchases,    n_b=treat_sessions
)
print(result)
# {'cvr_a': 0.020, 'cvr_b': 0.023, 'z_stat': 2.45,
#  'p_value': 0.014, 'significant': True, 'lift_pct': 15.0}
```

---

## 7. Decision Framework

| Outcome | Action |
|---|---|
| p < 0.05 AND primary metric ↑ AND all guardrails pass | Ship to 100% of mobile traffic |
| p < 0.05 AND primary metric ↑ BUT guardrail failed | Investigate and iterate before shipping |
| p ≥ 0.05 | Do not ship; explore alternative interventions |
| p < 0.05 AND primary metric ↓ | Kill treatment immediately |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Novelty effect (users excited by new UI) | Run for minimum 2 weeks; analyse by day |
| Cross-device contamination | Log device at session start; analyse mobile-only sessions |
| Holiday/seasonal confounding | Avoid running over major sale events |
| Revenue obfuscation in test data | Use live production revenue, not the sample dataset |

---

## 9. What This Experiment Does NOT Prove

- It does not tell you **why** mobile CVR is lower (that requires usability research)
- A positive result for this specific treatment cannot be generalised to all checkout changes
- A negative result does not mean mobile UX is fine — the specific changes tested may simply be wrong

---

*Experiment Proposal — Product Growth Intelligence Platform*  
*Dev Chahar | Manipal University Jaipur*
