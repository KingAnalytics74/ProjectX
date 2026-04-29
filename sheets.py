"""
Google Sheets persistence layer — drop-in replacement for CSV storage.

─── SETUP (one-time) ────────────────────────────────────────────────────────

Step 1 — Enable the API
  - Go to https://console.cloud.google.com
  - Create a project (or select existing)
  - Search "Google Sheets API" → Enable it
  - Search "Google Drive API" → Enable it

Step 2 — Create a Service Account
  - IAM & Admin → Service Accounts → Create Service Account
  - Give it any name (e.g. "safety-tool")
  - Click the account → Keys → Add Key → JSON → download the file

Step 3 — Create the Google Sheet
  - Create a new Google Sheet named "Safety Intelligence"
  - Rename the first tab (bottom) to: risk_assessments
  - Share the sheet with the service account email (Editor access)
    (the email looks like: safety-tool@your-project.iam.gserviceaccount.com)

Step 4 — Add secrets to Streamlit Cloud
  Go to your app → Settings → Secrets and paste:

    [gcp_service_account]
    type = "service_account"
    project_id = "your-project-id"
    private_key_id = "xxx"
    private_key = "-----BEGIN RSA PRIVATE KEY-----\\nxxx\\n-----END RSA PRIVATE KEY-----\\n"
    client_email = "safety-tool@your-project.iam.gserviceaccount.com"
    client_id = "xxx"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "xxx"

    [google_sheets]
    sheet_id = "the-long-id-from-your-sheet-url"

    The sheet_id is in the URL:
    https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit

─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

import data_manager as _csv

SHEET_TAB  = "risk_assessments"
SCOPES     = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _use_sheets() -> bool:
    try:
        st.secrets["gcp_service_account"]
        st.secrets["google_sheets"]["sheet_id"]
        return True
    except Exception:
        return False


@st.cache_resource
def _client() -> gspread.Client:
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _worksheet() -> gspread.Worksheet:
    sheet_id = st.secrets["google_sheets"]["sheet_id"]
    return _client().open_by_key(sheet_id).worksheet(SHEET_TAB)


def _ensure_headers(ws: gspread.Worksheet) -> None:
    if not ws.row_values(1):
        ws.append_row(_csv.COLUMNS, value_input_option="USER_ENTERED")


def load_data() -> pd.DataFrame:
    if not _use_sheets():
        return _csv.load_data()
    ws = _worksheet()
    _ensure_headers(ws)
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=_csv.COLUMNS)
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    return df


def save_entry(entry: dict) -> pd.DataFrame:
    if not _use_sheets():
        return _csv.save_entry(entry)
    ws = _worksheet()
    _ensure_headers(ws)
    df = load_data()
    entry = entry.copy()
    entry["id"] = int(df["id"].max()) + 1 if not df.empty else 1
    entry["date"] = datetime.now().strftime("%Y-%m-%d")
    level, _ = _csv.classify_risk(entry["risk_score"])
    entry["risk_level"] = level
    res_level, _ = _csv.classify_risk(entry["residual_risk_score"])
    entry["residual_risk_level"] = res_level
    ws.append_row(
        [str(entry.get(col, "")) for col in _csv.COLUMNS],
        value_input_option="USER_ENTERED",
    )
    return load_data()


def delete_entry(entry_id: int) -> pd.DataFrame:
    if not _use_sheets():
        return _csv.delete_entry(entry_id)
    ws = _worksheet()
    cell = ws.find(str(entry_id), in_column=1)
    if cell:
        ws.delete_rows(cell.row)
    return load_data()


def update_status(entry_id: int, new_status: str) -> pd.DataFrame:
    if not _use_sheets():
        return _csv.update_status(entry_id, new_status)
    ws = _worksheet()
    cell = ws.find(str(entry_id), in_column=1)
    if cell:
        status_col = _csv.COLUMNS.index("status") + 1
        ws.update_cell(cell.row, status_col, new_status)
    return load_data()
