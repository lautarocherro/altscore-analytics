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

# ── Brand colors ──────────────────────────────────────────────────────────────
GOLD = "#F3B229"
NAVY = "#103F79"

# ── Password gate ─────────────────────────────────────────────────────────────
# Password is stored in .streamlit/secrets.toml (local) or env var (Cloud Run)
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "Altscore2026")


def check_password() -> bool:
    """Returns True if the user entered the correct password."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        f"""
        <style>
        .login-box {{ text-align: center; padding: 4rem 2rem; }}
        .login-box h1 {{ font-size: 3rem; font-weight: 800; color: {GOLD}; }}
        .login-box p  {{ color: #aaa; font-size: 1.1rem; margin: 1rem 0 2rem; }}
        </style>
        <div class="login-box">
            <h1>📊 AltScore Analytics</h1>
            <p>Enter the team password to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
st.markdown(
    f"""
    <style>
    .landing {{ padding: 4rem 0; text-align: center; }}
    .landing h1 {{ font-size: 3rem; font-weight: 800;
               background: linear-gradient(90deg, {NAVY}, {GOLD});
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .landing p  {{ color: #aaa; font-size: 1.15rem; margin-top: .5rem; }}
    .card {{ background: #1c1f26; border-radius: 14px; padding: 2rem;
            border: 1px solid {NAVY}55; text-align: center; margin-top: 1rem; }}
    .card h3 {{ color: {GOLD}; margin-bottom: .5rem; }}
    .card p  {{ color: #999; font-size: .95rem; }}
    </style>
    <div class="landing">
        <h1>📊 AltScore Analytics</h1>
        <p>Internal dashboards — select a page from the sidebar</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        '<div class="card"><h3>💼 Deal Amounts</h3>'
        '<p>Distribution analysis &amp; High/Low Ticket clustering</p></div>',
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        '<div class="card"><h3>🔀 Stage Funnel</h3>'
        '<p>Conversion rates &amp; time between pipeline stages</p></div>',
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        '<div class="card"><h3>🏢 Company Contacts</h3>'
        '<p>Contact coverage, reachability &amp; ICP breakdown</p></div>',
        unsafe_allow_html=True,
    )

# Sidebar sign out
if st.sidebar.button("🚪 Sign out"):
    st.session_state["authenticated"] = False
    st.rerun()

st.markdown(
    "<div style='text-align:center;color:#555;font-size:.8rem;margin-top:3rem;'>"
    "Data: HubSpot · BigQuery · AltScore</div>",
    unsafe_allow_html=True,
)
