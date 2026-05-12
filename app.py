import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime

from data_manager import (
    HAZARD_CATEGORIES, DEPARTMENTS, classify_risk, get_summary_stats, get_incident_stats,
    INCIDENT_TYPES, INJURY_TYPES, TREATMENT_TYPES, INCIDENT_STATUSES, classify_riddor,
)
from database import load_data, save_entry, delete_entry, update_status, update_entry, _use_supabase
from incident_database import load_incidents, save_incident, update_incident, update_incident_status
from visualizations import (
    risk_matrix_heatmap, hazard_bar_chart, department_risk_chart,
    risk_trend_chart, risk_reduction_chart, monthly_volume_chart,
    risk_level_stacked_chart, control_effectiveness_chart, department_trend_lines,
    spc_imr_chart, spc_mr_chart, insights_risk_heatmap,
    incident_type_bar, incident_department_chart, riddor_donut,
    incident_trend_line, severity_treatment_heatmap,
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
         "💡 Insights", "🤖 AI Assistant", "🚨 Incident Management", "🔔 Alerts & Insights",
         "📁 All Assessments", "ℹ️ About"],
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
    _inc_df    = load_incidents()
    _inc_stats = get_incident_stats(_inc_df)
    st.markdown(f"**Incidents:** {_inc_stats['total']}")
    st.markdown(f"**RIDDOR Reportable:** :{'red' if _inc_stats['riddor_count'] > 0 else 'green'}[{_inc_stats['riddor_count']}]")
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
    k2.metric("Process Mean (X̅)", f"{x_bar:.2f}")
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
    c1.metric("X̅ (Process Mean)", f"{x_bar:.2f}")
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


elif page == "🤖 AI Assistant":
    from ai_advisor import ai_available, stream_summary, stream_controls, stream_chat, data_context

    st.title("🤖 AI Safety Advisor")
    st.caption("Powered by Claude AI — intelligent analysis, control suggestions, and a chat interface for your H&S data.")

    if not ai_available():
        st.warning(
            "**AI features require an Anthropic API key.**\n\n"
            "Add it in Streamlit Cloud → App Settings → Secrets:\n"
            "```toml\n[anthropic]\napi_key = \"sk-ant-...\"\n```"
        )
        st.stop()

    df = load_data()

    # ── Section 1 · Executive Summary ───────────────────────────────────────────────────
    st.subheader("📊 Executive Safety Summary")
    st.caption("AI-generated analysis of your entire risk assessment dataset.")

    if "ai_summary" not in st.session_state:
        st.session_state.ai_summary = None

    if st.button("🔍 Generate Summary", use_container_width=True, disabled=df.empty):
        with st.container(border=True):
            st.session_state.ai_summary = st.write_stream(stream_summary(df))
        st.rerun()
    elif st.session_state.ai_summary:
        with st.container(border=True):
            st.markdown(st.session_state.ai_summary)

    if df.empty:
        st.info("Add some risk assessments first to enable AI analysis.")
        st.stop()

    st.divider()

    # ── Section 2 · Control Suggestions ────────────────────────────────────────────────
    st.subheader("🛡️ AI Control Suggestions")
    st.caption("Describe a hazard to receive AI-recommended controls using the control hierarchy.")

    with st.form("ai_controls_form"):
        cca, ccb = st.columns(2)
        ai_cat  = cca.selectbox("Hazard Category", HAZARD_CATEGORIES)
        ai_desc = st.text_area(
            "Hazard Description *", height=80,
            placeholder="Describe the specific hazard and who might be harmed.",
        )
        ccc, ccd = st.columns(2)
        ai_lik  = ccc.slider("Likelihood", 1, 5, 3)
        ai_sev  = ccd.slider("Severity",   1, 5, 3)
        ai_ctrl = st.text_area("Existing Controls (optional)", height=60)
        ai_go   = st.form_submit_button("💡 Suggest Controls", use_container_width=True)

    if ai_go:
        if not ai_desc.strip():
            st.warning("Please enter a hazard description.")
        else:
            with st.container(border=True):
                st.write_stream(stream_controls(ai_cat, ai_desc, ai_lik, ai_sev, ai_ctrl))

    st.divider()

    # ── Section 3 · AI Chat ─────────────────────────────────────────────────────────────
    st.subheader("💬 Chat with Your Safety Data")
    st.caption("Ask questions about your risk assessments in plain English.")

    if "chat_api" not in st.session_state:
        st.session_state.chat_api = []
    if "chat_ui" not in st.session_state:
        st.session_state.chat_ui = []

    for role, content in st.session_state.chat_ui:
        with st.chat_message(role):
            st.markdown(content)

    if prompt := st.chat_input("Ask about your safety data…"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_ui.append(("user", prompt))

        if not st.session_state.chat_api:
            api_messages = [{"role": "user", "content": (
                "I have the following H&S risk assessment data for my organisation:\n\n"
                f"{data_context(df)}\n\n"
                f"My question: {prompt}"
            )}]
        else:
            api_messages = st.session_state.chat_api + [{"role": "user", "content": prompt}]

        with st.chat_message("assistant"):
            response = st.write_stream(stream_chat(api_messages))

        st.session_state.chat_ui.append(("assistant", response))

        if not st.session_state.chat_api:
            st.session_state.chat_api = [
                api_messages[0],
                {"role": "assistant", "content": response},
            ]
        else:
            st.session_state.chat_api.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ])

    if st.session_state.chat_ui:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_api = []
            st.session_state.chat_ui = []
            st.rerun()


