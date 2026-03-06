"""
AltScore Analytics — Multipage Streamlit Application
Entrypoint with password authentication.
"""

import streamlit as st

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

# ── Landing page ──────────────────────────────────────────────────────────────
st.markdown("## 📊 AltScore Analytics")
st.caption("Internal dashboards — select a page from the sidebar")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 💼 Deal Amounts")
    st.write("Distribution analysis & High/Low Ticket clustering")

with col2:
    st.markdown("### 🔀 Stage Funnel")
    st.write("Conversion rates & time between pipeline stages")

with col3:
    st.markdown("### 🏢 Company Contacts")
    st.write("Contact coverage, reachability & ICP breakdown")

# Sidebar sign out
if st.sidebar.button("🚪 Sign out"):
    st.session_state["authenticated"] = False
    st.rerun()

st.markdown(
    "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:3rem;'>"
    "Data: HubSpot · BigQuery · AltScore</div>",
    unsafe_allow_html=True,
)
