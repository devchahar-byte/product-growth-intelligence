-- ============================================================
-- Module 6: Segment Analysis
-- Conversion & engagement by device, channel, geography
-- ============================================================

-- ----------------------------------------------------------------
-- 6.1  Conversion by device × channel (heat-map data)
-- ----------------------------------------------------------------
WITH base AS (
  SELECT
    user_pseudo_id,
    MAX(device.category) AS device,
    COALESCE(
      ARRAY_AGG(traffic_source.medium ORDER BY event_timestamp LIMIT 1)[OFFSET(0)],
      '(none)'
    ) AS medium,
    MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) AS converted,
    SUM(COALESCE(ecommerce.purchase_revenue,0)) AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  device,
  medium,
  COUNT(*)         AS users,
  SUM(converted)   AS buyers,
  ROUND(SUM(revenue),2) AS revenue,
  ROUND(100*SAFE_DIVIDE(SUM(converted), COUNT(*)),2) AS cvr_pct
FROM base
GROUP BY 1, 2
ORDER BY users DESC;


-- ----------------------------------------------------------------
-- 6.2  RFM Segmentation  (Recency / Frequency / Monetary)
-- IMPORTANT: obfuscated revenue limits monetary precision
-- ----------------------------------------------------------------
WITH rfm_raw AS (
  SELECT
    user_pseudo_id,
    DATE_DIFF(
      DATE '2021-02-01',   -- analysis reference date (day after dataset end)
      MAX(PARSE_DATE('%Y%m%d', event_date)), DAY
    ) AS recency_days,
    COUNT(DISTINCT
      (SELECT ep.value.int_value FROM UNNEST(event_params) ep
       WHERE ep.key='ga_session_id')
    ) AS frequency,
    SUM(COALESCE(ecommerce.purchase_revenue, 0)) AS monetary
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
),
rfm_scores AS (
  SELECT *,
    NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,  -- lower recency = better
    NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
    NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
  FROM rfm_raw
)
SELECT
  user_pseudo_id,
  recency_days, frequency, monetary,
  r_score, f_score, m_score,
  (r_score + f_score + m_score) AS rfm_total,
  CASE
    WHEN (r_score + f_score + m_score) >= 13 THEN 'Champions'
    WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal Customers'
    WHEN (r_score + f_score + m_score) >= 7  THEN 'Potential Loyalists'
    WHEN r_score >= 4 AND (f_score + m_score) <= 4 THEN 'New Customers'
    WHEN r_score <= 2 AND (f_score + m_score) >= 8  THEN 'At Risk'
    ELSE 'Hibernating'
  END AS rfm_segment
FROM rfm_scores;


-- ----------------------------------------------------------------
-- 6.3  Engagement score vs. conversion
-- ----------------------------------------------------------------
WITH eng AS (
  SELECT
    user_pseudo_id,
    COUNT(*) AS total_events,
    COUNTIF(event_name='page_view')  AS pageviews,
    COUNTIF(event_name='view_item')  AS item_views,
    COUNTIF(event_name='add_to_cart') AS carts,
    MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) AS is_buyer
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  CASE
    WHEN total_events <= 5   THEN 'Low (1-5 events)'
    WHEN total_events <= 20  THEN 'Medium (6-20 events)'
    WHEN total_events <= 50  THEN 'High (21-50 events)'
    ELSE 'Very High (50+ events)'
  END AS engagement_bucket,
  COUNT(*) AS users,
  SUM(is_buyer) AS buyers,
  ROUND(100*SAFE_DIVIDE(SUM(is_buyer), COUNT(*)), 2) AS cvr_pct
FROM eng
GROUP BY 1
ORDER BY cvr_pct DESC;
