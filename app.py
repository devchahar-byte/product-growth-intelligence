import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from python.scripts.stats_helpers import (
    conversion_rate_ci,
    two_prop_z_test,
    sample_size_for_proportion
)

# -------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="Product Growth Intelligence Platform",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 8px 8px 0px 0px;
        padding-left: 18px;
        padding-right: 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Data Loader & Cache
# -------------------------------------------------------------
@st.cache_data
def load_data(file_path_or_buffer):
    df = pd.read_csv(file_path_or_buffer)
    # Schema normalization for flexible CSV uploads
    col_mapping = {
        'user_id': 'user_pseudo_id',
        'userId': 'user_pseudo_id',
        'session': 'session_id',
        'sessionId': 'session_id',
        'event': 'event_name',
        'eventType': 'event_name',
        'medium': 'traffic_medium',
        'channel': 'traffic_medium',
        'device': 'device_category',
        'device_type': 'device_category',
        'revenue': 'purchase_revenue',
        'price': 'purchase_revenue',
        'timestamp': 'event_timestamp',
        'date': 'event_date'
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns and v not in df.columns})
    
    if 'event_timestamp' in df.columns:
        df['event_timestamp'] = pd.to_datetime(df['event_timestamp'])
    else:
        df['event_timestamp'] = pd.Timestamp.now()
        
    if 'event_date' in df.columns:
        df['event_date'] = pd.to_datetime(df['event_date'])
    else:
        df['event_date'] = pd.to_datetime(df['event_timestamp']).dt.floor('d')
        
    if 'session_id' not in df.columns and 'user_pseudo_id' in df.columns:
        df['session_id'] = df['user_pseudo_id'].astype(str) + '_' + df['event_date'].astype(str)
        
    if 'traffic_medium' not in df.columns:
        df['traffic_medium'] = '(none)'
    if 'device_category' not in df.columns:
        df['device_category'] = 'desktop'
    if 'purchase_revenue' not in df.columns:
        df['purchase_revenue'] = 0.0
    else:
        df['purchase_revenue'] = pd.to_numeric(df['purchase_revenue'], errors='coerce').fillna(0.0)
        
    return df

# Header
st.title("🛒 Product Growth Intelligence Platform")
st.caption("Interactive E-Commerce Product Analytics, Conversion Funnels & Experimentation Engine | Dev Chahar")

# -------------------------------------------------------------
# Sidebar: Data Input & Filters
# -------------------------------------------------------------
st.sidebar.header("📁 Data Source & Filters")

data_source = st.sidebar.radio(
    "Select Data Source:",
    ["Sample GA4 E-Commerce Dataset", "Upload Custom CSV"]
)

if data_source == "Upload Custom CSV":
    uploaded_file = st.sidebar.file_uploader("Upload Event CSV", type=['csv'])
    if uploaded_file is not None:
        raw_df = load_data(uploaded_file)
    else:
        st.info("👆 Upload an event-level e-commerce CSV in the sidebar to begin analysis.")
        st.stop()
else:
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_ecommerce_events.csv")
    if os.path.exists(sample_path):
        raw_df = load_data(sample_path)
    else:
        from python.scripts.generate_sample_data import generate_sample_ecommerce_events
        raw_df = generate_sample_ecommerce_events(n_sessions=6000)
        raw_df.to_csv(sample_path, index=False)

# Global Filters
min_date = raw_df['event_date'].min().date()
max_date = raw_df['event_date'].max().date()

date_range = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)
devices = st.sidebar.multiselect("Device Category", raw_df['device_category'].unique(), default=raw_df['device_category'].unique())
channels = st.sidebar.multiselect("Traffic Channel", raw_df['traffic_medium'].unique(), default=raw_df['traffic_medium'].unique())

# Apply Filters
if len(date_range) == 2:
    start_d, end_d = date_range
    filtered_df = raw_df[
        (raw_df['event_date'].dt.date >= start_d) &
        (raw_df['event_date'].dt.date <= end_d) &
        (raw_df['device_category'].isin(devices)) &
        (raw_df['traffic_medium'].isin(channels))
    ]
