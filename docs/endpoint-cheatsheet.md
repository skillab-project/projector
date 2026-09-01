# Endpoint Cheatsheet

This page is the quick integration view for consumers of the Projector API.

For full field details, see [API reference](api-reference.md) and [Data model](data-model.md).

## Quick Map

| Endpoint | Use it when you need | Returns in one sentence |
| --- | --- | --- |
| `POST /projector/analyze-skills` | Job Demand Overview | Composition of a selected job-market slice: skills, sectors, employers, titles, trends and geography |
| `POST /projector/regional-temporal` | Regional Temporal Analysis | Regional demand by period, with top skills per region |
| `POST /projector/skill-explorer` | Skill Explorer | One skill distributed across sectors, regions and time |
| `POST /projector/sectoral-snapshot` | One-sector yearly snapshot or evolution | Static yearly sector rows enriched with skills, job titles and evolution metrics |
| `POST /projector/sector-skills-comparison` | Multi-sector heatmap | Sectors x skills matrix for count, share, rank or growth |
| `POST /projector/regional-sectoral` | Regional sector distribution | Static yearly region-sector distribution, plus optional evolution or time series |
| `POST /projector/sectoral-intelligence` | Legacy/drill-down sector detail | Observed sector-skill details from Tracker jobs |
| `POST /projector/emerging-skills` | Only trend information | Market volume trend plus emerging, declining, stable and new-entry skills |
| `POST /projector/temporal-projections` | Temporal Analysis | Monthly, quarterly or yearly evolution of the selected job-market slice |
| `POST /projector/statistical-comparison` | Inferential evidence layer | 2x2 chi-square evidence with p-value, effect size, observed/expected tables, ratios and warnings |
| `POST /projector/stop` | To interrupt a long analysis | Acknowledgement that a cooperative stop signal was sent |

## `POST /projector/analyze-skills`

Main endpoint for Job Demand Overview. It describes the composition of the selected job-market slice.

### Minimal Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31"
```

### Optional Sectoral Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "include_sectoral=true" \
  -d "sector_system=nace"
```

### What It Returns

```json
{
  "status": "completed",
  "dimension_summary": {
    "jobs_analyzed": 0,
    "geo_breakdown": []
  },
  "insights": {
    "ranking": [],
    "sectors": [],
    "job_titles": [],
    "employers": [],
    "trends": {},
    "regional": {},
    "sectoral": null,
    "sectoral_mode": null,
    "sectoral_views": null,
    "sector_view_names": null
  }
}
```

### How To Read It

| Field | Meaning | Typical UI use |
| --- | --- | --- |
| `status` | Whether the analysis completed or stopped | Request state badge |
| `dimension_summary.jobs_analyzed` | Number of Tracker jobs analyzed | KPI card |
| `dimension_summary.geo_breakdown` | Raw job counts by location code | Small table or map input |
| `insights.ranking` | Top skills with count and sector context | Top skills chart |
| `insights.sectors` | Tracker sector counts | Sector bar chart |
| `insights.job_titles` | Most frequent job titles | Job-title leaderboard |
| `insights.employers` | Most frequent employers | Employer leaderboard |
| `insights.trends` | Volume growth and skill trend changes | Trend tab |
| `insights.regional` | Raw and NUTS-like area breakdowns with specialization | Map and regional detail |
| `insights.sectoral` | Selected/default sectoral intelligence payload | Backward-compatible sector panel |
| `insights.sectoral_views` | NACE wrapper with Tracker sector items | Sector detail views |
| `insights.sector_view_names` | Display labels for observed views | UI labels |

### Sectoral Meaning In One Minute

When `include_sectoral=false`, ignore the `sectoral*` fields.

When `include_sectoral=true`:
- sectors come from Tracker `job["sectors"]`,
- skills come from Tracker `job["skills"]`,
- observed sector-skill counts come from job co-occurrence,
- no ISCO, canonical, matrix, or ESCO-NACE crosswalk data is used.

Important: sector totals are relationship counts. A job with multiple sectors contributes to each listed sector.

## `POST /projector/regional-temporal`

Use this for Regional Temporal Analysis. It compares regions over a live date range.

```bash
curl -X POST "http://127.0.0.1:8000/projector/regional-temporal" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "granularity=monthly"
```

Main response block:

```json
{
  "regional_temporal": {
    "raw": [],
    "nuts1": [],
    "nuts2": [],
    "nuts3": []
  }
}
```

Each area returns `code`, `total_jobs`, `market_share`, `periods` and `top_skills`.

## `POST /projector/skill-explorer`

Use this when the UI starts from a skill rather than a job keyword or sector.

```bash
curl -X POST "http://127.0.0.1:8000/projector/skill-explorer" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "skill_label=Python" \
  -d "mode=snapshot" \
  -d "start_year=2023" \
  -d "end_year=2024"
```

Main response fields:

| Field | Meaning |
| --- | --- |
| `skill` | Matched skill id/label |
| `total_mentions` | Total selected-skill mentions |
| `sectors` | Sector distribution for the selected skill |
| `regions` | Regional distribution for the selected skill |
| `time_series` | Skill mentions by year or live date bucket |
| `warnings` | Missing snapshot or low-data warnings |

