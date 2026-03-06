"""
AltScore — Budget Metrics Dashboard
Recreation of Looker Studio Budget Metrics
Top-of-funnel reach (contacts/companies) + Pipeline funnel conversions
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st
from datetime import date, timedelta
from analysis.shared import get_bq_client

# ── QUERIES ─────────────────────────────────────────────────────────────

QUERY_COMMS = """
SELECT
  ac.* EXCEPT(
    date_entered_positive_response
  ),
  d.date_entered_positive_response,
  d.date_entered_discovery_call,
  d.date_entered_demo,
  d.date_entered_proposal,
  d.date_entered_negotiation,
  d.date_entered_legal_documents,
  d.date_entered_delivery,
  d.date_entered_closed_won,
  d.days_from_positive_response_to_discovery_call,
  d.days_from_discovery_call_to_demo,
  d.annual_contract_value,
  d.house,
  c.name AS company_name,
  c.is_won AS is_company_won,
  c.hs_ideal_customer_profile,
  c.archetype_vertical_account as archetype_vertical,
  c.hs_ideal_customer_profile as ideal_customer_profile_tier
FROM `modeling-449120.internal_metrics.HUBSPOT_ALL_COMMS_BEFORE_POSRES` ac
LEFT JOIN `modeling-449120.internal_metrics.HUBSPOT_DEALS` d
  ON ac.deal_id = d.id
LEFT JOIN `modeling-449120.internal_metrics.HUBSPOT_COMPANIES` c
  ON ac.company_id = c.company_id
WHERE ac.hs_email_direction = 'EMAIL'
   OR ac.call_id IS NOT NULL
   OR ac.wpp_msg_id IS NOT NULL
   OR ac.linkedin_msg_id IS NOT NULL
