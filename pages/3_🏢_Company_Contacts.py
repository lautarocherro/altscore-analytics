"""Page wrapper — Company Contacts analysis"""
import sys, os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_settings import is_page_enabled

if not is_page_enabled("company_contacts"):
    st.info("This page is currently disabled.")
    st.stop()

if not st.session_state.get("authenticated"):
    st.warning("🔒 Please sign in from the home page")
    st.stop()

from analysis.company_contacts import main
main()
