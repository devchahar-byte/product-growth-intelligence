# ==============================================================
# Product Growth Intelligence Platform
# Notebook 1: EDA, Schema Validation & Data Quality
# Author: Dev Chahar | Manipal University Jaipur | Reg: 23FE10CSE00291
# Dataset: bigquery-public-data.ga4_obfuscated_sample_ecommerce
#
# Run as a Python script or paste cells into a Jupyter notebook.
# Requires: google-cloud-bigquery, pandas, matplotlib, seaborn
# ==============================================================

import os
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from google.cloud import bigquery

# ── Config ─────────────────────────────────────────────────────
PROJECT_ID = os.getenv('GCP_PROJECT', 'YOUR_PROJECT_ID')  # replace or set env var
DATASET    = 'bigquery-public-data.ga4_obfuscated_sample_ecommerce'
CLIENT     = bigquery.Client(project=PROJECT_ID)

PALETTE = sns.color_palette('husl', 8)
sns.set_theme(style='whitegrid', palette=PALETTE, font_scale=1.1)
FIGSIZE = (12, 5)

def run_query(sql: str) -> pd.DataFrame:
    """Execute a BigQuery SQL string and return a pandas DataFrame."""
    return CLIENT.query(sql).to_dataframe()

print('BigQuery client ready.')


# ──────────────────────────────────────────────────────────────
# SECTION 1 — Event-type inventory
# ──────────────────────────────────────────────────────────────
print('\n[1/6] Querying event inventory...')

event_counts_sql = f"""
SELECT
  event_name,
  COUNT(*)                       AS event_count,
  COUNT(DISTINCT user_pseudo_id) AS unique_users
FROM `{DATASET}.events_*`
GROUP BY event_name
ORDER BY event_count DESC
"""
df_events = run_query(event_counts_sql)
print(df_events.to_string(index=False))

# Visualise
fig, ax = plt.subplots(figsize=FIGSIZE)
top10 = df_events.head(10)
bars = ax.barh(top10['event_name'], top10['event_count'], color=PALETTE[0])
ax.set_xlabel('Event Count')
ax.set_title('Top 10 Events by Volume', fontweight='bold')
ax.invert_yaxis()
for bar, v in zip(bars, top10['event_count']):
    ax.text(v + max(top10['event_count'])*0.01, bar.get_y()+bar.get_height()/2,
            f'{v:,}', va='center', fontsize=9)
plt.tight_layout()
plt.savefig('../reports/fig01_event_inventory.png', dpi=150)
plt.show()
print('[1/6] Done. Fig saved: fig01_event_inventory.png')


# ──────────────────────────────────────────────────────────────
# SECTION 2 — Date coverage & daily volume
# ──────────────────────────────────────────────────────────────
print('\n[2/6] Daily event volume...')

daily_sql = f"""
SELECT
  PARSE_DATE('%Y%m%d', event_date) AS event_date,
  COUNT(*)                          AS events,
  COUNT(DISTINCT user_pseudo_id)    AS users
FROM `{DATASET}.events_*`
GROUP BY event_date
ORDER BY event_date
"""
df_daily = run_query(daily_sql)
df_daily['event_date'] = pd.to_datetime(df_daily['event_date'])

fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
axes[0].plot(df_daily['event_date'], df_daily['events'],
             color=PALETTE[1], linewidth=1.5)
axes[0].set_ylabel('Total Events')
axes[0].set_title('Daily Event & User Volume', fontweight='bold')
axes[1].plot(df_daily['event_date'], df_daily['users'],
             color=PALETTE[2], linewidth=1.5)
axes[1].set_ylabel('Unique Users')
axes[1].set_xlabel('Date')
plt.tight_layout()
plt.savefig('../reports/fig02_daily_volume.png', dpi=150)
plt.show()

print(f'  Date range: {df_daily.event_date.min().date()} to {df_daily.event_date.max().date()}')
print(f'  Total days: {len(df_daily)}')
print('[2/6] Done. Fig saved: fig02_daily_volume.png')


