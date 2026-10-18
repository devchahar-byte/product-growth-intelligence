-- ============================================================
-- Module 7: Data Quality & Reliability Validation
-- Run these before presenting any metric
-- ============================================================

-- ----------------------------------------------------------------
-- 7.1  Date coverage & row counts per day
-- ----------------------------------------------------------------
SELECT
  _TABLE_SUFFIX AS date_suffix,
  PARSE_DATE('%Y%m%d', _TABLE_SUFFIX) AS event_date,
  COUNT(*) AS total_rows,
  COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2
ORDER BY 2;


-- ----------------------------------------------------------------
-- 7.2  NULL rates for key dimensions
-- ----------------------------------------------------------------
SELECT
  COUNTIF(user_pseudo_id IS NULL)          AS null_user_id,
  COUNTIF(traffic_source.medium IS NULL)   AS null_medium,
  COUNTIF(device.category IS NULL)         AS null_device,
  COUNTIF(geo.country IS NULL)             AS null_country,
  COUNTIF(ecommerce.purchase_revenue IS NULL
          AND event_name='purchase')        AS null_purchase_rev_on_purchase,
  COUNT(*) AS total_rows
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`;


-- ----------------------------------------------------------------
-- 7.3  Duplicate event check (same user, ts, event_name)
-- ----------------------------------------------------------------
SELECT
  user_pseudo_id,
  event_name,
  event_timestamp,
  COUNT(*) AS occurrences
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2, 3
HAVING occurrences > 1
LIMIT 20;


-- ----------------------------------------------------------------
-- 7.4  Event ordering sanity: purchase without add_to_cart
-- ----------------------------------------------------------------
WITH user_events AS (
  SELECT
    user_pseudo_id,
    MAX(CASE WHEN event_name='add_to_cart' THEN 1 ELSE 0 END) AS had_cart,
    MAX(CASE WHEN event_name='purchase'    THEN 1 ELSE 0 END) AS had_purchase
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY 1
)
SELECT
  COUNTIF(had_purchase = 1 AND had_cart = 0) AS bought_without_cart,
  COUNTIF(had_purchase = 1)                 AS total_purchasers,
  ROUND(
    100 * SAFE_DIVIDE(
      COUNTIF(had_purchase = 1 AND had_cart = 0),
      COUNTIF(had_purchase = 1)
    ), 2
  ) AS pct_no_cart_before_purchase
FROM user_events;


-- ----------------------------------------------------------------
-- 7.5  Revenue anomaly detection (statistical outliers)
-- ----------------------------------------------------------------
WITH session_rev AS (
  SELECT
    CONCAT(user_pseudo_id,'_',
      CAST((SELECT ep.value.int_value FROM UNNEST(event_params) ep
            WHERE ep.key='ga_session_id') AS STRING)
    ) AS session_id,
    SUM(COALESCE(ecommerce.purchase_revenue,0)) AS session_revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE event_name='purchase'
  GROUP BY 1
),
stats AS (
  SELECT
    AVG(session_revenue)    AS mean_rev,
    STDDEV(session_revenue) AS std_rev
  FROM session_rev
)
SELECT
  r.session_id,
  r.session_revenue,
  s.mean_rev,
  s.std_rev,
  ROUND((r.session_revenue - s.mean_rev) / NULLIF(s.std_rev, 0), 2) AS z_score
FROM session_rev r, stats s
WHERE ABS((r.session_revenue - s.mean_rev) / NULLIF(s.std_rev, 0)) > 3
ORDER BY z_score DESC;


-- ----------------------------------------------------------------
-- 7.6  Obfuscation impact note
--      user_pseudo_id is obfuscated: cross-session user matching
--      may be unreliable. Revenue is also partially obfuscated.
-- ----------------------------------------------------------------
SELECT
  'WARNING: user_pseudo_id is obfuscated. Revenue fields may be'
  || ' artificially rounded or zeroed. Treat absolute monetary values'
  || ' as indicative only.' AS data_quality_note;
