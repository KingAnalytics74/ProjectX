import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

from data_manager import HAZARD_CATEGORIES, DEPARTMENTS, classify_risk, get_summary_stats
from database import load_data, save_entry, delete_entry, update_status, _use_supabase
from visualizations import (
    risk_matrix_heatmap, hazard_bar_chart, department_risk_chart,
    risk_trend_chart, risk_reduction_chart, monthly_volume_chart,
    risk_level_stacked_chart, control_effectiveness_chart, department_trend_lines,
    spc_imr_chart, spc_mr_chart, insights_risk_heatmap,
)

st.set_page_config(
    page_title="Safety Intelligence Tool",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.markdown("## 🛡️ Safety Intelligence")
    st.markdown("*NEBOSH-aligned Risk Assessment Platform*")
    st.divider()
    page = st.radio(
        "Navigate",
        ["📋 New Assessment", "📊 Dashboard", "📈 Trends",
         "💡 Insights", "🔔 Alerts & Insights", "📁 All Assessments", "ℹ️ About"],
        label_visibility="collapsed",
    )
    st.divider()
    df_all = load_data()
    stats = get_summary_stats(df_all)
    st.markdown(f"**Total Assessments:** {stats['total']}")
    st.markdown(f"**Open Items:** {stats['open']}")
    high_count = stats["very_high"] + stats["high"]
    st.markdown(f"**High/Very High:** :{'red' if high_count > 0 else 'green'}[{high_count}]")
    if not df_all.empty:
        _active = df_all[df_all["status"] != "Closed"].copy()
        _active["review_date"] = pd.to_datetime(_active["review_date"])
        _overdue = len(_active[_active["review_date"] < pd.Timestamp(date.today())])
        st.markdown(f"**Overdue Reviews:** :{'red' if _overdue > 0 else 'green'}[{_overdue}]")
    st.divider()
    if _use_supabase():
        st.success("🟢 Connected to Supabase")
    else:
        st.warning("🟡 Using local data — Supabase not connected")


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
        activity = st.text_input("Activity / Task", placeholder="e.g. Loading pallets using forklift")

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
        review_date = col10.date_input("Next Review Date", value=date.today() + timedelta(days=90))
        status = col11.selectbox("Status", ["Open", "In Progress", "Closed"])

        submitted = st.form_submit_button("💾 Save Assessment", use_container_width=True)

    if submitted:
        if not assessor or not location or not hazard_description or not existing_controls:
            st.error("Please complete all required fields (marked *).")
        else:
            save_entry({
                "assessor": assessor, "department": department, "location": location,
                "hazard_category": hazard_category, "hazard_description": hazard_description,
                "activity": activity, "likelihood": likelihood, "severity": severity,
                "risk_score": risk_score, "risk_level": risk_level,
                "existing_controls": existing_controls, "further_controls": further_controls,
                "residual_likelihood": res_likelihood, "residual_severity": res_severity,
                "residual_risk_score": residual_score, "residual_risk_level": residual_level,
                "review_date": review_date.strftime("%Y-%m-%d"), "status": status,
            })
            st.success(f"Assessment saved! Risk Score: **{risk_score}** — Level: **{risk_level}**")
            if risk_score >= 17:
                st.error("🚨 **VERY HIGH RISK** — Immediate action required. Notify the safety manager and do not proceed with the activity.")
            elif risk_score >= 12:
                st.warning("⚠️ **HIGH RISK** — Further controls must be implemented before work continues.")


elif page == "📊 Dashboard":
    st.title("📊 Safety Intelligence Dashboard")
    df = load_data()

    if df.empty:
        st.info("No assessments recorded yet. Add your first assessment using the form.")
        st.stop()

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Assessments", stats["total"])
    k2.metric("Open Items",        stats["open"])
    k3.metric("Very High Risk",    stats["very_high"])
    k4.metric("High Risk",         stats["high"])
    k5.metric("Avg Initial Score", stats["avg_risk"])
    k6.metric("Avg Residual Score", stats["avg_residual"],
              delta=f"-{round(stats['avg_risk'] - stats['avg_residual'], 1)}" if stats["avg_risk"] else None)

    st.divider()

    with st.expander("🔍 Filters", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        dept_filter = fc1.multiselect("Department", df["department"].unique().tolist(), default=[])
        cat_filter  = fc2.multiselect("Hazard Category", df["hazard_category"].unique().tolist(), default=[])
        lvl_filter  = fc3.multiselect("Risk Level", ["Low", "Medium", "High", "Very High"], default=[])

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

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(risk_matrix_heatmap(filtered), use_container_width=True)
    with col_r:
        st.plotly_chart(hazard_bar_chart(filtered), use_container_width=True)

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.plotly_chart(department_risk_chart(filtered), use_container_width=True)
    with col_r2:
        st.plotly_chart(risk_reduction_chart(filtered), use_container_width=True)

    if len(filtered) > 1:
        st.plotly_chart(risk_trend_chart(filtered), use_container_width=True)

    high_risk = filtered[filtered["risk_score"] >= 12].sort_values("risk_score", ascending=False)
    if not high_risk.empty:
        st.subheader("🚨 High & Very High Risk Items")
        st.dataframe(
            high_risk[["id", "date", "department", "location", "hazard_category", "risk_score", "risk_level", "status"]].rename(columns={
                "id": "ID", "date": "Date", "department": "Department", "location": "Location",
                "hazard_category": "Hazard", "risk_score": "Score", "risk_level": "Level", "status": "Status",
            }),
            use_container_width=True, hide_index=True,
        )


elif page == "📈 Trends":
    st.title("📈 Statistical Process Control")
    st.caption("Monitoring workplace safety as a managed process using SPC control charts and Nelson Rule signal detection.")
    df = load_data()

    if df.empty:
        st.info("No assessments recorded yet. Add your first assessment using the form.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])

    tmp     = df.copy()
    tmp["_month"] = tmp["date"].dt.to_period("M")
    monthly = tmp.groupby("_month")["risk_score"].mean().reset_index()
    monthly["label"] = monthly["_month"].astype(str)
    labels  = monthly["label"].tolist()
    values  = monthly["risk_score"].tolist()

    x_bar   = float(np.mean(values))
    mr      = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mr_bar  = float(np.mean(mr)) if mr else 0.001
    sigma   = mr_bar / 1.128
    ucl     = x_bar + 3 * sigma
    lcl     = max(1.0, x_bar - 3 * sigma)
    u2s     = x_bar + 2 * sigma
    l2s     = x_bar - 2 * sigma
    ucl_mr  = 3.267 * mr_bar
    USL     = 12.0
    Cpu     = (USL - x_bar) / (3 * sigma) if sigma > 0 else float("inf")

    def detect_signals(vals):
        signals = {}
        n = len(vals)
        for i in range(n):
            v, rules = vals[i], []
            if v > ucl or v < lcl:
                rules.append("Rule 1 — Point beyond ±3σ control limit")
            if i >= 7:
                w = vals[i - 7: i + 1]
                if all(p > x_bar for p in w) or all(p < x_bar for p in w):
                    rules.append("Rule 2 — 8 consecutive points on one side of centreline")
            if i >= 5:
                w = vals[i - 5: i + 1]
                d = [w[j + 1] - w[j] for j in range(len(w) - 1)]
                if all(x > 0 for x in d) or all(x < 0 for x in d):
                    rules.append("Rule 3 — 6 consecutive points trending monotonically")
            if i >= 2:
                w = vals[i - 2: i + 1]
                if sum(1 for p in w if p > u2s) >= 2 or sum(1 for p in w if p < l2s) >= 2:
                    rules.append("Rule 4 — 2 of 3 consecutive points beyond ±2σ")
            if rules:
                signals[i] = rules
        return signals

    signal_map  = detect_signals(values)
    signal_idx  = set(signal_map.keys())
    in_control  = len(signal_map) == 0

    if Cpu == float("inf"):
        capability_label = "Capable"
    elif Cpu >= 1.33:
        capability_label = "Capable"
    elif Cpu >= 1.0:
        capability_label = "Marginal"
    else:
        capability_label = "Not Capable"

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Process Status",    "In Control" if in_control else "Out of Control")
    k2.metric("Process Mean (X̄)", f"{x_bar:.2f}")
    k3.metric("Process σ",         f"{sigma:.2f}")
    k4.metric("Cpu  (USL = 12)",   f"{Cpu:.2f}" if Cpu != float("inf") else "∞")
    k5.metric("Signals Detected",  len(signal_map))

    if in_control:
        st.success("**Process is in statistical control.** No Nelson Rule violations detected.")
    else:
        st.error(f"**{len(signal_map)} Nelson Rule violation(s) detected.** Review the signal table below.")

    st.divider()
    st.subheader("I Chart — Individual Values")
    st.plotly_chart(spc_imr_chart(labels, values, signal_idx), use_container_width=True)

    if len(values) >= 2:
        st.subheader("MR Chart — Moving Range")
        st.plotly_chart(spc_mr_chart(labels, mr, ucl_mr, mr_bar), use_container_width=True)

    if signal_map:
        st.divider()
        st.subheader("🚨 Nelson Rule Violations")
        rows = [
            {"Month": labels[i], "Avg Risk Score": round(values[i], 2), "Violation": rule}
            for i, rules in signal_map.items()
            for rule in rules
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("⚙️ Process Capability")
    st.caption("USL = 12 (NEBOSH High Risk threshold). Cpu measures how far the process mean sits below this limit.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("X̄ (Process Mean)", f"{x_bar:.2f}")
    c2.metric("σ (Process Sigma)", f"{sigma:.2f}")
    c3.metric("Cpu",               f"{Cpu:.2f}" if Cpu != float("inf") else "∞")
    c4.metric("Capability",         capability_label)

    if Cpu >= 1.33:
        st.success(f"**Cpu = {Cpu:.2f}** — Process is capable. Risk scores are consistently below the High Risk threshold of 12.")
    elif Cpu >= 1.0:
        st.warning(f"**Cpu = {Cpu:.2f}** — Process is marginally capable. Risk scores are approaching the High Risk threshold.")
    else:
        st.error(f"**Cpu = {Cpu:.2f}** — Process is not capable. Risk scores regularly breach the High Risk threshold. Systematic intervention required.")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(monthly_volume_chart(df), use_container_width=True)
    with col_b:
        st.plotly_chart(risk_level_stacked_chart(df), use_container_width=True)

    st.plotly_chart(department_trend_lines(df), use_container_width=True)

    st.divider()
    st.subheader("📋 Period Summary")
    summary = (
        df.assign(month=df["date"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(
            Assessments=("id", "count"),
            Avg_Risk=("risk_score", "mean"),
            Avg_Residual=("residual_risk_score", "mean"),
            High_or_Very_High=("risk_level", lambda x: (x.isin(["High", "Very High"])).sum()),
        )
        .round(1)
        .reset_index()
        .rename(columns={"month": "Month", "Avg_Risk": "Avg Risk", "Avg_Residual": "Avg Residual"})
        .sort_values("Month", ascending=False)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🔬 Data Quality Report")
    st.caption("Automated check for duplicate records and missing required fields.")

    dups = df[df.duplicated(subset=["assessor", "department", "hazard_category", "date"], keep=False)]
    missing_dept = df[df["department"].isna() | (df["department"].astype(str).str.strip() == "")]
    missing_assessor = df[df["assessor"].isna() | (df["assessor"].astype(str).str.strip() == "")]

    dq1, dq2, dq3 = st.columns(3)
    dq1.metric("Potential Duplicates", len(dups))
    dq2.metric("Missing Department", len(missing_dept))
    dq3.metric("Missing Assessor", len(missing_assessor))

    if dups.empty and missing_dept.empty and missing_assessor.empty:
        st.success("Database is clean — no data quality issues detected.")
    else:
        if not dups.empty:
            with st.expander(f"⚠️ {len(dups)} Potential Duplicate Records", expanded=True):
                st.dataframe(
                    dups[["id", "date", "assessor", "department", "hazard_category", "risk_score"]].rename(
                        columns={"id": "ID", "date": "Date", "assessor": "Assessor",
                                 "department": "Department", "hazard_category": "Hazard", "risk_score": "Score"}
                    ), use_container_width=True, hide_index=True,
                )
        if not missing_dept.empty:
            with st.expander(f"⚠️ {len(missing_dept)} Records Missing Department"):
                st.dataframe(
                    missing_dept[["id", "date", "assessor", "hazard_category"]].rename(
                        columns={"id": "ID", "date": "Date", "assessor": "Assessor", "hazard_category": "Hazard"}
                    ), use_container_width=True, hide_index=True,
                )
        if not missing_assessor.empty:
            with st.expander(f"⚠️ {len(missing_assessor)} Records Missing Assessor"):
                st.dataframe(
                    missing_assessor[["id", "date", "department", "hazard_category"]].rename(
                        columns={"id": "ID", "date": "Date", "department": "Department", "hazard_category": "Hazard"}
                    ), use_container_width=True, hide_index=True,
                )


elif page == "💡 Insights":
    st.title("💡 Risk Insights")
    st.caption("Live analysis of your Supabase data — risk distribution, red zones, and top hazards.")
    df = load_data()

    if df.empty:
        st.info("No assessments recorded yet. Add your first assessment to see insights.")
        st.stop()

    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Total Records", len(df))
    i2.metric("Unique Departments", df["department"].nunique())
    i3.metric("Unique Hazard Types", df["hazard_category"].nunique())
    high_pct = round(100 * len(df[df["risk_score"] >= 12]) / len(df), 1)
    i4.metric("In Red Zone (≥12)", f"{high_pct}%")

    st.divider()
    st.subheader("Risk Matrix — Red Zone Analysis")
    st.caption("Likelihood on X-axis · Severity on Y-axis · Each dot = one assessment · Red zone = score ≥ 12")
    st.plotly_chart(insights_risk_heatmap(df), use_container_width=True)

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🔴 Top 10 Highest Risk Assessments")
        top10 = (
            df.sort_values("risk_score", ascending=False)
            .head(10)[["id", "department", "hazard_category", "risk_score", "risk_level", "status"]]
            .rename(columns={"id": "ID", "department": "Dept", "hazard_category": "Hazard",
                             "risk_score": "Score", "risk_level": "Level", "status": "Status"})
        )
        st.dataframe(top10, use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("📊 Risk Zone Breakdown")
        zone_counts = df["risk_level"].value_counts().reindex(
            ["Very High", "High", "Medium", "Low"], fill_value=0
        ).reset_index()
        zone_counts.columns = ["Risk Level", "Count"]
        zone_counts["Percentage"] = (zone_counts["Count"] / len(df) * 100).round(1).astype(str) + "%"
        st.dataframe(zone_counts, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🏭 Department Red Zone Count")
    red_zone = df[df["risk_score"] >= 12].groupby("department").size().reset_index(name="High Risk Count")
    red_zone = red_zone.sort_values("High Risk Count", ascending=False)
    if red_zone.empty:
        st.success("No departments currently have High or Very High risk assessments.")
    else:
        st.dataframe(red_zone, use_container_width=True, hide_index=True)


elif page == "🔔 Alerts & Insights":
    st.title("🔔 Alerts & Insights")
    st.caption("Data-driven safety intelligence — overdue reviews, risk velocity, and keyword analysis.")
    df = load_data()

    if df.empty:
        st.info("No assessments yet.")
        st.stop()

    today_ts = pd.Timestamp(date.today())

    st.subheader("📅 Overdue Review Alerts")
    active  = df[df["status"] != "Closed"].copy()
    active["review_date"] = pd.to_datetime(active["review_date"])
    overdue = active[active["review_date"] < today_ts].copy()
    overdue["days_overdue"] = (today_ts - overdue["review_date"]).dt.days
    overdue = overdue.sort_values("days_overdue", ascending=False)

    if overdue.empty:
        st.success("All active assessments are within their review window.")
    else:
        st.error(f"**{len(overdue)} assessment(s) overdue for review.**")
        st.dataframe(
            overdue[["id", "department", "location", "hazard_category",
                      "risk_level", "review_date", "days_overdue", "status"]].rename(columns={
                "id": "ID", "department": "Dept", "location": "Location",
                "hazard_category": "Hazard", "risk_level": "Level",
                "review_date": "Due Date", "days_overdue": "Days Overdue", "status": "Status",
            }),
            use_container_width=True, hide_index=True,
        )

    st.divider()
    st.subheader("📈 Department Risk Velocity")
    st.caption("Average risk score: last 60 days vs prior 60-day period. Green = improving, Red = worsening.")

    df["date"] = pd.to_datetime(df["date"])
    recent_avg = df[df["date"] >= (today_ts - pd.Timedelta(days=60))].groupby("department")["risk_score"].mean()
    prior_avg  = df[(df["date"] >= (today_ts - pd.Timedelta(days=120))) & (df["date"] < (today_ts - pd.Timedelta(days=60)))].groupby("department")["risk_score"].mean()

    if recent_avg.empty or prior_avg.empty:
        half = len(df) // 2
        if half > 0:
            recent_avg = df.iloc[half:].groupby("department")["risk_score"].mean()
            prior_avg  = df.iloc[:half].groupby("department")["risk_score"].mean()
            st.caption("_Using record order split — add more dated data for time-based velocity._")

    all_depts = sorted(set(recent_avg.index) | set(prior_avg.index))
    if all_depts:
        cols = st.columns(min(len(all_depts), 5))
        for i, dept in enumerate(all_depts):
            r, p = recent_avg.get(dept), prior_avg.get(dept)
            col  = cols[i % len(cols)]
            if r is not None and p is not None:
                col.metric(dept[:14], f"{r:.1f}", delta=f"{r - p:+.1f}", delta_color="inverse")
            elif r is not None:
                col.metric(dept[:14], f"{r:.1f}", delta="New")
            else:
                col.metric(dept[:14], f"{p:.1f}", delta="No recent data", delta_color="off")

    st.divider()
    st.subheader("🔍 Keyword Intelligence")
    st.caption("Scanning hazard descriptions for language that indicates elevated concern.")

    CRITICAL_KW = ["collapse", "explosion", "fatality", "electrocution", "asphyxiation", "engulfment", "entrapment", "drowning"]
    HIGH_KW     = ["toxic", "corrosive", "flammable", "fracture", "amputation", "burn", "entanglement", "crush", "fall from height", "serious injury"]
    CONCERN_KW  = ["pain", "stress", "near miss", "strain", "fatigue", "anxiety", "overload", "pressure", "discomfort", "repetitive"]

    def scan(keywords: list) -> list:
        hits = []
        for _, row in df.iterrows():
            text  = f"{row.get('hazard_description', '')} {row.get('existing_controls', '')}".lower()
            found = [kw for kw in keywords if kw in text]
            if found:
                hits.append({
                    "ID": int(row["id"]), "Department": row["department"],
                    "Hazard": row["hazard_category"], "Keywords Found": ", ".join(found),
                    "Risk Level": row["risk_level"], "Status": row["status"],
                })
        return hits

    critical_hits = scan(CRITICAL_KW)
    high_hits     = scan(HIGH_KW)
    concern_hits  = scan(CONCERN_KW)

    m1, m2, m3 = st.columns(3)
    m1.metric("Critical Terms Detected", len(critical_hits))
    m2.metric("High Concern Terms",      len(high_hits))
    m3.metric("General Concerns",        len(concern_hits))

    if critical_hits:
        st.error("**Critical language found — review these immediately:**")
        st.dataframe(pd.DataFrame(critical_hits), use_container_width=True, hide_index=True)
    if high_hits:
        with st.expander(f"High Concern — {len(high_hits)} match(es)", expanded=True):
            st.dataframe(pd.DataFrame(high_hits), use_container_width=True, hide_index=True)
    if concern_hits:
        with st.expander(f"General Concerns — {len(concern_hits)} match(es)", expanded=False):
            st.dataframe(pd.DataFrame(concern_hits), use_container_width=True, hide_index=True)
    if not critical_hits and not high_hits and not concern_hits:
        st.success("No flagged keywords found in current assessment descriptions.")


elif page == "📁 All Assessments":
    st.title("📁 All Risk Assessments")
    df = load_data()

    if df.empty:
        st.info("No assessments yet.")
        st.stop()

    st.download_button(
        "⬇️ Export to CSV", data=df.to_csv(index=False).encode("utf-8"),
        file_name="risk_assessments.csv", mime="text/csv",
    )
    st.divider()

    search  = st.text_input("🔍 Search (hazard, department, location…)", "")
    view_df = df.copy()
    if search:
        mask    = view_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)
        view_df = view_df[mask]

    for _, row in view_df.iterrows():
        rl, _  = classify_risk(int(row["risk_score"]))
        icon   = {"Low": "🟢", "Medium": "🟡", "High": "🔴", "Very High": "🟣"}.get(rl, "⚪")
        with st.expander(
            f"{icon} ID {int(row['id'])} | {row['hazard_category']} — "
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
*Built with Python · Streamlit · Plotly · Pandas · Supabase*
    """)
