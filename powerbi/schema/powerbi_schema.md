# Power BI Dashboard Schema
## Product Growth Intelligence Platform

**Author:** Dev Chahar | Manipal University Jaipur

This document defines all tables, relationships, measures (DAX), and page layouts for the Power BI dashboard. Import the SQL query outputs as CSV/BigQuery connector sources.

---

## 1. Data Sources (Tables to Import)

| Table Name | Source SQL | Refresh Frequency |
|---|---|---|
| `dim_sessions` | Module 2 — session summary | Daily |
| `dim_users` | Module 2 — user summary | Daily |
| `fact_funnel` | Module 3 — funnel aggregates | Daily |
| `fact_channel` | Module 4 — channel conversion | Daily |
| `fact_products` | Module 5 — product revenue | Daily |
| `fact_segments` | Module 6 — device/channel cross-tab | Daily |
| `fact_rfm` | Module 6 — RFM scores | Weekly |

---

## 2. Table Schemas

### dim_sessions
```
session_id          TEXT (PK)
user_pseudo_id      TEXT
session_date        DATE
medium              TEXT
device_category     TEXT
country             TEXT
total_events        INT
pageviews           INT
product_views       INT
add_to_carts        INT
begin_checkouts     INT
purchases           INT
has_purchase        BIT
session_revenue     DECIMAL
session_duration_sec DECIMAL
```

### fact_funnel
```
funnel_stage        TEXT
stage_order         INT
users               INT
pct_of_top          DECIMAL
drop_off_pct        DECIMAL (calculated)
```

### fact_channel
```
channel             TEXT
total_users         INT
buyers              INT
cvr_pct             DECIMAL
total_revenue       DECIMAL
avg_order_value     DECIMAL
```

### fact_products
```
item_id             TEXT
item_name           TEXT
item_category       TEXT
item_brand          TEXT
total_units_sold    INT
total_revenue       DECIMAL
avg_unit_price      DECIMAL
```

---

## 3. Key DAX Measures

```dax
-- Overall Purchase Conversion Rate
CVR_Overall = 
    DIVIDE(
        COUNTROWS(FILTER(dim_sessions, dim_sessions[has_purchase] = 1)),
        COUNTROWS(dim_sessions)
    )

-- Mobile Purchase CVR
CVR_Mobile = 
    CALCULATE(
        [CVR_Overall],
        dim_sessions[device_category] = "mobile"
    )

-- Desktop Purchase CVR
CVR_Desktop = 
    CALCULATE(
        [CVR_Overall],
        dim_sessions[device_category] = "desktop"
    )

-- Mobile vs Desktop CVR Gap
CVR_MobileDesktop_Gap = [CVR_Desktop] - [CVR_Mobile]

-- Total Revenue (indicative — obfuscated)
Total_Revenue = SUM(dim_sessions[session_revenue])

-- Average Order Value
AOV = DIVIDE([Total_Revenue], COUNTROWS(FILTER(dim_sessions, dim_sessions[has_purchase]=1)))

-- Weekly Active Users
WAU = CALCULATE(DISTINCTCOUNT(dim_sessions[user_pseudo_id]),
                DATESINPERIOD(dim_sessions[session_date], LASTDATE(dim_sessions[session_date]), -7, DAY))

-- Funnel Step Drop-off
Dropoff_ViewItem = 
    1 - DIVIDE(
        CALCULATE(COUNTROWS(FILTER(dim_sessions, dim_sessions[product_views] > 0))),
        COUNTROWS(dim_sessions)
    )

-- Cart Abandonment Rate
Cart_Abandonment_Rate =
    1 - DIVIDE(
        COUNTROWS(FILTER(dim_sessions, dim_sessions[purchases] > 0)),
        COUNTROWS(FILTER(dim_sessions, dim_sessions[add_to_carts] > 0))
    )
```

---

## 4. Dashboard Pages & Visuals

### Page 1: Executive Overview
| Visual | Type | Data |
|---|---|---|
| Overall CVR | KPI Card | `CVR_Overall` |
| Total Revenue | KPI Card | `Total_Revenue` |
| Total Sessions | KPI Card | `COUNTROWS(dim_sessions)` |
| AOV | KPI Card | `AOV` |
| Weekly Sessions + CVR Trend | Line + Clustered Column | `dim_sessions[session_date]` + measures |
| Funnel Chart | Funnel Visual | `fact_funnel` |

### Page 2: Funnel Deep Dive
| Visual | Type | Data |
|---|---|---|
| Full Funnel | Funnel | `fact_funnel` |
| Step Drop-off Rates | Bar Chart | `fact_funnel[drop_off_pct]` |
| Funnel by Device | Clustered Bar | `fact_segments` grouped by device |
| Funnel Over Time | Line Chart | Weekly CVR by week |

### Page 3: Channel Analysis
| Visual | Type | Data |
|---|---|---|
| CVR by Channel | Bar | `fact_channel[cvr_pct]` |
| Revenue by Channel | Bar | `fact_channel[total_revenue]` |
| Channel × Device Heatmap | Matrix | `fact_segments[cvr_pct]` |
| Channel Bubble Chart | Scatter | x=users, y=cvr_pct, size=revenue |

### Page 4: Product & Category
| Visual | Type | Data |
|---|---|---|
| Top 15 Products | Horizontal Bar | `fact_products[total_revenue]` |
| Category Conversion | Clustered Bar | view_to_cart_pct + cart_to_purchase_pct |
| Cart Abandonment Treemap | Treemap | `abandonment_rate_pct` |

### Page 5: Customer Segments
| Visual | Type | Data |
|---|---|---|
| RFM Donut | Donut | `fact_rfm[segment]` |
| Segment × CVR | Bar | `fact_rfm` joined with purchases |
| Device CVR Gap | KPI | `CVR_MobileDesktop_Gap` |
| Engagement Bucket CVR | Bar | `fact_segments` |

---

## 5. KPI Definitions (for report footnotes)

| KPI | Definition | Denominator |
|---|---|---|
| Purchase CVR | % of sessions resulting in purchase | Unique session starts |
| AOV | Average revenue per purchase transaction | Purchase events only |
| Cart Abandonment Rate | % of add-to-cart sessions without purchase | Sessions with add_to_cart |
| Checkout Abandonment Rate | % of begin_checkout sessions without purchase | Sessions with begin_checkout |
| WAU | Distinct users with any event in rolling 7 days | Calendar-based rolling window |

> [!WARNING]
> All revenue figures in this dashboard are based on the obfuscated sample dataset.
> Absolute monetary values should not be used for business decisions.
> Conversion rate trends and ratios are more reliable signals.

---

*Power BI Schema — Product Growth Intelligence Platform*
