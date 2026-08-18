# Overview

SKILLAB Projector is a FastAPI analytics layer on top of the SKILLAB Tracker.

The Tracker returns job postings. The Projector turns those jobs into aggregated intelligence for dashboards, analysts, and integration clients.

## What It Answers

- which skills are most requested in a selected market slice
- which skills are emerging, declining, or newly appearing
- which employers and job titles dominate hiring volume
- which locations show stronger concentration for a skill
- which Tracker API sectors contain each skill
- which skills are important inside a selected sector

## Main Users

Developers need a stable API that returns aggregated intelligence instead of raw job lists.

Dashboard authors need ready-to-visualize structures for rankings, trends, maps, and sector drill-downs.

Analysts need interpretable indicators without reading source code.

## Forecasting Scope

Current forecasting-like behavior is trend monitoring and period comparison over observed Tracker jobs.

Predictive forecasting, ML models and XAI forecast explanations are not implemented yet. See
[Forecasting scope](forecasting-scope.md).

## Public Endpoints

- `GET /projector/health`
- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

The main endpoint is `/projector/analyze-skills`.

## Main Output Areas

`/projector/analyze-skills` returns:

- `dimension_summary`: analyzed job count and raw geographic breakdown
- `insights.ranking`: paginated top-skill ranking
- `insights.sectors`: Tracker sector counts from `job["sectors"]`
- `insights.job_titles`: top job titles
- `insights.employers`: top employers
- `insights.trends`: market and skill trend analysis
- `insights.regional`: raw and NUTS-like geographic projections
- `insights.sectoral_views.nace`: observed sector-skill intelligence from Tracker job sectors

## Sector Model

Sector intelligence is API-only:

```text
job["sectors"] x job["skills"] -> sector-skill matrix
```

The runtime does not use local occupation-sector files, local occupation-skill files, hierarchy files, or workbook mappings for sector intelligence.

## Current Entry Points

Backend:

```bash
uvicorn app.main:app --reload
```

Dashboard:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```
