"""
AltDecision — 2026 New Business Deal Amounts
Streamlit dashboard: distribution analysis + High / Low Ticket clustering
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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ── Page config (no-op when running inside multipage app) ─────────────────────
try:
    st.set_page_config(
        page_title="AltDecision Deals · 2026",
        page_icon="💼",
        layout="wide",
    )
except st.errors.StreamlitAPIException:
    pass

# ── Global style ──────────────────────────────────────────────────────────────
GOLD = "#F3B229"
NAVY = "#103F79"
COLORS = {"Low Ticket": NAVY, "High Ticket": GOLD}

sns.set_theme(style="darkgrid", palette="muted", font_scale=1.1)
plt.rcParams.update({"figure.facecolor": "#0e1117", "axes.facecolor": "#262730",
                     "text.color": "white", "axes.labelcolor": "white",
                     "xtick.color": "white", "ytick.color": "white",
                     "axes.edgecolor": "#444", "grid.color": "#333"})

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
        <h1>💼 AltDecision · Deal Amount Analysis</h1>
        <p>New Business deals that entered demo from <strong>October 2025 to December 2026</strong></p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── BigQuery query ─────────────────────────────────────────────────────────────
QUERY = """
SELECT amount
FROM `modeling-449120.internal_metrics.HUBSPOT_DEALS`
WHERE date_entered_demo IS NOT NULL
  AND date_entered_demo BETWEEN '2025-10-01' AND '2026-12-31'
  AND dealtype = 'New Business'
  AND house   = 'AltDecision'
  AND amount  > 0
