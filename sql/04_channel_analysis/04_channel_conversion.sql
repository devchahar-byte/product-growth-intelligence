-- ============================================================
-- Module 4: Channel / Acquisition Analysis
-- First-Touch & Session Attribution Models
-- Dataset: bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- ============================================================

-- ----------------------------------------------------------------
-- 4.1  First-Touch User Channel Conversion Summary
-- Partitions all 270,154 unique users by their earliest observed medium.
-- Sum of total_users = total unique users; sum of buyers = total purchasers.
-- ----------------------------------------------------------------
WITH user_first_touch AS (
  SELECT
    user_pseudo_id,
    ARRAY_AGG(
      traffic_source.medium IGNORE NULLS
      ORDER BY event_timestamp ASC
      LIMIT 1
    )[SAFE_OFFSET(0)] AS first_medium,
    COUNTIF(event_name = 'purchase') AS total_purchases,
    MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS is_buyer,
    SUM(COALESCE(ecommerce.purchase_revenue, 0)) AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  COALESCE(first_medium, '(none)') AS channel,
  COUNT(DISTINCT user_pseudo_id) AS total_users,
  SUM(is_buyer) AS buyers,
  ROUND(100 * SAFE_DIVIDE(SUM(is_buyer), COUNT(DISTINCT user_pseudo_id)), 2) AS user_cvr_pct,
  SUM(total_purchases) AS total_orders,
  ROUND(SUM(revenue), 2) AS total_revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(total_purchases), 0)), 2) AS avg_order_value,
  ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(is_buyer), 0)), 2) AS revenue_per_buyer
FROM user_first_touch
GROUP BY 1
ORDER BY total_users DESC;


-- ----------------------------------------------------------------
-- 4.2  Session-Level Channel Summary
-- Evaluates conversion rate at the visit grain (one row per session).
-- ----------------------------------------------------------------
WITH session_channel AS (
  SELECT
    CONCAT(user_pseudo_id, '_', CAST(
      (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id') AS STRING
    )) AS session_id,
    ARRAY_AGG(traffic_source.medium IGNORE NULLS ORDER BY event_timestamp ASC LIMIT 1)[SAFE_OFFSET(0)] AS medium,
    MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS has_purchase,
    COUNTIF(event_name = 'purchase') AS purchase_events,
    SUM(COALESCE(ecommerce.purchase_revenue, 0)) AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id') IS NOT NULL
  GROUP BY 1
)
SELECT
  COALESCE(medium, '(none)') AS channel,
  COUNT(DISTINCT session_id) AS total_sessions,
  COUNTIF(has_purchase = 1) AS converting_sessions,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(has_purchase = 1), COUNT(DISTINCT session_id)), 2) AS session_cvr_pct,
  SUM(purchase_events) AS total_orders,
  ROUND(SUM(revenue), 2) AS total_revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(purchase_events), 0)), 2) AS avg_order_value
FROM session_channel
GROUP BY 1
ORDER BY total_sessions DESC;


-- ----------------------------------------------------------------
-- 4.3  New vs. Returning User Conversion
-- ----------------------------------------------------------------
WITH user_sessions AS (
  SELECT
    user_pseudo_id,
    COUNT(DISTINCT
      (SELECT ep.value.int_value FROM UNNEST(event_params) ep
       WHERE ep.key = 'ga_session_id')
    ) AS session_count,
    MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS is_buyer,
    COUNTIF(event_name = 'purchase') AS total_purchases,
    SUM(COALESCE(ecommerce.purchase_revenue, 0)) AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  CASE WHEN session_count = 1 THEN 'New User (1 session)'
       WHEN session_count <= 3 THEN 'Returning User (2-3 sessions)'
       ELSE 'Loyal User (4+ sessions)'
  END AS user_segment,
  COUNT(*) AS users,
  SUM(is_buyer) AS buyers,
  ROUND(100 * SAFE_DIVIDE(SUM(is_buyer), COUNT(*)), 2) AS user_cvr_pct,
  ROUND(SUM(revenue), 2) AS total_revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), NULLIF(SUM(total_purchases), 0)), 2) AS avg_order_value
FROM user_sessions
GROUP BY 1
ORDER BY user_cvr_pct DESC;
