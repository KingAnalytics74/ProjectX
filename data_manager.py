import pandas as pd
import os
from datetime import datetime

DATA_FILE = "risk_assessments.csv"

COLUMNS = [
    "id", "date", "assessor", "department", "location",
    "hazard_category", "hazard_description", "activity",
    "likelihood", "severity", "risk_score", "risk_level",
    "existing_controls", "further_controls",
    "residual_likelihood", "residual_severity",
    "residual_risk_score", "residual_risk_level",
    "review_date", "status"
]

HAZARD_CATEGORIES = [
    "Working at Height", "Manual Handling", "Chemical / COSHH",
    "Electrical", "Fire", "Machinery / Equipment", "Slips, Trips & Falls",
    "Noise & Vibration", "Lone Working", "Stress & Mental Health",
    "Display Screen Equipment", "Confined Spaces", "Biological Hazards",
    "Violence & Aggression", "Environmental"
]

DEPARTMENTS = [
    "Operations", "Maintenance", "Warehouse", "Office / Admin",
    "Construction", "Laboratory", "Logistics", "HR", "Finance", "IT", "Other"
]

RISK_LEVEL_MAP = {
    (1, 6): ("Low", "#2ecc71"),
    (7, 11): ("Medium", "#f39c12"),
    (12, 16): ("High", "#e74c3c"),
    (17, 25): ("Very High", "#8e44ad"),
}


def classify_risk(score: int) -> tuple[str, str]:
    for (low, high), (label, colour) in RISK_LEVEL_MAP.items():
        if low <= score <= high:
            return label, colour
    return "Unknown", "#95a5a6"


def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, parse_dates=["date", "review_date"])
        return df
    if os.path.exists("seed_data.csv"):
        return pd.read_csv("seed_data.csv", parse_dates=["date", "review_date"])
    return pd.DataFrame(columns=COLUMNS)


def save_entry(entry: dict) -> pd.DataFrame:
    df = load_data()
    new_id = int(df["id"].max()) + 1 if not df.empty else 1
    entry["id"] = new_id
    entry["date"] = datetime.now().strftime("%Y-%m-%d")

    risk_level, _ = classify_risk(entry["risk_score"])
    entry["risk_level"] = risk_level

    residual_level, _ = classify_risk(entry["residual_risk_score"])
    entry["residual_risk_level"] = residual_level

    new_row = pd.DataFrame([entry])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return df


def delete_entry(entry_id: int) -> pd.DataFrame:
    df = load_data()
    df = df[df["id"] != entry_id]
    df.to_csv(DATA_FILE, index=False)
    return df


def update_status(entry_id: int, new_status: str) -> pd.DataFrame:
    df = load_data()
    df.loc[df["id"] == entry_id, "status"] = new_status
    df.to_csv(DATA_FILE, index=False)
    return df


def get_summary_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {k: 0 for k in ["total", "very_high", "high", "medium", "low", "open", "avg_risk", "avg_residual"]}
    return {
        "total": len(df),
        "very_high": len(df[df["risk_level"] == "Very High"]),
        "high": len(df[df["risk_level"] == "High"]),
        "medium": len(df[df["risk_level"] == "Medium"]),
        "low": len(df[df["risk_level"] == "Low"]),
        "open": len(df[df["status"] == "Open"]),
        "avg_risk": round(df["risk_score"].mean(), 1),
        "avg_residual": round(df["residual_risk_score"].mean(), 1),
    }