# ──────────────────────────────────────────────────────────────
# SECTION 3 — NULL / missing dimension audit
# ──────────────────────────────────────────────────────────────
print('\n[3/6] NULL rate audit...')

null_sql = f"""
SELECT
  COUNTIF(user_pseudo_id IS NULL)              AS null_user_id,
  COUNTIF(traffic_source.medium IS NULL)       AS null_medium,
  COUNTIF(device.category IS NULL)             AS null_device,
  COUNTIF(geo.country IS NULL)                 AS null_country,
  COUNTIF(ecommerce.purchase_revenue IS NULL
          AND event_name='purchase')            AS null_rev_on_purchase,
  COUNT(*) AS total_rows
FROM `{DATASET}.events_*`
"""
df_null = run_query(null_sql)
total = df_null['total_rows'].iloc[0]
print('\nNULL counts and rates:')
for col in df_null.columns:
    if col != 'total_rows':
        n = df_null[col].iloc[0]
        print(f'  {col:<35}: {n:>8,}  ({100*n/total:.2f}%)')

print('\nInterpretation:')
print('  - null_medium indicates direct / untracked traffic — normal in GA4.')
print('  - null_rev_on_purchase > 0 indicates obfuscation or tracking gaps.')
print('[3/6] Done.')


# ──────────────────────────────────────────────────────────────
# SECTION 4 — Device & channel distribution
# ──────────────────────────────────────────────────────────────
print('\n[4/6] Device & channel distributions...')

device_sql = f"""
SELECT device.category AS device, COUNT(DISTINCT user_pseudo_id) AS users
FROM `{DATASET}.events_*`
GROUP BY 1 ORDER BY users DESC
"""
channel_sql = f"""
SELECT COALESCE(traffic_source.medium,'(none)') AS medium,
       COUNT(DISTINCT user_pseudo_id) AS users
FROM `{DATASET}.events_*`
GROUP BY 1 ORDER BY users DESC LIMIT 12
"""
df_device  = run_query(device_sql)
df_channel = run_query(channel_sql)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].pie(df_device['users'], labels=df_device['device'],
            autopct='%1.1f%%', colors=PALETTE[:len(df_device)])
axes[0].set_title('Users by Device Category', fontweight='bold')

axes[1].barh(df_channel['medium'], df_channel['users'], color=PALETTE[3])
axes[1].set_xlabel('Unique Users')
axes[1].set_title('Top Traffic Channels (medium)', fontweight='bold')
axes[1].invert_yaxis()
plt.tight_layout()
plt.savefig('../reports/fig03_device_channel_dist.png', dpi=150)
plt.show()
print('[4/6] Done. Fig saved: fig03_device_channel_dist.png')


# ──────────────────────────────────────────────────────────────
# SECTION 5 — Duplicate & ordering anomalies
# ──────────────────────────────────────────────────────────────
print('\n[5/6] Duplicate event check...')

dup_sql = f"""
SELECT COUNT(*) AS dup_count
FROM (
  SELECT user_pseudo_id, event_name, event_timestamp, COUNT(*) AS c
  FROM `{DATASET}.events_*`
  GROUP BY 1,2,3
  HAVING c > 1
)
"""
df_dup = run_query(dup_sql)
dup_count = df_dup['dup_count'].iloc[0]
print(f'  Duplicate (user, event_name, timestamp) rows: {dup_count:,}')
if dup_count > 0:
    print('  ⚠ Duplicates found — deduplicate before aggregation.')
else:
    print('  ✓ No duplicates detected.')
print('[5/6] Done.')


# ──────────────────────────────────────────────────────────────
# SECTION 6 — Revenue distribution on purchase events
# ──────────────────────────────────────────────────────────────
print('\n[6/6] Revenue distribution...')

