-- ============================================================
-- Module 2: User-level & Session-level Summary Layer
-- Builds base tables for all downstream analysis
-- ============================================================

-- ----------------------------------------------------------------
-- 2.1  Session-level summary  (one row per session)
-- Metric definitions:
--   session_id         : user_pseudo_id + ga_session_id
--   session_start_ts   : first event timestamp in session
--   channel            : traffic_source.medium (first non-null)
--   total_events       : count of events in session
--   pageviews          : count of page_view events
--   has_purchase       : 1 if purchase event fired, else 0
--   session_revenue    : sum of ecommerce.purchase_revenue
-- ----------------------------------------------------------------
WITH raw AS (
  SELECT
    user_pseudo_id,
    -- Extract ga_session_id from event_params array
    (SELECT ep.value.int_value
     FROM UNNEST(event_params) AS ep
     WHERE ep.key = 'ga_session_id') AS ga_session_id,

    event_name,
    event_timestamp,
    PARSE_DATE('%Y%m%d', event_date) AS event_date,

    traffic_source.medium   AS medium,
    traffic_source.source   AS source,
    traffic_source.name     AS campaign,
    device.category         AS device_category,
    geo.country             AS country,
    ecommerce.purchase_revenue AS purchase_revenue

  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
),

session_base AS (
  SELECT
    CONCAT(user_pseudo_id, '_', CAST(ga_session_id AS STRING)) AS session_id,
    user_pseudo_id,
    ga_session_id,

    MIN(event_date)       AS session_date,
    MIN(event_timestamp)  AS session_start_ts,
    MAX(event_timestamp)  AS session_end_ts,

    -- Channel attribution: first medium seen in session
    MAX(medium)           AS medium,
    MAX(source)           AS source,
    MAX(campaign)         AS campaign,
    MAX(device_category)  AS device_category,
    MAX(country)          AS country,

    COUNT(*)              AS total_events,
    COUNTIF(event_name = 'page_view')          AS pageviews,
    COUNTIF(event_name = 'view_item')          AS product_views,
    COUNTIF(event_name = 'add_to_cart')        AS add_to_carts,
    COUNTIF(event_name = 'begin_checkout')     AS begin_checkouts,
    COUNTIF(event_name = 'add_payment_info')   AS payment_infos,
    COUNTIF(event_name = 'purchase')           AS purchases,

    -- Binary purchase flag
    MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS has_purchase,

    -- Revenue
    SUM(COALESCE(purchase_revenue, 0)) AS session_revenue,

    -- Session duration in seconds
    ROUND(
      (MAX(event_timestamp) - MIN(event_timestamp)) / 1e6,
      1
    ) AS session_duration_sec

  FROM raw
  WHERE ga_session_id IS NOT NULL
  GROUP BY 1, 2, 3
)

SELECT * FROM session_base
ORDER BY session_date, user_pseudo_id;


-- ----------------------------------------------------------------
-- 2.2  User-level summary  (one row per user)
-- ----------------------------------------------------------------
WITH raw AS (
  SELECT
    user_pseudo_id,
    (SELECT ep.value.int_value FROM UNNEST(event_params) AS ep
     WHERE ep.key = 'ga_session_id') AS ga_session_id,
    event_name,
    PARSE_DATE('%Y%m%d', event_date) AS event_date,
    traffic_source.medium  AS medium,
    device.category        AS device_category,
    ecommerce.purchase_revenue AS purchase_revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
),

user_base AS (
  SELECT
    user_pseudo_id,
    MIN(event_date)                          AS first_seen_date,
    MAX(event_date)                          AS last_seen_date,
    COUNT(DISTINCT ga_session_id)            AS total_sessions,
    COUNT(*)                                 AS total_events,
    COUNTIF(event_name = 'purchase')         AS total_purchases,
    SUM(COALESCE(purchase_revenue, 0))       AS lifetime_revenue,
    MAX(CASE WHEN event_name='purchase'
             THEN 1 ELSE 0 END)              AS is_buyer,
    -- Dominant channel
    (SELECT AS STRUCT medium, COUNT(*) AS cnt
     FROM UNNEST(ARRAY_AGG(medium IGNORE NULLS))
     GROUP BY medium ORDER BY cnt DESC LIMIT 1
    ).medium                                 AS primary_medium,
    -- Dominant device
    MAX(device_category)                     AS primary_device
  FROM raw
  WHERE ga_session_id IS NOT NULL
  GROUP BY user_pseudo_id
)

SELECT
  *,
  DATE_DIFF(last_seen_date, first_seen_date, DAY) AS user_lifespan_days,
  SAFE_DIVIDE(lifetime_revenue, total_purchases)  AS avg_order_value
FROM user_base;
