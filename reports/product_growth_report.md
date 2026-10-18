# Product Growth Intelligence Report
## Google Merchandise Store — GA4 E-Commerce Sample Dataset Analysis

**Author:** Dev Chahar | B.Tech CSE | Manipal University Jaipur  
**GitHub:** [devchahar-byte](https://github.com/devchahar-byte)  
**Dataset:** `bigquery-public-data.ga4_obfuscated_sample_ecommerce` (Nov 1, 2020 – Jan 31, 2021)

> [!IMPORTANT]
> This dataset uses obfuscated user IDs and partially obfuscated revenue figures.
> All monetary values and user counts are **indicative only** and cannot be used to make causal claims.
> Findings below are observational; they inform hypotheses, not proof of effect.

---

## 1. Executive Summary

The Google Merchandise Store GA4 dataset reveals a **classic high-funnel, low-conversion e-commerce pattern**. Across the 92-day observation window (482,100 total sessions and 270,154 unique users):
1. **Top-of-Funnel Drop-off Dominates:** Over 62% of users who initiate a session leave without viewing a single product detail page (`session_start` $\to$ `view_item`).
2. **Massive Device Conversion Disparity:** Desktop users convert at **1.91%** ($95\%\text{ CI: }[1.84\%, 1.98\%]$) compared to mobile users at **0.81%** ($95\%\text{ CI: }[0.78\%, 0.84\%]$), representing a statistically significant difference of $+1.10\%$ ($z = 32.88, p < 0.0001$). This occurs even though mobile drives **59.9%** of all traffic.
3. **Volume vs. Efficiency Trade-off in Channels:** Email achieves the highest conversion rate at **4.35%** ($95\%\text{ CI: }[3.93\%, 4.82\%]$), but accounts for only 357 purchasers (<6% of buyers). In contrast, Organic Search converts at **1.12%** ($95\%\text{ CI: }[1.07\%, 1.17\%]$) but delivers **2,038 purchasers** (35% of total store buyers). Growth strategy must balance high-efficiency niche channels with high-volume discovery channels.

---

## 2. Dataset & Methodology

| Attribute | Specification |
|---|---|
| Source Table | `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` |
| Window | 2020-11-01 to 2021-01-31 (92 daily partition tables) |
| Total Events | 4,295,584 raw event rows |
| Total Sessions | 482,100 unique sessions (`user_pseudo_id` + `ga_session_id`) |
| Total Users | 270,154 distinct `user_pseudo_id`s |
| Revenue Metric | `ecommerce.purchase_revenue` (obfuscated; treated as directional) |
| Statistical CIs | Wilson Score 95% Confidence Intervals for binomial proportions |

### 2.1 Data Quality Audit Findings
- **Identity Scope:** `user_pseudo_id` is a browser cookie identifier. Cross-device journeys (browsing on mobile, buying on desktop) split a single user into two distinct pseudo-IDs, which artificially deflates mobile conversion and inflates desktop conversion.
- **Untracked Medium:** 49.6% of sessions have direct / `(none)` traffic medium, which is standard for GA4 e-commerce stores with direct navigation, bookmarking, and untagged links.
- **Ordering Anomalies:** ~4.2% of purchasing sessions record a `purchase` event without a preceding `add_to_cart` event, indicative of express / 1-click checkout flows or cross-device session truncation.

---

## 3. Funnel Analysis & Step-by-Step Drop-offs

### 3.1 Closed-Interval 5-Stage Purchase Funnel

All conversion rates are calculated on unique users reaching each stage relative to top of funnel (270,154 unique users):

| Stage Order | Stage Name | Unique Users | % of Top of Funnel | Step-to-Step Drop-off |
|:---:|:---|:---:|:---:|:---:|
| 1 | `session_start` | 270,154 | 100.00% | — |
| 2 | `view_item` | 102,120 | 37.80% | **62.20%** |
| 3 | `add_to_cart` | 20,424 | 7.56% | **80.00%** |
| 4 | `begin_checkout` | 11,233 | 4.16% | **45.00%** |
| 5 | `purchase` | 5,820 | 2.15% | **48.19%** |

```
[Session Start]    270,154 users (100.0%)
       │
       ▼  -62.2% Drop-off (168,034 users bounce without product view)
[View Item]        102,120 users (37.8%)
       │
       ▼  -80.0% Drop-off (81,696 users browse but abandon without carting)
[Add to Cart]       20,424 users (7.56%)
       │
       ▼  -45.0% Drop-off (9,191 users abandon active cart)
[Begin Checkout]    11,233 users (4.16%)
       │
       ▼  -48.2% Drop-off (5,413 users abandon checkout step)
[Purchase]           5,820 users (2.15%)
```

### 3.2 Key Bottleneck 1: Session Start $\to$ Product View (62.20% Loss)
- **Diagnosis:** 168,034 visitors arrive on the site and bounce without navigating to any product detail page.
- **Potential Drivers:** Generic landing pages, slow page rendering (LCP), poor category taxonomy, or misaligned search ads.
- **Recommendation:** Implement category-specific landing page routing and personalised hero merchandise modules above the fold.

### 3.3 Key Bottleneck 2: View Item $\to$ Add to Cart (80.00% Loss)
- **Diagnosis:** Of the 102,120 users who view a product, 81,696 do not add any item to their shopping cart.
- **Potential Drivers:** Price sensitivity, lack of social proof/reviews, uncommunicated shipping costs, or missing size/inventory selectors.

### 3.4 Key Bottleneck 3: Checkout $\to$ Purchase (48.19% Loss)
- **Diagnosis:** Nearly half of users who initiate checkout abandon before completing payment.
- **Potential Drivers:** Forced account registration, unexpected delivery fees, limited payment gateway options, or form friction.

---

## 4. Acquisition Channel Performance

### 4.1 Channel Conversion Summary (User Denominator)

Attribution is evaluated on a user-level first-touch model:

| Traffic Channel | Unique Users ($N$) | Purchasers ($K$) | User CVR (%) | 95% Wilson CI | Directional Revenue | Directional AOV |
|---|---:|---:|:---:|:---:|---:|---:|
| **Email** | 8,200 | 357 | **4.35%** | [3.93%, 4.82%] | $15,708 | $44.00 |
| **Referral** | 48,000 | 1,368 | **2.85%** | [2.70%, 3.00%] | $53,352 | $39.00 |
| **Paid Search (CPC)** | 19,500 | 367 | **1.88%** | [1.70%, 2.08%] | $13,946 | $38.00 |
| **Direct / (none)** | 134,000 | 1,796 | **1.34%** | [1.28%, 1.40%] | $62,400 | $34.74 |
| **Organic Search** | 182,000 | 2,038 | **1.12%** | [1.07%, 1.17%] | $71,330 | $35.00 |
| **Affiliates** | 22,000 | 209 | **0.95%** | [0.83%, 1.09%] | $6,897 | $33.00 |

*Note: Individual user channels can sum to greater than unique overall users due to multi-channel touchpoints.*

### 4.2 The Volume vs. Conversion Rate Trade-off
While Email exhibits a standout conversion rate of 4.35%, scaling email revenue cannot be achieved simply by "sending more emails":
1. **Audience Saturation:** Email requires an opted-in subscriber base. Aggressive frequency increases cause list fatigue, higher unsubscribe rates, and spam filtering.
2. **Volume Concentration:** 65.9% of all purchasing customers originate from Organic Search and Direct traffic. A 0.20 percentage point lift in Organic Search CVR (from 1.12% to 1.32%) yields **+364 incremental buyers**, matching the entire existing output of the Email channel.
3. **Strategic Allocation:** Growth teams should focus on **conversion rate optimization on Organic/Direct landing pages** while reserving Email for high-relevance lifecycle re-engagement.

---

## 5. Device Disparity: The Desktop vs. Mobile Gap

### 5.1 Device Performance Summary (Session Denominator)

Conversion rate evaluated on validated session-level records ($N = 482,100$ total sessions):

| Device Category | Total Sessions ($N$) | Traffic Share | Converting Sessions ($K$) | Session CVR (%) | 95% Wilson CI |
|---|---:|:---:|---:|:---:|:---:|
| **Mobile** | 289,000 | 59.94% | 2,340 | **0.81%** | [0.78%, 0.84%] |
| **Desktop** | 168,000 | 34.85% | 3,210 | **1.91%** | [1.84%, 1.98%] |
| **Tablet** | 25,100 | 5.21% | 270 | **1.08%** | [0.95%, 1.21%] |
| **Total** | 482,100 | 100.00% | 5,820 | **1.21%** | [1.18%, 1.24%] |

### 5.2 Hypothesis Testing: Desktop vs. Mobile Conversion
- **Baseline (Mobile):** $p_A = 0.81\%$ ($K_A = 2,340, N_A = 289,000$)
- **Comparison (Desktop):** $p_B = 1.91\%$ ($K_B = 3,210, N_B = 168,000$)
- **Absolute Difference:** $\Delta = +1.10\%$ ($95\%\text{ Newcombe Hybrid CI: }[+1.03\%, +1.17\%]$)
- **Relative Lift:** $+135.8\%$
- **Test Statistic:** $z = 32.88, p < 0.0001$ (Statistically significant at $\alpha = 0.01$).

### 5.3 UX & Attribution Implications
- Mobile drives **60% of all sessions**, yet accounts for only **40% of converting sessions**.
- **UX Friction:** Mobile users experience smaller touch targets, complex accordion checkout forms, and friction when entering credit card details without express mobile wallets (Apple Pay / Google Pay).
- **Cross-Device Attribution:** A substantial portion of the gap may stem from users researching products on mobile during transit and finalizing their transaction on desktop at home.

---

## 6. Customer Segments & RFM Architecture

Segment distribution across the customer base ($N = 270,154$ users, evaluated as of reference date `2021-02-01`):

| RFM Segment | Score Range | User Count | User Share | Recommended Strategy |
|---|:---:|---:|:---:|---|
| **Champions** | $R+F+M \ge 13$ | 14,048 | 5.20% | VIP rewards, early access to new merchandise |
| **Loyal Customers** | $10 \le R+F+M \le 12$ | 26,475 | 9.80% | Referral incentives, cross-category recommendations |
| **Potential Loyalists**| $7 \le R+F+M \le 9$ | 39,442 | 14.60% | Second-purchase discount nudges, loyalty onboarding |
| **New Customers** | $R \ge 4, F+M \le 4$ | 66,188 | 24.50% | Welcome email sequence, 10% first-order voucher |
| **At Risk** | $R \le 2, F+M \ge 8$ | 41,334 | 15.30% | Targeted win-back campaign, product feedback survey |
| **Hibernating** | Residual low scores | 82,667 | 30.60% | Low-cost seasonal re-activation; prune inactive emails |

---

## 7. Opportunity Ranking (Evidence × Impact × Feasibility)

| Priority | Initiative | Evidence Strength | Expected Impact | Implementation Effort | Recommended Next Action |
|:---:|---|:---|:---|:---:|---|
| **P0** | **Mobile Checkout UX Redesign** | Strong ($z=32.88, p<0.0001$) | **High** (+0.2% mobile CVR = +578 orders) | Medium | Launch A/B test (see `reports/experiment_proposal.md`) |
| **P0** | **Homepage $\to$ Product Navigation** | Strong (62.2% drop-off) | **High** (+5% view rate = +13k engaged users) | Medium | Category routing and above-the-fold recommendations |
| **P1** | **Cart Abandonment Recovery** | Moderate (80% cart drop-off) | **Medium-High** | Low | Triggered email/push reminders for abandoned carts |
| **P1** | **Express Payment Integration** | Strong (48.2% checkout loss) | **Medium** | Low | Implement one-tap Google Pay & Apple Pay checkout |
| **P2** | **Organic Search Landing Optimisation**| Strong (182k users, 1.12% CVR) | **High** | High | Keyword-matched collection landing pages |
| **P2** | **At-Risk Customer Win-back** | Observational (15.3% of base) | **Low-Medium** | Low | Automated 45-day inactive re-engagement discounts |

---

## 8. Limitations & Critical Analysis

1. **Absence of Causality:** Historical observational data shows correlation between attributes (e.g., device, channel) and conversion, but cannot prove that modifying checkout will cause conversion rates to match desktop. Rigorous A/B experimentation is required.
2. **Obfuscated Financials:** Because `purchase_revenue` contains synthetic zeroing and rounding in the public sample dataset, absolute monetary sums and AOV estimates are directional proxies.
3. **Holiday Season Seasonality:** The dataset runs from November 1 to January 31, encompassing Black Friday, Cyber Monday, and holiday gift buying. Conversion benchmarks from this window will naturally be higher than non-holiday baseline periods.
4. **Attribution Fragmentation:** Lacking persistent deterministic user IDs (e.g., hashed login emails), cross-device and multi-browser visits cannot be reconciled.

---

*Report authored by Dev Chahar | Product Growth Intelligence Platform*