rev_sql = f"""
SELECT ecommerce.purchase_revenue AS revenue
FROM `{DATASET}.events_*`
WHERE event_name = 'purchase'
  AND ecommerce.purchase_revenue > 0
"""
df_rev = run_query(rev_sql)

print(df_rev['revenue'].describe().round(2).to_string())

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].hist(df_rev['revenue'], bins=60, color=PALETTE[4], edgecolor='white')
axes[0].set_xlabel('Purchase Revenue')
axes[0].set_ylabel('Frequency')
axes[0].set_title('Revenue Distribution', fontweight='bold')

axes[1].boxplot(df_rev['revenue'].clip(upper=df_rev['revenue'].quantile(0.99)),
                vert=False, patch_artist=True,
                boxprops=dict(facecolor=PALETTE[5]))
axes[1].set_xlabel('Purchase Revenue (capped at 99th pct)')
axes[1].set_title('Revenue Box-plot (Outlier View)', fontweight='bold')

plt.tight_layout()
plt.savefig('../reports/fig04_revenue_distribution.png', dpi=150)
plt.show()

print('\nData Quality Summary')
print('=' * 50)
print('  1. Revenue field is partially obfuscated — treat as indicative.')
print('  2. user_pseudo_id is a proxy ID, not a true user identifier.')
print('  3. Some purchase events may lack cart events (cross-device).')
print('  4. Medium/channel NULLs map to direct/untracked traffic.')
print('[6/6] Done. All EDA figures saved to reports/ folder.')


# ==============================================================
# Notebook 2: Funnel & Conversion Analysis
# ==============================================================
print('\n' + '='*60)
print('NOTEBOOK 2 — Funnel & Conversion Analysis')
print('='*60)

# ── Funnel data ────────────────────────────────────────────────
funnel_sql = f"""
WITH f AS (
  SELECT
    user_pseudo_id,
    MAX(CASE WHEN event_name='session_start'  THEN 1 ELSE 0 END) AS s1,
    MAX(CASE WHEN event_name='view_item'      THEN 1 ELSE 0 END) AS s2,
    MAX(CASE WHEN event_name='add_to_cart'    THEN 1 ELSE 0 END) AS s3,
    MAX(CASE WHEN event_name='begin_checkout' THEN 1 ELSE 0 END) AS s4,
    MAX(CASE WHEN event_name='purchase'       THEN 1 ELSE 0 END) AS s5
  FROM `{DATASET}.events_*`
  GROUP BY user_pseudo_id
)
SELECT SUM(s1) n1, SUM(s2) n2, SUM(s3) n3, SUM(s4) n4, SUM(s5) n5 FROM f
"""
df_funnel = run_query(funnel_sql).iloc[0]

stages  = ['Session Start', 'View Item', 'Add to Cart', 'Begin Checkout', 'Purchase']
counts  = [df_funnel.n1, df_funnel.n2, df_funnel.n3, df_funnel.n4, df_funnel.n5]
dropoff = [None] + [round(100*(1 - counts[i]/counts[i-1]), 1) for i in range(1, 5)]

print('\nConversion Funnel:')
print(f'{"Stage":<25} {"Users":>10} {"Drop-off %":>12}')
print('-' * 50)
for stage, count, drop in zip(stages, counts, dropoff):
    print(f'{stage:<25} {int(count):>10,} {str(drop)+"%" if drop else "—":>12}')

# Funnel chart
fig, ax = plt.subplots(figsize=(10, 6))
colors = [PALETTE[i] for i in range(5)]
bars = ax.barh(stages[::-1], counts[::-1], color=colors[::-1])
for bar, count in zip(bars, counts[::-1]):
    ax.text(count + max(counts)*0.01, bar.get_y()+bar.get_height()/2,
            f'{int(count):,}', va='center', fontsize=10)
ax.set_xlabel('Unique Users')
ax.set_title('Purchase Conversion Funnel', fontweight='bold', fontsize=14)
plt.tight_layout()
plt.savefig('../reports/fig05_funnel.png', dpi=150)
plt.show()

