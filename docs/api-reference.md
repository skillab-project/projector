# API Reference

## Index
- [Base path](#base-path)
- [Content type](#content-type)
- [POST /projector/analyze-skills](#1-post-projectoranalyze-skills)
  - [Purpose](#purpose)
  - [When to use it](#when-to-use-it)
  - [Parameters](#parameters)
  - [Response shape](#response-shape)
  - [Response fields](#response-fields)
- [POST /projector/emerging-skills](#2-post-projectoremerging-skills)
- [POST /projector/stop](#3-post-projectorstop)
- [Status code policy](#recommended-status-code-policy-for-production)

---

## Base path
All public endpoints are exposed under `/projector`.

## Content type
Current endpoints accept:
- `application/x-www-form-urlencoded`

---

## 1. POST `/projector/analyze-skills`

### On this section
- [Purpose](#purpose)
- [When to use it](#when-to-use-it)
- [Parameters](#parameters)
- [Response shape](#response-shape)
- [Response fields](#response-fields)

### Purpose
Runs a complete analysis over the selected batch of job postings and returns a multi-dimensional intelligence payload.

### When to use it
Use this endpoint when you need a full market snapshot for a given selection.

Typical use cases:
- dashboard initial load,
- top skills in a period,
- top employers in a market slice,
- regional specialization analysis,
- trend widget fed from the same batch.

### Parameters
#### `keywords`
- Type: list of strings
- Required: no
- Meaning: free-text terms used to filter the source vacancies.

#### `locations`
- Type: list of strings
- Required: no
- Meaning: location filters forwarded to Tracker as raw `location_code` values.

#### `min_date`
- Type: `YYYY-MM-DD`
- Required: yes
- Meaning: lower time boundary of the analysis window.

#### `max_date`
- Type: `YYYY-MM-DD`
- Required: yes
- Meaning: upper time boundary of the analysis window.

#### `page`
- Type: integer
- Required: no
- Default: `1`
- Meaning: page index used only for the returned `insights.ranking` array.

#### `page_size`
- Type: integer
- Required: no
- Default: `50`
- Meaning: number of skill-ranking items returned.

#### `demo`
- Type: boolean
- Required: no
- Default: `false`
- Meaning: when true, the engine synthesizes NUTS-like geography from country-level data to demonstrate regional analytics.

### Response shape
```json
{
  "status": "completed",
  "dimension_summary": {
    "jobs_analyzed": 1250,
    "geo_breakdown": [
      { "location": "IT", "job_count": 820 }
    ]
  },
  "insights": {
    "ranking": [],
    "sectors": [],
    "job_titles": [],
    "employers": [],
    "trends": {
      "market_health": {
        "status": "expanding",
        "volume_growth_percentage": 12.5
      },
      "trends": []
    },
    "regional": {
      "raw": [],
      "nuts1": [],
      "nuts2": [],
      "nuts3": []
    }
  }
}