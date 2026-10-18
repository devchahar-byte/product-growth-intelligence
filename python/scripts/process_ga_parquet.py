import pandas as pd

df = pd.read_parquet('data/ga_sample.parquet')
rows = []

for idx, r in df.iterrows():
    vid = str(r['fullVisitorId'])
    visit_id = str(r['visitId'])
    sid = f"{vid}_{visit_id}"
    dt = str(r['date'])
    dev = r['device'].get('deviceCategory', 'desktop') if isinstance(r['device'], dict) else 'desktop'
    ch = str(r['channelGrouping'])
    
    totals = r['totals'] if isinstance(r['totals'], dict) else {}
    rev = float(totals.get('transactionRevenue', 0.0) or 0.0) / 1e6
    txs = int(totals.get('transactions', 0) or 0)
    
    # 1. session_start
    rows.append({
        'session_id': sid,
        'user_id': vid,
        'event_name': 'session_start',
        'event_date': dt,
        'device_category': dev.lower(),
        'traffic_medium': ch.lower(),
        'purchase_revenue': 0.0
    })
    
    # 2. page_view / view_item
    rows.append({
        'session_id': sid,
        'user_id': vid,
        'event_name': 'view_item',
        'event_date': dt,
        'device_category': dev.lower(),
        'traffic_medium': ch.lower(),
        'purchase_revenue': 0.0
    })
    
    # Check hits for e-commerce actions
    hits = r['hits'] if isinstance(r['hits'], list) else []
    had_cart = False
    had_checkout = False
    
    for h in hits:
        if isinstance(h, dict):
            ecom = h.get('eCommerceAction', {})
            act = str(ecom.get('action_type', ''))
            if act in ['2', '3']:
                had_cart = True
            if act in ['5']:
                had_checkout = True

    if had_cart or txs > 0:
        rows.append({
            'session_id': sid,
            'user_id': vid,
            'event_name': 'add_to_cart',
            'event_date': dt,
            'device_category': dev.lower(),
            'traffic_medium': ch.lower(),
            'purchase_revenue': 0.0
        })
        
    if had_checkout or txs > 0:
        rows.append({
            'session_id': sid,
            'user_id': vid,
            'event_name': 'begin_checkout',
            'event_date': dt,
            'device_category': dev.lower(),
            'traffic_medium': ch.lower(),
            'purchase_revenue': 0.0
        })
        
    if txs > 0:
        rows.append({
            'session_id': sid,
            'user_id': vid,
            'event_name': 'purchase',
            'event_date': dt,
            'device_category': dev.lower(),
            'traffic_medium': ch.lower(),
            'purchase_revenue': round(rev, 2)
        })

df_out = pd.DataFrame(rows)
df_out.to_csv('data/google_analytics_real_events.csv', index=False)
print('Google Analytics real clickstream generated successfully!')
print(df_out['event_name'].value_counts())
print(f'Total rows: {len(df_out):,}')
