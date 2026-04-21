# Endpoint Cheatsheet

This page is the quick integration view for consumers of the Projector API.

For full field details, see [API reference](api-reference.md) and [Data model](data-model.md).

## Quick Map

| Endpoint | Use it when you need | Returns in one sentence |
| --- | --- | --- |
| `POST /projector/analyze-skills` | A full dashboard snapshot | Skills, sectors, employers, titles, trends, geography and optional ISCO/NACE sectoral intelligence |
| `POST /projector/emerging-skills` | Only trend information | Market volume trend plus emerging, declining, stable and new-entry skills |
| `POST /projector/stop` | To interrupt a long analysis | Acknowledgement that a cooperative stop signal was sent |

## `POST /projector/analyze-skills`

Main endpoint for dashboards and analytical clients.

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
  -d "sector_system=both" \
  -d "sector_level=nace_section"
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
| `insights.sectors` | Base ISCO-oriented sector counts | Sector bar chart |
| `insights.job_titles` | Most frequent job titles | Job-title leaderboard |
| `insights.employers` | Most frequent employers | Employer leaderboard |
| `insights.trends` | Volume growth and skill trend changes | Trend tab |
| `insights.regional` | Raw and NUTS-like area breakdowns with specialization | Map and regional detail |
| `insights.sectoral` | Selected/default sectoral intelligence payload | Backward-compatible sector panel |
| `insights.sectoral_views` | Full ISCO and NACE sectoral payloads | ISCO/NACE switcher and detail views |
| `insights.sector_view_names` | Display labels for observed/canonical/matrix views | UI labels |

### Sectoral Meaning In One Minute

When `include_sectoral=false`, ignore the `sectoral*` fields.

When `include_sectoral=true`:
- ISCO answers: "What kind of job is this?"
- NACE answers: "In which industry does this job operate?"
- Observed means skills found in Tracker jobs.
- Canonical means skills from ESCO occupation-skill relations.
- Official Matrix means ESCO matrix skill-group profiles.
- NACE Derived Canonical and Aggregated Official Matrix are ESCO-derived views re-aggregated through the ESCO-NACE crosswalk.

Important: NACE supports multiple mappings per occupation, so NACE totals describe skill-sector relationships, not strict unique job counts.

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
| `trends[].primary_sector` | Main ISCO sector associated with the skill |

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
