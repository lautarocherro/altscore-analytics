"""
AltScore — HubSpot Communications Analysis
Streamlit dashboard: daily outreach volume and reach by owner.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from analysis.shared import get_bq_client

QUERY = """
SELECT
    hs_timestamp,
    hubspot_owner_name,
    company_id,
    contact_id,
    type,
    hs_call_disposition,
    hs_email_status
FROM `modeling-449120.internal_metrics.HUBSPOT_ALL_COMMS_BEFORE_POSRES`
"""

@st.cache_data(show_spinner="Querying BigQuery…", ttl=600)
def load_data() -> pd.DataFrame:
    client = get_bq_client()
    df = client.query(QUERY).to_dataframe()
    df["hs_timestamp"] = pd.to_datetime(df["hs_timestamp"])
    df["date"] = df["hs_timestamp"].dt.date
    df["hubspot_owner_name"] = df["hubspot_owner_name"].fillna("Unknown")
    df["type"] = df["type"].fillna("Unknown")
    return df

def main():
    try:
        st.set_page_config(
            page_title="AltScore · HubSpot Comms",
            page_icon="📧",
            layout="wide",
        )
    except st.errors.StreamlitAPIException:
        pass

    sns.set_theme(style="darkgrid", palette="muted", font_scale=1.1)
    plt.rcParams.update({
        "figure.facecolor": "#0e1117", "axes.facecolor": "#262730",
        "text.color": "white", "axes.labelcolor": "white",
        "xtick.color": "white", "ytick.color": "white",
        "axes.edgecolor": "#444", "grid.color": "#333",
    })

    st.markdown("## 📧 HubSpot Communications Analysis")
    st.caption("Daily outreach volume and reach before positive response.")

    df = load_data()

    # ── Sidebar filters ──────────────────────────────────────────────────
    st.sidebar.header("🎛  Filters")

    min_date = df["date"].min()
    max_date = df["date"].max()
    date_range = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    owner_options = sorted(df["hubspot_owner_name"].unique().tolist())
    selected_owners = st.sidebar.multiselect("HubSpot Owner", owner_options, default=owner_options)

    type_options = sorted(df["type"].unique().tolist())
    selected_types = st.sidebar.multiselect("Activity Type", type_options, default=type_options)

    # Apply filters
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
    else:
        mask = pd.Series(True, index=df.index)

    mask &= df["hubspot_owner_name"].isin(selected_owners)
    mask &= df["type"].isin(selected_types)
    df_filt = df[mask].copy()

    # ═══════════════════════════════════════════════════════════════════
    # KPI CARDS
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    
    total_comms = len(df_filt)
    unique_companies = df_filt["company_id"].nunique()
    unique_contacts = df_filt["contact_id"].nunique()
    comms_per_company = total_comms / unique_companies if unique_companies > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Activities", f"{total_comms:,}")
    c2.metric("Unique Companies", f"{unique_companies:,}")
    c3.metric("Unique Contacts", f"{unique_contacts:,}")
    c4.metric("Avg Comms / Company", f"{comms_per_company:.1f}")

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # Daily Trend
    # ═══════════════════════════════════════════════════════════════════
    st.subheader("📈 Daily Outreach Trend")
    
    daily_stats = df_filt.groupby("date").agg(
        Activities=("type", "count"),
        Companies=("company_id", "nunique"),
        Contacts=("contact_id", "nunique")
    ).reset_index()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(daily_stats["date"], daily_stats["Companies"], marker="o", label="Unique Companies", linewidth=2, color="#4c72b0")
    ax.plot(daily_stats["date"], daily_stats["Contacts"], marker="s", label="Unique Contacts", linewidth=2, color="#55a868")
    ax.set_title("Companies & Contacts Contacted Daily", fontsize=14, pad=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("Count")
    ax.legend(facecolor="#1c1f26", edgecolor="#444")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # ═══════════════════════════════════════════════════════════════════
    # Owner Analysis
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("👤 Owner Performance")
    
    owner_stats = df_filt.groupby("hubspot_owner_name").agg(
        Activities=("type", "count"),
        Companies=("company_id", "nunique"),
        Contacts=("contact_id", "nunique")
    ).reset_index().sort_values("Activities", ascending=False)
    
    owner_stats["Rate (Comms/Company)"] = (owner_stats["Activities"] / owner_stats["Companies"]).round(1)

    col_tbl, col_chart = st.columns([1, 1])
    
    with col_tbl:
        st.dataframe(owner_stats.rename(columns={
            "hubspot_owner_name": "Owner",
            "Activities": "Total Comms",
            "Companies": "Companies",
            "Contacts": "Contacts"
        }), width="stretch", hide_index=True)

    with col_chart:
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        sns.barplot(data=owner_stats, y="hubspot_owner_name", x="Activities", ax=ax2, palette="viridis", edgecolor="#444")
        ax2.set_title("Activities by Owner", fontsize=14, pad=12)
        ax2.set_xlabel("Total Activities")
        ax2.set_ylabel("")
        plt.tight_layout()
        st.pyplot(fig2)
        plt.close()

    # ═══════════════════════════════════════════════════════════════════
    # Type Breakdown
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📊 Activity Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**By Type**")
        type_counts = df_filt["type"].value_counts()
        fig3, ax3 = plt.subplots(figsize=(6, 6))
        ax3.pie(type_counts, labels=type_counts.index, autopct="%1.1f%%", startangle=140, 
                textprops={"color": "white"}, wedgeprops={"edgecolor": "#444"})
        ax3.set_title("Activities by Type", color="white")
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close()

    with col2:
        st.markdown("**Owner Activity Mix**")
        mix = df_filt.groupby(["hubspot_owner_name", "type"]).size().unstack(fill_value=0)
        # Normalize to 100%
        mix_perc = mix.div(mix.sum(axis=1), axis=0) * 100
        fig4, ax4 = plt.subplots(figsize=(7, 5))
        mix_perc.plot(kind="barh", stacked=True, ax=ax4, edgecolor="#444")
        ax4.set_title("Activity Mix by Owner (%)", color="white")
        ax4.set_xlabel("Percentage (%)")
        ax4.set_ylabel("")
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left', facecolor="#1c1f26", edgecolor="#444")
        plt.tight_layout()
        st.pyplot(fig4)
        plt.close()

    st.markdown(
        "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:2rem;'>"
        "Data: HUBSPOT_ALL_COMMS_BEFORE_POSRES · BigQuery · AltScore</div>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
