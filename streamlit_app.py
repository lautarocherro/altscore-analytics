"""
AltScore Analytics — Multipage Streamlit Application
Entrypoint with password authentication and programmatic page routing.
"""

import streamlit as st
from app_settings import is_page_enabled

st.set_page_config(
    page_title="AltScore Analytics",
    page_icon="📊",
    layout="wide",
)

# ── Password gate ─────────────────────────────────────────────────────────────
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "Altscore2026")


def check_password() -> bool:
    """Returns True if the user entered the correct password."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown("## 📊 AltScore Analytics")
    st.caption("Enter the team password to continue")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        password = st.text_input("🔑 Password", type="password", key="pw_input")
        if st.button("Sign in", type="primary", use_container_width=True):
            if password == APP_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    return False


if not check_password():
    st.stop()

# ── Build page list (only enabled pages show in sidebar) ──────────────────────
pages = [
    st.Page("pages/home.py", title="Home", icon="📊", default=True),
]

if is_page_enabled("deal_amounts"):
    pages.append(st.Page("pages/1_💼_Deal_Amounts.py", title="Deal Amounts", icon="💼"))
if is_page_enabled("stage_funnel"):
    pages.append(st.Page("pages/2_🔀_Stage_Funnel.py", title="Stage Funnel", icon="🔀"))
if is_page_enabled("company_contacts"):
    pages.append(st.Page("pages/3_🏢_Company_Contacts.py", title="Company Contacts", icon="🏢"))
if is_page_enabled("budget_metrics"):
    pages.append(st.Page("pages/4_📈_Budget_Metrics.py", title="Budget Metrics", icon="📈"))
if is_page_enabled("budget_waterfall"):
    pages.append(st.Page("pages/5_🌊_Budget_Waterfall.py", title="Budget Waterfall", icon="🌊"))

pg = st.navigation(pages)

# Sidebar sign out
if st.sidebar.button("🚪 Sign out"):
    st.session_state["authenticated"] = False
    st.rerun()

pg.run()
