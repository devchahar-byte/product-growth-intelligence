-- ============================================================
-- Module 3: Conversion Funnel Analysis
-- Canonical Sequential Session Funnel & User-Level Reach Layer
-- Dataset: bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- ============================================================

-- ----------------------------------------------------------------
-- 3.1  Sequential Session Conversion Funnel
-- Evaluates within-session progression enforcing strict stage ordering:
-- session_start (t1) <= view_item (t2) <= add_to_cart (t3)
-- <= begin_checkout (t4) <= purchase (t5)
-- ----------------------------------------------------------------
WITH raw_events AS (
  SELECT
    user_pseudo_id,
    (SELECT ep.value.int_value FROM UNNEST(event_params) AS ep
     WHERE ep.key = 'ga_session_id') AS ga_session_id,
    event_name,
    event_timestamp,
    PARSE_DATE('%Y%m%d', event_date) AS event_date,
    device.category AS device_category
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
),

session_timestamps AS (
  SELECT
    CONCAT(user_pseudo_id, '_', CAST(ga_session_id AS STRING)) AS session_id,
    user_pseudo_id,
    ga_session_id,
    ARRAY_AGG(device_category IGNORE NULLS ORDER BY event_timestamp ASC LIMIT 1)[SAFE_OFFSET(0)] AS device_category,
    MIN(CASE WHEN event_name = 'session_start'  THEN event_timestamp END) AS t_session,
    MIN(CASE WHEN event_name = 'view_item'      THEN event_timestamp END) AS t_view,
    MIN(CASE WHEN event_name = 'add_to_cart'    THEN event_timestamp END) AS t_cart,
    MIN(CASE WHEN event_name = 'begin_checkout' THEN event_timestamp END) AS t_checkout,
    MIN(CASE WHEN event_name = 'purchase'       THEN event_timestamp END) AS t_purchase
  FROM raw_events
  WHERE ga_session_id IS NOT NULL
  GROUP BY 1, 2, 3
),

sequential_flags AS (
  SELECT
    session_id,
    device_category,
    -- Step 1: Session initiated
    CASE WHEN t_session IS NOT NULL THEN 1 ELSE 0 END AS s1_session,

    -- Step 2: Product viewed after or at session start
    CASE WHEN t_session IS NOT NULL
              AND t_view IS NOT NULL
              AND t_view >= t_session THEN 1 ELSE 0 END AS s2_view,

    -- Step 3: Item added to cart after or at product view
    CASE WHEN t_session IS NOT NULL
              AND t_view IS NOT NULL
              AND t_cart IS NOT NULL
              AND t_view >= t_session
              AND t_cart >= t_view THEN 1 ELSE 0 END AS s3_cart,

    -- Step 4: Checkout initiated after or at cart add
    CASE WHEN t_session IS NOT NULL
              AND t_view IS NOT NULL
              AND t_cart IS NOT NULL
              AND t_checkout IS NOT NULL
              AND t_view >= t_session
              AND t_cart >= t_view
              AND t_checkout >= t_cart THEN 1 ELSE 0 END AS s4_checkout,

    -- Step 5: Purchase completed after or at checkout begin
    CASE WHEN t_session IS NOT NULL
              AND t_view IS NOT NULL
              AND t_cart IS NOT NULL
              AND t_checkout IS NOT NULL
              AND t_purchase IS NOT NULL
              AND t_view >= t_session
              AND t_cart >= t_view
              AND t_checkout >= t_cart
              AND t_purchase >= t_checkout THEN 1 ELSE 0 END AS s5_purchase
  FROM session_timestamps
),

funnel_counts AS (
  SELECT
    SUM(s1_session)  AS n1,
    SUM(s2_view)     AS n2,
    SUM(s3_cart)     AS n3,
    SUM(s4_checkout) AS n4,
    SUM(s5_purchase) AS n5
  FROM sequential_flags
)

SELECT
  '1. Session Start'   AS funnel_stage, 1 AS stage_order, n1 AS sessions,
  100.0 AS pct_of_top, 0.0 AS step_drop_off_pct
FROM funnel_counts
UNION ALL
SELECT '2. View Item', 2, n2, ROUND(100 * SAFE_DIVIDE(n2, n1), 2), ROUND(100 * (1 - SAFE_DIVIDE(n2, n1)), 2)
FROM funnel_counts
UNION ALL
SELECT '3. Add to Cart', 3, n3, ROUND(100 * SAFE_DIVIDE(n3, n1), 2), ROUND(100 * (1 - SAFE_DIVIDE(n3, n2)), 2)
FROM funnel_counts
UNION ALL
SELECT '4. Begin Checkout', 4, n4, ROUND(100 * SAFE_DIVIDE(n4, n1), 2), ROUND(100 * (1 - SAFE_DIVIDE(n4, n3)), 2)
FROM funnel_counts
UNION ALL
SELECT '5. Purchase', 5, n5, ROUND(100 * SAFE_DIVIDE(n5, n1), 2), ROUND(100 * (1 - SAFE_DIVIDE(n5, n4)), 2)
FROM funnel_counts
ORDER BY stage_order;


-- ----------------------------------------------------------------
-- 3.2  Sequential Funnel by Device Category
-- ----------------------------------------------------------------
SELECT
  device_category,
  SUM(s1_session)  AS sessions,
  SUM(s2_view)     AS product_views,
  SUM(s3_cart)     AS cart_adders,
  SUM(s4_checkout) AS checkouts,
  SUM(s5_purchase) AS purchases,
  ROUND(100 * SAFE_DIVIDE(SUM(s5_purchase), SUM(s1_session)), 2) AS session_cvr_pct
FROM sequential_flags
GROUP BY device_category
ORDER BY sessions DESC;


-- ----------------------------------------------------------------
-- 3.3  User-Level Lifetime Event Reach Analysis (Non-Sequential)
-- Distinct from the sequential session funnel: measures whether a unique
-- user ever experienced an event at any point across the entire period.
-- ----------------------------------------------------------------
WITH user_reach AS (
  SELECT
    user_pseudo_id,
    MAX(CASE WHEN event_name = 'session_start'  THEN 1 ELSE 0 END) AS reached_session,
    MAX(CASE WHEN event_name = 'view_item'      THEN 1 ELSE 0 END) AS reached_view,
    MAX(CASE WHEN event_name = 'add_to_cart'    THEN 1 ELSE 0 END) AS reached_cart,
    MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END) AS reached_checkout,
    MAX(CASE WHEN event_name = 'purchase'       THEN 1 ELSE 0 END) AS reached_purchase
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)
SELECT
  COUNT(DISTINCT user_pseudo_id) AS total_unique_users,
  SUM(reached_session)   AS users_with_session_start,
  SUM(reached_view)      AS users_with_view_item,
  SUM(reached_cart)      AS users_with_add_to_cart,
  SUM(reached_checkout)  AS users_with_checkout,
  SUM(reached_purchase)  AS users_with_purchase,
  ROUND(100 * SAFE_DIVIDE(SUM(reached_purchase), COUNT(DISTINCT user_pseudo_id)), 2) AS user_cvr_pct
FROM user_reach;
