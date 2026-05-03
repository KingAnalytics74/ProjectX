# Safety Intelligence Tool

A data-driven health & safety risk assessment platform built with Python and Streamlit, aligned to NEBOSH standards.

## Features

- **Risk Assessment Form** — NEBOSH 5×5 likelihood × severity scoring
- **Dashboard** — risk matrix heatmap, hazard frequency, department hotspots
- **Statistical Process Control** — I-MR charts, Nelson Rules, process capability (Cpu)
- **Alerts & Insights** — overdue review alerts, department risk velocity, keyword intelligence
- **All Assessments** — full records with search, status updates, and CSV export
- **Supabase integration** — persistent cloud database with CSV fallback

## Tech Stack

- Python · Streamlit · Plotly · Pandas · NumPy · Supabase (PostgREST)

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Add Supabase secrets to `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://your-project.supabase.co"
key = "your-anon-public-key"
```

4. Run: `streamlit run app.py`

## Database Setup (Supabase)

Run this SQL in Supabase → SQL Editor:

```sql
create table if not exists risk_assessments (
    id                   bigserial primary key,
    date                 date,
    assessor             text,
    department           text,
    location             text,
    hazard_category      text,
    hazard_description   text,
    activity             text,
    likelihood           int,
    severity             int,
    risk_score           int,
    risk_level           text,
    existing_controls    text,
    further_controls     text,
    residual_likelihood  int,
    residual_severity    int,
    residual_risk_score  int,
    residual_risk_level  text,
    review_date          date,
    status               text
);

alter table risk_assessments enable row level security;
create policy "anon_select" on risk_assessments for select using (true);
create policy "anon_insert" on risk_assessments for insert with check (true);
create policy "anon_update" on risk_assessments for update using (true) with check (true);
create policy "anon_delete" on risk_assessments for delete using (true);
```

## Deployment

Deploy on [Streamlit Cloud](https://streamlit.io/cloud) — connect your GitHub repo and add secrets in the app settings.
