# Data Model

Current response fields. Metric formulas live in [Statistics](statistic.md).

Related issues: #3, #4, #7, #8, #44, #47, #48, #52, #54, #74.

## Root Response

`POST /projector/analyze-skills`

```json
{
  "status": "completed",
  "dimension_summary": {},
  "insights": {}
}
```

## Dimension Summary

```json
{
  "jobs_analyzed": 1250,
  "geo_breakdown": [
    { "location": "IT", "job_count": 820 }
  ]
}
```

## Job Demand Overview / Skill Ranking

```json
{
  "name": "Python",
  "frequency": 120,
  "skill_id": "http://data.europa.eu/esco/skill/...",
  "is_green": false,
  "is_digital": true,
  "sector_spread": 4,
  "primary_sector": "Information and communication"
}
```

`sector_spread` and `primary_sector` use Tracker `job["sectors"]`.

## Temporal Analysis Response

`POST /projector/temporal-projections`

```json
{
  "status": "completed",
  "total_jobs": 120,
  "insights": {
    "window": {
      "min_date": "2024-01-01",
      "max_date": "2024-12-31"
    },
    "granularity": "monthly",
    "forecast_method": "last_delta_baseline",
    "periods": [],
    "skills": []
  }
}
```

Period row:

```json
{
  "period": "2024-01",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "job_count": 30,
  "growth_vs_previous": null
}
```

Skill row:

```json
{
  "skill_id": "skill-python",
  "name": "Python",
  "total_count": 42,
  "latest_count": 12,
  "growth_rate": 20.0,
  "trend_type": "emerging",
  "is_green": false,
  "is_digital": true,
  "series": [],
  "forecast": []
}
```

## Statistical Comparison Response

`POST /projector/statistical-comparison`

```json
{
  "status": "completed",
  "comparison_type": "sector_skill",
  "method": "chi_square_2x2",
  "alpha": 0.05,
  "significant": true,
  "statistic": 6.06,
  "p_value": 0.0138,
  "effect_size": 0.1741,
  "effect_size_label": "small",
  "interpretation": "Observed difference is statistically significant...",
  "groups": [
    { "label": "ICT", "count": 40, "total": 100, "share": 0.4 },
    { "label": "Education", "count": 20, "total": 100, "share": 0.2 }
  ],
  "expected_counts": [[30.0, 70.0], [30.0, 70.0]],
  "warnings": []
}
```

## Count Lists

Used by sectors, job titles and employers:

```json
{
  "name": "Example",
  "count": 10
}
```

## Sector Snapshot Response

`POST /projector/sectoral-snapshot`

```json
{
  "status": "completed",
  "year": 2024,
  "reference_year": 2023,
  "data_source": "postgres",
  "window": {
    "label": "2024 snapshot",
    "min_date": "2024-01-01",
    "max_date": "2024-12-31"
  },
  "total_jobs": 1200,
  "sector_filter": [],
  "sectors": []
}
```

## Sector Snapshot Row

```json
{
  "sector": "Information and communication",
  "sector_label": "Information and communication",
  "job_count": 420,
  "job_share": 0.3281,
  "total_skill_mentions": 1260,
  "unique_skills": 38,
  "evolution": {},
  "top_skills": [],
  "all_skills": [],
  "top_job_titles": []
}
```

## Skill Entry

```json
{
  "skill_id": "skill-python",
  "label": "Python",
  "count": 188,
  "frequency": 0.1492,
  "share_in_sector": 0.1492,
  "rank": 1,
  "growth_vs_reference_year": 0.24,
  "growth_value": 0.24,
  "sector_breadth": 4,
  "is_green": false,
  "is_digital": true
}
```

Used in `top_skills` and `all_skills`.

## Sector Evolution

```json
{
  "reference_year": 2023,
  "job_count_current": 420,
  "job_count_reference": 360,
  "job_delta": 60,
  "job_growth_percentage": 0.1667,
  "job_growth_value": 0.1667,
  "new_skill_count": 4,
  "disappeared_skill_count": 2,
  "growing_skill_count": 12,
  "declining_skill_count": 7,
  "skill_churn": 0.1579,
  "top_new_skills": [],
  "top_disappeared_skills": [],
  "top_growing_skills": [],
  "top_declining_skills": []
}
```

If the reference year has no sector jobs and the selected year has sector jobs:

```json
"job_growth_percentage": "new_entry"
```

## Evolution Skill Row

```json
{
  "skill_id": "skill-python",
  "label": "Python",
  "count": 188,
  "reference_count": 152,
  "delta": 36
}
```

## Top Job Title

```json
{
  "name": "Software Engineer",
  "count": 86
}
```

## Sector Skills Comparison Response

`POST /projector/sector-skills-comparison`

```json
{
  "status": "completed",
  "year": 2024,
  "reference_year": 2023,
  "data_source": "postgres",
  "metric": "share",
  "window": {},
  "sectors": [],
  "skills": [],
  "matrix": []
}
```

## Sector Skills Comparison Cell

```json
{
  "sector": "Information and communication",
  "sector_label": "Information and communication",
  "skill_id": "skill-python",
  "label": "Python",
  "count": 188,
  "share": 0.1492,
  "rank": 1,
  "rank_score": 1.0,
  "growth": 0.24,
  "growth_value": 0.24,
  "value": 0.1492,
  "display_value": "14.9%",
  "is_green": false,
  "is_digital": true
}
```

`value` is the selected heatmap metric.

## Legacy Sectoral Detail

`POST /projector/sectoral-intelligence` and `include_sectoral=true` in `/analyze-skills` still return observed sectoral details:

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

Use this for drill-down compatibility. Use `/sectoral-snapshot` and `/sector-skills-comparison` for the current dashboard sector views.
