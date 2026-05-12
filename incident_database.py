"""
Incident persistence — Supabase REST API with CSV fallback.
Mirrors database.py but targets the 'incidents' table / incidents.csv.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

import data_manager as _dm
from database import _use_supabase

TABLE = "incidents"
_TIMEOUT = 10


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


def _load_csv() -> pd.DataFrame:
    import os
    if os.path.exists(_dm.INCIDENT_FILE):
        df = pd.read_csv(_dm.INCIDENT_FILE)
        df["days_lost"] = pd.to_numeric(df["days_lost"], errors="coerce").fillna(0).astype(int)
        df["riddor_reportable"] = df["riddor_reportable"].astype(str).str.lower().map(
            {"true": True, "false": False, "1": True, "0": False}
        ).fillna(False)
        return df
    return pd.DataFrame(columns=_dm.INCIDENT_COLUMNS)


def _save_csv(df: pd.DataFrame) -> None:
    df.to_csv(_dm.INCIDENT_FILE, index=False)


def load_incidents() -> pd.DataFrame:
    if not _use_supabase():
        return _load_csv()
    try:
        resp = requests.get(
            _url(), headers=_headers(),
            params={"select": "*", "order": "id"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return pd.DataFrame(columns=_dm.INCIDENT_COLUMNS)
        df = pd.DataFrame(data)
        df["days_lost"] = pd.to_numeric(df["days_lost"], errors="coerce").fillna(0).astype(int)
        df["riddor_reportable"] = df["riddor_reportable"].astype(bool)
        return df
    except Exception:
        return _load_csv()


def save_incident(entry: dict) -> pd.DataFrame:
    entry = entry.copy()
    entry.pop("id", None)
    entry["date"] = datetime.now().strftime("%Y-%m-%d")
    riddor, category = _dm.classify_riddor(entry)
    entry["riddor_reportable"] = riddor
    entry["riddor_category"] = category

    if not _use_supabase():
        df = _load_csv()
        entry["id"] = int(df["id"].max()) + 1 if not df.empty else 1
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        _save_csv(df)
        return df
    try:
        payload = {k: (bool(v) if isinstance(v, (bool, )) else v) for k, v in entry.items()}
        resp = requests.post(
            _url(), headers=_headers("return=representation"),
            json=payload, timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        df = _load_csv()
        entry["id"] = int(df["id"].max()) + 1 if not df.empty else 1
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        _save_csv(df)
        return df
    return load_incidents()


def delete_incident(entry_id: int) -> pd.DataFrame:
    if not _use_supabase():
        df = _load_csv()
        df = df[df["id"] != entry_id]
        _save_csv(df)
        return df
    try:
        resp = requests.delete(
            f"{_url()}?id=eq.{entry_id}",
            headers=_headers(), timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        df = _load_csv()
        df = df[df["id"] != entry_id]
        _save_csv(df)
        return df
    return load_incidents()


def update_incident_status(entry_id: int, new_status: str) -> pd.DataFrame:
    return update_incident(entry_id, {"status": new_status})


def update_incident(entry_id: int, fields: dict) -> pd.DataFrame:
    if not _use_supabase():
        df = _load_csv()
        for col, val in fields.items():
            df.loc[df["id"] == entry_id, col] = val
        _save_csv(df)
        return df
    try:
        resp = requests.patch(
            f"{_url()}?id=eq.{entry_id}",
            headers=_headers("return=representation"),
            json=fields, timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        df = _load_csv()
        for col, val in fields.items():
            df.loc[df["id"] == entry_id, col] = val
        _save_csv(df)
        return df
    return load_incidents()
