import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_sample_ecommerce_events(n_sessions=8000, seed=42):
    """
    Generates realistic event-level e-commerce telemetry mimicking GA4 export.
    Columns:
      - event_timestamp: datetime
      - event_date: YYYY-MM-DD
      - user_pseudo_id: string
      - session_id: string
      - event_name: string
      - device_category: string ('desktop', 'mobile', 'tablet')
      - traffic_medium: string ('organic', 'cpc', 'referral', 'email', 'direct')
      - country: string
      - item_name: string (optional)
      - item_category: string (optional)
      - price: float (optional)
      - purchase_revenue: float (optional)
    """
    np.random.seed(seed)
    
    start_date = datetime(2025, 11, 1)
    end_date = datetime(2026, 1, 31)
    date_range_days = (end_date - start_date).days
    
    channels = ['organic', 'cpc', 'referral', 'email', 'direct']
    channel_probs = [0.40, 0.20, 0.15, 0.05, 0.20]
    
    devices = ['mobile', 'desktop', 'tablet']
    device_probs = [0.58, 0.36, 0.06]
    
    countries = ['United States', 'India', 'United Kingdom', 'Canada', 'Germany']
    country_probs = [0.45, 0.25, 0.12, 0.10, 0.08]
    
    products = [
        ('Google Crewneck Sweatshirt', 'Apparel', 48.00),
        ('Android Classic Tee', 'Apparel', 24.00),
        ('Google Insulated Tumbler', 'Drinkware', 22.00),
        ('Chrome Dino Pin', 'Accessories', 8.50),
        ('YouTube Canvas Tote Bag', 'Lifestyle', 18.00),
        ('Google Wireless Power Bank', 'Electronics', 35.00),
        ('Nest Mini Smart Speaker', 'Electronics', 49.00),
    ]
    
    rows = []
    
    for i in range(1, n_sessions + 1):
        # 1 user can have multiple sessions
        user_num = np.random.randint(1, int(n_sessions * 0.65))
        user_id = f"USR_{user_num:05d}"
        session_id = f"{user_id}_S{i:05d}"
        
        day_offset = np.random.randint(0, date_range_days)
        minute_offset = np.random.randint(0, 1440)
        session_time = start_date + timedelta(days=day_offset, minutes=minute_offset)
        event_date_str = session_time.strftime('%Y-%m-%d')
        
        channel = np.random.choice(channels, p=channel_probs)
        device = np.random.choice(devices, p=device_probs)
        country = np.random.choice(countries, p=country_probs)
        
        # 1. Base Event: session_start
        rows.append({
            'event_timestamp': session_time,
            'event_date': event_date_str,
            'user_pseudo_id': user_id,
            'session_id': session_id,
            'event_name': 'session_start',
            'device_category': device,
            'traffic_medium': channel,
            'country': country,
            'item_name': None,
            'item_category': None,
            'price': 0.0,
            'purchase_revenue': 0.0
        })
        
        # 2. view_item (Probabilities depend on device and channel)
        view_prob = 0.52 if device == 'desktop' else 0.40
        if channel == 'email':
            view_prob += 0.20
            
        if np.random.rand() < view_prob:
            session_time += timedelta(seconds=np.random.randint(5, 60))
            prod = products[np.random.randint(0, len(products))]
            rows.append({
                'event_timestamp': session_time,
                'event_date': event_date_str,
                'user_pseudo_id': user_id,
                'session_id': session_id,
                'event_name': 'view_item',
                'device_category': device,
                'traffic_medium': channel,
                'country': country,
                'item_name': prod[0],
                'item_category': prod[1],
                'price': prod[2],
                'purchase_revenue': 0.0
            })
            
            # 3. add_to_cart
            cart_prob = 0.35 if device == 'desktop' else 0.22
            if channel == 'referral':
                cart_prob += 0.10
                
            if np.random.rand() < cart_prob:
                session_time += timedelta(seconds=np.random.randint(15, 120))
                rows.append({
                    'event_timestamp': session_time,
                    'event_date': event_date_str,
                    'user_pseudo_id': user_id,
                    'session_id': session_id,
                    'event_name': 'add_to_cart',
                    'device_category': device,
                    'traffic_medium': channel,
                    'country': country,
                    'item_name': prod[0],
                    'item_category': prod[1],
                    'price': prod[2],
                    'purchase_revenue': 0.0
                })
                
                # 4. begin_checkout
                checkout_prob = 0.65 if device == 'desktop' else 0.45
                if np.random.rand() < checkout_prob:
                    session_time += timedelta(seconds=np.random.randint(20, 180))
                    rows.append({
                        'event_timestamp': session_time,
                        'event_date': event_date_str,
                        'user_pseudo_id': user_id,
                        'session_id': session_id,
                        'event_name': 'begin_checkout',
                        'device_category': device,
                        'traffic_medium': channel,
                        'country': country,
                        'item_name': prod[0],
                        'item_category': prod[1],
                        'price': prod[2],
                        'purchase_revenue': 0.0
                    })
                    
                    # 5. purchase (Desktop converts 2.2x better than mobile)
                    purchase_prob = 0.60 if device == 'desktop' else 0.32
                    if np.random.rand() < purchase_prob:
                        session_time += timedelta(seconds=np.random.randint(30, 240))
                        qty = np.random.choice([1, 2, 3], p=[0.75, 0.20, 0.05])
                        revenue = round(prod[2] * qty, 2)
                        rows.append({
                            'event_timestamp': session_time,
                            'event_date': event_date_str,
                            'user_pseudo_id': user_id,
                            'session_id': session_id,
                            'event_name': 'purchase',
                            'device_category': device,
                            'traffic_medium': channel,
                            'country': country,
                            'item_name': prod[0],
                            'item_category': prod[1],
                            'price': prod[2],
                            'purchase_revenue': revenue
                        })

    df = pd.DataFrame(rows)
    df.sort_values(by='event_timestamp', inplace=True)
    return df

if __name__ == '__main__':
    df = generate_sample_ecommerce_events(n_sessions=6000)
    df.to_csv('data/sample_ecommerce_events.csv', index=False)
    print(f"Sample dataset generated successfully: {len(df):,} events across {df['session_id'].nunique():,} sessions.")
