import streamlit as st
import pandas as pd
from datetime import date, timedelta

from data_manager import (
    HAZARD_CATEGORIES, DEPARTMENTS, classify_risk,
    load_data, save_entry, delete_entry, update_status, get_summary_stats,
)
from visualizations import (
    risk_matrix_heatmap, hazard_bar_chart,
    department_risk_chart, risk_trend_chart, risk_reduction_chart,
)

st.set_page_config(
    page_title="Safety Intelligence Tool",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Safety Intelligence")
    st.markdown("*NEBOSH-aligned Risk Assessment Platform*")
    st.divider()
    page = st.radio(
        "Navigate",
        ["📋 New Assessment", "📊 Dashboard", "📁 All Assessments", "ℹ️ About"],
        label_visibility="collapsed",
    )
    st.divider()
    df_all = load_data()
    stats = get_summary_stats(df_all)
    st.markdown(f"**Total Assessments:** {stats['total']}")
    st.markdown(f"**Open Items:** {stats['open']}")

    high_count = stats["very_high"] + stats["high"]
    colour = "red" if high_count > 0 else "green"
    st.markdown(f"**High/Very High:** :{colour}[{high_count}]")


# ── Helper ─────────────────────────────────────────────────────────────────────
def risk_badge(level: str) -> str:
    colours = {"Low": "green", "Medium": "orange", "High": "red", "Very High": "violet"}
    return f":{colours.get(level, 'gray')}[{level}]"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — New Assessment Form
# ══════════════════════════════════════════════════════════════════════════════
if page == "📋 New Assessment":
    st.title("📋 New Risk Assessment")
    st.caption("Complete all fields using NEBOSH risk assessment principles.")

    with st.form("risk_form", clear_on_submit=True):
        st.subheader("1 · Site & Assessor Details")
        col1, col2, col3 = st.columns(3)
        assessor   = col1.text_input("Assessor Name *", placeholder="e.g. J. Smith")
        department = col2.selectbox("Department *", DEPARTMENTS)
        location   = col3.text_input("Location / Area *", placeholder="e.g. Warehouse Bay 3")

        st.subheader("2 · Hazard Identification")
        col4, col5 = st.columns([1, 2])
        hazard_category    = col4.selectbox("Hazard Category *", HAZARD_CATEGORIES)
        hazard_description = col5.text_area(
            "Hazard Description *",
            placeholder="Describe the hazard and who might be harmed.",
            height=80,
        )
        activity = st.text_input(
            "Activity / Task", placeholder="e.g. Loading pallets using forklift"
        )

        st.subheader("3 · Initial Risk Rating")
        st.caption("Rate **before** controls are applied.")
        col6, col7 = st.columns(2)
        likelihood = col6.slider("Likelihood (1 = Rare  →  5 = Almost Certain)", 1, 5, 3)
        severity   = col7.slider("Severity  (1 = Negligible  →  5 = Catastrophic)", 1, 5, 3)

        risk_score = likelihood * severity
        risk_level, _ = classify_risk(risk_score)
        col6.metric("Risk Score", risk_score)
        col7.metric("Risk Level", risk_level)

        st.subheader("4 · Controls")
        existing_controls = st.text_area(
            "Existing Controls *",
            placeholder="List the controls already in place.",
            height=80,
        )
        further_controls = st.text_area(
            "Further / Recommended Controls",
            placeholder="List any additional controls required to reduce the risk.",
            height=80,
        )

        st.subheader("5 · Residual Risk Rating")
        st.caption("Rate **after** all controls are applied.")
        col8, col9 = st.columns(2)
        res_likelihood = col8.slider("Residual Likelihood", 1, 5, max(1, likelihood - 1))
        res_severity   = col9.slider("Residual Severity",   1, 5, max(1, severity - 1))

        residual_score = res_likelihood * res_severity
        residual_level, _ = classify_risk(residual_score)
        col8.metric("Residual Score", residual_score)
        col9.metric("Residual Level", residual_level)

        st.subheader("6 · Review & Status")
        col10, col11 = st.columns(2)
        review_date = col10.date_input(
            "Next Review Date", value=date.today() + timedelta(days=90)
        )
        status = col11.selectbox("Status", ["Open", "In Progress", "Closed"])

        submitted = st.form_submit_button("💾 Save Assessment", use_container_width=True)

    if submitted:
        if not assessor or not location or not hazard_description or not existing_controls:
            st.error("Please complete all required fields (marked *).")
        else:
            entry = {
                "assessor": assessor,
                "department": department,
                "location": location,
                "hazard_category": hazard_category,
                "hazard_description": hazard_description,
                "activity": activity,
                "likelihood": likelihood,
                "severity": severity,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "existing_controls": existing_controls,
                "further_controls": further_controls,
                "residual_likelihood": res_likelihood,
                "residual_severity": res_severity,
                "residual_risk_score": residual_score,
                "residual_risk_level": residual_level,
                "review_date": review_date.strftime("%Y-%m-%d"),
                "status": status,
            }
            save_entry(entry)
            st.success(f"Assessment saved! Risk Score: **{risk_score}** — Level: **{risk_level}**")

            if risk_score >= 17:
                st.error(
                    "🚨 **VERY HIGH RISK** — Immediate action required. "
                    "Notify the safety manager and do not proceed with the activity."
                )
            elif risk_score >= 12:
                st.warning(
                    "⚠️ **HIGH RISK** — Further controls must be implemented before work continues."
                )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.title("📊 Safety Intelligence Dashboard")

    df = load_data()

    if df.empty:
        st.info("No assessments recorded yet. Add your first assessment using the form.")
        st.stop()

    # ── KPI row ──────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Assessments", stats["total"])
    k2.metric("Open Items",         stats["open"])
    k3.metric("Very High Risk",     stats["very_high"],  delta=None)
    k4.metric("High Risk",          stats["high"])
    k5.metric("Avg Initial Score",  stats["avg_risk"])
    k6.metric("Avg Residual Score", stats["avg_residual"],
              delta=f"-{round(stats['avg_risk'] - stats['avg_residual'], 1)}" if stats["avg_risk"] else None)

    st.divider()

    # ── Filters ──────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        dept_filter = fc1.multiselect(
            "Department", df["department"].unique().tolist(), default=[]
        )
        cat_filter = fc2.multiselect(
            "Hazard Category", df["hazard_category"].unique().tolist(), default=[]
        )
        lvl_filter = fc3.multiselect(
            "Risk Level", ["Low", "Medium", "High", "Very High"], default=[]
        )

    filtered = df.copy()
    if dept_filter:
        filtered = filtered[filtered["department"].isin(dept_filter)]
    if cat_filter:
        filtered = filtered[filtered["hazard_category"].isin(cat_filter)]
    if lvl_filter:
        filtered = filtered[filtered["risk_level"].isin(lvl_filter)]

    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    # ── Charts row 1 ─────────────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.plotly_chart(risk_matrix_heatmap(filtered), use_container_width=True)
    with col_r:
        st.plotly_chart(hazard_bar_chart(filtered), use_container_width=True)

    # ── Charts row 2 ─────────────────────────────────────────────────────────
    col_l2, col_r2 = st.columns([1, 1])
    with col_l2:
        st.plotly_chart(department_risk_chart(filtered), use_container_width=True)
    with col_r2:
        st.plotly_chart(risk_reduction_chart(filtered), use_container_width=True)

    # ── Trend ────────────────────────────────────────────────────────────────
    if len(filtered) > 1:
        st.plotly_chart(risk_trend_chart(filtered), use_container_width=True)

    # ── High-risk alert table ─────────────────────────────────────────────────
    high_risk = filtered[filtered["risk_score"] >= 12].sort_values("risk_score", ascending=False)
    if not high_risk.empty:
        st.subheader("🚨 High & Very High Risk Items")
        display_cols = [
            "id", "date", "department", "location",
            "hazard_category", "risk_score", "risk_level", "status"
        ]
        st.dataframe(
            high_risk[display_cols].rename(columns={
                "id": "ID", "date": "Date", "department": "Department",
                "location": "Location", "hazard_category": "Hazard",
                "risk_score": "Score", "risk_level": "Level", "status": "Status"
            }),
            use_container_width=True,
            hide_index=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — All Assessments
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁 All Assessments":
    st.title("📁 All Risk Assessments")

    df = load_data()

    if df.empty:
        st.info("No assessments yet.")
        st.stop()

    # Export
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Export to CSV", data=csv_data,
        file_name="risk_assessments.csv", mime="text/csv",
    )

    st.divider()

    # Search
    search = st.text_input("🔍 Search (hazard, department, location…)", "")
    view_df = df.copy()
    if search:
        mask = view_df.apply(
            lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1
        )
        view_df = view_df[mask]

    for _, row in view_df.iterrows():
        rl, _ = classify_risk(int(row["risk_score"]))
        colour = {"Low": "🟢", "Medium": "🟡", "High": "🔴", "Very High": "🟣"}.get(rl, "⚪")
        with st.expander(
            f"{colour} ID {int(row['id'])} | {row['hazard_category']} — "
            f"{row['department']} | Score: {int(row['risk_score'])} ({row['risk_level']}) | {row['status']}"
        ):
            c1, c2 = st.columns(2)
            c1.markdown(f"**Assessor:** {row['assessor']}")
            c1.markdown(f"**Location:** {row['location']}")
            c1.markdown(f"**Date:** {row['date']}")
            c1.markdown(f"**Activity:** {row.get('activity', '—')}")
            c2.markdown(f"**Likelihood:** {int(row['likelihood'])}  |  **Severity:** {int(row['severity'])}")
            c2.markdown(f"**Risk Score:** {int(row['risk_score'])}  ({row['risk_level']})")
            c2.markdown(f"**Residual Score:** {int(row['residual_risk_score'])}  ({row['residual_risk_level']})")
            c2.markdown(f"**Review Date:** {row['review_date']}")

            st.markdown(f"**Existing Controls:** {row['existing_controls']}")
            if pd.notna(row.get("further_controls")) and row["further_controls"]:
                st.markdown(f"**Further Controls:** {row['further_controls']}")

            sa, sb, sc = st.columns([1, 1, 3])
            new_status = sa.selectbox(
                "Update Status", ["Open", "In Progress", "Closed"],
                index=["Open", "In Progress", "Closed"].index(row["status"]),
                key=f"status_{int(row['id'])}",
            )
            if sb.button("💾 Update", key=f"upd_{int(row['id'])}"):
                update_status(int(row["id"]), new_status)
                st.rerun()
            if sc.button("🗑️ Delete", key=f"del_{int(row['id'])}"):
                delete_entry(int(row["id"]))
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — About
# ══════════════════════════════════════════════════════════════════════════════
elif page == "ℹ️ About":
    st.title("ℹ️ About This Tool")
    st.markdown("""
### Data-Driven Safety Intelligence Tool
Built for H&S professionals transitioning into **Safety Analytics**.

---

#### Risk Rating System (NEBOSH Standard)
| Score | Level | Action Required |
|-------|-------|----------------|
| 1 – 6 | 🟢 Low | Monitor; review annually |
| 7 – 11 | 🟡 Medium | Implement controls within 30 days |
| 12 – 16 | 🔴 High | Implement controls before work continues |
| 17 – 25 | 🟣 Very High | Stop work immediately; notify management |

#### Risk Score Formula
```
Risk Score = Likelihood × Severity
```

#### Likelihood Scale
| Rating | Description |
|--------|-------------|
| 1 | Rare — unlikely to occur |
| 2 | Unlikely — could occur but not expected |
| 3 | Possible — might occur occasionally |
| 4 | Likely — will probably occur |
| 5 | Almost Certain — expected to occur regularly |

#### Severity Scale
| Rating | Description |
|--------|-------------|
| 1 | Negligible — no injury / minor near miss |
| 2 | Minor — first aid treatment |
| 3 | Moderate — RIDDOR reportable / medical treatment |
| 4 | Major — serious injury / hospitalisation |
| 5 | Catastrophic — fatality / multiple serious injuries |

---
*Built with Python · Streamlit · Plotly · Pandas*
    """)
