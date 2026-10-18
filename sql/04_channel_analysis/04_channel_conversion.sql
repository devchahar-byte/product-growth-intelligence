-- ============================================================
-- Module 4: Channel / Acquisition Analysis
-- Which traffic channels bring converting users?
-- ============================================================

-- ----------------------------------------------------------------
-- 4.1  Channel conversion summary
-- ----------------------------------------------------------------
WITH user_channel AS (
  SELECT
    user_pseudo_id,
    -- First-touch medium across entire dataset
    ARRAY_AGG(
      traffic_source.medium
      ORDER BY event_timestamp ASC
      LIMIT 1
    )[OFFSET(0)] AS first_medium,
    MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) AS is_buyer,
    SUM(COALESCE(ecommerce.purchase_revenue, 0))           AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  COALESCE(first_medium, '(none)')  AS channel,
  COUNT(DISTINCT user_pseudo_id)    AS total_users,
  SUM(is_buyer)                     AS buyers,
  ROUND(100 * SAFE_DIVIDE(SUM(is_buyer), COUNT(DISTINCT user_pseudo_id)), 2) AS cvr_pct,
  ROUND(SUM(revenue), 2)            AS total_revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), SUM(is_buyer)), 2) AS avg_order_value
FROM user_channel
GROUP BY 1
ORDER BY total_users DESC;


-- ----------------------------------------------------------------
-- 4.2  Channel + device cross-tab
-- ----------------------------------------------------------------
WITH base AS (
  SELECT
    user_pseudo_id,
    ARRAY_AGG(traffic_source.medium ORDER BY event_timestamp LIMIT 1)[OFFSET(0)] AS medium,
    MAX(device.category) AS device,
    MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) AS is_buyer
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  COALESCE(medium,'(none)') AS medium,
  device,
  COUNT(*)                  AS users,
  SUM(is_buyer)             AS buyers,
  ROUND(100*SAFE_DIVIDE(SUM(is_buyer), COUNT(*)), 2) AS cvr_pct
FROM base
GROUP BY 1, 2
ORDER BY users DESC;


-- ----------------------------------------------------------------
-- 4.3  New vs Returning user conversion
-- ----------------------------------------------------------------
WITH user_type AS (
  SELECT
    user_pseudo_id,
    -- new_or_established from user_first_touch_timestamp proximity
    MIN(PARSE_DATE('%Y%m%d', event_date)) AS first_date,
    COUNT(DISTINCT
      (SELECT ep.value.int_value FROM UNNEST(event_params) ep
       WHERE ep.key = 'ga_session_id')
    ) AS session_count,
    MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) AS is_buyer
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  CASE WHEN session_count = 1 THEN 'New User'
       WHEN session_count <= 3 THEN 'Returning (2-3 sessions)'
       ELSE 'Loyal (4+ sessions)'
  END AS user_segment,
  COUNT(*) AS users,
  SUM(is_buyer) AS buyers,
  ROUND(100*SAFE_DIVIDE(SUM(is_buyer), COUNT(*)), 2) AS cvr_pct
FROM user_type
GROUP BY 1
ORDER BY cvr_pct DESC;
