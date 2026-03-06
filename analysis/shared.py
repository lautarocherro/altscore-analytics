"""
Shared credentials + BigQuery client utilities for analysis dashboards.
Works both locally (file) and in Cloud Run (env var / Secret Manager).
"""

import json
import os
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "modeling-449120"

# ── Resolve service-account credentials ──────────────────────────────────────
# Priority:
#   1. GCP_SA_JSON env-var  (Cloud Run / Docker — raw JSON string)
#   2. Local file            (development)
_LOCAL_CREDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "credentials", "service_account.json",
)


@st.cache_resource(show_spinner=False)
def _get_credentials() -> service_account.Credentials:
    sa_json = os.environ.get("GCP_SA_JSON")
    if sa_json:
        info = json.loads(sa_json)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    if os.path.isfile(_LOCAL_CREDS_PATH):
        return service_account.Credentials.from_service_account_file(
            _LOCAL_CREDS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    raise FileNotFoundError(
        "No service-account credentials found. "
        "Set GCP_SA_JSON env var or place credentials/service_account.json"
    )


@st.cache_resource(show_spinner=False)
def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID, credentials=_get_credentials())
