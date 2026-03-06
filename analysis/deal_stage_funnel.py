"""
AltDecision — Deal Stage Funnel Analysis
Streamlit dashboard: days between stages, time in stage, and conversion rates
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import seaborn as sns
import streamlit as st
from analysis.shared import get_bq_client

# ── Page config (no-op when running inside multipage app) ─────────────────────
try:
    st.set_page_config(
        page_title="AltDecision · Stage Funnel",
        page_icon="🔀",
        layout="wide",
    )
except st.errors.StreamlitAPIException:
    pass

# ── Global style ──────────────────────────────────────────────────────────────
GOLD = "#F3B229"
NAVY = "#103F79"
ACCENT_1 = NAVY
ACCENT_2 = GOLD
ACCENT_3 = "#5B9BD5"   # lighter blue
ACCENT_4 = "#D4A028"   # darker gold
ACCENT_5 = "#1A5FAF"   # medium blue

STAGE_PALETTE = [
    "#103F79", "#1A5FAF", "#3A7FD5", "#5B9BD5",
    "#F3B229", "#D4A028", "#B88B1F", "#8B6A15",
]

sns.set_theme(style="darkgrid", palette="muted", font_scale=1.1)
plt.rcParams.update({
    "figure.facecolor": "#0e1117", "axes.facecolor": "#262730",
    "text.color": "white", "axes.labelcolor": "white",
    "xtick.color": "white", "ytick.color": "white",
    "axes.edgecolor": "#444", "grid.color": "#333",
})

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .hero { padding: 2rem 0 1rem; text-align: center; }
    .hero h1 { font-size: 2.6rem; font-weight: 800;
               background: linear-gradient(90deg, #103F79, #F3B229);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p  { color: #aaa; font-size: 1.05rem; margin-top: .3rem; }
    .stat-box { background: #1c1f26; border-radius: 12px; padding: 1.2rem 1.6rem;
                border: 1px solid #103F7955; text-align: center; }
    .stat-val  { font-size: 2rem; font-weight: 700; color: #F3B229; }
    .stat-lbl  { font-size: .85rem; color: #888; margin-top: .2rem; }
    </style>
    <div class="hero">
        <h1>🔀 AltDecision · Stage Funnel Analysis</h1>
        <p>Conversion rates &amp; time between pipeline stages — <strong>New Business</strong> deals from <strong>Positive Response</strong></p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Pipeline definition ──────────────────────────────────────────────────────
# Ordered stages with their numeric_final_dealstage value
STAGES = [
    ("Positive Response", 1),
    ("Discovery Call",    2),
    ("Demo",              3),
    ("Proposal",          4),
    ("Negotiation",       5),
    ("Legal Documents",   6),
    ("Delivery",          7),
    ("Closed Won",        8),
]

# Actual prefixed names used in final_dealstage column
CLOSED_WON_LABEL = "H: Closed Won"
STAGE_NAMES = [s[0] for s in STAGES]
STAGE_NUMS  = {name: num for name, num in STAGES}

# Transition columns mapping
TRANSITION_COLS = [
    ("Positive Response → Discovery Call", "days_from_positive_response_to_discovery_call"),
    ("Discovery Call → Demo",             "days_from_discovery_call_to_demo"),
    ("Demo → Proposal",                   "days_from_demo_to_proposal"),
    ("Proposal → Negotiation",            "days_from_proposal_to_negotiation"),
    ("Negotiation → Legal Docs",          "days_from_negotiation_to_legal_documents"),
    ("Legal Docs → Delivery",             "days_from_legal_documents_to_delivery"),
    ("Delivery → Closed Won",             "days_from_delivery_to_closed_won"),
]

DAYS_IN_COLS = [
    ("Positive Response", "days_from_positive_response_to_discovery_call"),
    ("Discovery Call",    "days_from_discovery_call_to_demo"),
    ("Demo",              "days_in_demo"),
    ("Proposal",          "days_in_proposal"),
    ("Negotiation",       "days_in_negotiation"),
    ("Legal Documents",   "days_in_legal_documents"),
    ("Delivery",          "days_in_delivery"),
    ("Closed Won",        "days_in_closed_won"),
    ("Closed Lost",       "days_in_closed_lost"),
]

# ── BigQuery query ────────────────────────────────────────────────────────────
QUERY = """
SELECT
    numeric_final_dealstage,
    final_dealstage,
    house,
    days_in_demo,
    days_in_proposal,
    days_in_negotiation,
    days_in_legal_documents,
    days_in_delivery,
    days_in_closed_won,
    days_in_closed_lost,
    days_from_positive_response_to_discovery_call,
    days_from_discovery_call_to_demo,
    days_from_demo_to_proposal,
    days_from_proposal_to_negotiation,
    days_from_negotiation_to_legal_documents,
    days_from_legal_documents_to_delivery,
    days_from_delivery_to_closed_won,
    days_from_demo_to_closed_won,
    days_open,
    days_deal_open,
    amount
