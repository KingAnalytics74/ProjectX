import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


RISK_COLOURS = {
    "Low": "#27ae60",
    "Medium": "#e67e22",
    "High": "#e74c3c",
    "Very High": "#8e44ad",
}

_PAPER = "#FFFFFF"
_PLOT  = "#F0F2F6"
_FONT  = "#262730"


def risk_matrix_heatmap(df: pd.DataFrame) -> go.Figure:
    """5×5 risk matrix with scatter points for each assessment."""
    z = [
        [1,  2,  3,  4,  5],
        [2,  4,  6,  8,  10],
        [3,  6,  9,  12, 15],
        [4,  8,  12, 16, 20],
        [5,  10, 15, 20, 25],
    ]
    cell_colours = []
    for row in z:
        colour_row = []
        for val in row:
            if val <= 6:
                colour_row.append("#2ecc71")
            elif val <= 11:
                colour_row.append("#f39c12")
            elif val <= 16:
                colour_row.append("#e74c3c")
            else:
                colour_row.append("#8e44ad")
        cell_colours.append(colour_row)

    fig = go.Figure()

    for r_idx, row in enumerate(z):
        for c_idx, val in enumerate(row):
            fig.add_shape(
                type="rect",
                x0=c_idx + 0.5, x1=c_idx + 1.5,
                y0=r_idx + 0.5, y1=r_idx + 1.5,
                fillcolor=cell_colours[r_idx][c_idx],
                line=dict(color="white", width=1),
                opacity=0.6,
            )
            fig.add_annotation(
                x=c_idx + 1, y=r_idx + 1,
                text=str(val), showarrow=False,
                font=dict(color="white", size=11, family="Arial Black",),
            )

    if not df.empty:
        for _, row in df.iterrows():
            jitter_x = row["severity"] + (hash(str(row["id"])) % 10) * 0.04 - 0.18
            jitter_y = row["likelihood"] + (hash(str(row["id"]) + "y") % 10) * 0.04 - 0.18
            colour = RISK_COLOURS.get(row["risk_level"], "#555")
            fig.add_trace(go.Scatter(
                x=[jitter_x], y=[jitter_y],
                mode="markers",
                marker=dict(size=10, color=colour, line=dict(color="white", width=1.5)),
                name=row["hazard_category"],
                text=f"ID {int(row['id'])}: {row['hazard_category']}<br>"
                     f"Dept: {row['department']}<br>"
                     f"Score: {int(row['risk_score'])} ({row['risk_level']})",
                hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            ))

    fig.update_layout(
        title="Risk Matrix",
        xaxis=dict(title="Severity", tickvals=list(range(1, 6)), range=[0.5, 5.5]),
        yaxis=dict(title="Likelihood", tickvals=list(range(1, 6)), range=[0.5, 5.5]),
        height=420,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
    )
    return fig


