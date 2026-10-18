# Metric Definitions & Audit Framework
## Product Growth Intelligence Platform

**Author:** Dev Chahar | Manipal University Jaipur  
**Repository:** [product-growth-intelligence](https://github.com/devchahar-byte/product-growth-intelligence)  
**Dataset:** `bigquery-public-data.ga4_obfuscated_sample_ecommerce`

This document is the canonical mathematical and operational reference for every metric, dimension, and statistical test used across the SQL layer, Python analyses, Power BI models, and Streamlit dashboards.

---

## 1. Session Model & Identity Resolution

### 1.1 Session Identifier Construction
In GA4 export schemas, there is no single top-level `session_id` column. A session is uniquely identified by combining the pseudo-anonymous client identifier with the session epoch timestamp:

$$\text{session\_id} = \text{CONCAT}(\text{user\_pseudo\_id}, \text{'\_'}, \text{CAST}(\text{ga\_session\_id AS STRING}))$$

where `ga_session_id` is extracted from the unnested `event_params` array where `key = 'ga_session_id'` (`value.int_value`).

### 1.2 Session Boundary & Timeout Logic
- A session starts upon the first recorded event where a new `ga_session_id` is assigned (typically triggering a `session_start` event).
- GA4 defaults to a **30-minute inactivity timeout**. If a user returns after 30 minutes of inactivity, a new `ga_session_id` is generated, beginning a new session.
- `session_start_ts = MIN(event_timestamp)` (in microseconds).
- `session_end_ts = MAX(event_timestamp)` (in microseconds).
- `session_duration_sec = (session_end_ts - session_start_ts) / 1,000,000`.
- Single-event sessions or sessions where all events share the identical microsecond timestamp have `session_duration_sec = 0.0`.

### 1.3 Cross-Session & Cross-Device Effects
- `user_pseudo_id` is tied to a specific browser instance (stored in local cookies/storage).
- If a user browses products on mobile Safari and completes the purchase on Desktop Chrome, GA4 logs **two separate `user_pseudo_id`s**.
- Consequently, mobile appears as a non-converting session/user, while desktop appears as a converting session/user with low prior engagement. This attribution limitation must be accounted for when interpreting device conversion disparities.

---

## 2. Conversion Metrics: Session CVR vs. User CVR

A frequent error in analytics implementations is counting raw `purchase` event rows in the numerator and dividing by sessions or users. If a session logs multiple purchases (e.g., duplicate webhooks or multiple checkout completions), raw event counts produce an invalid metric that exceeds true conversion.

### 2.1 Session-Level Conversion Rate (Session CVR)
Defined as the proportion of eligible visits that result in at least one completed transaction:

$$\text{Session CVR} = \frac{\sum_{i=1}^{S} \mathbb{I}(\text{session}_i \text{ has } \ge 1 \text{ purchase})}{\text{Total Unique Sessions } (S)}$$

In SQL:
```sql
SAFE_DIVIDE(
  COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN session_id END),
  COUNT(DISTINCT session_id)
)
```

### 2.2 User-Level Conversion Rate (User CVR)
Defined as the proportion of unique visitors who make at least one purchase within the observation window:

$$\text{User CVR} = \frac{\sum_{j=1}^{U} \mathbb{I}(\text{user}_j \text{ has } \ge 1 \text{ purchase})}{\text{Total Unique Users } (U)}$$

In SQL:
```sql
SAFE_DIVIDE(
  COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN user_pseudo_id END),
  COUNT(DISTINCT user_pseudo_id)
)
```

### 2.3 Mathematical Impact of Multi-Session Users
Consider a user who visits 5 times and purchases during session 5:
- **User CVR Contribution:** $\frac{1 \text{ purchaser}}{1 \text{ user}} = 100\%$
- **Session CVR Contribution:** $\frac{1 \text{ converting session}}{5 \text{ total sessions}} = 20\%$

When a customer base exhibits high frequency (repeat visits before buying), **User CVR will be significantly higher than Session CVR**. Both metrics are valid, but they answer different questions:
- *Session CVR* measures landing-to-checkout efficiency per visit.
- *User CVR* measures customer acquisition efficiency per person.

---

## 3. Funnel Stage Definitions & Drop-off Mechanics

The e-commerce conversion funnel is evaluated across 5 closed-interval stages:

| Stage Order | Stage Name | Trigger Event | Scope | Operational Definition |
|:---:|:---|:---|:---|:---|
| 1 | `session_start` | `session_start` | Session / User | Visit initiated |
| 2 | `view_item` | `view_item` | Session / User | Product detail page loaded |
| 3 | `add_to_cart` | `add_to_cart` | Session / User | Item added to cart |
| 4 | `begin_checkout` | `begin_checkout` | Session / User | User entered checkout workflow |
| 5 | `purchase` | `purchase` | Session / User | Transaction confirmed |

### 3.1 Funnel Calculations
For any stage $k \in \{1, 2, 3, 4, 5\}$ with volume $N_k$:
- **Percent of Top (Top-of-Funnel Conversion):**
  $$\text{Top \%}_k = \frac{N_k}{N_1} \times 100$$
- **Step-to-Step Drop-off Rate:**
  $$\text{Drop-off \%}_k = \left(1 - \frac{N_k}{N_{k-1}}\right) \times 100 \quad (k \ge 2)$$
- **Step-to-Step Transition Efficiency:**
  $$\text{Step Efficiency \%}_k = \left(\frac{N_k}{N_{k-1}}\right) \times 100 \quad (k \ge 2)$$

---

## 4. User Segmentation & Customer Lifecycle

### 4.1 New vs. Returning Visitors
Within the observation window:
- **New User:** A `user_pseudo_id` associated with exactly 1 distinct `ga_session_id`.
- **Returning User (2–3 sessions):** A `user_pseudo_id` associated with 2 or 3 distinct `ga_session_id`s.
- **Loyal / Frequent User (4+ sessions):** A `user_pseudo_id` associated with 4 or more distinct `ga_session_id`s.

*Limitation:* Because the dataset covers 92 days (Nov 2020 – Jan 2021), historical sessions before Nov 1, 2020 are unobserved. Some "New Users" may be established customers clearing cookies or returning after 90 days.

### 4.2 RFM Segmentation Rules
- **Recency ($R$):** Days elapsed from user's last observed event date to reference date `2021-02-01` (`DATE_DIFF('2021-02-01', MAX(event_date), DAY)`). Ranked into 5 quintiles (5 = lowest days, most recent).
- **Frequency ($F$):** Total count of unique `ga_session_id`s for the user. Ranked into 5 quintiles (5 = highest session count).
- **Monetary ($M$):** Sum of `purchase_revenue`. Ranked into 5 quintiles (5 = highest total spend).
- **RFM Score:** $R + F + M \in [3, 15]$.

| Segment | Score / Condition | Business Meaning |
|---|---|---|
| **Champions** | $R+F+M \ge 13$ | Bought recently, buy often, high total spend |
| **Loyal Customers** | $10 \le R+F+M \le 12$ | Consistent engagement and above-average spend |
| **Potential Loyalists** | $7 \le R+F+M \le 9$ | Recent buyers with average frequency |
| **New Customers** | $R \ge 4$ and $F+M \le 4$ | High recency but low frequency/monetary |
| **At Risk** | $R \le 2$ and $F+M \ge 8$ | Formerly frequent spenders who have not visited recently |
| **Hibernating** | All other combinations | Low recency and low historical activity |

---

## 5. Statistical Inference & Uncertainty Bounds

### 5.1 Wilson Score Confidence Interval for Proportions
For conversion rate $\hat{p} = \frac{K}{N}$ with confidence level $1 - \alpha$ (standard normal quantile $z = \Phi^{-1}(1 - \alpha/2)$):

$$\tilde{p} = \frac{K + \frac{z^2}{2}}{N + z^2}$$

$$\text{Margin} = \frac{z}{N + z^2} \sqrt{\frac{K(N - K)}{N} + \frac{z^2}{4}}$$

$$\text{CI}_{1-\alpha} = \left[\max\left(0, \tilde{p} - \text{Margin}\right), \min\left(1, \tilde{p} + \text{Margin}\right)\right]$$

*Properties:* Valid for small $N$, preserves bounds strictly in $[0, 1]$, and eliminates zero-width intervals when $K \in \{0, N\}$.

### 5.2 Difference in Two Proportions & Hybrid Score Interval
For Treatment ($B$) vs. Control ($A$) difference $\Delta = p_B - p_A$:
- **Relative Lift:**
  $$\text{Lift \%} = \frac{p_B - p_A}{p_A} \times 100 \quad (\text{undefined if } p_A = 0)$$
- **Newcombe Hybrid Score CI for Difference:**
  Using Wilson intervals $[l_A, u_A]$ for group $A$ and $[l_B, u_B]$ for group $B$:
  $$\Delta_{\text{lower}} = (p_B - p_A) - \sqrt{(p_B - l_B)^2 + (u_A - p_A)^2}$$
  $$\Delta_{\text{upper}} = (p_B - p_A) + \sqrt{(u_B - p_B)^2 + (p_A - l_A)^2}$$
- **Two-Proportion Z-Test:**
  Pooled proportion $p_{\text{pool}} = \frac{K_A + K_B}{N_A + N_B}$, standard error $SE = \sqrt{p_{\text{pool}}(1 - p_{\text{pool}})\left(\frac{1}{N_A} + \frac{1}{N_B}\right)}$, test statistic $z = \frac{p_B - p_A}{SE}$.

---

## 6. Audit Checklist for Analysts

When reviewing analytical deliverables in this repository, confirm:
1. Denominators are explicitly designated as **Sessions** or **Unique Users**.
2. No metric combines raw purchase event rows with unique session counts.
3. Obfuscation caveats are stated alongside absolute currency figures.
4. Confidence intervals accompany all headline conversion rates.
5. Statistical tests validate $N > 0$ and $0 \le K \le N$.
