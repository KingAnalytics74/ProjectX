"""
Supabase persistence layer with automatic CSV fallback.

If Supabase secrets are not configured the app falls back to seed_data.csv
so it remains functional at all times.

─── SETUP ───────────────────────────────────────────────────────────────────

Step 1 — Run this SQL in Supabase → SQL Editor:

    create table if not exists risk_assessments (
        id                  bigserial primary key,
        date                date,
        assessor            text,
        department          text,
        location            text,
        hazard_category     text,
        hazard_description  text,
        activity            text,
        likelihood          int,
        severity            int,
        risk_score          int,
        risk_level          text,
        existing_controls   text,
        further_controls    text,
        residual_likelihood  int,
        residual_severity    int,
        residual_risk_score  int,
        residual_risk_level  text,
        review_date         date,
        status              text
    );

Step 2 — In Streamlit Cloud → your app → Settings → Secrets, add:

    [supabase]
    url = "https://gwvnzokdkwgeztsyatza.supabase.co"
    key = "<your anon/public key>"

    Get the anon key from:
    Supabase Dashboard → Project Settings → API → Project API keys → anon public

─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
from datetime import datetime

import data_manager as _csv

TABLE = "risk_assessments"


def _use_supabase() -> bool:
    try:
        st.secrets["supabase"]["url"]
        st.secrets["supabase"]["key"]
        return True
    except Exception:
        return False


@st.cache_resource
def _client():
    from supabase import create_client
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


def load_data() -> pd.DataFrame:
    if not _use_supabase():
        return _csv.load_data()
    resp = _client().table(TABLE).select("*").order("id").execute()
    if not resp.data:
        return pd.DataFrame(columns=_csv.COLUMNS)
    df = pd.DataFrame(resp.data)
    df["date"] = pd.to_datetime(df["date"])
    df["review_date"] = pd.to_datetime(df["review_date"])
    return df


def save_entry(entry: dict) -> pd.DataFrame:
    if not _use_supabase():
        return _csv.save_entry(entry)
    entry = entry.copy()
    entry.pop("id", None)
    entry["date"] = datetime.now().strftime("%Y-%m-%d")
    level, _ = _csv.classify_risk(entry["risk_score"])
    entry["risk_level"] = level
    res_level, _ = _csv.classify_risk(entry["residual_risk_score"])
    entry["residual_risk_level"] = res_level
    _client().table(TABLE).insert(entry).execute()
    return load_data()


def delete_entry(entry_id: int) -> pd.DataFrame:
    if not _use_supabase():
        return _csv.delete_entry(entry_id)
    _client().table(TABLE).delete().eq("id", entry_id).execute()
    return load_data()


def update_status(entry_id: int, new_status: str) -> pd.DataFrame:
    if not _use_supabase():
        return _csv.update_status(entry_id, new_status)
    _client().table(TABLE).update({"status": new_status}).eq("id", entry_id).execute()
    return load_data()