## `POST /projector/regional-sectoral`

Use this for yearly regional x sector views. It reads PostgreSQL snapshots and does not perform live Tracker aggregation.

```bash
curl -X POST "http://127.0.0.1:8000/projector/regional-sectoral" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "locations=IT"
```

Main response block:

```json
{
  "regional_sectoral": {
    "raw": [],
    "nuts1": [],
    "nuts2": [],
    "nuts3": []
  }
}
```

Each area returns `code`, `total_jobs`, and `top_sectors`. Each sector item returns `sector`, `sector_code`, `count`, `share_in_region`, and `specialization`.

Optional modes:

- `reference_year`: returns `regional_sectoral_evolution`
- `start_year` / `end_year`: returns `regional_sectoral_time_series`
- `level`: chooses `raw`, `nuts1`, `nuts2` or `nuts3` for optional blocks
- `metric`: chooses `count`, `share` or `growth` as displayed value

## `POST /projector/sectoral-snapshot`

Use this for Sector Overview.

### Snapshot Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/sectoral-snapshot" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "locations=IT"
```

### Evolution Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/sectoral-snapshot" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "reference_year=2023" \
  -d "locations=IT"
```

### Main Fields

| Field | Meaning |
| --- | --- |
| `sectors[].job_count` | jobs linked to the sector |
| `sectors[].job_share` | sector share inside the snapshot |
| `sectors[].top_skills` | top-10 skills |
| `sectors[].all_skills` | full skill list |
| `sectors[].top_job_titles` | most frequent job titles |
| `sectors[].evolution` | sector change between `reference_year` and `year` |

## `POST /projector/sector-skills-comparison`

Use this for the Sector Skills Comparison heatmap.

```bash
curl -X POST "http://127.0.0.1:8000/projector/sector-skills-comparison" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "metric=share"
```

Metrics:

- `count`
- `share`
- `rank`
- `growth`

## `POST /projector/emerging-skills`

Use this when you only need trends.

### Minimal Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/emerging-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31"
```

### What It Returns

```json
{
  "status": "completed",
  "insights": {
    "market_health": {
      "status": "expanding",
      "volume_growth_percentage": 0.0
    },
    "trends": []
  }
}
```

### How To Read It

| Field | Meaning |
| --- | --- |
| `market_health.status` | Overall job-volume direction for the selected period |
| `market_health.volume_growth_percentage` | Percentage change between the first and second half of the period |
| `trends[].name` | Skill label |
| `trends[].growth` | Growth percentage, or `new_entry` |
| `trends[].trend_type` | `emerging`, `declining`, or `stable` |
| `trends[].primary_sector` | Main Tracker sector associated with the skill |

## `POST /projector/temporal-projections`

Use this for Temporal Analysis: monthly, quarterly or yearly evolution of the same keyword/date/region job-market slice.

### Minimal Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/temporal-projections" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "granularity=quarterly"
```

### What It Returns

```json
{
  "status": "completed",
  "total_jobs": 120,
  "insights": {
    "granularity": "quarterly",
    "forecast_method": "last_delta_baseline",
    "periods": [],
    "skills": []
  }
}
```

### How To Read It

| Field | Meaning |
| --- | --- |
| `periods[].job_count` | Jobs uploaded in the period |
| `periods[].growth_vs_previous` | Job-count growth versus the previous period |
| `skills[].series[].count` | Skill mentions in the period |
| `skills[].growth_rate` | Latest period growth versus previous period |
| `skills[].forecast[].projected_count` | Short-term baseline projection from recent count deltas |

## `POST /projector/statistical-comparison`

Use this as an inferential layer for existing comparison views.

### Minimal Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/statistical-comparison" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "comparison_type=sector_skill" \
  -d "group_a_label=ICT" \
  -d "group_a_count=40" \
  -d "group_a_total=100" \
  -d "group_b_label=Education" \
  -d "group_b_count=20" \
  -d "group_b_total=100"
```

### How To Read It

| Field | Meaning |
| --- | --- |
| `p_value` | Chi-square p-value for the observed 2x2 count difference |
| `significant` | Whether `p_value < alpha` |
| `effect_size` | Phi/Cramer's V for the 2x2 table |
| `effect_size_label` | `negligible`, `small`, `medium`, or `large` |
| `comparison_question` | Human-readable question tested by this comparison |
| `observed_table` | Actual 2x2 table used by the test |
| `expected_table` | Expected 2x2 table under the independence baseline |
| `share_difference_percentage_points` | Difference between group shares in percentage points |
| `relative_risk` | Group A share divided by group B share, when computable |
| `odds_ratio` | Odds ratio between group A and group B, when computable |
| `evidence_level` | `none`, `weak`, `moderate`, or `strong` |
| `practical_relevance` | Same scale as `effect_size_label`, kept explicit for UI copy |
| `warnings[]` | Sample-size cautions, especially low expected counts |

## `POST /projector/stop`

Use this for a cancel/stop button during long-running analyses.

### Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/stop"
```

### What It Returns

```json
{
  "status": "signal_sent"
}
```

### How To Read It

This does not kill the process immediately. It sends a cooperative stop signal. The running analysis stops when it reaches a safe checkpoint.
