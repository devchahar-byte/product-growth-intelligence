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
from python.scripts.metrics import (
    normalize_event_schema,
    compute_session_metrics,
    compute_channel_metrics,
    compute_device_metrics,
    calculate_sequential_funnel,
    validate_timestamp_ordering
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
    df_raw = pd.read_csv(file_path_or_buffer)
    df, meta = normalize_event_schema(df_raw)
    return df, meta

# Header
st.title("🛒 Product Growth Intelligence Platform")
st.caption("Interactive E-Commerce Product Analytics, Conversion Funnels & Experimentation Engine | Dev Chahar")

# -------------------------------------------------------------
# Sidebar: Data Input & Filters
# -------------------------------------------------------------
st.sidebar.header("📁 Data Source & Filters")

data_source = st.sidebar.radio(
    "Select Data Source:",
    ["Sample GA4 E-Commerce Dataset (Canonical Benchmark)", "Upload Custom CSV"]
)

if data_source == "Upload Custom CSV":
    uploaded_file = st.sidebar.file_uploader("Upload Event CSV", type=['csv'])
    if uploaded_file is not None:
        raw_df, meta = load_data(uploaded_file)
        if meta.get('session_id_fallback'):
            st.sidebar.warning("⚠️ **Approximated Sessions:** Uploaded CSV lacks session identifiers; sessions estimated by User.")
    else:
        st.info("👆 Upload an event-level e-commerce CSV in the sidebar to begin analysis.")
        st.stop()
else:
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_ecommerce_events.csv")
    if os.path.exists(sample_path):
        raw_df, meta = load_data(sample_path)
    else:
        from python.scripts.generate_sample_data import generate_sample_ecommerce_events
        generated_df = generate_sample_ecommerce_events(n_sessions=6000)
        generated_df.to_csv(sample_path, index=False)
        raw_df, meta = load_data(sample_path)
    st.sidebar.caption("Benchmark: Validated GA4 E-Commerce Sample (Google Merchandise Store).")

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
kpi_summary = compute_session_metrics(filtered_df)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Events", f"{kpi_summary['total_events']:,}")
c2.metric("Sessions", f"{kpi_summary['total_sessions']:,}")
c3.metric("Unique Users", f"{kpi_summary['unique_users']:,}")
c4.metric("Converting Sessions", f"{kpi_summary['converting_sessions']:,}", help=f"Total purchase events: {kpi_summary['total_purchase_events']:,}")
c5.metric("Session CVR", f"{kpi_summary['session_cvr_pct']:.2f}%", help="Sessions with >=1 purchase / Total sessions")
c6.metric("Total Revenue", f"${kpi_summary['total_revenue']:,.2f}")

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
    st.subheader("Interactive Sequential Conversion Funnel & Drop-off Leakages")
    st.caption("Stage transitions enforce chronological event timestamp order within each session.")
    
    funnel_df = calculate_sequential_funnel(filtered_df)
    
    col_chart, col_table = st.columns([3, 2])
    
    with col_chart:
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_df['Stage'],
            x=funnel_df['Sessions'],
            textinfo="value+percent initial+percent previous",
            marker={"color": ["#3b82f6", "#60a5fa", "#8b5cf6", "#a855f7", "#10b981"]}
        ))
        fig_funnel.update_layout(title="Sequential 5-Stage Purchase Funnel", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
    with col_table:
        st.write("### Stage Breakdown Table")
        st.dataframe(funnel_df, use_container_width=True)
        
        # Highlight top bottleneck
        if len(funnel_df) > 1 and max(funnel_df['Step Drop-off (%)'].values[1:]) > 0:
            max_drop_idx = int(np.argmax(funnel_df['Step Drop-off (%)'].values[1:]) + 1)
            st.error(f"🚨 **Primary Funnel Bottleneck:** {funnel_df['Stage'].iloc[max_drop_idx-1]} → {funnel_df['Stage'].iloc[max_drop_idx]} with a **{funnel_df['Step Drop-off (%)'].iloc[max_drop_idx]}% drop-off**.")

# -------------------------------------------------------------
# TAB 2: CHANNEL ROI
# -------------------------------------------------------------
with tab_channel:
    st.subheader("Acquisition Channel Performance & Efficiency")
    
    channel_agg = compute_channel_metrics(filtered_df)
    
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
    
    dev_agg = compute_device_metrics(filtered_df)
    
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
        base_cvr_default = float(kpi_summary['session_cvr_pct']) if kpi_summary['session_cvr_pct'] > 0 else 2.0
        base_cvr_pct = st.number_input("Baseline Conversion Rate (%)", min_value=0.01, max_value=50.0, value=base_cvr_default, step=0.1)
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
        
        days_span = max(1, (max_date - min_date).days)
        avg_daily_sessions = kpi_summary['total_sessions'] / days_span
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
            diff_label = f"+{res['lift_pct']}%" if res['lift_pct'] is not None else "undefined"
            st.write(f"Relative Lift: **{diff_label}**")
            st.write(f"Difference 95% CI: **[{res['diff_ci_lower']*100:.2f}%, {res['diff_ci_upper']*100:.2f}%]**")
            st.write(f"Z-Statistic: **{res['z_stat']}** | p-value: **{res['p_value']:.4e}**")
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
        audit_res = validate_timestamp_ordering(filtered_df)
        if not audit_res['applicable']:
            st.info(f"ℹ️ {audit_res['message']}")
        elif audit_res['is_valid']:
            st.success(f"✅ Timestamp ordering validated: All {audit_res['total_multi_event_sessions']:,} multi-event sessions have chronologically ordered events.")
        else:
            st.warning(f"⚠️ Timestamp anomaly: {audit_res['non_monotonic_sessions']:,} of {audit_res['total_multi_event_sessions']:,} multi-event sessions contain out-of-order event timestamps.")

st.markdown("---")
st.caption("Product Growth Intelligence Platform | Developed by Dev Chahar (Manipal University Jaipur)")

