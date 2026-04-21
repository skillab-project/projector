# Overview

SKILLAB Projector is a FastAPI analytics layer on top of the SKILLAB Tracker.

The Tracker returns job-posting data. The Projector turns that data into aggregated intelligence for dashboards, analysts and integration clients.

## What It Answers

The service helps answer:

- which skills are most requested in a selected market slice,
- which skills are emerging, declining or newly appearing,
- which employers and job titles dominate hiring volume,
- which locations show stronger concentration for a skill,
- which skills characterize ISCO or NACE sectors,
- how observed skills compare with ESCO canonical and matrix references.

## Main Users

Developers:
- need a stable API that returns aggregated intelligence instead of raw job lists.

Dashboard authors:
- need ready-to-visualize structures for rankings, trends, maps and sector drill-downs.

Analysts and stakeholders:
- need interpretable indicators without reading source code.

## Public Endpoints

- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

The main endpoint is `/projector/analyze-skills`.

## Main Output Areas

`/projector/analyze-skills` returns:

- `dimension_summary`: analyzed job count and raw geographic breakdown,
- `insights.ranking`: paginated top-skill ranking,
- `insights.sectors`: base ISCO-oriented sector counts,
- `insights.job_titles`: top job titles,
- `insights.employers`: top employers,
- `insights.trends`: market and skill trend analysis,
- `insights.regional`: raw and NUTS-like geographic projections,
- `insights.sectoral*`: optional ISCO/NACE sectoral intelligence.

## Sector Systems

ISCO is occupation-based:

```text
job -> occupation -> isco_group -> ISCO label
```

NACE is economic-activity-based:

```text
job -> occupation -> ESCO-NACE crosswalk -> NACE code/title
```

Both systems are useful and intentionally coexist:
- ISCO is closer to occupational structure,
- NACE is closer to economic activity.

In NACE mode, canonical and matrix views are ESCO-derived projections aggregated through the ESCO-NACE crosswalk.

## Current Entry Points

Backend:

```bash
uvicorn app.main:app --reload
```

Dashboard:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```
