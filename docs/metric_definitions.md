# Metric Definitions
## Product Growth Intelligence Platform

**Author:** Dev Chahar | Manipal University Jaipur | Reg: 23FE10CSE00291

This document is the canonical reference for every KPI used in SQL queries, Python notebooks, and the Power BI dashboard. Any change to a definition here must be reflected in all consuming artefacts.

---

## 1. Session Metrics

| Metric | Definition | SQL Implementation | Notes |
|---|---|---|---|
| **Session** | One continuous visit, identified by `ga_session_id` within a `user_pseudo_id` | `CONCAT(user_pseudo_id, '_', ga_session_id)` | Different devices = different sessions |
| **Session Start** | User fires the `session_start` event | `event_name = 'session_start'` | One per session |
| **Session Duration** | Time between first and last event in session (seconds) | `(MAX(ts) - MIN(ts)) / 1e6` | 0 for bounce sessions |
| **Bounce Session** | Session with only 1 event or 0 seconds duration | `session_duration_sec = 0` | Proxy; GA4 has no native bounce |

---

## 2. Funnel Metrics

| Metric | Definition | Denominator | Event Name |
|---|---|---|---|
| **Product View Rate** | % of sessions with at least 1 product view | Session starts | `view_item` |
| **Add-to-Cart Rate** | % of sessions with at least 1 add-to-cart | Session starts | `add_to_cart` |
| **Checkout Initiation Rate** | % of sessions with begin_checkout | Session starts | `begin_checkout` |
| **Purchase Conversion Rate (CVR)** | % of sessions resulting in a purchase | Session starts | `purchase` |
| **Cart Abandonment Rate** | % of add-to-cart sessions without purchase | Sessions with add_to_cart | Binary flag |
| **Checkout Abandonment Rate** | % of begin_checkout sessions without purchase | Sessions with begin_checkout | Binary flag |
| **View-to-Cart Rate** | % of product view sessions that add to cart | Sessions with view_item | — |

---

## 3. Revenue Metrics

| Metric | Definition | Field | Caveat |
|---|---|---|---|
| **Total Revenue** | Sum of `purchase_revenue` across all purchase events | `ecommerce.purchase_revenue` | Obfuscated in sample |
| **Average Order Value (AOV)** | Revenue / number of purchase events | `SUM(revenue) / COUNT(purchases)` | Obfuscated |
| **Revenue per User** | Total revenue / unique users | Divide by `COUNT(DISTINCT user_pseudo_id)` | Approximate |
| **Item Revenue** | `price × quantity` at item level | `item.price * item.quantity` | Use when `purchase_revenue` is NULL |

---

## 4. User Metrics

| Metric | Definition | Notes |
|---|---|---|
| **Unique Users** | `COUNT(DISTINCT user_pseudo_id)` | Proxy ID; not true unique persons |
| **New User** | User with only 1 observed session in dataset | Cannot reliably distinguish from returning users across devices |
| **Buyer** | User with at least 1 purchase event | `MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) = 1` |
| **User Lifespan** | Days between first and last event | `DATE_DIFF(last_seen, first_seen, DAY)` |

---

## 5. Channel Metrics

| Metric | Definition | Source Field |
|---|---|---|
| **Medium** | Traffic medium (organic, cpc, referral, email, none) | `traffic_source.medium` |
| **Source** | Traffic source (google, bing, newsletter, etc.) | `traffic_source.source` |
| **Campaign** | UTM campaign name | `traffic_source.name` |
| **First Touch Attribution** | Credit given to the first observed medium for a user | `ARRAY_AGG(...ORDER BY event_timestamp LIMIT 1)` |

---

## 6. RFM Definitions

| Dimension | Definition | Calculation |
|---|---|---|
| **Recency** | Days since last event (relative to 2021-02-01) | `DATE_DIFF(DATE '2021-02-01', MAX(event_date), DAY)` |
| **Frequency** | Number of distinct sessions | `COUNT(DISTINCT ga_session_id)` |
| **Monetary** | Sum of purchase_revenue (indicative) | `SUM(purchase_revenue)` |
| **RFM Score** | Quintile-based (1–5 per dimension), summed | `NTILE(5)` per dimension |

---

## 7. Statistical Definitions

| Term | Definition |
|---|---|
| **Wilson Score CI** | 95% confidence interval for a proportion that stays within [0,1]. Preferred over normal approximation for small samples. |
| **MDE (Minimum Detectable Effect)** | The smallest relative lift in CVR that the experiment is powered to detect. Default: 10% relative. |
| **Statistical Power** | Probability of detecting a true effect of size MDE. Default: 80%. |
| **Significance Level (α)** | Probability of falsely rejecting H₀. Default: 0.05 (two-tailed). |
| **Sample Ratio Mismatch (SRM)** | Significant deviation from expected group split ratio — indicates a broken randomisation mechanism. |

---

*Metric Definitions — Product Growth Intelligence Platform*  
*Dev Chahar | Manipal University Jaipur*