# Drop-off bar
fig, ax = plt.subplots(figsize=(10, 4))
transitions = [
    'Session → View Item',
    'View Item → Add Cart',
    'Add Cart → Checkout',
    'Checkout → Purchase'
]
drop_vals = dropoff[1:]
bar_colors = ['#e74c3c' if d and d > 50 else '#f39c12' if d and d > 25 else '#27ae60'
              for d in drop_vals]
bars = ax.bar(transitions, drop_vals, color=bar_colors, edgecolor='white')
for bar, val in zip(bars, drop_vals):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f'{val}%', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Drop-off %')
ax.set_title('Step-by-Step Funnel Drop-off Rates', fontweight='bold', fontsize=13)
ax.set_ylim(0, 105)
plt.xticks(rotation=10)
plt.tight_layout()
plt.savefig('../reports/fig06_dropoff_rates.png', dpi=150)
plt.show()

# ── Device funnel ──────────────────────────────────────────────
dev_funnel_sql = f"""
WITH f AS (
  SELECT
    device.category AS device,
    user_pseudo_id,
    MAX(CASE WHEN event_name='session_start' THEN 1 ELSE 0 END) AS s1,
    MAX(CASE WHEN event_name='purchase'      THEN 1 ELSE 0 END) AS s5
  FROM `{DATASET}.events_*`
  GROUP BY 1,2
)
SELECT device, SUM(s1) sessions, SUM(s5) purchasers,
  ROUND(100*SAFE_DIVIDE(SUM(s5),SUM(s1)),2) AS cvr
FROM f GROUP BY device ORDER BY sessions DESC
"""
df_dev_funnel = run_query(dev_funnel_sql)

fig, ax = plt.subplots(figsize=(8, 4))
x = range(len(df_dev_funnel))
ax.bar(x, df_dev_funnel['cvr'], color=PALETTE[:len(df_dev_funnel)], edgecolor='white', width=0.5)
ax.set_xticks(x)
ax.set_xticklabels(df_dev_funnel['device'])
ax.set_ylabel('Conversion Rate (%)')
ax.set_title('Purchase Conversion Rate by Device', fontweight='bold')
for i, (_, row) in enumerate(df_dev_funnel.iterrows()):
    ax.text(i, row['cvr']+0.05, f"{row['cvr']}%", ha='center', fontsize=10)
plt.tight_layout()
plt.savefig('../reports/fig07_device_cvr.png', dpi=150)
plt.show()

print('\nFunnel analysis complete. Figures saved.')


# ==============================================================
# Notebook 3: Channel, Product & Segment Analysis
# ==============================================================
print('\n' + '='*60)
print('NOTEBOOK 3 — Channel, Product & Segment Analysis')
print('='*60)

# ── Channel CVR ────────────────────────────────────────────────
channel_cvr_sql = f"""
WITH uc AS (
  SELECT
    user_pseudo_id,
    COALESCE(
      ARRAY_AGG(traffic_source.medium ORDER BY event_timestamp LIMIT 1)[OFFSET(0)],
      '(none)'
    ) AS medium,
    MAX(CASE WHEN event_name='purchase' THEN 1 ELSE 0 END) AS is_buyer,
    SUM(COALESCE(ecommerce.purchase_revenue,0)) AS revenue
  FROM `{DATASET}.events_*`
  GROUP BY user_pseudo_id
)
SELECT medium, COUNT(*) users, SUM(is_buyer) buyers,
  ROUND(100*SAFE_DIVIDE(SUM(is_buyer),COUNT(*)),2) AS cvr_pct,
  ROUND(SUM(revenue),2) total_revenue
FROM uc GROUP BY 1 ORDER BY users DESC
"""
df_ch = run_query(channel_cvr_sql)

