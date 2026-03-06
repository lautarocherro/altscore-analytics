import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# Import cached loaders to prevent duplicate DB hits
from analysis.budget_metrics import load_comms_data, load_deals_data

def main():
    try:
        st.set_page_config(
            page_title="AltScore · Budget Waterfall",
            page_icon="🌊",
            layout="wide",
        )
    except st.errors.StreamlitAPIException:
        pass

    st.markdown("## 🌊 Budget Waterfall")
    st.caption("Time-sliced progression and funnel conversion matrix")

    # Load raw data
    df_comms_raw = load_comms_data()
    df_deals_raw = load_deals_data()

    if isinstance(df_comms_raw['hs_timestamp'].iloc[0], str) or isinstance(df_comms_raw['hs_timestamp'].iloc[0], pd.Timestamp):
         df_comms_raw['hs_timestamp'] = pd.to_datetime(df_comms_raw['hs_timestamp']).dt.date

    # ── Filters Sidebar ───────────────────────────────────────────────────
    st.sidebar.header("🎛  Filters")
    
    # Date Range
    today = date.today()
    default_start = today.replace(day=1) - relativedelta(months=3) # Default to last 3 months
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(default_start, today),
        max_value=today
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_range[0], date_range[0]
        
    # Dropdowns for deals 
    won_company_opts = [True, False]
    selected_won_company = st.sidebar.selectbox("Won Company", ["All", "True", "False"], index=2)
    
    if "dealtype" in df_deals_raw.columns:
        dealtype_opts = sorted(df_deals_raw["dealtype"].dropna().unique().tolist())
        selected_dealtype = st.sidebar.multiselect("Dealtype", dealtype_opts, default=["New Business"] if "New Business" in dealtype_opts else dealtype_opts)
    else:
        selected_dealtype = []
    
    # ICP Options
    if "ideal_customer_profile_tier" in df_comms_raw.columns:
        df_comms_raw["ideal_customer_profile_tier"] = df_comms_raw["ideal_customer_profile_tier"].fillna("Null_Value")
        def format_icp_name(val):
            if val == "Null_Value": return "Null"
            return str(val).replace("_", " ").title()
        raw_icp_opts = sorted(df_comms_raw["ideal_customer_profile_tier"].unique().tolist())
        if raw_icp_opts:
            selected_icp = st.sidebar.multiselect("Ideal Customer Tier", raw_icp_opts, format_func=format_icp_name)
        else: selected_icp = []
    else: selected_icp = []
        
    # Product
    if "house" in df_deals_raw.columns:
        product_opts = sorted(df_deals_raw["house"].dropna().unique().tolist())
        default_product = ["AltDecision"] if "AltDecision" in product_opts else product_opts
        selected_product = st.sidebar.multiselect("Product", product_opts, default=default_product)
    else: selected_product = []
    
    # Channel
    if "channel" in df_deals_raw.columns:
        channel_opts = sorted(df_deals_raw["channel"].dropna().unique().tolist())
        selected_channel = st.sidebar.multiselect("Channel", channel_opts)
    else: selected_channel = []
        
    # SDR
    if "sdr" in df_deals_raw.columns:
        sdr_opts = sorted(df_deals_raw["sdr"].dropna().unique().tolist())
        selected_sdr = st.sidebar.multiselect("SDR", sdr_opts)
    elif "sdr" in df_comms_raw.columns:
        sdr_opts = sorted(df_comms_raw["sdr"].dropna().unique().tolist())
        selected_sdr = st.sidebar.multiselect("SDR", sdr_opts)
    else: selected_sdr = []
        
    # Archetype Vertical
    if "archetype_vertical" in df_comms_raw.columns:
        arch_opts = sorted(df_comms_raw["archetype_vertical"].dropna().unique().tolist())
        selected_archetype = st.sidebar.multiselect("Archetype Vertical", arch_opts)
    else: selected_archetype = []

    # ── Apply Base Filters ──────────────────────────────────────────────────
    
    # Comms base masking (Note: We won't strictly subset Comms by date yet, so we can group by month)
    # Actually, we SHOULD subset by the global date range to restrict the matrix window.
    mask_comms = (df_comms_raw['hs_timestamp'] >= start_date) & (df_comms_raw['hs_timestamp'] <= end_date)
    if selected_won_company != "All" and 'is_company_won' in df_comms_raw.columns:
        mask_comms &= (df_comms_raw['is_company_won'] == (selected_won_company == "True"))
    if selected_icp and 'ideal_customer_profile_tier' in df_comms_raw.columns:
        mask_comms &= df_comms_raw['ideal_customer_profile_tier'].isin(selected_icp)
    if selected_sdr and 'sdr' in df_comms_raw.columns:
        mask_comms &= df_comms_raw['sdr'].isin(selected_sdr)
    if selected_archetype and 'archetype_vertical' in df_comms_raw.columns:
        mask_comms &= df_comms_raw['archetype_vertical'].isin(selected_archetype)
        
    df_comms = df_comms_raw[mask_comms].copy()

    # Deals base masking
    mask_deals = pd.Series(True, index=df_deals_raw.index)
    if selected_dealtype and 'dealtype' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['dealtype'].isin(selected_dealtype)
    if selected_icp and 'hs_ideal_customer_profile' in df_deals_raw.columns:
        df_deals_raw["hs_ideal_customer_profile"] = df_deals_raw["hs_ideal_customer_profile"].fillna("Null_Value")
        mask_deals &= df_deals_raw['hs_ideal_customer_profile'].isin(selected_icp)
    if selected_product and 'house' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['house'].isin(selected_product)
    if selected_channel and 'channel' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['channel'].isin(selected_channel)
    if selected_sdr and 'sdr' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['sdr'].isin(selected_sdr)
    if selected_archetype and 'archetype_vertical_account' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['archetype_vertical_account'].isin(selected_archetype)
    elif selected_archetype and 'archetype_vertical' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['archetype_vertical'].isin(selected_archetype)
        
    df_deals = df_deals_raw[mask_deals].copy()

    # ── Time Slicing & Waterfall Matrix Logic ───────────────────────────────
    
    st.markdown("---")
    
    # We will aggregate count metric per stage, bucketed by Month-Year.
    # The columns will be the months present in the selected date range.
    
    stages = [
        ("Positive Response", "date_entered_positive_response"),
        ("Discovery Call", "date_entered_discovery_call"),
        ("Qualified Lead (Demo)", "date_entered_demo"),
        ("Proposal", "date_entered_proposal"),
        ("Negotiation", "date_entered_negotiation"),
        ("Legal Docs", "date_entered_legal_documents"),
        ("Delivery", "date_entered_delivery"),
        ("Closed Won", "date_entered_closed_won")
    ]
    
    # Generate month labels within range
    # e.g. "2023-01", "2023-02"
    # To do this safely, we will map each date_entered column to a 'YYYY-MM' string,
    # then pivot.
    
    # We'll build a result dictionary: { "Stage Name": { "2023-01": 10, "2023-02": 15, "Total": 25 } }
    matrix = {}
    
    # Pre-calculate periods for the columns so they are ordered properly
    periods = pd.period_range(start=start_date, end=end_date, freq='M').strftime('%Y-%b').tolist()
    
    # Reach row (Contacts Reached)
    # We use hs_timestamp 
    if not df_comms.empty:
        df_comms['month_bucket'] = pd.to_datetime(df_comms['hs_timestamp']).dt.to_period('M').dt.strftime('%Y-%b')
        reach_counts = df_comms.groupby('month_bucket')['contact_id'].nunique().to_dict()
    else:
        reach_counts = {}
        
    reach_row = {"Stage": "0. Contacts Reached"}
    total_reach = 0
    for p in periods:
        val = reach_counts.get(p, 0)
        reach_row[p] = val
        total_reach += val
    reach_row["Total"] = total_reach
    
    matrix["0. Contacts Reached"] = reach_row
    
    # Funnel stages
    for i, (stage_name, col_name) in enumerate(stages):
        stage_label = f"{i+1}. {stage_name}"
        row = {"Stage": stage_label}
        total_stage = 0
        
        if col_name in df_deals.columns:
            # Filter to bounds
            mask_stage = df_deals[col_name].notna() & (df_deals[col_name] >= start_date) & (df_deals[col_name] <= end_date)
            df_stage = df_deals[mask_stage].copy()
            
            if not df_stage.empty:
                df_stage['month_bucket'] = pd.to_datetime(df_stage[col_name]).dt.to_period('M').dt.strftime('%Y-%b')
                stage_counts = df_stage.groupby('month_bucket').size().to_dict()
            else:
                stage_counts = {}
                
            for p in periods:
                val = stage_counts.get(p, 0)
                row[p] = val
                total_stage += val
        else:
            for p in periods:
                row[p] = 0
                
        row["Total"] = total_stage
        matrix[stage_label] = row
        
    df_matrix = pd.DataFrame(list(matrix.values()))
    
    # ── Visuals ─────────────────────────────────────────────────────────────
    
    st.subheader("📊 Aggregate Funnel Waterfall")
    
    # Plotly Funnel Chart based on the 'Total' column
    funnel_stages = df_matrix["Stage"].tolist()
    funnel_vals = df_matrix["Total"].tolist()
    
    fig = go.Figure(go.Funnel(
        y=funnel_stages,
        x=funnel_vals,
        textinfo="value+percent initial+percent previous",
        opacity=0.85,
        marker={"color": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22"]}
    ))
    fig.update_layout(margin={"l": 200, "r": 20, "t": 20, "b": 20}, height=500)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📅 Time-Sliced Progression Matrix")
    
    st.dataframe(
        df_matrix, 
        use_container_width=True, 
        hide_index=True,
    )

if __name__ == "__main__":
    main()
