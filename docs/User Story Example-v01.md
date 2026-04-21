# User Story Example

This example is aligned with the current Projector API and dashboard behavior.

## User Story

As a labor-market analyst, I want to explore demand for a skill or keyword across time, geography and sectors, so that I can identify market priorities and sector-specific skill gaps.

## Flow

1. The analyst opens the Streamlit dashboard.
2. The analyst enters one or more keywords.
3. The analyst selects a date range and optional location.
4. The dashboard calls `POST /projector/analyze-skills`.
5. The backend fetches matching Tracker jobs, enriches metadata and returns aggregated intelligence.
6. The analyst reviews skill rankings, trends, geography, employers and sectoral views.

## Sectoral Variant

If the analyst enables sectoral intelligence, the dashboard sends:

```text
include_sectoral=true
sector_system=both
sector_level=nace_section
```

The response includes:
- ISCO sectoral data under `insights.sectoral_views.isco`
- NACE level data under `insights.sectoral_views.nace.levels`
- display names under `insights.sector_view_names`

## Acceptance Criteria

- The user can launch a full analysis from the dashboard.
- The dashboard can render skills, trends, geography, employers and titles.
- The dashboard can switch between ISCO and NACE sector views.
- NACE level switching updates the active NACE sectoral payload.
- The stop button calls `POST /projector/stop` and treats it as cooperative cancellation.