else:
    filtered_df = raw_df

# -------------------------------------------------------------
# Top-Level KPI Ribbon
# -------------------------------------------------------------
total_events = len(filtered_df)
total_sessions = filtered_df['session_id'].nunique()
unique_users = filtered_df['user_pseudo_id'].nunique()
converting_sessions = filtered_df[filtered_df['event_name'] == 'purchase']['session_id'].nunique()
total_purchases = len(filtered_df[filtered_df['event_name'] == 'purchase'])
total_revenue = filtered_df['purchase_revenue'].sum()
overall_cvr = (converting_sessions / total_sessions * 100) if total_sessions > 0 else 0
aov = (total_revenue / total_purchases) if total_purchases > 0 else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Events", f"{total_events:,}")
c2.metric("Sessions", f"{total_sessions:,}")
c3.metric("Unique Users", f"{unique_users:,}")
c4.metric("Converting Sessions", f"{converting_sessions:,}", help=f"Total purchase events: {total_purchases:,}")
c5.metric("Session CVR", f"{overall_cvr:.2f}%", help="Sessions with >=1 purchase / Total sessions")
c6.metric("Total Revenue", f"${total_revenue:,.2f}")

st.divider()

# -------------------------------------------------------------
# Main Navigation Tabs
# -------------------------------------------------------------
tab_funnel, tab_channel, tab_device, tab_rfm, tab_ab, tab_dq = st.tabs([
    "📊 Funnel Analysis",
    "🚀 Channel ROI",
    "📱 Device Disparity",
    "🎯 RFM Segmentation",
    "🧪 A/B Test Sizing & Evaluation",
    "🔍 Data Quality Audit"
])