"""


@st.cache_data(show_spinner="Querying BigQuery…", ttl=600)
def load_data() -> pd.DataFrame:
    client = get_bq_client()
    df = client.query(QUERY).to_dataframe()
    df["log_amount"] = np.log10(df["amount"])
    return df


df = load_data()

# ── KMeans ────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cluster(data: pd.DataFrame):
    X = data[["log_amount"]].values
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    km = KMeans(n_clusters=2, random_state=42, n_init="auto")
    labels = km.fit_predict(X_sc)

    centers = km.cluster_centers_
    high_id = int(np.argmax(centers))

    seg = pd.Series(labels, index=data.index).map(
        {high_id: "High Ticket", 1 - high_id: "Low Ticket"}
    )

    boundary_log = float(
        scaler.inverse_transform(
            [[(centers[0, 0] + centers[1, 0]) / 2]]
        )[0, 0]
    )
    boundary_usd = 10 ** boundary_log
    return seg, boundary_usd


df["segment"], boundary_usd = cluster(df)

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)

def kpi(col, val, lbl):
    col.markdown(
        f'<div class="stat-box"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True,
    )

kpi(c1, f"{len(df):,}", "Total Deals")
kpi(c2, f"${df['amount'].mean():,.0f}", "Mean Amount")
kpi(c3, f"${df['amount'].median():,.0f}", "Median Amount")
kpi(c4, f"${df['amount'].max():,.0f}", "Max Amount")
kpi(c5, f"${boundary_usd:,.0f}", "Cluster Boundary")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1 — Distribution plots
# ═══════════════════════════════════════════════════════════════════════
st.subheader("📊 Amount Distribution")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Histogram + KDE", "Box Plot", "ECDF", "Log-scale Histogram"]
)

def fmt_usd(x, _):
    return f"${x:,.0f}"

# ── Tab 1: Histogram + KDE ────────────────────────────────────────────
with tab1:
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.histplot(df["amount"], bins=30, kde=True, color=COLORS["Low Ticket"], ax=ax)
    ax.set_xlabel("Amount (USD)")
    ax.set_ylabel("Count")
    ax.set_title("Deal Amount — Histogram & KDE")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    plt.xticks(rotation=25)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ── Tab 2: Box plot ───────────────────────────────────────────────────
with tab2:
    fig, ax = plt.subplots(figsize=(5, 3))
    sns.boxplot(y=df["amount"], color="#A8D8A8", ax=ax, width=0.4)
    ax.set_ylabel("Amount (USD)")
    ax.set_title("Deal Amount — Box Plot")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ── Tab 3: ECDF ───────────────────────────────────────────────────────
with tab3:
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.ecdfplot(df["amount"], color=COLORS["High Ticket"], ax=ax)
    ax.set_xlabel("Amount (USD)")
    ax.set_ylabel("Proportion")
    ax.set_title("Cumulative Distribution (ECDF)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    plt.xticks(rotation=25)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ── Tab 4: Log histogram ──────────────────────────────────────────────
with tab4:
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.histplot(df["log_amount"], bins=30, kde=True, color="#9B7FC8", ax=ax)
    ax.set_xlabel("log₁₀(Amount)")
    ax.set_ylabel("Count")
    ax.set_title("Log₁₀-Scale Histogram + KDE")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2 — Clustering
# ═══════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("🎯 High Ticket vs Low Ticket — K-Means (k = 2)")

col_left, col_right = st.columns(2)

# ── Left: KDE per segment ─────────────────────────────────────────────
with col_left:
    st.markdown("**KDE by Segment (log₁₀ scale)**")
    fig, ax = plt.subplots(figsize=(7, 4))
    for seg, color in COLORS.items():
        sub = df.loc[df["segment"] == seg, "log_amount"]
        sns.kdeplot(sub, ax=ax, label=f"{seg} (n={len(sub):,})",
                    fill=True, alpha=0.4, color=color)
    ax.axvline(np.log10(boundary_usd), color="white", ls="--", lw=1.5,
               label=f"Boundary ≈ ${boundary_usd:,.0f}")
    ax.set_xlabel("log₁₀(Amount)")
    ax.legend(facecolor="#1c1f26", edgecolor="#444")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ── Right: Box per segment ────────────────────────────────────────────
with col_right:
    st.markdown("**Box Plot by Segment (USD)**")
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=df, x="segment", y="amount",
                order=["Low Ticket", "High Ticket"],
                palette=COLORS, width=0.45, ax=ax)
    ax.set_xlabel("")
    ax.set_ylabel("Amount (USD)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ── Strip plot ────────────────────────────────────────────────────────
st.markdown("**Individual Deals — Strip Plot**")
fig, ax = plt.subplots(figsize=(12, 3))
sns.stripplot(data=df.sort_values("amount"),
              x="amount", y="segment",
              order=["Low Ticket", "High Ticket"],
              hue="segment", palette=COLORS,
              size=5, alpha=0.7, jitter=True, ax=ax, legend=False)
ax.axvline(boundary_usd, color="white", ls="--", lw=1.5,
           label=f"Boundary ≈ ${boundary_usd:,.0f}")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_usd))
ax.set_xlabel("Amount (USD)")
ax.set_ylabel("")
ax.legend(facecolor="#1c1f26", edgecolor="#444")
plt.xticks(rotation=25)
plt.tight_layout()
st.pyplot(fig)
plt.close()

# ── Segment summary table ─────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Segment Summary")

summary = (
    df.groupby("segment")["amount"]
    .agg(
        Deals="count",
        Mean="mean",
        Median="median",
        Min="min",
        Max="max",
        Std="std",
    )
    .round(2)
    .reindex(["Low Ticket", "High Ticket"])
    .reset_index()
    .rename(columns={"segment": "Segment"})
)
for col in ["Mean", "Median", "Min", "Max", "Std"]:
    summary[col] = summary[col].apply(lambda v: f"${v:,.0f}")

st.dataframe(summary, use_container_width=True, hide_index=True)

# ── Elbow curve ───────────────────────────────────────────────────────
with st.expander("🔍 Elbow Curve — validate K = 2"):
    from sklearn.preprocessing import StandardScaler as _SS
    X = df[["log_amount"]].values
    X_sc = _SS().fit_transform(X)
    inertias = []
    K_range = range(1, min(9, len(df)))
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        km.fit(X_sc)
        inertias.append(km.inertia_)

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(list(K_range), inertias, marker="o", color=COLORS["Low Ticket"])
    ax.axvline(2, color=COLORS["High Ticket"], ls="--", label="K = 2 (chosen)")
    ax.set_xlabel("Number of Clusters (K)")
    ax.set_ylabel("Inertia")
    ax.set_title("Elbow Curve — K-Means on log₁₀(Amount)")
    ax.legend(facecolor="#1c1f26", edgecolor="#444")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:2rem;'>"
    "Data: HubSpot Deals · BigQuery · AltScore</div>",
    unsafe_allow_html=True,
)
