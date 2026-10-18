-- ============================================================
-- Module 3: Conversion Funnel Analysis
-- Funnel stages: session_start → view_item → add_to_cart
--                → begin_checkout → purchase
-- ============================================================

-- ----------------------------------------------------------------
-- 3.1  Aggregate funnel: total unique users at each stage
--      (overall, not per-session)
-- ----------------------------------------------------------------
WITH funnel_events AS (
  SELECT
    user_pseudo_id,
    MAX(CASE WHEN event_name = 'session_start'   THEN 1 ELSE 0 END) AS stage_session,
    MAX(CASE WHEN event_name = 'view_item'       THEN 1 ELSE 0 END) AS stage_view_item,
    MAX(CASE WHEN event_name = 'add_to_cart'     THEN 1 ELSE 0 END) AS stage_add_cart,
    MAX(CASE WHEN event_name = 'begin_checkout'  THEN 1 ELSE 0 END) AS stage_checkout,
    MAX(CASE WHEN event_name = 'purchase'        THEN 1 ELSE 0 END) AS stage_purchase
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
)

SELECT
  'session_start'  AS funnel_stage, 1 AS stage_order,
  SUM(stage_session)  AS users,
  ROUND(100 * SUM(stage_session)  / SUM(stage_session), 2) AS pct_of_top
FROM funnel_events

UNION ALL

SELECT 'view_item', 2,
  SUM(stage_view_item),
  ROUND(100 * SUM(stage_view_item) / SUM(stage_session), 2)
FROM funnel_events

UNION ALL

SELECT 'add_to_cart', 3,
  SUM(stage_add_cart),
  ROUND(100 * SUM(stage_add_cart) / SUM(stage_session), 2)
FROM funnel_events

UNION ALL

SELECT 'begin_checkout', 4,
  SUM(stage_checkout),
  ROUND(100 * SUM(stage_checkout) / SUM(stage_session), 2)
FROM funnel_events

UNION ALL

SELECT 'purchase', 5,
  SUM(stage_purchase),
  ROUND(100 * SUM(stage_purchase) / SUM(stage_session), 2)
FROM funnel_events

ORDER BY stage_order;


-- ----------------------------------------------------------------
-- 3.2  Step-to-step drop-off rates
-- ----------------------------------------------------------------
WITH funnel AS (
  SELECT
    user_pseudo_id,
    MAX(CASE WHEN event_name='session_start'  THEN 1 ELSE 0 END) AS s1,
    MAX(CASE WHEN event_name='view_item'      THEN 1 ELSE 0 END) AS s2,
    MAX(CASE WHEN event_name='add_to_cart'    THEN 1 ELSE 0 END) AS s3,
    MAX(CASE WHEN event_name='begin_checkout' THEN 1 ELSE 0 END) AS s4,
    MAX(CASE WHEN event_name='purchase'       THEN 1 ELSE 0 END) AS s5
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY user_pseudo_id
),
totals AS (
  SELECT
    SUM(s1) AS n1, SUM(s2) AS n2,
    SUM(s3) AS n3, SUM(s4) AS n4, SUM(s5) AS n5
  FROM funnel
)
SELECT
  'session_start → view_item'     AS transition,
  ROUND(100*(1 - n2/n1), 2)       AS drop_off_pct
FROM totals
UNION ALL
SELECT 'view_item → add_to_cart',
  ROUND(100*(1 - n3/n2), 2) FROM totals
UNION ALL
SELECT 'add_to_cart → begin_checkout',
  ROUND(100*(1 - n4/n3), 2) FROM totals
UNION ALL
SELECT 'begin_checkout → purchase',
  ROUND(100*(1 - n5/n4), 2) FROM totals;


-- ----------------------------------------------------------------
-- 3.3  Funnel by device category
-- ----------------------------------------------------------------
WITH device_funnel AS (
  SELECT
    device.category AS device_category,
    user_pseudo_id,
    MAX(CASE WHEN event_name='session_start'  THEN 1 ELSE 0 END) AS s1,
    MAX(CASE WHEN event_name='view_item'      THEN 1 ELSE 0 END) AS s2,
    MAX(CASE WHEN event_name='add_to_cart'    THEN 1 ELSE 0 END) AS s3,
    MAX(CASE WHEN event_name='begin_checkout' THEN 1 ELSE 0 END) AS s4,
    MAX(CASE WHEN event_name='purchase'       THEN 1 ELSE 0 END) AS s5
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY 1, 2
)
SELECT
  device_category,
  SUM(s1) AS session_starts,
  SUM(s2) AS product_viewers,
  SUM(s3) AS cart_adders,
  SUM(s4) AS checkout_starters,
  SUM(s5) AS purchasers,
  ROUND(100 * SAFE_DIVIDE(SUM(s5), SUM(s1)), 2) AS overall_cvr_pct
FROM device_funnel
GROUP BY device_category
ORDER BY session_starts DESC;


-- ----------------------------------------------------------------
-- 3.4  Weekly funnel trend
-- ----------------------------------------------------------------
WITH weekly AS (
  SELECT
    DATE_TRUNC(PARSE_DATE('%Y%m%d', event_date), WEEK) AS week_start,
    user_pseudo_id,
    MAX(CASE WHEN event_name='session_start' THEN 1 ELSE 0 END) AS s1,
    MAX(CASE WHEN event_name='purchase'      THEN 1 ELSE 0 END) AS s5
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  GROUP BY 1, 2
)
SELECT
  week_start,
  SUM(s1) AS sessions,
  SUM(s5) AS purchasers,
  ROUND(100 * SAFE_DIVIDE(SUM(s5), SUM(s1)), 3) AS weekly_cvr_pct
FROM weekly
GROUP BY 1
ORDER BY 1;