elif page == "🚨 Incident Management":
    from ai_advisor import ai_available, stream_incident_analysis, incident_data_context, stream_chat

    st.title("🚨 Incident Management")
    st.caption("Log, investigate and analyse workplace incidents — RIDDOR auto-classification included.")

    inc_df = load_incidents()

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Log Incident", "🔍 Investigate", "📊 Dashboard", "🤖 AI Analysis"])

    with tab1:
        st.subheader("Log a New Incident")
        with st.form("incident_form", clear_on_submit=True):
            st.subheader("1 · Incident Details")
            d1, d2, d3 = st.columns(3)
            inc_date    = d1.date_input("Date *", value=date.today())
            inc_time    = d2.text_input("Time (HH:MM)", placeholder="e.g. 14:30")
            reported_by = d3.text_input("Reported By *", placeholder="Your name")

            st.subheader("2 · Location & Classification")
            l1, l2, l3 = st.columns(3)
            inc_dept     = l1.selectbox("Department *", DEPARTMENTS)
            inc_location = l2.text_input("Location / Area *", placeholder="e.g. Warehouse Bay 3")
            inc_type     = l3.selectbox("Incident Type *", INCIDENT_TYPES)

            st.subheader("3 · Description")
            inc_desc = st.text_area(
                "What happened? *", height=100,
                placeholder="Describe the incident — what occurred, sequence of events, immediate outcome.",
            )

            st.subheader("4 · Injured Person")
            st.caption("Leave blank if not applicable (e.g. Near Miss or Dangerous Occurrence).")
            p1, p2, p3, p4 = st.columns(4)
            injured_name = p1.text_input("Name")
            injured_role = p2.text_input("Job Role / Title")
            injury_type  = p3.selectbox("Injury Type", INJURY_TYPES)
            body_part    = p4.text_input("Body Part Affected")

            st.subheader("5 · Treatment & Absence")
            t1, t2 = st.columns(2)
            treatment = t1.selectbox("Treatment Required", TREATMENT_TYPES)
            days_lost = int(t2.number_input("Working Days Lost", min_value=0, step=1, value=0))

            st.subheader("6 · Investigation (initial)")
            imm_cause   = st.text_area("Immediate Cause (optional)", height=60,
                                       placeholder="The direct act or condition that caused the incident.")
            root_cause  = st.text_area("Root Cause (optional)", height=60,
                                       placeholder="The underlying management system failure.")
            contributing = st.text_area("Contributing Factors (optional)", height=60,
                                        placeholder="Environmental, human, or organisational factors.")

            st.subheader("7 · Corrective Actions")
            actions      = st.text_area("Actions Required (optional)", height=80,
                                        placeholder="List corrective actions to prevent recurrence.")
            a1, a2       = st.columns(2)
            action_owner = a1.text_input("Action Owner", placeholder="Person responsible")
            action_due   = a2.date_input("Action Due Date", value=date.today() + timedelta(days=30))

            st.subheader("8 · Status")
            inc_status = st.selectbox("Initial Status", INCIDENT_STATUSES)

            submit_inc = st.form_submit_button("💾 Save Incident", use_container_width=True)

        if submit_inc:
            if not reported_by or not inc_location or not inc_desc:
                st.error("Please complete all required fields (marked *).")
            else:
                entry = {
                    "date": inc_date.strftime("%Y-%m-%d"),
                    "time": inc_time,
                    "department": inc_dept,
                    "location": inc_location,
                    "incident_type": inc_type,
                    "description": inc_desc,
                    "injured_person_name": injured_name,
                    "injured_person_role": injured_role,
                    "injury_type": injury_type,
                    "body_part_affected": body_part,
                    "treatment": treatment,
                    "days_lost": days_lost,
                    "immediate_cause": imm_cause,
                    "root_cause": root_cause,
                    "contributing_factors": contributing,
                    "corrective_actions": actions,
                    "action_owner": action_owner,
                    "action_due_date": action_due.strftime("%Y-%m-%d"),
                    "status": inc_status,
                    "reported_by": reported_by,
                }
                save_incident(entry)
                riddor_flag, riddor_cat = classify_riddor(entry)
                st.success("Incident logged successfully.")
                if riddor_flag:
                    st.error(
                        f"⚠️ **RIDDOR REPORTABLE — Category: {riddor_cat}**\n\n"
                        "This incident must be reported to the HSE within the statutory timeframe. "
                        "Visit the HSE RIDDOR online reporting service to submit the report."
                    )
                else:
                    st.info("ℹ️ Not RIDDOR reportable based on the information provided. Review if circumstances change.")

    with tab2:
        if inc_df.empty:
            st.info("No incidents logged yet. Use the 'Log Incident' tab to record your first incident.")
        else:
            open_mask = inc_df["status"] != "Closed"
            display_df = inc_df[open_mask] if open_mask.any() else inc_df
            options = {
                int(row["id"]): (
                    f"ID {int(row['id'])} | {row['incident_type']} — "
                    f"{row['department']} | {row['date']} | {row['status']}"
                )
                for _, row in display_df.iterrows()
            }
            sel_id = st.selectbox(
                "Select incident to investigate",
                options=list(options.keys()),
                format_func=lambda x: options[x],
            )
            if sel_id is not None:
                row = inc_df[inc_df["id"] == sel_id].iloc[0]
                riddor_badge = f"🔴 {row['riddor_category']}" if row["riddor_reportable"] else "🟢 Not reportable"
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Date:** {row['date']}")
                c1.markdown(f"**Department:** {row['department']}")
                c1.markdown(f"**Location:** {row['location']}")
                c2.markdown(f"**Reported by:** {row['reported_by']}")
                c2.markdown(f"**Treatment:** {row['treatment']}")
                c2.markdown(f"**Days Lost:** {int(row['days_lost'])}")
                c3.markdown(f"**RIDDOR:** {riddor_badge}")
                c3.markdown(f"**Status:** {row['status']}")
                st.markdown(f"**Description:** {row['description']}")
                st.divider()
                with st.form("investigate_form"):
                    st.subheader("Investigation Details")
                    imm  = st.text_area("Immediate Cause",    value=str(row.get("immediate_cause", "") or ""),    height=80)
                    root = st.text_area("Root Cause",         value=str(row.get("root_cause", "") or ""),         height=80)
                    cont = st.text_area("Contributing Factors", value=str(row.get("contributing_factors", "") or ""), height=80)

                    st.subheader("Corrective Actions")
                    acts  = st.text_area("Actions Required", value=str(row.get("corrective_actions", "") or ""), height=100)
                    ca1, ca2 = st.columns(2)
                    own   = ca1.text_input("Action Owner", value=str(row.get("action_owner", "") or ""))
                    try:
                        due_default = pd.to_datetime(row.get("action_due_date")).date()
                    except Exception:
                        due_default = date.today() + timedelta(days=30)
                    due   = ca2.date_input("Action Due Date", value=due_default)

                    new_st = st.selectbox(
                        "Status",
                        INCIDENT_STATUSES,
                        index=INCIDENT_STATUSES.index(row["status"]) if row["status"] in INCIDENT_STATUSES else 0,
                    )
                    save_inv = st.form_submit_button("💾 Save Investigation", use_container_width=True)

                if save_inv:
                    update_incident(int(sel_id), {
                        "immediate_cause": imm, "root_cause": root,
                        "contributing_factors": cont, "corrective_actions": acts,
                        "action_owner": own, "action_due_date": due.strftime("%Y-%m-%d"),
                        "status": new_st,
                    })
                    st.success("Investigation saved.")
                    st.rerun()

    with tab3:
        if inc_df.empty:
            st.info("No incidents to display yet.")
        else:
            inc_stats = get_incident_stats(inc_df)
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Total Incidents",    inc_stats["total"])
            k2.metric("Accidents",          inc_stats["accidents"])
            k3.metric("Near Misses",        inc_stats["near_misses"])
            k4.metric("RIDDOR Reportable",  inc_stats["riddor_count"])
            k5.metric("Open",               inc_stats["open"])
            k6.metric("Total Days Lost",    inc_stats["days_lost_total"])

            st.divider()

            with st.expander("🔍 Filters", expanded=False):
                fc1, fc2, fc3 = st.columns(3)
                dept_f = fc1.multiselect("Department",    inc_df["department"].unique().tolist(),    default=[])
                type_f = fc2.multiselect("Incident Type", inc_df["incident_type"].unique().tolist(), default=[])
                stat_f = fc3.multiselect("Status",        inc_df["status"].unique().tolist(),        default=[])

            filtered_inc = inc_df.copy()
            if dept_f:
                filtered_inc = filtered_inc[filtered_inc["department"].isin(dept_f)]
            if type_f:
                filtered_inc = filtered_inc[filtered_inc["incident_type"].isin(type_f)]
            if stat_f:
                filtered_inc = filtered_inc[filtered_inc["status"].isin(stat_f)]

            if filtered_inc.empty:
                st.warning("No records match the selected filters.")
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.plotly_chart(incident_type_bar(filtered_inc), use_container_width=True)
                with col_b:
                    st.plotly_chart(riddor_donut(filtered_inc), use_container_width=True)

                col_c, col_d = st.columns(2)
                with col_c:
                    st.plotly_chart(incident_department_chart(filtered_inc), use_container_width=True)
                with col_d:
                    st.plotly_chart(severity_treatment_heatmap(filtered_inc), use_container_width=True)

                if len(filtered_inc) >= 2:
                    st.plotly_chart(incident_trend_line(filtered_inc), use_container_width=True)

                riddor_items = filtered_inc[filtered_inc["riddor_reportable"].astype(bool)]
                if not riddor_items.empty:
                    st.divider()
                    st.error(f"⚠️ **{len(riddor_items)} RIDDOR Reportable Incident(s) — HSE notification required**")
                    st.dataframe(
                        riddor_items[[
                            "id", "date", "department", "incident_type",
                            "riddor_category", "treatment", "days_lost", "status",
                        ]].rename(columns={
                            "id": "ID", "date": "Date", "department": "Dept",
                            "incident_type": "Type", "riddor_category": "RIDDOR Category",
                            "treatment": "Treatment", "days_lost": "Days Lost", "status": "Status",
                        }),
                        use_container_width=True, hide_index=True,
                    )

    with tab4:
        if not ai_available():
            st.warning(
                "**AI features require an Anthropic API key.**\n\n"
                "Add it in Streamlit Cloud → App Settings → Secrets:\n"
                "```toml\n[anthropic]\napi_key = \"sk-ant-...\"\n```"
            )
        elif inc_df.empty:
            st.info("Log some incidents first to enable AI analysis.")
        else:
            st.subheader("📊 Incident Pattern Analysis")
            st.caption("AI-generated analysis of your incident data for systemic improvement.")

            if "inc_summary" not in st.session_state:
                st.session_state.inc_summary = None

            if st.button("🔍 Generate Incident Analysis", use_container_width=True):
                with st.container(border=True):
                    st.session_state.inc_summary = st.write_stream(stream_incident_analysis(inc_df))
                st.rerun()
            elif st.session_state.inc_summary:
                with st.container(border=True):
                    st.markdown(st.session_state.inc_summary)

            st.divider()
            st.subheader("💬 Chat about Incidents")
            st.caption("Ask questions about your incident data in plain English.")

            if "inc_chat_api" not in st.session_state:
                st.session_state.inc_chat_api = []
            if "inc_chat_ui" not in st.session_state:
                st.session_state.inc_chat_ui = []

            for role, content in st.session_state.inc_chat_ui:
                with st.chat_message(role):
                    st.markdown(content)

            if prompt := st.chat_input("Ask about your incident data…", key="inc_chat_input"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.inc_chat_ui.append(("user", prompt))

                if not st.session_state.inc_chat_api:
                    api_messages = [{"role": "user", "content": (
                        "I have the following workplace incident data for my organisation:\n\n"
                        f"{incident_data_context(inc_df)}\n\n"
                        f"My question: {prompt}"
                    )}]
                else:
                    api_messages = st.session_state.inc_chat_api + [{"role": "user", "content": prompt}]

                with st.chat_message("assistant"):
                    response = st.write_stream(stream_chat(api_messages))

                st.session_state.inc_chat_ui.append(("assistant", response))
                if not st.session_state.inc_chat_api:
                    st.session_state.inc_chat_api = [
                        api_messages[0],
                        {"role": "assistant", "content": response},
                    ]
                else:
                    st.session_state.inc_chat_api.extend([
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": response},
                    ])

            if st.session_state.inc_chat_ui:
                if st.button("🗑️ Clear Incident Chat"):
                    st.session_state.inc_chat_api = []
                    st.session_state.inc_chat_ui = []
                    st.rerun()


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
        row_id    = int(row["id"])
        rl, _     = classify_risk(int(row["risk_score"]))
        icon      = {"Low": "🟢", "Medium": "🟡", "High": "🔴", "Very High": "🟣"}.get(rl, "⚪")
        is_editing = st.session_state.get("editing_id") == row_id
        with st.expander(
            f"{icon} ID {row_id} | {row['hazard_category']} — "
            f"{row['department']} | Score: {int(row['risk_score'])} ({row['risk_level']}) | {row['status']}",
            expanded=is_editing,
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

            _last_by = row.get("last_edited_by", "")
            _last_at = row.get("last_edited_at", "")
            if pd.notna(_last_by) and str(_last_by).strip():
                st.caption(f"✏️ Last edited by **{_last_by}** on {_last_at}")

            sa, sb, sc, sd = st.columns([2, 1, 1, 1])
            new_status = sa.selectbox(
                "Update Status", ["Open", "In Progress", "Closed"],
                index=["Open", "In Progress", "Closed"].index(row["status"]),
                key=f"status_{row_id}",
            )
            if sb.button("💾 Save", key=f"upd_{row_id}"):
                update_status(row_id, new_status)
                st.rerun()
            if sc.button("✏️ Edit", key=f"edit_btn_{row_id}"):
                st.session_state["editing_id"] = row_id
                st.rerun()
            if sd.button("🗑️ Delete", key=f"del_{row_id}"):
                delete_entry(row_id)
                st.session_state.pop("editing_id", None)
                st.rerun()

            if is_editing:
                st.divider()
                st.subheader("✏️ Edit Assessment")
                with st.form(key=f"edit_form_{row_id}"):
                    ef1, ef2, ef3 = st.columns(3)
                    e_assessor   = ef1.text_input("Assessor Name", value=str(row["assessor"]))
                    _dept_idx    = DEPARTMENTS.index(row["department"]) if row["department"] in DEPARTMENTS else 0
                    e_department = ef2.selectbox("Department", DEPARTMENTS, index=_dept_idx)
                    e_location   = ef3.text_input("Location / Area", value=str(row["location"]))

                    ef4, ef5 = st.columns([1, 2])
                    _haz_idx     = HAZARD_CATEGORIES.index(row["hazard_category"]) if row["hazard_category"] in HAZARD_CATEGORIES else 0
                    e_hazard_cat  = ef4.selectbox("Hazard Category", HAZARD_CATEGORIES, index=_haz_idx)
                    e_hazard_desc = ef5.text_area("Hazard Description", value=str(row["hazard_description"]), height=70)
                    e_activity    = st.text_input("Activity / Task", value=str(row.get("activity", "") or ""))

                    ef6, ef7 = st.columns(2)
                    e_likelihood = ef6.slider("Likelihood", 1, 5, int(row["likelihood"]))
                    e_severity   = ef7.slider("Severity",   1, 5, int(row["severity"]))

                    e_existing = st.text_area("Existing Controls", value=str(row["existing_controls"]), height=70)
                    e_further  = st.text_area("Further Controls",  value=str(row.get("further_controls", "") or ""), height=70)

                    ef8, ef9 = st.columns(2)
                    e_res_like = ef8.slider("Residual Likelihood", 1, 5, int(row["residual_likelihood"]))
                    e_res_sev  = ef9.slider("Residual Severity",   1, 5, int(row["residual_severity"]))

                    ef10, ef11 = st.columns(2)
                    try:
                        _rev_date = pd.to_datetime(row["review_date"]).date()
                    except Exception:
                        _rev_date = date.today() + timedelta(days=90)
                    e_review_date = ef10.date_input("Next Review Date", value=_rev_date)
                    _stat_idx     = ["Open", "In Progress", "Closed"].index(row["status"])
                    e_status      = ef11.selectbox("Status", ["Open", "In Progress", "Closed"], index=_stat_idx)

                    e_edited_by = st.text_input("✏️ Edited by *", placeholder="Your name — required")

                    btn_save, btn_cancel = st.columns(2)
                    save_edit   = btn_save.form_submit_button("💾 Save Changes", use_container_width=True)
                    cancel_edit = btn_cancel.form_submit_button("✕ Cancel",       use_container_width=True)

                if cancel_edit:
                    st.session_state["editing_id"] = None
                    st.rerun()
                if save_edit:
                    if not e_edited_by.strip():
                        st.error("Please enter your name in 'Edited by'.")
                    else:
                        update_entry(row_id, {
                            "assessor": e_assessor, "department": e_department, "location": e_location,
                            "hazard_category": e_hazard_cat, "hazard_description": e_hazard_desc,
                            "activity": e_activity,
                            "likelihood": e_likelihood, "severity": e_severity,
                            "risk_score": e_likelihood * e_severity,
                            "existing_controls": e_existing, "further_controls": e_further,
                            "residual_likelihood": e_res_like, "residual_severity": e_res_sev,
                            "residual_risk_score": e_res_like * e_res_sev,
                            "review_date": e_review_date.strftime("%Y-%m-%d"),
                            "status": e_status,
                            "last_edited_by": e_edited_by.strip(),
                            "last_edited_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        st.session_state["editing_id"] = None
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
