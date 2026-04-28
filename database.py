"""
Supabase persistence layer — drop-in replacement for CSV storage in data_manager.py.

─── SETUP (one-time) ────────────────────────────────────────────────────────

1. Create a free project at https://supabase.com

2. Open the SQL Editor in Supabase and run:

    create table risk_assessments (
        id            bigserial primary key,
        date          date,
        assessor      text,
        department    text,
        location      text,
        hazard_category    text,
        hazard_description text,
        activity      text,
        likelihood    int,
        severity      int,
        risk_score    int,
        risk_level    text,
        existing_controls  text,
        further_controls   text,
        residual_likelihood  int,
        residual_severity    int,
        residual_risk_score  int,
        residual_risk_level  text,
        review_date   date,
        status        text
    );

3. In Streamlit Cloud → App settings → Secrets, add:

    [supabase]
    url = "https://xxxxxxxxxxxx.supabase.co"
    key = "your-anon-public-key"

4. In app.py, replace:
        from data_manager import ... load_data, save_entry, delete_entry, update_status ...
   with:
        from database import load_data, save_entry, delete_entry, update_status
   (keep the other data_manager imports for constants/classify_risk)

─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

from data_manager import classify_risk, COLUMNS

TABLE = "risk_assessments"


@st.cache_resource
def _client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


def load_data() -> pd.DataFrame:
    resp = _client().table(TABLE).select("*").order("id").execute()
    if not resp.data:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(resp.data)
    df["date"] = pd.to_datetime(df["date"])
    df["review_date"] = pd.to_datetime(df["review_date"])
    return df


def save_entry(entry: dict) -> pd.DataFrame:
    entry = entry.copy()
    entry.pop("id", None)
    entry["date"] = datetime.now().strftime("%Y-%m-%d")
    level, _ = classify_risk(entry["risk_score"])
    entry["risk_level"] = level
    res_level, _ = classify_risk(entry["residual_risk_score"])
    entry["residual_risk_level"] = res_level
    _client().table(TABLE).insert(entry).execute()
    return load_data()


def delete_entry(entry_id: int) -> pd.DataFrame:
    _client().table(TABLE).delete().eq("id", entry_id).execute()
    return load_data()


def update_status(entry_id: int, new_status: str) -> pd.DataFrame:
    _client().table(TABLE).update({"status": new_status}).eq("id", entry_id).execute()
    return load_data()
