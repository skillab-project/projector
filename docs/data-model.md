# Data Model

This document describes current response fields. Metric formulas live in [Statistics](statistic.md).

## Root Response

`POST /projector/analyze-skills` returns:

```json
{
  "status": "completed",
  "dimension_summary": {},
  "insights": {}
}
```

`status` is usually `completed` or `stopped`.

## Dimension Summary

```json
{
  "jobs_analyzed": 1250,
  "geo_breakdown": [
    { "location": "IT", "job_count": 820 }
  ]
}
```

- `jobs_analyzed`: Tracker jobs processed.
- `geo_breakdown`: job count by raw `location_code`.

## Insights

Main fields:

- `ranking`: top observed skills.
- `sectors`: top Tracker sectors.
- `job_titles`: most frequent job titles.
- `employers`: most frequent employers.
- `trends`: skill and volume changes between two time slices.
- `regional`: geographic breakdown.
- `sectoral`: observed sector intelligence when `include_sectoral=true`.
- `sectoral_views`: NACE view wrapper for dashboard use.

## Skill Ranking

```json
{
  "name": "Python",
  "frequency": 120,
  "skill_id": "http://data.europa.eu/esco/skill/...",
  "is_green": false,
  "is_digital": false,
  "sector_spread": 4,
  "primary_sector": "Information and communication"
}
```

`sector_spread` and `primary_sector` are based on Tracker `job["sectors"]`.

## Count Lists

`sectors`, `job_titles` and `employers` use:

```json
{
  "name": "Example",
  "count": 10
}
```

## Sectoral View

Current sectoral view is observed-only and API-only:

```json
{
  "sectoral_mode": "nace",
  "sectoral_views": {
    "nace": {
      "sector_level": "tracker_sector",
      "items": []
    }
  }
}
```

## Sectoral Item

```json
{
  "sector": "Information and communication",
  "sector_label": "Information and communication",
  "observed_skills": {},
  "observed_groups": {},
  "sector_metrics": {},
  "skill_transversal_insights": []
}
```

## Observed Skills

```json
{
  "sector": "Information and communication",
  "total_skill_mentions": 100,
  "unique_skills": 25,
  "top_skills": [
    {
      "skill_id": "http://data.europa.eu/esco/skill/...",
      "label": "Python",
      "count": 10,
      "frequency": 0.1,
      "is_green": false,
      "is_digital": false
    }
  ]
}
```

## Skill Transversal Insights

```json
{
  "label": "Python",
  "count": 10,
  "importance_in_sector": 0.1,
  "sector_breadth": 4,
  "dominant_sector_label": "Information and communication",
  "dominant_share": 0.52
}
```

These fields explain how a selected sector's top skills behave across all sectors in the result.