"""

QUERY_DEALS = """
SELECT *
FROM `modeling-449120.internal_metrics.HUBSPOT_DEALS`
"""

# ── DATA LOADING ────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Querying Communications (Reach)…", ttl=600)
def load_comms_data() -> pd.DataFrame:
    client = get_bq_client()
    df = client.query(QUERY_COMMS).to_dataframe()
    # Ensure date columns are formatted
    if 'timestamp' in df.columns:
        df['comm_date'] = pd.to_datetime(df['timestamp']).dt.date
    else:
        # Fallback if timestamp missing: try to derive from entered POSRES
        # The Looker Studio date filter applies to when the action occurred.
        # We will assume "createdate" or actual timestamp exists in 'ac'.
        # Let's inspect the columns. We'll dump a debug flag below.
        pass
    return df

@st.cache_data(show_spinner="Querying Deals (Funnel)…", ttl=600)
def load_deals_data() -> pd.DataFrame:
    client = get_bq_client()
    df = client.query(QUERY_DEALS).to_dataframe()
    
    # Convert date columns for filtering
    date_cols = [c for c in df.columns if 'date_entered' in c]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col]).dt.date
    
    return df


def main():
    try:
        st.set_page_config(
            page_title="AltScore · Budget Metrics",
            page_icon="📈",
            layout="wide",
        )
    except st.errors.StreamlitAPIException:
        pass

    st.markdown("## 📈 Budget Metrics")
    st.caption("Top-of-funnel reach & pipeline conversions")

    # Load raw data
    df_comms_raw = load_comms_data()
    df_deals_raw = load_deals_data()

    # We need to find the actual comm date column. Let's fallback to 'createdate' or similar if 'timestamp' missing.
    if 'timestamp' in df_comms_raw.columns:
        df_comms_raw['comm_date'] = pd.to_datetime(df_comms_raw['timestamp']).dt.date
    elif 'createdate' in df_comms_raw.columns:
        df_comms_raw['comm_date'] = pd.to_datetime(df_comms_raw['createdate']).dt.date
    else:
        # Just grab the first date_entered we can find as a rough proxy if all else fails
        df_comms_raw['comm_date'] = pd.to_datetime(df_comms_raw.get('date_entered_positive_response', pd.NaT)).dt.date

    # ── Filters Sidebar ───────────────────────────────────────────────────
    st.sidebar.header("🎛  Filters")
    
    # Date Range
    today = date.today()
    default_start = date(today.year, today.month, 1)
    
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
    # Use deals raw to populate options
    won_company_opts = [True, False]
    selected_won_company = st.sidebar.selectbox("Won Company", ["All", "True", "False"], index=0)
    
    if "dealtype" in df_deals_raw.columns:
        dealtype_opts = sorted(df_deals_raw["dealtype"].dropna().unique().tolist())
        selected_dealtype = st.sidebar.multiselect("Dealtype", dealtype_opts, default=["New Business"] if "New Business" in dealtype_opts else dealtype_opts)
    else:
        selected_dealtype = []
    
    if "ideal_customer_profile_tier" in df_comms_raw.columns:
        icp_opts = sorted(df_comms_raw["ideal_customer_profile_tier"].dropna().unique().tolist())
    elif "hs_ideal_customer_profile" in df_deals_raw.columns:
        icp_opts = sorted(df_deals_raw["hs_ideal_customer_profile"].dropna().unique().tolist())
    else:
        icp_opts = []
    
    if icp_opts:
        selected_icp = st.sidebar.multiselect("Ideal Customer Tier", icp_opts, default=icp_opts)
    else:
        selected_icp = []

    # Apply Filters to Comms
    mask_comms = (df_comms_raw['comm_date'] >= start_date) & (df_comms_raw['comm_date'] <= end_date)
    if selected_won_company != "All" and 'is_company_won' in df_comms_raw.columns:
        b_val = selected_won_company == "True"
        mask_comms &= (df_comms_raw['is_company_won'] == b_val)
    if selected_icp and 'ideal_customer_profile_tier' in df_comms_raw.columns:
        mask_comms &= df_comms_raw['ideal_customer_profile_tier'].isin(selected_icp)
        
    df_comms = df_comms_raw[mask_comms].copy()

    mask_deals = pd.Series(True, index=df_deals_raw.index)
                 
    if selected_dealtype and 'dealtype' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['dealtype'].isin(selected_dealtype)
    if selected_icp and 'hs_ideal_customer_profile' in df_deals_raw.columns:
        mask_deals &= df_deals_raw['hs_ideal_customer_profile'].isin(selected_icp)
        
    df_deals = df_deals_raw[mask_deals].copy()

    # ── KPIs: Playgound V1/V2 Top Section ──────────────────────────────────
    st.markdown("---")
    
    # Reach Metrics (from Comms)
    contacts_reached = df_comms['contact_id'].nunique() if 'contact_id' in df_comms.columns else len(df_comms)
    companies_contacted = df_comms['company_id'].nunique() if 'company_id' in df_comms.columns else 0
    contacts_per_company = contacts_reached / companies_contacted if companies_contacted > 0 else 0
    
    # Funnel Metrics (from Deals)
    def count_stage(col):
        return df_deals[col].notna().sum() if col in df_deals.columns else 0

    pos_res_count = count_stage('date_entered_positive_response')
    deals_per_company = (pos_res_count / companies_contacted * 100) if companies_contacted > 0 else 0
    
    disc_call_count = count_stage('date_entered_discovery_call')
    # Qualified Leads = Demo
    qual_leads_count = count_stage('date_entered_demo')
    proposal_count = count_stage('date_entered_proposal')
    negotiation_count = count_stage('date_entered_negotiation')
    legal_docs_count = count_stage('date_entered_legal_documents')
    delivery_count = count_stage('date_entered_delivery')
    closed_won_count = count_stage('date_entered_closed_won')
    
    # Calculate amount for Qualified Leads (Demo stage)
    if 'date_entered_demo' in df_deals.columns:
        df_qual = df_deals[df_deals['date_entered_demo'].notna()]
        qual_value = df_qual['amount'].sum() if 'amount' in df_qual.columns else 0
    else:
        df_qual = pd.DataFrame()
        qual_value = 0
        
    avg_qual_value = qual_value / qual_leads_count if qual_leads_count > 0 else 0

    st.subheader("🎯 Reach & Early Funnel")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contacts Reached", f"{contacts_reached:,}")
    c2.metric("Companies Contacted", f"{companies_contacted:,}")
    c3.metric("Contacts per Company", f"{contacts_per_company:.2f}")
    c4.metric("Deals per Company (Conv.)", f"{deals_per_company:.2f}%")
    
    st.markdown("---")
    st.subheader("💼 Pipeline Conversions")
    
    # Row 1: Early/Mid Funnel
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("1. Positive Responses", f"{pos_res_count:,}")
    c2.metric("2. Discovery Calls", f"{disc_call_count:,}")
    c3.metric("3. Qualified Leads (Demo)", f"{qual_leads_count:,}")
    c4.metric("4. Proposals", f"{proposal_count:,}")
    
    # Row 2: Late Funnel
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("5. Negotiation", f"{negotiation_count:,}")
    c2.metric("6. Legal Docs", f"{legal_docs_count:,}")
    c3.metric("7. Delivery", f"{delivery_count:,}")
    c4.metric("8. Closed Won", f"{closed_won_count:,}")
    
    # Row 3: Values
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Qualified $", f"${qual_value:,.0f}")
    c2.metric("Avg Qualified $", f"${avg_qual_value:,.0f}")
    c3.empty()
    c4.empty()
    
    # ── Tables ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📝 Deal Details")
    
    tab1, tab2, tab3 = st.tabs(["Positive Responses", "Discovery Calls", "Qualified Leads"])
    
    # We want: Dealname, Date, SDR (or Owner)
    cols_to_show = ["dealname", "date_entered_positive_response"]
    if "hubspot_owner_id" in df_deals.columns: cols_to_show.append("hubspot_owner_id")
    
    with tab1:
        if 'date_entered_positive_response' in df_deals.columns:
            df_pos = df_deals[df_deals['date_entered_positive_response'].notna()].copy()
            show_cols = [c for c in cols_to_show if c in df_pos.columns]
            st.dataframe(df_pos[show_cols].sort_values("date_entered_positive_response", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No positive response date found in Deals table.")
        
    with tab2:
        if 'date_entered_discovery_call' in df_deals.columns:
            df_disc = df_deals[df_deals['date_entered_discovery_call'].notna()].copy()
            show_cols = [c for c in ["dealname", "date_entered_discovery_call", "hubspot_owner_id"] if c in df_disc.columns]
            st.dataframe(df_disc[show_cols].sort_values("date_entered_discovery_call", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No discovery call date found in Deals table.")
        
    with tab3:
        show_cols = [c for c in ["dealname", "date_entered_demo", "amount"] if c in df_qual.columns]
        st.dataframe(df_qual[show_cols].sort_values("amount", ascending=False), use_container_width=True, hide_index=True)

    # For debugging the schema initially on Cloud
    with st.expander("Debug: DataFrame Schemas"):
        st.write("Comms Columns:", df_comms_raw.columns.tolist())
        st.write("Deals Columns:", df_deals_raw.columns.tolist())
