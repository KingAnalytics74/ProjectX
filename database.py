"""
Supabase persistence via direct REST API — no supabase package required.
Uses only the `requests` library (already a Streamlit dependency).

Secrets required in Streamlit Cloud → Settings → Secrets:

    [supabase]
    url = "https://gwvnzokdkwgeztsyatza.supabase.co"
    key = "<anon public key>"

Falls back to seed_data.csv if secrets are absent or if any API call fails.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

import data_manager as _csv

TABLE = "risk_assessments"
_TIMEOUT = 10


def _use_supabase() -> bool:
    try:
        st.secrets["supabase"]["url"]
        st.secrets["supabase"]["key"]
        return True
    except Exception:
        return False


def _url() -> str:
    return f"{st.secrets['supabase']['url']}/rest/v1/{TABLE}"


def _headers(prefer: str = "") -> dict:
    h = {
        "apikey": st.secrets["supabase"]["key"],
        "Authorization": f"Bearer {st.secrets['supabase']['key']}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def load_data() -> pd.DataFrame:
    if not _use_supabase():
        return _csv.load_data()
    try:
        resp = requests.get(
            _url(), headers=_headers(),
            params={"select": "*", "order": "id"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return pd.DataFrame(columns=_csv.COLUMNS)
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df["review_date"] = pd.to_datetime(df["review_date"])
        return df
    except Exception:
        return _csv.load_data()


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
    try:
        resp = requests.post(
            _url(), headers=_headers("return=representation"),
            json=entry, timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        return _csv.save_entry(entry)
    return load_data()


def delete_entry(entry_id: int) -> pd.DataFrame:
    if not _use_supabase():
        return _csv.delete_entry(entry_id)
    try:
        resp = requests.delete(
            f"{_url()}?id=eq.{entry_id}",
            headers=_headers(), timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        return _csv.delete_entry(entry_id)
    return load_data()


def update_status(entry_id: int, new_status: str) -> pd.DataFrame:
    if not _use_supabase():
        return _csv.update_status(entry_id, new_status)
    try:
        resp = requests.patch(
            f"{_url()}?id=eq.{entry_id}",
            headers=_headers("return=representation"),
            json={"status": new_status}, timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        return _csv.update_status(entry_id, new_status)
    return load_data()
