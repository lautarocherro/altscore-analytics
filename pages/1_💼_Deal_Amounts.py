"""Page wrapper — Deal Amounts analysis"""
import sys, os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Auth gate — redirect unauthenticated users
if not st.session_state.get("authenticated"):
    st.warning("🔒 Please sign in from the home page")
    st.stop()

import analysis.altdecision_deals  # noqa: F401, E402
