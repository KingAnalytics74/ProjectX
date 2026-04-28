import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


RISK_COLOURS = {
    "Low": "#2ecc71",
    "Medium": "#f39c12",
    "High": "#e74c3c",
    "Very High": "#8e44ad",
}


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
                font=dict(color="white", size=11, family="Arial Black"),
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
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
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
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
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
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
        showlegend=False,
    )
    return fig


def risk_trend_chart(df: pd.DataFrame) -> go.Figure:
    if "date" not in df.columns or df["date"].isna().all():
        return go.Figure()
    trend = (
        df.groupby(pd.to_datetime(df["date"]).dt.to_period("M"))["risk_score"]
        .mean()
        .reset_index()
    )
    trend["date"] = trend["date"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["date"], y=trend["risk_score"],
        mode="lines+markers",
        line=dict(color="#3498db", width=2),
        marker=dict(size=8, color="#3498db"),
        fill="tozeroy",
        fillcolor="rgba(52,152,219,0.15)",
        name="Avg Monthly Risk",
    ))
    fig.add_hline(y=12, line_dash="dash", line_color="#e74c3c",
                  annotation_text="High Risk Threshold", annotation_position="top left")
    fig.update_layout(
        title="Average Risk Score Trend Over Time",
        xaxis_title="Month",
        yaxis_title="Avg Risk Score",
        height=320,
        margin=dict(l=40, r=20, t=40, b=40),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
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
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