FROM `modeling-449120.internal_metrics.HUBSPOT_DEALS`
WHERE date_entered_positive_response IS NOT NULL
  AND date_entered_positive_response BETWEEN '2025-10-01' AND '2026-12-31'
  AND dealtype = 'New Business'
  AND house   = 'AltDecision'
"""


@st.cache_data(show_spinner="Querying BigQuery…", ttl=600)
def load_data() -> pd.DataFrame:
    client = get_bq_client()
    raw = client.query(QUERY).to_dataframe()

    # Cap unreasonable day values (bad data: some values > 1e9)
    MAX_DAYS = 730  # 2 years
    day_cols = [c for c in raw.columns if c.startswith("days")]
    for c in day_cols:
        raw[c] = raw[c].where(raw[c] <= MAX_DAYS)
    return raw


df = load_data()

# ── Sidebar filters ──────────────────────────────────────────────────────────
st.sidebar.header("🎛  Filters")
all_final_stages = sorted(df["final_dealstage"].dropna().unique().tolist())
selected_stages = st.sidebar.multiselect(
    "Final deal stage",
    options=all_final_stages,
    default=all_final_stages,
)
mask = df["final_dealstage"].isin(selected_stages)
df_filt = df[mask].copy()

# ═══════════════════════════════════════════════════════════════════════
# KPI CARDS
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")

total_deals = len(df_filt)
won_deals   = int(df_filt["final_dealstage"].str.contains("Closed Won", na=False).sum())
lost_deals  = int(df_filt["final_dealstage"].str.contains("Closed Lost", na=False).sum())
closed_deals = won_deals + lost_deals
win_rate    = won_deals / closed_deals * 100 if closed_deals else 0

# days_deal_open has bad data; compute from days_in_* sum as fallback
days_cols_for_total = [c for c in df_filt.columns if c.startswith("days_in_")]
df_filt["_total_days"] = df_filt[days_cols_for_total].sum(axis=1, min_count=1)
avg_days = df_filt["_total_days"].mean()
med_days = df_filt["_total_days"].median()

c1, c2, c3, c4, c5 = st.columns(5)


def kpi(col, val, lbl):
    col.markdown(
        f'<div class="stat-box"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True,
    )


kpi(c1, f"{total_deals:,}",        "Total Deals")
kpi(c2, f"{won_deals:,}",          "Closed Won")
kpi(c3, f"{win_rate:.1f}%",        "Win Rate (Won/Closed)")
kpi(c4, f"{avg_days:,.0f}" if pd.notna(avg_days) else "–",  "Avg Days in Pipeline")
kpi(c5, f"{med_days:,.0f}" if pd.notna(med_days) else "–",  "Median Days in Pipeline")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1 — Funnel: Conversion Rates
# ═══════════════════════════════════════════════════════════════════════
st.subheader("📊 Stage Funnel — Conversion Rates")

# Count deals that *reached* each stage (final_dealstage >= stage number)
funnel_counts = []
for name, num in STAGES:
    reached = int((df_filt["numeric_final_dealstage"] >= num).sum())
    funnel_counts.append({"Stage": name, "Reached": reached})

funnel_df = pd.DataFrame(funnel_counts)
funnel_df["Conversion %"] = (
    funnel_df["Reached"] / funnel_df["Reached"].iloc[0] * 100
).round(1)
funnel_df["Stage→Stage %"] = 100.0
for i in range(1, len(funnel_df)):
    prev = funnel_df.loc[i - 1, "Reached"]
    curr = funnel_df.loc[i, "Reached"]
    funnel_df.loc[i, "Stage→Stage %"] = round(curr / prev * 100, 1) if prev else 0

# ── Funnel bar chart ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.barh(
    funnel_df["Stage"][::-1],
    funnel_df["Reached"][::-1],
    color=STAGE_PALETTE[:len(funnel_df)][::-1],
    edgecolor="#444",
    height=0.6,
)

for bar, (_, row) in zip(bars, funnel_df[::-1].iterrows()):
    width = bar.get_width()
    ax.text(
        width + total_deals * 0.02, bar.get_y() + bar.get_height() / 2,
        f'{int(row["Reached"]):,}  ({row["Conversion %"]:.0f}%)',
        va="center", fontsize=11, color="white", fontweight="bold",
    )

ax.set_xlabel("Number of Deals")
ax.set_title("Deals Reaching Each Stage (cumulative funnel)", fontsize=14, pad=12)
ax.set_xlim(0, total_deals * 1.35)
plt.tight_layout()
st.pyplot(fig)
plt.close()

# ── Stage-to-stage conversion table ──────────────────────────────────
st.markdown("**Stage-to-Stage Conversion Rates**")
conv_rows = []
for i in range(1, len(funnel_df)):
    prev_name = funnel_df.loc[i - 1, "Stage"]
    curr_name = funnel_df.loc[i, "Stage"]
    prev_count = funnel_df.loc[i - 1, "Reached"]
    curr_count = funnel_df.loc[i, "Reached"]
    drop = prev_count - curr_count
    conv_rows.append({
        "Transition": f"{prev_name} → {curr_name}",
        "Entered": prev_count,
        "Progressed": curr_count,
        "Dropped": drop,
        "Conversion %": f'{funnel_df.loc[i, "Stage→Stage %"]:.1f}%',
        "Drop %": f'{(drop / prev_count * 100):.1f}%' if prev_count else "–",
    })
st.dataframe(pd.DataFrame(conv_rows), width="stretch", hide_index=True)

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2 — Days Between Stages (Transition Times)
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("⏱  Days Between Stages (Transition Times)")

tab_box, tab_table = st.tabs(["Box Plots", "Summary Table"])

# Prepare transition data (melt into long format)
trans_data = []
for label, col in TRANSITION_COLS:
    valid = df_filt[col].dropna()
    if not valid.empty:
        temp = valid.to_frame("days").copy()
        temp["Transition"] = label
        trans_data.append(temp)

if trans_data:
    trans_long = pd.concat(trans_data, ignore_index=True)
    # Keep order
    trans_order = [t[0] for t in TRANSITION_COLS if t[0] in trans_long["Transition"].values]

    with tab_box:
        fig, ax = plt.subplots(figsize=(14, 6))
        sns.boxplot(
            data=trans_long, y="Transition", x="days",
            order=trans_order,
            palette=STAGE_PALETTE[:len(trans_order)],
            width=0.5, ax=ax, fliersize=3,
        )
        ax.set_xlabel("Days")
        ax.set_ylabel("")
        ax.set_title("Distribution of Days Between Consecutive Stages", fontsize=14, pad=12)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with tab_table:
        summary_rows = []
        for label, col in TRANSITION_COLS:
            valid = df_filt[col].dropna()
            if valid.empty:
                continue
            summary_rows.append({
                "Transition": label,
                "N": int(len(valid)),
                "Mean": f"{valid.mean():.1f}",
                "Median": f"{valid.median():.1f}",
                "P25": f"{valid.quantile(0.25):.1f}",
                "P75": f"{valid.quantile(0.75):.1f}",
                "Min": f"{valid.min():.1f}",
                "Max": f"{valid.max():.1f}",
            })
        st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)
else:
    st.info("No transition data available for the current filters.")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 3 — Days In Stage
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🏠 Days Spent In Each Stage")

tab_violin, tab_tbl2 = st.tabs(["Violin Plots", "Summary Table"])

stage_data = []
for label, col in DAYS_IN_COLS:
    valid = df_filt[col].dropna()
    if not valid.empty:
        temp = valid.to_frame("days").copy()
        temp["Stage"] = label
        stage_data.append(temp)

if stage_data:
    stage_long = pd.concat(stage_data, ignore_index=True)
    stage_order = [s[0] for s in DAYS_IN_COLS if s[0] in stage_long["Stage"].values]

    with tab_violin:
        fig, ax = plt.subplots(figsize=(14, 6))
        sns.violinplot(
            data=stage_long, y="Stage", x="days",
            order=stage_order,
            palette=STAGE_PALETTE[:len(stage_order)],
            inner="box", ax=ax, cut=0, density_norm="width",
        )
        ax.set_xlabel("Days")
        ax.set_ylabel("")
        ax.set_title("Distribution of Days Spent In Each Stage", fontsize=14, pad=12)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with tab_tbl2:
        summary_rows2 = []
        for label, col in DAYS_IN_COLS:
            valid = df_filt[col].dropna()
            if valid.empty:
                continue
            summary_rows2.append({
                "Stage": label,
                "N": int(len(valid)),
                "Mean": f"{valid.mean():.1f}",
                "Median": f"{valid.median():.1f}",
                "P25": f"{valid.quantile(0.25):.1f}",
                "P75": f"{valid.quantile(0.75):.1f}",
                "Min": f"{valid.min():.1f}",
                "Max": f"{valid.max():.1f}",
            })
        st.dataframe(pd.DataFrame(summary_rows2), width="stretch", hide_index=True)
else:
    st.info("No days-in-stage data available for the current filters.")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 4 — Cumulative Timeline: Positive Response → Closed Won
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🏁 Total Journey: Positive Response → Closed Won")

# Sum all transition columns for deals that reached Closed Won
transition_cols_for_total = [col for _, col in TRANSITION_COLS]
won_mask = df_filt["final_dealstage"].str.contains("Closed Won", na=False)
df_won = df_filt.loc[won_mask, transition_cols_for_total].copy()
df_won["total_days"] = df_won.sum(axis=1, min_count=1)
pr_to_won = df_won["total_days"].dropna()

if not pr_to_won.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Distribution (Histogram + KDE)**")
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.histplot(pr_to_won, bins=25, kde=True, color=ACCENT_3, ax=ax)
        ax.axvline(pr_to_won.median(), color=ACCENT_2, ls="--", lw=2,
                   label=f"Median = {pr_to_won.median():.0f} days")
        ax.set_xlabel("Days from Positive Response to Closed Won")
        ax.set_ylabel("Count")
        ax.legend(facecolor="#1c1f26", edgecolor="#444")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col_right:
        st.markdown("**Cumulative Distribution (ECDF)**")
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.ecdfplot(pr_to_won, color=ACCENT_4, ax=ax)
        ax.axvline(pr_to_won.median(), color=ACCENT_2, ls="--", lw=1.5,
                   label=f"Median = {pr_to_won.median():.0f} days")
        ax.axhline(0.5, color="#555", ls=":", lw=1)
        ax.set_xlabel("Days from Positive Response to Closed Won")
        ax.set_ylabel("Proportion of Deals")
        ax.legend(facecolor="#1c1f26", edgecolor="#444")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Quick stats
    st.markdown("**Key Stats**")
    qs1, qs2, qs3, qs4 = st.columns(4)
    kpi(qs1, f"{pr_to_won.mean():.0f}", "Mean Days")
    kpi(qs2, f"{pr_to_won.median():.0f}", "Median Days")
    kpi(qs3, f"{pr_to_won.quantile(0.25):.0f}", "P25 (fast deals)")
    kpi(qs4, f"{pr_to_won.quantile(0.75):.0f}", "P75 (slow deals)")
else:
    st.info("No Positive Response → Closed Won data available for the current filters.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:2rem;'>"
    "Data: HubSpot Deals · BigQuery · AltScore</div>",
    unsafe_allow_html=True,
)
