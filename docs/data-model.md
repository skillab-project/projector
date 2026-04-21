# Data Model and Metric Semantics

This document explains the response fields returned by the current API models in `app/schemas/responses.py`.

## Root Response

`POST /projector/analyze-skills` returns:

```json
{
  "status": "completed",
  "dimension_summary": {},
  "insights": {}
}
```

`status` is usually:
- `completed`
- `stopped`

`POST /projector/stop` returns:

```json
{ "status": "signal_sent" }
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

Fields:
- `jobs_analyzed`: number of Tracker job records processed by the endpoint.
- `geo_breakdown`: count by raw `location_code`.

## Insights

The main `insights` object contains:

- `ranking`
- `sectors`
- `job_titles`
- `employers`
- `trends`
- `regional`
- `sectoral`
- `sectoral_mode`
- `sectoral_views`
- `sector_view_names`

The last four fields are meaningful when `include_sectoral=true`; otherwise they are `null`.

## Skill Ranking

Each item in `insights.ranking` has:

```json
{
  "name": "Python",
  "frequency": 120,
  "skill_id": "http://data.europa.eu/esco/skill/...",
  "is_green": false,
  "is_digital": false,
  "sector_spread": 4,
  "primary_sector": "Software developers"
}
```

Fields:
- `name`: resolved skill label when available.
- `frequency`: number of times the skill appears in the analyzed jobs.
- `skill_id`: original skill URI/id.
- `is_green`: green-skill flag. Currently false by default in runtime enrichment.
- `is_digital`: digital-skill flag. Currently false by default in runtime enrichment.
- `sector_spread`: number of distinct ISCO sectors associated with this skill in the analyzed batch.
- `primary_sector`: most frequent ISCO sector for this skill.

## Count Lists

`insights.sectors`, `insights.job_titles` and `insights.employers` use:

```json
{
  "name": "Example",
  "count": 10
}
```

`sectors` in the base ranking path is ISCO-oriented. NACE-specific sectoral data lives in `insights.sectoral_views.nace`.

## Trends

```json
{
  "market_health": {
    "status": "expanding",
    "volume_growth_percentage": 12.5
  },
  "trends": [
    {
      "name": "Python",
      "growth": 20.0,
      "trend_type": "emerging",
      "primary_sector": "Software developers",
      "is_green": false,
      "is_digital": false
    }
  ]
}
```

Trend calculation compares two halves of the selected date range.

`growth` can be:
- a numeric percentage,
- `"new_entry"` when the skill was absent in the first half and present in the second.

`trend_type` can be:
- `emerging`
- `declining`
- `stable`

`market_health.status` is currently computed from total job volume and is normally `expanding` or `shrinking`.

## Regional Projections

```json
{
  "raw": [],
  "nuts1": [],
  "nuts2": [],
  "nuts3": []
}
```

Each regional area item has:

```json
{
  "code": "ITC4",
  "total_jobs": 120,
  "market_share": 9.6,
  "top_skills": [
    {
      "skill": "Python",
      "count": 33,
      "specialization": 1.78
    }
  ]
}
```

Fields:
- `code`: raw or projected geographic code.
- `total_jobs`: jobs assigned to the area.
- `market_share`: percentage of all analyzed jobs represented by the area.
- `top_skills`: most frequent skills in the area.
- `specialization`: Location Quotient-like score. Values above `1` indicate above-average local concentration compared with the full analyzed market.

## Sectoral Item

Each sectoral item can contain:

```json
{
  "sector": "C25",
  "sector_label": "Information and communication",
  "observed_skills": {},
  "canonical_skills": {},
  "observed_groups": {},
  "canonical_groups": {},
  "matrix_groups": {},
  "sector_metrics": {},
  "skill_transversal_insights": [],
  "isco_interpretation": null
}
```

## Sector Skill Summary

Used by `observed_skills` and `canonical_skills`:

```json
{
  "sector": "C25",
  "total_skill_mentions": 100,
  "unique_skills": 25,
  "top_skills": [
    {
      "skill_id": "http://data.europa.eu/esco/skill/...",
      "count": 10,
      "frequency": 0.1,
      "label": "Python",
      "is_green": false,
      "is_digital": false
    }
  ]
}
```

`observed_skills` comes from Tracker job evidence. `canonical_skills` comes from ESCO occupation-skill relations.

## Sector Group Summary

Used by `observed_groups`, `canonical_groups` and `matrix_groups`:

```json
{
  "total_group_mentions": 100.0,
  "unique_groups": 8,
  "top_groups": [
    {
      "group_id": "S4",
      "group_label": "Working with computers",
      "count": 30.0,
      "frequency": 0.3
    }
  ]
}
```

## Sector Metrics

```json
{
  "coverage_unique_skills": 25,
  "dominance_top10_share": 0.72
}
```

Fields:
- `coverage_unique_skills`: number of unique observed skills in the sector.
- `dominance_top10_share`: share of observed skill mentions represented by the top 10 skills.

## Skill Transversal Insights

```json
{
  "skill_id": "http://data.europa.eu/esco/skill/...",
  "label": "Python",
  "count": 10,
  "importance_in_sector": 0.1,
  "sector_breadth": 4,
  "dominant_sector": "J",
  "dominant_sector_label": "Information and communication",
  "dominant_share": 0.52,
  "top_sectors": [
    {
      "sector": "J",
      "sector_label": "Information and communication",
      "count": 52,
      "share": 0.52
    }
  ]
}
```

Fields:
- `importance_in_sector`: share of a skill inside the current sector.
- `sector_breadth`: number of sectors where the skill appears.
- `dominant_share`: share of all mentions for that skill found in the dominant sector.

## ISCO Interpretation

Only ISCO sectoral items include `isco_interpretation`.

```json
{
  "sector": "C25",
  "emerging_skills": [],
  "missing_skills": [],
  "stability_overlap": 0.42,
  "observed_skill_count": 30,
  "canonical_skill_count": 80,
  "overlap_skill_count": 20
}
```

Fields:
- `emerging_skills`: observed skills not present in canonical ESCO relations.
- `missing_skills`: canonical skills not observed in the current market slice.
- `stability_overlap`: Jaccard overlap between observed and canonical skill sets.

## Sectoral Views

`insights.sectoral_views` contains both systems:

```json
{
  "isco": {
    "sector_level": "isco_group",
    "items": []
  },
  "nace": {
    "selected_level": "nace_section",
    "levels": {
      "nace_section": { "sector_level": "nace_section", "items": [] },
      "nace_division": { "sector_level": "nace_division", "items": [] },
      "nace_group": { "sector_level": "nace_group", "items": [] },
      "nace_class": { "sector_level": "nace_class", "items": [] }
    }
  }
}
```

NACE canonical and matrix groups are ESCO-derived projections aggregated through the ESCO-NACE crosswalk.

## Interpretation Caveats

- `frequency` means count in the top ranking, but relative share inside nested sector summaries.
- NACE is multi-mapping aware; NACE sector totals are relation counts, not strict unique job counts.
- `demo=true` regional projections are synthetic when source location codes are only country-level.
