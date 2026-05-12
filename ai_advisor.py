import os
import json
import anthropic
import pandas as pd
import streamlit as st
from typing import Generator


_MODEL = "claude-opus-4-7"

_SYSTEM = (
    "You are an expert Health & Safety advisor with NEBOSH and IOSH qualifications, "
    "specialising in UK workplace safety law: Health and Safety at Work Act 1974, "
    "Management of Health and Safety at Work Regulations 1999, COSHH, RIDDOR, and "
    "Manual Handling Regulations.\n\n"
    "Use the NEBOSH 5×5 risk matrix: Likelihood × Severity = Risk Score. "
    "Levels: Low (1–6), Medium (7–11), High (12–16), Very High (17–25).\n\n"
    "Control hierarchy: Eliminate → Substitute → Engineering → Administrative → PPE.\n\n"
    "Be concise, professional, and actionable. Use bullet points and numbered lists."
)


def _api_key() -> str | None:
    try:
        return st.secrets["anthropic"]["api_key"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def ai_available() -> bool:
    return bool(_api_key())


def _client() -> anthropic.Anthropic:
    key = _api_key()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    return anthropic.Anthropic(api_key=key)


def data_context(df: pd.DataFrame) -> str:
    if df.empty:
        return "{}"
    try:
        top5 = (
            df.nlargest(5, "risk_score")
            [["hazard_category", "department", "risk_score", "risk_level",
              "hazard_description", "existing_controls", "status"]]
            .to_dict(orient="records")
        )
        return json.dumps({
            "total_assessments": len(df),
            "risk_distribution": df["risk_level"].value_counts().to_dict(),
            "departments": df["department"].value_counts().head(8).to_dict(),
            "hazard_categories": df["hazard_category"].value_counts().head(8).to_dict(),
            "avg_risk_score": round(float(df["risk_score"].mean()), 2),
            "avg_residual_score": round(float(df["residual_risk_score"].mean()), 2),
            "open_items": int((df["status"] == "Open").sum()),
            "high_risk_count": int((df["risk_score"] >= 12).sum()),
            "top_5_risks": top5,
        }, indent=2, default=str)
    except Exception:
        return json.dumps({"total_assessments": len(df)})


def _system_block() -> list[dict]:
    return [{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}]


def stream_summary(df: pd.DataFrame) -> Generator[str, None, None]:
    try:
        with _client().messages.stream(
            model=_MODEL,
            max_tokens=1500,
            system=_system_block(),
            messages=[{"role": "user", "content": (
                "Analyse this H&S risk assessment data and provide:\n"
                "1. **Overall Safety Status** — key headline stats\n"
                "2. **Top Priority Risks** — top 3 requiring immediate action\n"
                "3. **Patterns** — recurring issues or trends\n"
                "4. **Recommendations** — 4–5 specific, actionable steps\n"
                "5. **Compliance Flags** — any UK H&S legal obligations triggered\n\n"
                f"Data:\n{data_context(df)}"
            )}],
        ) as stream:
            yield from stream.text_stream
    except anthropic.AuthenticationError:
        yield "❌ Invalid API key. Check `[anthropic]` in Streamlit Secrets."
    except anthropic.RateLimitError:
        yield "❌ Rate limit reached. Please wait a moment and try again."
    except Exception as e:
        yield f"❌ AI request failed: {e}"


def stream_controls(
    hazard_category: str,
    hazard_description: str,
    likelihood: int,
    severity: int,
    existing_controls: str,
) -> Generator[str, None, None]:
    score = likelihood * severity
    try:
        with _client().messages.stream(
            model=_MODEL,
            max_tokens=800,
            system=_system_block(),
            messages=[{"role": "user", "content": (
                "Suggest additional controls for this workplace hazard using the control hierarchy.\n\n"
                f"**Hazard Category:** {hazard_category}\n"
                f"**Description:** {hazard_description}\n"
                f"**Likelihood:** {likelihood}/5  |  **Severity:** {severity}/5  |  "
                f"**Risk Score:** {score}\n"
                f"**Existing Controls:** {existing_controls or 'None specified'}\n\n"
                "Provide 4–6 specific additional controls ordered: "
                "Eliminate → Substitute → Engineering → Administrative → PPE. "
                "For each, briefly explain how it reduces this specific risk."
            )}],
        ) as stream:
            yield from stream.text_stream
    except anthropic.AuthenticationError:
        yield "❌ Invalid API key."
    except Exception as e:
        yield f"❌ AI request failed: {e}"


def stream_chat(messages: list[dict]) -> Generator[str, None, None]:
    try:
        with _client().messages.stream(
            model=_MODEL,
            max_tokens=800,
            system=_system_block(),
            messages=messages,
        ) as stream:
            yield from stream.text_stream
    except anthropic.AuthenticationError:
        yield "❌ Invalid API key."
    except Exception as e:
        yield f"❌ AI request failed: {e}"


def incident_data_context(df: pd.DataFrame) -> str:
    if df.empty:
        return "{}"
    try:
        recent5 = (
            df.sort_values("date", ascending=False)
            .head(5)[["id", "incident_type", "department", "treatment",
                       "riddor_reportable", "riddor_category", "days_lost", "status"]]
            .to_dict(orient="records")
        )
        riddor_mask = df["riddor_reportable"].astype(bool)
        return json.dumps({
            "total_incidents": len(df),
            "incident_types": df["incident_type"].value_counts().to_dict(),
            "departments": df["department"].value_counts().head(8).to_dict(),
            "treatment_breakdown": df["treatment"].value_counts().to_dict(),
            "riddor_count": int(riddor_mask.sum()),
            "riddor_categories": df[riddor_mask]["riddor_category"].value_counts().to_dict(),
            "total_days_lost": int(df["days_lost"].fillna(0).sum()),
            "open_count": int((df["status"] != "Closed").sum()),
            "near_miss_ratio_pct": round(
                float((df["incident_type"] == "Near Miss").sum() / len(df) * 100), 1
            ),
            "recent_5_incidents": recent5,
        }, indent=2, default=str)
    except Exception:
        return json.dumps({"total_incidents": len(df)})


def stream_incident_analysis(df: pd.DataFrame) -> Generator[str, None, None]:
    try:
        with _client().messages.stream(
            model=_MODEL,
            max_tokens=1500,
            system=_system_block(),
            messages=[{"role": "user", "content": (
                "Analyse this workplace incident data and provide:\n"
                "1. **Incident Pattern Summary** — key headline stats and trends\n"
                "2. **RIDDOR Compliance Flags** — incidents requiring HSE notification\n"
                "3. **Root Cause Patterns** — recurring themes in causes or departments\n"
                "4. **Systemic Improvement Recommendations** — 4–5 specific actions\n"
                "5. **Leading Indicator Observations** — near miss ratio, early warning signs\n\n"
                f"Data:\n{incident_data_context(df)}"
            )}],
        ) as stream:
            yield from stream.text_stream
    except anthropic.AuthenticationError:
        yield "❌ Invalid API key. Check `[anthropic]` in Streamlit Secrets."
    except anthropic.RateLimitError:
        yield "❌ Rate limit reached. Please wait a moment and try again."
    except Exception as e:
        yield f"❌ AI request failed: {e}"