fig, ax1 = plt.subplots(figsize=(12, 5))
ax2 = ax1.twinx()
bars = ax1.bar(df_ch['medium'], df_ch['users'], color=PALETTE[0], alpha=0.7, label='Users')
ax2.plot(df_ch['medium'], df_ch['cvr_pct'], 'o-', color='red', linewidth=2, label='CVR %')
ax1.set_xlabel('Traffic Medium')
ax1.set_ylabel('Unique Users', color=PALETTE[0])
ax2.set_ylabel('Conversion Rate %', color='red')
ax1.set_title('Channel: User Volume vs. Conversion Rate', fontweight='bold')
plt.xticks(rotation=20)
fig.legend(loc='upper right', bbox_to_anchor=(0.95, 0.95))
plt.tight_layout()
plt.savefig('../reports/fig08_channel_cvr.png', dpi=150)
plt.show()

# ── Top products ───────────────────────────────────────────────
prod_sql = f"""
SELECT
  item.item_name,
  item.item_category,
  SUM(item.quantity)          AS units_sold,
  ROUND(SUM(item.price * item.quantity), 2) AS revenue
FROM `{DATASET}.events_*`, UNNEST(items) AS item
WHERE event_name = 'purchase'
GROUP BY 1,2
ORDER BY revenue DESC
LIMIT 15
"""
df_prod = run_query(prod_sql)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(df_prod['item_name'][::-1], df_prod['revenue'][::-1],
               color=PALETTE[2], edgecolor='white')
ax.set_xlabel('Total Revenue')
ax.set_title('Top 15 Products by Purchase Revenue', fontweight='bold')
for bar, rev in zip(bars, df_prod['revenue'][::-1]):
    ax.text(rev + max(df_prod['revenue'])*0.01, bar.get_y()+bar.get_height()/2,
            f'\${rev:,.0f}', va='center', fontsize=8)
plt.tight_layout()
plt.savefig('../reports/fig09_top_products.png', dpi=150)
plt.show()

# ── RFM Segment distribution ───────────────────────────────────
rfm_sql = f"""
WITH rfm_raw AS (
  SELECT user_pseudo_id,
    DATE_DIFF(DATE '2021-02-01', MAX(PARSE_DATE('%Y%m%d',event_date)), DAY) AS recency,
    COUNT(DISTINCT (SELECT ep.value.int_value FROM UNNEST(event_params) ep
                    WHERE ep.key='ga_session_id')) AS frequency,
    SUM(COALESCE(ecommerce.purchase_revenue,0)) AS monetary
  FROM `{DATASET}.events_*`
  GROUP BY user_pseudo_id
),
scored AS (
  SELECT *,
    NTILE(5) OVER (ORDER BY recency DESC)   AS r,
    NTILE(5) OVER (ORDER BY frequency ASC)  AS f,
    NTILE(5) OVER (ORDER BY monetary ASC)   AS m
  FROM rfm_raw
)
SELECT
  CASE
    WHEN (r+f+m) >= 13 THEN 'Champions'
    WHEN (r+f+m) >= 10 THEN 'Loyal Customers'
    WHEN (r+f+m) >= 7  THEN 'Potential Loyalists'
    WHEN r >= 4 AND (f+m) <= 4 THEN 'New Customers'
    WHEN r <= 2 AND (f+m) >= 8 THEN 'At Risk'
    ELSE 'Hibernating'
  END AS segment,
  COUNT(*) AS users
FROM scored
GROUP BY 1 ORDER BY users DESC
"""
df_rfm = run_query(rfm_sql)

fig, ax = plt.subplots(figsize=(8, 5))
wedges, texts, autotexts = ax.pie(
    df_rfm['users'], labels=df_rfm['segment'],
    autopct='%1.1f%%', colors=PALETTE[:len(df_rfm)],
    pctdistance=0.85
)
ax.set_title('RFM Customer Segments', fontweight='bold', fontsize=13)
plt.tight_layout()
plt.savefig('../reports/fig10_rfm_segments.png', dpi=150)
plt.show()

print('\nAll analysis notebooks complete.')
print('Figures saved to: product-growth-intelligence/reports/')