# -------------------------------------------------------------
# TAB 1: FUNNEL ANALYSIS
# -------------------------------------------------------------
with tab_funnel:
    st.subheader("Interactive Conversion Funnel & Drop-off Leakages")
    
    stages = ['session_start', 'view_item', 'add_to_cart', 'begin_checkout', 'purchase']
    stage_labels = ['Session Start', 'View Item', 'Add to Cart', 'Begin Checkout', 'Purchase']
    
    # Calculate unique sessions reaching each stage
    stage_counts = []
    for stage in stages:
        cnt = filtered_df[filtered_df['event_name'] == stage]['session_id'].nunique()
        stage_counts.append(cnt)
        
    funnel_df = pd.DataFrame({
        'Stage': stage_labels,
        'Sessions': stage_counts
    })
    
    # Calculate drops
    funnel_df['% of Top'] = (funnel_df['Sessions'] / funnel_df['Sessions'].iloc[0] * 100).round(2)
    step_drops = [0.0]
    for i in range(1, len(funnel_df)):
        prev = funnel_df['Sessions'].iloc[i-1]
        curr = funnel_df['Sessions'].iloc[i]
        drop = round(100 * (1 - curr / prev), 2) if prev > 0 else 0
        step_drops.append(drop)
    funnel_df['Step Drop-off (%)'] = step_drops
    
    col_chart, col_table = st.columns([3, 2])
    
    with col_chart:
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_df['Stage'],
            x=funnel_df['Sessions'],
            textinfo="value+percent initial+percent previous",
            marker={"color": ["#3b82f6", "#60a5fa", "#8b5cf6", "#a855f7", "#10b981"]}
        ))
        fig_funnel.update_layout(title="5-Stage Purchase Funnel", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
    with col_table:
        st.write("### Stage Breakdown Table")
        st.dataframe(funnel_df, use_container_width=True)
        
        # Highlight top bottleneck
        max_drop_idx = np.argmax(funnel_df['Step Drop-off (%)'].values[1:]) + 1
        st.error(f"🚨 **Primary Funnel Bottleneck:** {funnel_df['Stage'].iloc[max_drop_idx-1]} → {funnel_df['Stage'].iloc[max_drop_idx]} with a **{funnel_df['Step Drop-off (%)'].iloc[max_drop_idx]}% drop-off**.")

# -------------------------------------------------------------
# TAB 2: CHANNEL ROI
# -------------------------------------------------------------
with tab_channel:
    st.subheader("Acquisition Channel Performance & Efficiency")
    
    channel_summary = []
    for med, grp in filtered_df.groupby('traffic_medium'):
        s_count = grp['session_id'].nunique()
        c_count = grp[grp['event_name'] == 'purchase']['session_id'].nunique()
        p_events = (grp['event_name'] == 'purchase').sum()
        rev = grp['purchase_revenue'].sum()
        cvr = round(100 * c_count / s_count, 2) if s_count > 0 else 0.0
        aov_val = round(rev / p_events, 2) if p_events > 0 else 0.0
        channel_summary.append({
            'traffic_medium': med,
            'sessions': s_count,
            'converting_sessions': c_count,
            'purchases': p_events,
            'revenue': round(rev, 2),
            'cvr_pct': cvr,
            'aov': aov_val
        })
    channel_agg = pd.DataFrame(channel_summary)
    
    fig_ch = px.scatter(
        channel_agg,
        x='sessions',
        y='cvr_pct',
        size='revenue',
        color='traffic_medium',
        hover_name='traffic_medium',
        text='traffic_medium',
        title="Channel Quadrant: Session Volume vs. Conversion Rate % (Size = Revenue)",
        labels={'sessions': 'Total Sessions', 'cvr_pct': 'Session CVR (%)'}
    )
    fig_ch.update_traces(textposition='top center')
    st.plotly_chart(fig_ch, use_container_width=True)
    st.dataframe(channel_agg, use_container_width=True)

# -------------------------------------------------------------
# TAB 3: DEVICE DISPARITY
# -------------------------------------------------------------
with tab_device:
    st.subheader("Mobile vs. Desktop Conversion Gap")
    
    dev_summary = []
    for dev, grp in filtered_df.groupby('device_category'):
        s_count = grp['session_id'].nunique()
        c_count = grp[grp['event_name'] == 'purchase']['session_id'].nunique()
        p_events = (grp['event_name'] == 'purchase').sum()
        rev = grp['purchase_revenue'].sum()
        cvr = round(100 * c_count / s_count, 2) if s_count > 0 else 0.0
        dev_summary.append({
            'device_category': dev,
            'sessions': s_count,
            'converting_sessions': c_count,
            'purchases': p_events,
            'revenue': round(rev, 2),
            'cvr_pct': cvr
        })
    dev_agg = pd.DataFrame(dev_summary)
    
    c_pie, c_bar = st.columns(2)
    with c_pie:
        fig_dev_pie = px.pie(dev_agg, names='device_category', values='sessions', title="Traffic Share by Device", hole=0.4)
        st.plotly_chart(fig_dev_pie, use_container_width=True)
    with c_bar:
        fig_dev_bar = px.bar(dev_agg, x='device_category', y='cvr_pct', color='device_category', title="Conversion Rate (%) by Device", text='cvr_pct')
        st.plotly_chart(fig_dev_bar, use_container_width=True)
        
    # Statistical comparison between Desktop and Mobile
    d_desk = dev_agg[dev_agg['device_category'] == 'desktop']
    d_mob = dev_agg[dev_agg['device_category'] == 'mobile']
    
    if len(d_desk) > 0 and len(d_mob) > 0:
        c_desk, n_desk = int(d_desk['converting_sessions'].iloc[0]), int(d_desk['sessions'].iloc[0])
        c_mob, n_mob = int(d_mob['converting_sessions'].iloc[0]), int(d_mob['sessions'].iloc[0])
        
        stat_res = two_prop_z_test(c_mob, n_mob, c_desk, n_desk)
        
        diff_str = f"+{stat_res['lift_pct']}%" if stat_res['lift_pct'] is not None else "undefined"
        st.info(f"**Desktop vs Mobile Z-Test:** Desktop CVR is **{stat_res['cvr_b']*100:.2f}%** vs Mobile CVR of **{stat_res['cvr_a']*100:.2f}%**. Relative Lift: **{diff_str}** (Diff 95% CI: [{stat_res['diff_ci_lower']*100:.2f}%, {stat_res['diff_ci_upper']*100:.2f}%], Z-score: {stat_res['z_stat']}, p-value: {stat_res['p_value']:.4e}). Statistically Significant: **{stat_res['significant']}**.")

# -------------------------------------------------------------
# TAB 4: RFM SEGMENTATION
# -------------------------------------------------------------
with tab_rfm:
    st.subheader("Recency, Frequency, Monetary (RFM) Customer Segmentation")
    
    # Calculate user-level metrics
    max_d = filtered_df['event_date'].max()
    user_rfm = filtered_df.groupby('user_pseudo_id').agg(
        last_date=('event_date', 'max'),
        frequency=('session_id', 'nunique'),
        monetary=('purchase_revenue', 'sum')
    ).reset_index()
    
    user_rfm['recency_days'] = (max_d - user_rfm['last_date']).dt.days
    
    # Simple quantiles (fallback if small counts)
    try:
        user_rfm['r_score'] = pd.qcut(user_rfm['recency_days'], 4, labels=[4, 3, 2, 1], duplicates='drop').astype(int)
        user_rfm['f_score'] = pd.qcut(user_rfm['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4]).astype(int)
        user_rfm['m_score'] = pd.qcut(user_rfm['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4]).astype(int)
        
        user_rfm['rfm_sum'] = user_rfm['r_score'] + user_rfm['f_score'] + user_rfm['m_score']
        
        def assign_segment(score):
            if score >= 10: return "Champions"
            elif score >= 8: return "Loyal Customers"
            elif score >= 6: return "Potential Loyalists"
            elif score >= 4: return "At Risk"
            else: return "Hibernating"
            
        user_rfm['Segment'] = user_rfm['rfm_sum'].apply(assign_segment)
        seg_counts = user_rfm['Segment'].value_counts().reset_index()
        seg_counts.columns = ['Segment', 'Users']
        
        fig_rfm = px.pie(seg_counts, names='Segment', values='Users', title="Customer Base Segment Distribution", hole=0.45)
        st.plotly_chart(fig_rfm, use_container_width=True)
        st.dataframe(user_rfm.head(20), use_container_width=True)
    except Exception as e:
        st.warning(f"RFM requires broader variation in transaction counts: {e}")

# -------------------------------------------------------------
# TAB 5: A/B TEST SIZING & EVALUATION
# -------------------------------------------------------------
with tab_ab:
    st.subheader("A/B Testing Experimentation Calculator")
    st.caption("Plan sample sizes and evaluate post-experiment significance")
    
    col_plan, col_eval = st.columns(2)
    
    with col_plan:
        st.markdown("### 1. Pre-Experiment Sample Sizing")
        base_cvr_pct = st.number_input("Baseline Conversion Rate (%)", min_value=0.1, max_value=50.0, value=float(overall_cvr) if overall_cvr > 0 else 2.0, step=0.1)
        mde_pct = st.slider("Minimum Detectable Effect (Relative Lift %)", min_value=1, max_value=50, value=10)
        power_val = st.selectbox("Statistical Power (1 - β)", [0.80, 0.90], index=0)
        alpha_val = st.selectbox("Significance Level (α)", [0.05, 0.01], index=0)
        
        req_sample = sample_size_for_proportion(
            baseline_cvr=base_cvr_pct / 100,
            min_detectable_effect=mde_pct / 100,
            alpha=alpha_val,
            power=power_val
        )
        st.success(f"**Required Sample Size:** **{req_sample:,}** sessions per variant (**{req_sample*2:,}** total).")
        
        avg_daily_sessions = total_sessions / max(1, (max_date - min_date).days)
        est_days = round((req_sample * 2) / max(1, avg_daily_sessions))
        st.info(f"⏱️ Estimated test duration at current traffic: **{est_days} days**.")
        
    with col_eval:
        st.markdown("### 2. Live A/B Significance Evaluator")
        conv_control = st.number_input("Control Conversions", value=150, step=1)
        n_control = st.number_input("Control Total Visitors", value=5000, step=10)
        conv_treat = st.number_input("Treatment Conversions", value=195, step=1)
        n_treat = st.number_input("Treatment Total Visitors", value=5000, step=10)
        
        if st.button("Evaluate Statistical Significance"):
            res = two_prop_z_test(conv_control, n_control, conv_treat, n_treat)
            st.write(f"Control CVR: **{res['cvr_a']*100:.2f}%**")
            st.write(f"Treatment CVR: **{res['cvr_b']*100:.2f}%**")
            st.write(f"Relative Lift: **+{res['lift_pct']}%**")
            st.write(f"Z-Statistic: **{res['z_stat']}** | p-value: **{res['p_value']:.4f}**")
            if res['significant']:
                st.balloons()
                st.success("🎉 Statistically Significant! The observed lift is unlikely to be due to chance.")
            else:
                st.warning("Inconclusive. The difference does not reach statistical significance.")

# -------------------------------------------------------------
# TAB 6: DATA QUALITY AUDIT
# -------------------------------------------------------------
with tab_dq:
    st.subheader("Data Reliability & Quality Checks")
    
    dq_col1, dq_col2 = st.columns(2)
    
    with dq_col1:
        st.markdown("### Missing / NULL Dimension Check")
        null_counts = filtered_df.isnull().sum().reset_index()
        null_counts.columns = ['Dimension', 'Missing Count']
        null_counts['Missing Rate (%)'] = (null_counts['Missing Count'] / len(filtered_df) * 100).round(2)
        st.dataframe(null_counts, use_container_width=True)
        
    with dq_col2:
        st.markdown("### Sequencing & Timestamp Sanity Check")
        # Check sessions with purchase but no add_to_cart
        session_event_pivot = filtered_df.pivot_table(
            index='session_id',
            columns='event_name',
            aggfunc='size',
            fill_value=0
        )
        if 'purchase' in session_event_pivot and 'add_to_cart' in session_event_pivot:
            skipped_cart = (session_event_pivot['purchase'] > 0) & (session_event_pivot['add_to_cart'] == 0)
            n_skipped = int(skipped_cart.sum())
            total_purchasing_sessions = int((session_event_pivot['purchase'] > 0).sum())
            rate = round(100 * n_skipped / total_purchasing_sessions, 2) if total_purchasing_sessions > 0 else 0
            st.write(f"Purchasing sessions without preceding cart event: **{n_skipped:,} / {total_purchasing_sessions:,} ({rate}%)**.")
            st.caption("Commonly caused by 1-click buy or cross-device session tracking loss.")
        
        # Real timestamp monotonicity validation within sessions
        ts_checks = filtered_df.groupby('session_id')['event_timestamp'].agg(['count', lambda s: s.is_monotonic_increasing])
        ts_checks.columns = ['event_count', 'is_monotonic']
        multi_event_sessions = ts_checks[ts_checks['event_count'] > 1]
        non_monotonic_sessions = int((~multi_event_sessions['is_monotonic']).sum())
        total_multi_sessions = len(multi_event_sessions)
        
        if non_monotonic_sessions == 0:
            st.success(f"✅ Timestamp ordering validated: All {total_multi_sessions:,} multi-event sessions have chronologically ordered events.")
        else:
            st.warning(f"⚠️ Timestamp anomaly: {non_monotonic_sessions:,} of {total_multi_sessions:,} multi-event sessions contain out-of-order event timestamps.")

st.markdown("---")
st.caption("Product Growth Intelligence Platform | Developed by Dev Chahar (Manipal University Jaipur)")
