-- ============================================================
-- Product Growth Intelligence Platform
-- Module 1: Schema Exploration & Dataset Validation
-- Dataset: bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- Author: Dev Chahar | Manipal University Jaipur
-- ============================================================

-- ----------------------------------------------------------------
-- 1.1  Event types present in the dataset
-- ----------------------------------------------------------------
SELECT
  event_name,
  COUNT(*)                          AS event_count,
  COUNT(DISTINCT user_pseudo_id)    AS unique_users,
  MIN(PARSE_DATE('%Y%m%d', event_date)) AS first_date,
  MAX(PARSE_DATE('%Y%m%d', event_date)) AS last_date
FROM
  `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY event_name
ORDER BY event_count DESC;


-- ----------------------------------------------------------------
-- 1.2  Available top-level columns and sample row
-- ----------------------------------------------------------------
SELECT *
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20201101'
LIMIT 1;


-- ----------------------------------------------------------------
-- 1.3  Traffic_source breakdown (channel / medium / source)
-- ----------------------------------------------------------------
SELECT
  traffic_source.medium   AS medium,
  traffic_source.source   AS source,
  traffic_source.name     AS campaign,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM
  `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2, 3
ORDER BY users DESC
LIMIT 50;


-- ----------------------------------------------------------------
-- 1.4  Device category distribution
-- ----------------------------------------------------------------
SELECT
  device.category          AS device_category,
  device.operating_system  AS os,
  device.browser           AS browser,
  COUNT(*)                 AS events,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM
  `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2, 3
ORDER BY users DESC;


-- ----------------------------------------------------------------
-- 1.5  Geo breakdown: country / region
-- ----------------------------------------------------------------
SELECT
  geo.country   AS country,
  geo.region    AS region,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(*) AS events
FROM
  `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2
ORDER BY users DESC
LIMIT 30;


-- ----------------------------------------------------------------
-- 1.6  Event params keys available (unnested)
-- ----------------------------------------------------------------
SELECT
  ep.key,
  COUNT(*) AS occurrences
FROM
  `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
  UNNEST(event_params) AS ep
GROUP BY ep.key
ORDER BY occurrences DESC;


-- ----------------------------------------------------------------
-- 1.7  E-commerce item fields available
-- ----------------------------------------------------------------
SELECT
  item.item_id,
  item.item_name,
  item.item_category,
  item.item_category2,
  item.item_brand,
  item.price,
  item.quantity,
  ecommerce.purchase_revenue
FROM
  `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`,
  UNNEST(items) AS item
WHERE event_name = 'purchase'
  AND _TABLE_SUFFIX BETWEEN '20201101' AND '20201115'
LIMIT 20;
