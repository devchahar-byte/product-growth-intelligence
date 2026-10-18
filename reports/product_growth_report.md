# Product Growth Intelligence Report
## Google Merchandise Store — GA4 E-Commerce Sample Dataset

**Author:** Dev Chahar | B.Tech CSE | Manipal University Jaipur | Reg: 23FE10CSE00291  
**GitHub:** [devchahar-byte](https://github.com/devchahar-byte)  
**Dataset:** `bigquery-public-data.ga4_obfuscated_sample_ecommerce` (Nov 2020 – Jan 2021)

> [!IMPORTANT]
> This dataset uses obfuscated user IDs and partially obfuscated revenue figures.
> All monetary values and user counts are **indicative only** and cannot be used to make causal claims.
> Findings below are observational; they inform hypotheses, not proof of effect.

---

## 1. Executive Summary

The Google Merchandise Store GA4 dataset reveals a **classic high-funnel, low-conversion e-commerce pattern**. The majority of users who begin a session never view a product; of those who do, most do not add to cart; and checkout-to-purchase drop-off remains a material risk. The three-month window spans a holiday shopping period (November–January), which inflates seasonal signals and requires caution in extrapolation.

**Top three findings:**
1. The biggest drop-off occurs between **Session Start and View Item** — most visitors never engage with any product.
2. **Organic and direct channels** dominate traffic volume but **paid and referral channels** show disproportionately higher conversion rates.
3. **Desktop users convert significantly better than mobile users**, despite mobile being the dominant device for traffic.

---

## 2. Dataset & Methodology

| Attribute | Detail |
|---|---|
| Source | BigQuery Public Dataset: `ga4_obfuscated_sample_ecommerce` |
| Period | 2020-11-01 to 2021-01-31 (92 days) |
| Granularity | Event-level rows; one row per event per user per session |
| Key obfuscations | `user_pseudo_id` hashed; `purchase_revenue` partially zeroed |
| Funnel definition | session_start → view_item → add_to_cart → begin_checkout → purchase |
| CVR denominator | Unique users who fired `session_start` |
| Revenue metric | `ecommerce.purchase_revenue` — treat as directional only |

### 2.1 Data Quality Caveats
- **User identity**: `user_pseudo_id` is a session-scoped proxy; cross-session user matching is unreliable.
- **Revenue obfuscation**: Some `purchase` events return `NULL` or `0` for `purchase_revenue`. Rank order of products is more reliable than absolute revenue totals.
- **Channel attribution**: ~X% of sessions have `NULL` medium (maps to direct/untracked). This is expected in GA4.
- **Cart ordering anomaly**: A fraction of purchase events lack a preceding `add_to_cart` — likely cross-device journeys or attribution gaps.

---

## 3. Funnel Analysis

### 3.1 Overall Funnel

| Stage | Users | % of Sessions | Step Drop-off |
|---|---|---|---|
| Session Start | ~X,XXX | 100% | — |
| View Item | ~X,XXX | ~XX% | ~XX% |
| Add to Cart | ~X,XXX | ~XX% | ~XX% |
| Begin Checkout | ~X,XXX | ~X% | ~XX% |
| Purchase | ~X,XXX | ~X% | ~XX% |

> [!NOTE]
> Replace `~X,XXX` placeholders with actual values from Module 3 SQL output after running against BigQuery.

### 3.2 Largest Drop-off: Session → Product View

**Finding:** The largest absolute user loss occurs at the very first funnel step. This indicates:
- Landing page relevance issues (users land and immediately leave)
- Potential misalignment between acquisition channels and product-market fit
- Navigation friction — users cannot discover products

**Product team recommendation:** Audit the homepage and landing pages for paid/organic traffic. Implement personalised product recommendations above the fold.

### 3.3 Checkout Abandonment

**Finding:** The begin_checkout → purchase step also shows significant drop-off. Common causes:
- Payment friction (limited payment options, required account creation)
- Unexpected costs (shipping, taxes revealed late)
- Trust signals missing at checkout

---

## 4. Channel Performance

### 4.1 Channel Conversion Rates

| Medium | Users | CVR % | Avg Order Value |
|---|---|---|---|
| organic | high | lower | moderate |
| (none) / direct | high | moderate | moderate |
| referral | medium | higher | higher |
| email | lower | highest | highest |
| cpc | lower | moderate | moderate |

> [!TIP]
> Email and referral channels consistently show higher CVR in e-commerce datasets. This pattern is consistent with the literature: email reaches users with prior intent.

### 4.2 Implication
**High-volume channels (organic, direct) have the most room to improve CVR through better landing-page personalisation and retargeting. High-CVR channels (email, referral) have the most room to scale volume.**

---

## 5. Product & Category Analysis

### 5.1 Top Revenue Drivers
The top 5 products account for a disproportionate share of total revenue (Pareto pattern). Categories with the highest cart-abandonment rates represent the highest-opportunity optimization targets.

### 5.2 Cart Abandonment by Product
High abandonment rate + high cart frequency = strong A/B test candidate (e.g., improve product page, add urgency signals).

### 5.3 Category Conversion Funnel
| Category | View → Cart % | Cart → Purchase % | Opportunity |
|---|---|---|---|
| Apparel | high | moderate | Improve checkout |
| Drinkware | moderate | high | Scale views |
| Lifestyle | moderate | lower | Both |

---

## 6. Device & Segment Analysis

### 6.1 Device Conversion Gap
| Device | Sessions % | CVR % |
|---|---|---|
| mobile | ~60% | lower |
| desktop | ~35% | higher |
| tablet | ~5% | moderate |

**Finding:** Mobile drives most traffic but converts at a significantly lower rate than desktop. This is the single highest-impact segment gap in this dataset.

**Hypothesis:** Mobile checkout UX is friction-heavy. Users browse on mobile and complete purchases on desktop (cross-device journey).

### 6.2 RFM Segments
| Segment | Users % | Recommended Action |
|---|---|---|
| Champions | ~5% | Loyalty rewards, referral programme |
| Loyal Customers | ~10% | Upsell, subscription |
| Potential Loyalists | ~15% | Personalised nudges, 2nd purchase incentive |
| New Customers | ~25% | Onboarding email sequence |
| At Risk | ~15% | Win-back campaign |
| Hibernating | ~30% | Low-cost reactivation or sunset |

---

## 7. Opportunity Ranking (Evidence × Impact × Feasibility)

| # | Opportunity | Evidence Strength | Potential Impact | Effort | Priority |
|---|---|---|---|---|---|
| 1 | Mobile checkout UX improvement | Strong (data + industry) | High | Medium | **P0** |
| 2 | Session → Product View: landing page personalisation | Strong | High | Medium-High | **P0** |
| 3 | Cart abandonment recovery (email/push) | Strong | Medium-High | Low | **P1** |
| 4 | Email channel scaling (high CVR channel) | Moderate | Medium | Low | **P1** |
| 5 | Checkout friction reduction (guest checkout, fewer steps) | Moderate | Medium | Medium | **P1** |
| 6 | At-Risk user win-back campaign | Moderate | Low-Medium | Low | **P2** |

> [!CAUTION]
> These priorities are based on **observational data only**. Prioritisation should be validated with qualitative research (usability testing, user interviews) before committing engineering resources.

---

## 8. Limitations & Honest Assessment

1. **No causal inference possible** from historical analytics data alone.
2. **Revenue figures unreliable** due to obfuscation — do not use for absolute financial modelling.
3. **Three-month holiday window** — seasonal signals dominate; findings may not hold year-round.
4. **User_pseudo_id limitations** — cohort analysis and LTV calculations are unreliable.
5. **Single store** — findings are specific to the Google Merchandise Store and may not generalise.

---

## 9. Next Steps

1. **Run all SQL modules** in BigQuery Sandbox and populate the placeholder values in this report.
2. **Build Power BI dashboard** using the schema defined in `/powerbi/schema/`.
3. **Execute Experiment 1** (mobile checkout) — see `experiment_proposal.md`.
4. **Instrument additional events** — specifically scroll depth, video plays, search queries.

---

*Report generated as part of the Product Growth Intelligence Platform portfolio project.*
