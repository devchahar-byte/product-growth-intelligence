-- ============================================================
-- Module 5: Product & Category Revenue Analysis
-- Item-level revenue isolation & deduplicated cart abandonment
-- Dataset: bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- ============================================================

-- ----------------------------------------------------------------
-- 5.1  Top Products by Purchase Revenue
-- Item revenue is strictly computed from item price * item quantity.
-- Transaction-level purchase_revenue is never duplicated across items.
-- ----------------------------------------------------------------
WITH purchased_items AS (
  SELECT
    item.item_id,
    item.item_name,
    item.item_category,
    item.item_category2,
    item.item_brand,
    item.price AS unit_price,
    COALESCE(item.quantity, 1) AS qty_purchased,
    -- Strictly isolate item-level revenue without falling back to full transaction revenue
    ROUND(COALESCE(item.price * COALESCE(item.quantity, 1), 0.0), 2) AS item_revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'purchase'
    AND item.item_id IS NOT NULL
)
SELECT
  item_id,
  item_name,
  item_category,
  item_brand,
  SUM(qty_purchased) AS total_units_sold,
  ROUND(SUM(item_revenue), 2) AS total_revenue,
  ROUND(AVG(unit_price), 2) AS avg_unit_price,
  COUNT(*) AS item_purchase_occurrences
FROM purchased_items
GROUP BY 1, 2, 3, 4
ORDER BY total_revenue DESC
LIMIT 30;


-- ----------------------------------------------------------------
-- 5.2  Category-Level Conversion & Revenue
-- ----------------------------------------------------------------
WITH category_views AS (
  SELECT
    item.item_category AS category,
    COUNT(DISTINCT user_pseudo_id) AS viewers
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'view_item'
    AND item.item_category IS NOT NULL
  GROUP BY 1
),

category_carts AS (
  SELECT
    item.item_category AS category,
    COUNT(DISTINCT user_pseudo_id) AS carted
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'add_to_cart'
    AND item.item_category IS NOT NULL
  GROUP BY 1
),

category_purchases AS (
  SELECT
    item.item_category AS category,
    COUNT(DISTINCT user_pseudo_id) AS purchasers,
    ROUND(SUM(COALESCE(item.price * COALESCE(item.quantity, 1), 0.0)), 2) AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'purchase'
    AND item.item_category IS NOT NULL
  GROUP BY 1
)

SELECT
  v.category,
  v.viewers,
  COALESCE(c.carted, 0) AS cart_users,
  COALESCE(p.purchasers, 0) AS purchase_users,
  COALESCE(p.revenue, 0.0) AS total_revenue,
  ROUND(100 * SAFE_DIVIDE(c.carted, v.viewers), 2) AS view_to_cart_pct,
  ROUND(100 * SAFE_DIVIDE(p.purchasers, c.carted), 2) AS cart_to_purchase_pct,
  ROUND(100 * SAFE_DIVIDE(p.purchasers, v.viewers), 2) AS overall_item_cvr_pct
FROM category_views AS v
LEFT JOIN category_carts AS c ON v.category = c.category
LEFT JOIN category_purchases AS p ON v.category = p.category
ORDER BY total_revenue DESC;


-- ----------------------------------------------------------------
-- 5.3  Product-Level Cart Abandonment Rate
-- Deduplicated at the (session_id, item_id) grain to prevent row multiplication
-- when an item is added to cart multiple times within a single session.
-- ----------------------------------------------------------------
WITH distinct_carted_items AS (
  SELECT DISTINCT
    CONCAT(user_pseudo_id, '_', CAST(
      (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id') AS STRING
    )) AS session_id,
    item.item_id,
    item.item_name,
    item.item_category
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'add_to_cart'
    AND item.item_id IS NOT NULL
    AND (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id') IS NOT NULL
),

distinct_purchased_items AS (
  SELECT DISTINCT
    CONCAT(user_pseudo_id, '_', CAST(
      (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id') AS STRING
    )) AS session_id,
    item.item_id
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'purchase'
    AND item.item_id IS NOT NULL
    AND (SELECT ep.value.int_value FROM UNNEST(event_params) ep WHERE ep.key = 'ga_session_id') IS NOT NULL
)

SELECT
  c.item_id,
  c.item_name,
  c.item_category,
  COUNT(DISTINCT c.session_id) AS sessions_carted,
  COUNTIF(p.item_id IS NULL) AS sessions_abandoned,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(p.item_id IS NULL), COUNT(DISTINCT c.session_id)), 2) AS abandonment_rate_pct
FROM distinct_carted_items AS c
LEFT JOIN distinct_purchased_items AS p
  ON c.session_id = p.session_id
  AND c.item_id = p.item_id
GROUP BY 1, 2, 3
HAVING sessions_carted >= 5
ORDER BY abandonment_rate_pct DESC
LIMIT 30;
