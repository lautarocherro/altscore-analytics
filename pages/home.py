"""Home / Landing page — shown by default after login."""

import streamlit as st
from app_settings import is_page_enabled

st.markdown("## 📊 AltScore Analytics")
st.caption("Internal dashboards — select a page from the sidebar")

# Build list of enabled pages
enabled = []
if is_page_enabled("deal_amounts"):
    enabled.append(("💼", "Deal Amounts", "Distribution analysis & High/Low Ticket clustering",
                     "pages/1_💼_Deal_Amounts.py"))
if is_page_enabled("stage_funnel"):
    enabled.append(("🔀", "Stage Funnel", "Conversion rates & time between pipeline stages",
                     "pages/2_🔀_Stage_Funnel.py"))
if is_page_enabled("company_contacts"):
    enabled.append(("🏢", "Company Contacts", "Contact coverage, reachability & ICP breakdown",
                     "pages/3_🏢_Company_Contacts.py"))
if is_page_enabled("budget_metrics"):
    enabled.append(("📈", "Budget Metrics", "Top-of-funnel reach & deeper funnel conversions",
                     "pages/4_📈_Budget_Metrics.py"))

if not enabled:
    st.info("No pages are currently enabled. Update `app_config.toml` to activate pages.")
else:
    # Center cards dynamically based on how many are enabled
    cols = st.columns(len(enabled))
    for col, (icon, title, desc, path) in zip(cols, enabled):
        with col:
            st.markdown(f"### {icon} {title}")
            st.write(desc)
            st.page_link(path, label="Open →", icon=icon)

st.markdown(
    "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:3rem;'>"
    "Data: HubSpot · BigQuery · AltScore</div>",
    unsafe_allow_html=True,
)