def hazard_bar_chart(df: pd.DataFrame) -> go.Figure:
    counts = (
        df.groupby(["hazard_category", "risk_level"])
        .size()
        .reset_index(name="count")
    )
    fig = px.bar(
        counts, x="hazard_category", y="count", color="risk_level",
        color_discrete_map=RISK_COLOURS,
        category_orders={"risk_level": ["Low", "Medium", "High", "Very High"]},
        labels={"hazard_category": "Hazard Category", "count": "Count", "risk_level": "Risk Level"},
        title="Hazard Frequency by Category",
    )
    fig.update_layout(
        xaxis_tickangle=-35,
        height=380,
        margin=dict(l=40, r=20, t=40, b=100),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def department_risk_chart(df: pd.DataFrame) -> go.Figure:
    dept = (
        df.groupby("department")["risk_score"]
        .agg(["mean", "max", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_risk", "max": "max_risk", "count": "assessments"})
        .sort_values("avg_risk", ascending=True)
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dept["avg_risk"], y=dept["department"],
        orientation="h",
        marker_color=[
            "#8e44ad" if v > 16 else "#e74c3c" if v > 11 else "#f39c12" if v > 6 else "#2ecc71"
            for v in dept["avg_risk"]
        ],
        name="Avg Risk Score",
        text=[f"{v:.1f}" for v in dept["avg_risk"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Department Risk Hotspots (Avg Score)",
        xaxis=dict(title="Average Risk Score", range=[0, 27]),
        height=max(300, 60 * len(dept) + 80),
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        showlegend=False,
    )
    return fig


def risk_trend_chart(df: pd.DataFrame) -> go.Figure:
    if "date" not in df.columns or df["date"].isna().all():
        return go.Figure()
    tmp = df.copy()
    tmp["_month"] = pd.to_datetime(tmp["date"]).dt.to_period("M")
    trend = tmp.groupby("_month")["risk_score"].mean().reset_index()
    trend["label"] = trend["_month"].astype(str)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["label"], y=trend["risk_score"],
        mode="lines+markers",
        line=dict(color="#3498db", width=2),
        marker=dict(size=8, color="#3498db"),
        fill="tozeroy",
        fillcolor="rgba(52,152,219,0.15)",
        name="Avg Monthly Risk",
    ))

    if len(trend) >= 2:
        x_idx = np.arange(len(trend))
        coeffs = np.polyfit(x_idx, trend["risk_score"].values, 1)
        last_period = trend["_month"].iloc[-1]
        f_labels = [(last_period + i).to_timestamp().strftime("%Y-%m") for i in range(1, 4)]
        f_vals   = [max(1.0, float(np.polyval(coeffs, len(trend) - 1 + i))) for i in range(1, 4)]
        fig.add_trace(go.Scatter(
            x=[trend["label"].iloc[-1]] + f_labels,
            y=[float(trend["risk_score"].iloc[-1])] + f_vals,
            mode="lines+markers",
            line=dict(color="#e67e22", width=2, dash="dot"),
            marker=dict(size=7, color="#e67e22", symbol="diamond"),
            name="3-Month Forecast",
        ))

    fig.add_hline(y=12, line_dash="dash", line_color="#e74c3c",
                  annotation_text="High Risk Threshold", annotation_position="top left")
    fig.update_layout(
        title="Average Risk Score — Historical & Forecast",
        xaxis_title="Month",
        yaxis_title="Avg Risk Score",
        height=340,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def risk_reduction_chart(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    ids = [str(int(i)) for i in df["id"]]
    fig.add_trace(go.Bar(
        x=ids, y=df["risk_score"],
        name="Initial Risk", marker_color="#e74c3c", opacity=0.8
    ))
    fig.add_trace(go.Bar(
        x=ids, y=df["residual_risk_score"],
        name="Residual Risk", marker_color="#2ecc71", opacity=0.8
    ))
    fig.update_layout(
        barmode="overlay",
        title="Risk Reduction After Controls",
        xaxis_title="Assessment ID",
        yaxis_title="Risk Score",
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def monthly_volume_chart(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["_month"] = pd.to_datetime(tmp["date"]).dt.to_period("M")
    vol = tmp.groupby("_month").size().reset_index(name="count")
    vol["label"] = vol["_month"].astype(str)
    fig = go.Figure(go.Bar(
        x=vol["label"], y=vol["count"],
        marker_color="#004B87",
        text=vol["count"], textposition="outside",
    ))
    fig.update_layout(
        title="Monthly Assessment Volume",
        xaxis_title="Month",
        yaxis_title="Assessments Submitted",
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        showlegend=False,
    )
    return fig


def risk_level_stacked_chart(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["_month"] = pd.to_datetime(tmp["date"]).dt.to_period("M").astype(str)
    counts = tmp.groupby(["_month", "risk_level"]).size().reset_index(name="count")
    fig = go.Figure()
    for level in ["Low", "Medium", "High", "Very High"]:
        subset = counts[counts["risk_level"] == level]
        fig.add_trace(go.Bar(
            x=subset["_month"], y=subset["count"],
            name=level,
            marker_color=RISK_COLOURS[level],
        ))
    fig.update_layout(
        barmode="stack",
        title="Risk Level Distribution by Month",
        xaxis_title="Month",
        yaxis_title="Count",
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def control_effectiveness_chart(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["_month"] = pd.to_datetime(tmp["date"]).dt.to_period("M")
    tmp["reduction"] = tmp["risk_score"] - tmp["residual_risk_score"]
    eff = tmp.groupby("_month")["reduction"].mean().reset_index()
    eff["label"] = eff["_month"].astype(str)
    fig = go.Figure(go.Scatter(
        x=eff["label"], y=eff["reduction"],
        mode="lines+markers",
        line=dict(color="#27ae60", width=2),
        marker=dict(size=8, color="#27ae60"),
        fill="tozeroy",
        fillcolor="rgba(39,174,96,0.12)",
        name="Avg Risk Reduction",
    ))
    fig.update_layout(
        title="Average Risk Reduction by Controls (per Month)",
        xaxis_title="Month",
        yaxis_title="Avg Score Reduction",
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_PLOT,
        font=dict(color=_FONT),
        showlegend=False,
    )
    return fig


def department_trend_lines(df: pd.DataFrame) -> go.Figure:
    tmp = df.copy()
    tmp["_month"] = pd.to_datetime(tmp["date"]).dt.to_period("M").astype(str)
    dept_trend = tmp.groupby(["_month", "department"])["risk_score"].mean().reset_index()
    fig = go.Figure()
    for dept in dept_trend["department"].unique():
        subset = dept_trend[dept_trend["department"] == dept]
        fig.add_trace(go.Scatter(
            x=subset["_month"], y=subset["risk_score"],
            mode="lines+markers", name=dept,
            line=dict(width=2), marker=dict(size=6),
        ))
    fig.update_layout(
        title="Department Risk Score Over Time",
        xaxis_title="Month", yaxis_title="Avg Risk Score",
        height=380,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor=_PAPER, plot_bgcolor=_PLOT, font=dict(color=_FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
    )
    return fig


def spc_imr_chart(labels: list, values: list, signal_indices: set) -> go.Figure:
    if len(values) < 2:
        return go.Figure()
    x_bar  = float(np.mean(values))
    mr_bar = float(np.mean(np.abs(np.diff(values))))
    sigma  = mr_bar / 1.128
    ucl    = x_bar + 3 * sigma
    lcl    = max(1.0, x_bar - 3 * sigma)
    u2s    = x_bar + 2 * sigma
    l2s    = x_bar - 2 * sigma
    u1s    = x_bar + sigma
    l1s    = x_bar - sigma

    point_colours = ["#e74c3c" if i in signal_indices else "#004B87" for i in range(len(values))]

    fig = go.Figure()
    fig.add_hrect(y0=u2s, y1=ucl,  fillcolor="rgba(231,76,60,0.07)",  line_width=0)
    fig.add_hrect(y0=lcl, y1=l2s,  fillcolor="rgba(231,76,60,0.07)",  line_width=0)
    fig.add_hrect(y0=u1s, y1=u2s,  fillcolor="rgba(230,126,34,0.06)", line_width=0)
    fig.add_hrect(y0=l2s, y1=l1s,  fillcolor="rgba(230,126,34,0.06)", line_width=0)
    fig.add_hline(y=ucl,   line_dash="dash",  line_color="#e74c3c", line_width=1.5,
                  annotation_text=f"UCL = {ucl:.2f}", annotation_position="top right")
    fig.add_hline(y=x_bar, line_dash="solid", line_color="#27ae60", line_width=2,
                  annotation_text=f"CL = {x_bar:.2f}",  annotation_position="top right")
    if lcl > 1.0:
        fig.add_hline(y=lcl, line_dash="dash", line_color="#e74c3c", line_width=1.5,
                      annotation_text=f"LCL = {lcl:.2f}", annotation_position="bottom right")
    for y, label in [(u2s, "+2σ"), (l2s, "−2σ"), (u1s, "+1σ"), (l1s, "−1σ")]:
        colour = "#e67e22" if "2σ" in label else "#95a5a6"
        fig.add_hline(y=y, line_dash="dot", line_color=colour, line_width=1,
                      annotation_text=label, annotation_position="right")
    fig.add_trace(go.Scatter(
        x=labels, y=values,
        mode="lines+markers",
        line=dict(color="#004B87", width=2),
        marker=dict(size=11, color=point_colours, line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{x}</b><br>Avg Risk: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="I Chart — Monthly Average Risk Score",
        xaxis_title="Month", yaxis_title="Avg Risk Score",
        yaxis=dict(range=[max(0, lcl - sigma), ucl + sigma]),
        height=420,
        margin=dict(l=40, r=110, t=50, b=40),
        paper_bgcolor=_PAPER, plot_bgcolor=_PLOT, font=dict(color=_FONT),
        showlegend=False,
    )
    return fig


def insights_risk_heatmap(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for lik in range(1, 6):
        for sev in range(1, 6):
            score = lik * sev
            if score <= 6:
                colour = "#2ecc71"
            elif score <= 11:
                colour = "#f39c12"
            elif score <= 16:
                colour = "#e74c3c"
            else:
                colour = "#8e44ad"
            fig.add_shape(
                type="rect",
                x0=lik - 0.5, x1=lik + 0.5,
                y0=sev - 0.5, y1=sev + 0.5,
                fillcolor=colour, line=dict(color="white", width=1),
                opacity=0.55,
            )
            fig.add_annotation(
                x=lik, y=sev, text=str(score), showarrow=False,
                font=dict(color="white", size=12, family="Arial Black"),
            )
    if not df.empty:
        for _, row in df.iterrows():
            jx = row["likelihood"] + (hash(str(row["id"])) % 10) * 0.04 - 0.18
            jy = row["severity"] + (hash(str(row["id"]) + "y") % 10) * 0.04 - 0.18
            fig.add_trace(go.Scatter(
                x=[jx], y=[jy], mode="markers",
                marker=dict(size=11, color=RISK_COLOURS.get(row["risk_level"], "#555"),
                            line=dict(color="white", width=1.5)),
                text=(f"ID {int(row['id'])}: {row['hazard_category']}<br>"
                      f"Dept: {row['department']}<br>"
                      f"Score: {int(row['risk_score'])} ({row['risk_level']})"),
                hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            ))
    fig.update_layout(
        title="Risk Matrix — Live Data (Likelihood × Severity)",
        xaxis=dict(
            title="Likelihood →",
            tickvals=list(range(1, 6)),
            ticktext=["1 Rare", "2 Unlikely", "3 Possible", "4 Likely", "5 Almost Certain"],
            range=[0.5, 5.5],
        ),
        yaxis=dict(
            title="Severity →",
            tickvals=list(range(1, 6)),
            ticktext=["1 Negligible", "2 Minor", "3 Moderate", "4 Major", "5 Catastrophic"],
            range=[0.5, 5.5],
        ),
        height=500,
        margin=dict(l=130, r=20, t=50, b=110),
        paper_bgcolor=_PAPER, plot_bgcolor=_PLOT, font=dict(color=_FONT),
        showlegend=False,
    )
    return fig


def spc_mr_chart(labels: list, mr_values: list, ucl_mr: float, cl_mr: float) -> go.Figure:
    signal_idx  = {i for i, v in enumerate(mr_values) if v > ucl_mr}
    bar_colours = ["#e74c3c" if i in signal_idx else "#8e44ad" for i in range(len(mr_values))]
    fig = go.Figure()
    fig.add_hline(y=ucl_mr, line_dash="dash",  line_color="#e74c3c", line_width=1.5,
                  annotation_text=f"UCL = {ucl_mr:.2f}", annotation_position="top right")
    fig.add_hline(y=cl_mr,  line_dash="solid", line_color="#27ae60", line_width=2,
                  annotation_text=f"R̄ = {cl_mr:.2f}",   annotation_position="top right")
    fig.add_trace(go.Bar(
        x=labels[1:], y=mr_values,
        marker_color=bar_colours,
        hovertemplate="<b>%{x}</b><br>MR: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="MR Chart — Moving Range (Process Variability)",
        xaxis_title="Month", yaxis_title="Moving Range",
        height=300,
        margin=dict(l=40, r=110, t=50, b=40),
        paper_bgcolor=_PAPER, plot_bgcolor=_PLOT, font=dict(color=_FONT),
        showlegend=False,
    )
    return fig
