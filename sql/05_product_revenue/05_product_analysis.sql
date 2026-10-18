-- ============================================================
-- Module 5: Product & Category Revenue Analysis
-- ============================================================

-- ----------------------------------------------------------------
-- 5.1  Top products by purchase revenue
-- ----------------------------------------------------------------
WITH purchased_items AS (
  SELECT
    item.item_id,
    item.item_name,
    item.item_category,
    item.item_category2,
    item.item_brand,
    item.price                         AS unit_price,
    item.quantity                      AS qty_purchased,
    COALESCE(item.price * item.quantity,
             ecommerce.purchase_revenue) AS item_revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'purchase'
)
SELECT
  item_id,
  item_name,
  item_category,
  item_brand,
  SUM(qty_purchased)   AS total_units_sold,
  ROUND(SUM(item_revenue), 2) AS total_revenue,
  ROUND(AVG(unit_price), 2)   AS avg_unit_price,
  COUNT(*)             AS purchase_events
FROM purchased_items
GROUP BY 1, 2, 3, 4
ORDER BY total_revenue DESC
LIMIT 30;


-- ----------------------------------------------------------------
-- 5.2  Category-level revenue and conversion
-- ----------------------------------------------------------------
WITH views AS (
  SELECT item.item_category AS category, COUNT(DISTINCT user_pseudo_id) AS viewers
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'view_item'
  GROUP BY 1
),
carts AS (
  SELECT item.item_category AS category, COUNT(DISTINCT user_pseudo_id) AS carted
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'add_to_cart'
  GROUP BY 1
),
purchases AS (
  SELECT
    item.item_category AS category,
    COUNT(DISTINCT user_pseudo_id) AS purchasers,
    ROUND(SUM(item.price * item.quantity), 2) AS revenue
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'purchase'
  GROUP BY 1
)
SELECT
  v.category,
  v.viewers,
  c.carted,
  p.purchasers,
  p.revenue,
  ROUND(100 * SAFE_DIVIDE(c.carted, v.viewers), 2)    AS view_to_cart_pct,
  ROUND(100 * SAFE_DIVIDE(p.purchasers, c.carted), 2) AS cart_to_purchase_pct,
  ROUND(100 * SAFE_DIVIDE(p.purchasers, v.viewers), 2) AS overall_item_cvr_pct
FROM views v
LEFT JOIN carts    c ON v.category = c.category
LEFT JOIN purchases p ON v.category = p.category
ORDER BY revenue DESC;


-- ----------------------------------------------------------------
-- 5.3  Product-level cart abandonment
--      (added to cart but never purchased in same session)
-- ----------------------------------------------------------------
WITH carted AS (
  SELECT
    CONCAT(user_pseudo_id, '_',
      CAST(
        (SELECT ep.value.int_value FROM UNNEST(event_params) ep
         WHERE ep.key='ga_session_id') AS STRING)
    ) AS session_id,
    item.item_id,
    item.item_name,
    item.item_category
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'add_to_cart'
),
bought AS (
  SELECT
    CONCAT(user_pseudo_id, '_',
      CAST(
        (SELECT ep.value.int_value FROM UNNEST(event_params) ep
         WHERE ep.key='ga_session_id') AS STRING)
    ) AS session_id,
    item.item_id
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
       UNNEST(items) AS item
  WHERE event_name = 'purchase'
)
SELECT
  c.item_id,
  c.item_name,
  c.item_category,
  COUNT(*) AS times_carted,
  COUNTIF(b.item_id IS NULL) AS times_abandoned,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(b.item_id IS NULL), COUNT(*)), 2) AS abandonment_rate_pct
FROM carted c
LEFT JOIN bought b ON c.session_id = b.session_id AND c.item_id = b.item_id
GROUP BY 1, 2, 3
HAVING times_carted >= 5
ORDER BY abandonment_rate_pct DESC
LIMIT 30;
