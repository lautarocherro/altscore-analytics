"""
AltScore — Company Contacts Analysis
Streamlit dashboard: valid contacts per company, contact coverage, ICP breakdown
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import streamlit as st
from analysis.shared import get_bq_client

QUERY = """
SELECT
  comp.company_id,
  comp.name AS company_name,
  comp.createdate,
  comp.first_contact,
  comp.hs_ideal_customer_profile,
  comp.hs_analytics_source,
  comp.enrichment_source_country,
  COUNT(
    CASE
      WHEN cont.email IS NOT NULL
        OR cont.phone IS NOT NULL
        OR cont.hs_linkedin_url IS NOT NULL
      THEN cont.contact_id
    END
  ) AS valid_contacts_count
FROM `modeling-449120.internal_metrics.HUBSPOT_COMPANIES_FIRST_CONTACT` AS comp
LEFT JOIN `modeling-449120.internal_metrics.HUBSPOT_CONTACTS` AS cont
  ON comp.company_id = cont.company_id 
  OR comp.company_id = cont.secondary_company_id 
  OR comp.company_id = cont.tertiary_company_id
WHERE comp.createdate >= '2025-10-01'
GROUP BY 1, 2, 3, 4, 5, 6, 7
"""


@st.cache_data(show_spinner="Querying BigQuery…", ttl=600)
def load_data() -> pd.DataFrame:
    client = get_bq_client()
    raw = client.query(QUERY).to_dataframe()
    raw["has_valid_contact"] = raw["valid_contacts_count"] > 0
    raw["was_contacted"] = raw["first_contact"].notna()
    raw["createdate"] = pd.to_datetime(raw["createdate"])
    raw["create_month"] = raw["createdate"].dt.to_period("M").astype(str)
    raw["icp"] = raw["hs_ideal_customer_profile"].fillna("Unknown")
    raw["source"] = raw["hs_analytics_source"].fillna("Unknown")
    raw["enrichment_source_country"] = raw["enrichment_source_country"].fillna("Unknown")
    return raw


def main():
    try:
        st.set_page_config(
            page_title="AltScore · Company Contacts",
            page_icon="🏢",
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

    st.markdown("## 🏢 Company Contacts Analysis")
    st.caption("Contact coverage & reachability — companies created from **October 2025**")

    df = load_data()

    # ── Sidebar filters ──────────────────────────────────────────────────
    st.sidebar.header("🎛  Filters")

    icp_options = sorted(df["icp"].unique().tolist())
    selected_icp = st.sidebar.multiselect("Ideal Customer Tier", options=icp_options, default=icp_options)

    icp_options = sorted(df["icp"].unique().tolist())
    selected_icp = st.sidebar.multiselect("ICP Tier", options=icp_options, default=icp_options)

    sources = sorted(df["source"].unique().tolist())
    selected_sources = st.sidebar.multiselect("Analytics Source", options=sources, default=[])
    
    active_sources = selected_sources if selected_sources else sources

    enrichment_countries = sorted(df["enrichment_source_country"].unique().tolist())
    selected_enrichments = st.sidebar.multiselect("Enrichment Source Country", options=enrichment_countries, default=[])
    
    active_enrichments = selected_enrichments if selected_enrichments else enrichment_countries

    months = sorted(df["create_month"].unique().tolist())
    selected_months = st.sidebar.multiselect("Created Month", options=months, default=months)

    mask = (
        df["icp"].isin(selected_icp) 
        & df["create_month"].isin(selected_months) 
        & df["source"].isin(active_sources)
        & df["enrichment_source_country"].isin(active_enrichments)
    )
    df_filt = df[mask].copy()

    # ═══════════════════════════════════════════════════════════════════
    # KPI CARDS
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")

    total_companies    = len(df_filt)
    with_contacts      = int(df_filt["has_valid_contact"].sum())
    without_contacts   = total_companies - with_contacts
    contact_rate       = with_contacts / total_companies * 100 if total_companies else 0
    contacted          = int(df_filt["was_contacted"].sum())
    contacted_rate     = contacted / total_companies * 100 if total_companies else 0
    avg_contacts       = df_filt["valid_contacts_count"].mean()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Companies", f"{total_companies:,}")
    c2.metric("With Valid Contacts", f"{with_contacts:,}")
    c3.metric("Without Contacts", f"{without_contacts:,}")
    c4.metric("Contact Coverage", f"{contact_rate:.1f}%")
    c5.metric("Contacted", f"{contacted:,} ({contacted_rate:.0f}%)")
    c6.metric("Avg Contacts/Company", f"{avg_contacts:.1f}")

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 1 — Contact Coverage Breakdown
    # ═══════════════════════════════════════════════════════════════════
    st.subheader("📊 Contact Coverage")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Companies With vs Without Valid Contacts**")
        fig, ax = plt.subplots(figsize=(5, 4))
        labels = ["With Contacts", "Without Contacts"]
        sizes = [with_contacts, without_contacts]
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct="%1.1f%%",
            startangle=90, textprops={"color": "white", "fontsize": 11},
            wedgeprops={"edgecolor": "#444", "linewidth": 1},
        )
        for t in autotexts:
            t.set_fontweight("bold")
        ax.set_title("Contact Coverage", fontsize=14, pad=12, color="white")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col_right:
        st.markdown("**Contacted vs Not Contacted**")
        fig, ax = plt.subplots(figsize=(5, 4))
        not_contacted = total_companies - contacted
        labels2 = ["Contacted", "Not Contacted"]
        sizes2 = [contacted, not_contacted]
        wedges2, texts2, autotexts2 = ax.pie(
            sizes2, labels=labels2, autopct="%1.1f%%",
            startangle=90, textprops={"color": "white", "fontsize": 11},
            wedgeprops={"edgecolor": "#444", "linewidth": 1},
        )
        for t in autotexts2:
            t.set_fontweight("bold")
        ax.set_title("Outreach Coverage", fontsize=14, pad=12, color="white")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 2 — Valid Contacts Distribution
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📈 Valid Contacts per Company")

    tab_hist, tab_table = st.tabs(["Distribution", "Top Companies"])

    with tab_hist:
        fig, ax = plt.subplots(figsize=(12, 4))
        max_contacts = int(df_filt["valid_contacts_count"].quantile(0.95))
        plot_data = df_filt["valid_contacts_count"].clip(upper=max_contacts + 1)
        sns.histplot(plot_data, bins=range(0, max_contacts + 3),
                     ax=ax, edgecolor="#444")
        ax.set_xlabel("Number of Valid Contacts")
        ax.set_ylabel("Number of Companies")
        ax.set_title("Distribution of Valid Contacts per Company", fontsize=14, pad=12)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with tab_table:
        top = (df_filt[["company_id", "company_name", "enrichment_source_country", "valid_contacts_count", "icp", "was_contacted"]]
               .sort_values("valid_contacts_count", ascending=False)
               .head(20)
               .rename(columns={"company_id": "Company ID"})
               .reset_index(drop=True))
        top.columns = ["Company ID", "Company", "Enrichment Country", "Valid Contacts", "ICP", "Contacted"]
        st.dataframe(top, width="stretch", hide_index=True)

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 3 — ICP Breakdown
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("🎯 Breakdown by Ideal Customer Tier")

    icp_stats = (
        df_filt.groupby("icp")
        .agg(
            Companies=("company_id", "count"),
            With_Contacts=("has_valid_contact", "sum"),
            Contacted=("was_contacted", "sum"),
            Avg_Contacts=("valid_contacts_count", "mean"),
        )
        .reset_index()
    )
    icp_stats["Contact Coverage %"] = (icp_stats["With_Contacts"] / icp_stats["Companies"] * 100).round(1)
    icp_stats["Contacted %"] = (icp_stats["Contacted"] / icp_stats["Companies"] * 100).round(1)
    icp_stats["Avg_Contacts"] = icp_stats["Avg_Contacts"].round(1)
    icp_stats = icp_stats.rename(columns={
        "icp": "Ideal Customer Tier",
        "With_Contacts": "With Contacts",
        "Avg_Contacts": "Avg Contacts",
    })
    icp_stats = icp_stats.sort_values("Companies", ascending=False).reset_index(drop=True)

    col_tbl, col_chart = st.columns([1, 1])

    with col_tbl:
        st.dataframe(icp_stats, width="stretch", hide_index=True)

    with col_chart:
        fig, ax = plt.subplots(figsize=(7, 4))
        x = range(len(icp_stats))
        w = 0.35
        bars1 = ax.bar([i - w/2 for i in x], icp_stats["Contact Coverage %"],
                       width=w, label="Contact Coverage %", edgecolor="#444")
        bars2 = ax.bar([i + w/2 for i in x], icp_stats["Contacted %"],
                       width=w, label="Contacted %", edgecolor="#444")
        ax.set_xticks(list(x))
        ax.set_xticklabels(icp_stats["Ideal Customer Tier"], rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Percentage")
        ax.set_title("Coverage & Contacted Rate by ICP", fontsize=14, pad=12)
        ax.legend(facecolor="#1c1f26", edgecolor="#444")

        for bar in bars1:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.0f}%",
                    ha="center", va="bottom", fontsize=8, color="white")
        for bar in bars2:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.0f}%",
                    ha="center", va="bottom", fontsize=8, color="white")

        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # ═══════════════════════════════════════════════════════════════════

    # SECTION 3.6 — Enrichment Country Breakdown
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📍 Breakdown by Enrichment Source Country")

    enrich_stats = (
        df_filt.groupby("enrichment_source_country")
        .agg(
            Companies=("company_id", "count"),
            With_Contacts=("has_valid_contact", "sum"),
            Contacted=("was_contacted", "sum"),
            Avg_Contacts=("valid_contacts_count", "mean"),
        )
        .reset_index()
    )
    enrich_stats["Contact Coverage %"] = (enrich_stats["With_Contacts"] / enrich_stats["Companies"] * 100).round(1)
    enrich_stats["Contacted %"] = (enrich_stats["Contacted"] / enrich_stats["Companies"] * 100).round(1)
    enrich_stats["Avg_Contacts"] = enrich_stats["Avg_Contacts"].round(1)
    enrich_stats = enrich_stats.rename(columns={
        "enrichment_source_country": "Enrichment Country",
        "With_Contacts": "With Contacts",
        "Avg_Contacts": "Avg Contacts",
    })
    enrich_stats = enrich_stats.sort_values("Companies", ascending=False).reset_index(drop=True)

    col_tbl_enr, col_chart_enr = st.columns([1, 1])

    with col_tbl_enr:
        st.dataframe(enrich_stats, width="stretch", hide_index=True)

    with col_chart_enr:
        fig_enr, ax_enr = plt.subplots(figsize=(7, 4))
        x_enr = range(len(enrich_stats))
        w = 0.35
        bars1_enr = ax_enr.bar([i - w/2 for i in x_enr], enrich_stats["Contact Coverage %"],
                       width=w, label="Contact Coverage %", edgecolor="#444")
        bars2_enr = ax_enr.bar([i + w/2 for i in x_enr], enrich_stats["Contacted %"],
                       width=w, label="Contacted %", edgecolor="#444")
        ax_enr.set_xticks(list(x_enr))
        ax_enr.set_xticklabels(enrich_stats["Enrichment Country"], rotation=30, ha="right", fontsize=9)
        ax_enr.set_ylabel("Percentage")
        ax_enr.set_title("Coverage & Contacted Rate by Enrichment Country", fontsize=14, pad=12)
        ax_enr.legend(facecolor="#1c1f26", edgecolor="#444")

        for bar in bars1_enr:
            h = bar.get_height()
            ax_enr.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.0f}%",
                    ha="center", va="bottom", fontsize=8, color="white")
        for bar in bars2_enr:
            h = bar.get_height()
            ax_enr.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.0f}%",
                    ha="center", va="bottom", fontsize=8, color="white")

        plt.tight_layout()
        st.pyplot(fig_enr)
        plt.close()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 4 — Monthly Trend
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📅 Monthly Trend")

    monthly = (
        df_filt.groupby("create_month")
        .agg(
            Companies=("company_id", "count"),
            With_Contacts=("has_valid_contact", "sum"),
            Contacted=("was_contacted", "sum"),
        )
        .reset_index()
    )
    monthly["Contact Coverage %"] = (monthly["With_Contacts"] / monthly["Companies"] * 100).round(1)
    monthly["Contacted %"] = (monthly["Contacted"] / monthly["Companies"] * 100).round(1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))

    ax1.bar(monthly["create_month"], monthly["Companies"], edgecolor="#444")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Companies Created")
    ax1.set_title("New Companies per Month", fontsize=13, pad=10)
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right")

    ax2.plot(monthly["create_month"], monthly["Contact Coverage %"],
             marker="o", label="Contact Coverage %", linewidth=2)
    ax2.plot(monthly["create_month"], monthly["Contacted %"],
             marker="s", label="Contacted %", linewidth=2)
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Percentage")
    ax2.set_title("Coverage & Contacted Rate Trend", fontsize=13, pad=10)
    ax2.legend(facecolor="#1c1f26", edgecolor="#444")
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 5 — Actionable Lists
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📋 Actionable Lists")

    st.markdown("#### Companies with no valid contacts")
    df_no_contacts = df_filt[~df_filt["has_valid_contact"]].sort_values("createdate", ascending=False)
    if df_no_contacts.empty:
        st.info("All companies have at least one valid contact!")
    else:
        st.dataframe(
            df_no_contacts[["company_id", "company_name", "enrichment_source_country", "icp"]].rename(columns={
                "company_id": "Company ID",
                "company_name": "Company",
                "enrichment_source_country": "Enrichment Country",
                "icp": "Tier"
            }),
            width="stretch",
            hide_index=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### Companies with valid contacts but no 'first_contact'")
    df_no_first_contact = df_filt[df_filt["has_valid_contact"] & ~df_filt["was_contacted"]].sort_values("createdate", ascending=False)
    if df_no_first_contact.empty:
        st.info("All companies with valid contacts have been contacted!")
    else:
        st.dataframe(
            df_no_first_contact[["company_id", "company_name", "enrichment_source_country", "valid_contacts_count", "icp"]].rename(columns={
                "company_id": "Company ID",
                "company_name": "Company",
                "enrichment_source_country": "Enrichment Country",
                "valid_contacts_count": "Contacts",
                "icp": "Tier"
            }),
            width="stretch",
            hide_index=True
        )

    st.markdown(
        "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:2rem;'>"
        "Data: HubSpot Companies & Contacts · BigQuery · AltScore</div>",
        unsafe_allow_html=True,
    )
