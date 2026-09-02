# Demo Dashboard Guide

Developer handoff guide for `app/example_dashboard/demo_dashboard.py`.

Related issues: #33, #88, #89, #90, #94, #96.

## Purpose

The Streamlit dashboard is a demo/reference UI for frontend developers. It shows which endpoint each view calls, which request parameters matter, and which response fields drive each chart or table.

Each view includes:

- an `API` marker with endpoint, example request, example response and fields used
- metric help on charts, tables and KPIs
- collapsible inferential evidence boxes where the view compares two groups
- Italian and English labels

## Navigation

| View | Question answered | Endpoint | Data source |
| --- | --- | --- | --- |
| Job Demand Overview | What does this selected job-market slice look like? | `POST /projector/analyze-skills` | Tracker API/cache |
| Temporal Analysis | How does this job-market slice evolve over time? | `POST /projector/temporal-projections` | Tracker API/cache |
| Regional Temporal Analysis | Where and when does demand grow for selected filters? | `POST /projector/regional-temporal` | Tracker API/cache |
| Sector Overview | What does one sector look like in one year or between years? | `POST /projector/sectoral-snapshot` | PostgreSQL snapshots |
| Sector Skills Comparison | How do sectors compare on selected skills? | `POST /projector/sector-skills-comparison` | PostgreSQL snapshots |
| Regional Sector Distribution | Which sectors are strongest by region, and how do they evolve? | `POST /projector/regional-sectoral` | PostgreSQL snapshots |
| Skill Explorer | Where is one skill requested and how does it evolve? | `POST /projector/skill-explorer` | PostgreSQL snapshots or Tracker API/cache |

## View Details

### Job Demand Overview

Parameters: `keywords`, `min_date`, `max_date`, optional `locations`, optional demo NUTS flag.

Uses:

- `dimension_summary.jobs_analyzed`
- `dimension_summary.geo_breakdown`
- `insights.ranking`
- `insights.trends`
- `insights.regional`
- `insights.sectors`
- `insights.job_titles`
- `insights.employers`

### Temporal Analysis

Parameters: `keywords`, `min_date`, `max_date`, optional `locations`, `granularity`, `forecast_periods`, `top_k`.

Uses:

- `total_jobs`
- `insights.periods`
- `insights.skills[].series`
- `insights.skills[].forecast`

The baseline projection is descriptive, not predictive ML.

### Regional Temporal Analysis

Parameters: `keywords`, `min_date`, `max_date`, optional `locations`, `granularity`, `top_k_regions`, `top_k_skills`, demo NUTS flag.

Uses:

- `regional_temporal.raw`
- `regional_temporal.nuts1`
- `regional_temporal.nuts2`
- `regional_temporal.nuts3`
- `area.periods`
- `area.top_skills`

The user chooses the territorial level inside the view.

Inferential layer:

- endpoint: `POST /projector/statistical-comparison`
- comparison type: `regional_skill`
- shown when a regional skill can be compared with the remaining regions

### Sector Overview

Parameters: `sector`, `region`, mode `Snapshot` or `Sector Evolution`.

Snapshot uses one `year`.

Evolution uses `from year` and `to year`.

Uses:

- `sectors[].job_count`
- `sectors[].job_share`
- `sectors[].total_skill_mentions`
- `sectors[].unique_skills`
- `sectors[].top_skills`
- `sectors[].all_skills`
- `sectors[].top_job_titles`
- `sectors[].evolution`

The bubble chart uses `all_skills` when available.

Inferential layer:

- endpoint: `POST /projector/statistical-comparison`
- comparison type: `sector_evolution`
- shown in Sector Evolution mode to validate the observed sector change between two years

### Sector Skills Comparison

Parameters: `year`, optional `region`, selected `sectors`, selected `skills`, `metric`.

For `Growth between years`, the UI switches from a single year selector to `from year` and `to year`.

Uses:

- `matrix[].sector_label`
- `matrix[].label`
- `matrix[].count`
- `matrix[].share`
- `matrix[].rank`
- `matrix[].growth_value`
- `matrix[].value`
- `matrix[].display_value`

Inferential layer:

- endpoint: `POST /projector/statistical-comparison`
- comparison type: `sector_skill`
- shown for a selected skill/sector pair when enough counts are available

### Regional Sector Distribution

Parameters: mode, year or year range, region, regional level, sectors, metric, top-k.

Modes:

- `Snapshot`: reads `regional_sectoral.{raw,nuts1,nuts2,nuts3}`
- `Evolution`: reads `regional_sectoral_evolution`
- `Time series`: reads `regional_sectoral_time_series`

Uses:

- `area.code`
- `area.total_jobs`
- `area.top_sectors`
- `regional_sectoral_evolution[].current_count`
- `regional_sectoral_evolution[].reference_count`
- `regional_sectoral_evolution[].delta`
- `regional_sectoral_evolution[].growth`
- `regional_sectoral_time_series[].series`

Inferential layer:

- endpoint: `POST /projector/statistical-comparison`
- comparison type: `regional_sector`
- shown when one region-sector relationship can be compared with the rest of the market

### Skill Explorer

Parameters: search by `skill_label` or `skill_id`, mode `snapshot` or `live`, years or date range, optional region, top-k.

Snapshot mode uses PostgreSQL annual snapshots.

Live mode uses Tracker API/cache and should use shorter date windows.

Uses:

- `skill`
- `total_mentions`
- `sectors`
- `regions`
- `time_series`
- `warnings`

## Data Source Rules

- User-facing annual sector views read PostgreSQL snapshots.
- Live/date-range views read Tracker API through the cache layer.
- Backfill, refresh and scheduler scripts are the components that populate PostgreSQL snapshots from Tracker.
- No dashboard control asks users to choose cache/static/live internals except Skill Explorer, where `snapshot` and `live` are part of the analytical question.

## Statistical Evidence Box

The box is always collapsed by default and appears inside comparison views only.

It shows:

- the tested question
- method description
- p-value, evidence level and practical relevance
- observed group shares
- share difference in percentage points
- relative risk and odds ratio when computable
- observed 2x2 table
- expected 2x2 table
- assumptions, limitations and warnings

Use it as validation context, not as a primary navigation area.
