# API Reference

## Base path
All public endpoints are exposed under `/projector`.

## Content type
Current endpoints accept:
- `application/x-www-form-urlencoded`

---

## 1. POST `/projector/analyze-skills`

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
```

### Response fields
#### `status`
Possible values in practice:
- `completed`
- `stopped`

#### `dimension_summary.jobs_analyzed`
Total number of jobs actually processed after filters.

#### `dimension_summary.geo_breakdown`
Distribution of the retrieved batch by raw location code.

#### `insights.ranking`
Paginated list of top skills.

#### `insights.sectors`
Distribution of jobs by sector label.

#### `insights.job_titles`
Top job titles as written in the source vacancies.

#### `insights.employers`
Top hiring organizations.

#### `insights.trends`
Trend analysis computed on the selected time window.

#### `insights.regional`
Geographic decomposition of the analyzed jobs.

---

## 2. POST `/projector/emerging-skills`

### Purpose
Runs a trend-focused analysis by splitting the selected time window into two sub-periods and comparing them.

### When to use it
Use this endpoint when you only care about change over time and do not need the full ranking/employer/regional package.

### Parameters
#### `min_date`
- Type: `YYYY-MM-DD`
- Required: yes

#### `max_date`
- Type: `YYYY-MM-DD`
- Required: yes

#### `keywords`
- Type: list of strings
- Required: no
- Meaning: optional text filter applied before trend analysis.

### Response shape
```json
{
  "status": "completed",
  "insights": {
    "market_health": {
      "status": "expanding",
      "volume_growth_percentage": 8.3
    },
    "trends": [
      {
        "name": "Cloud computing",
        "growth": "new_entry",
        "trend_type": "emerging",
        "primary_sector": "Information technology",
        "is_green": false,
        "is_digital": true
      }
    ]
  }
}
```

### Notes
- the endpoint computes a midpoint date internally,
- period A covers the first half of the selected window,
- period B covers the second half,
- the payload is intentionally lighter than `analyze-skills`.

---

## 3. POST `/projector/stop`

### Purpose
Asks the engine to stop an ongoing long-running process safely.

### Request body
No parameters.

### Response
```json
{
  "status": "signal_sent"
}
```

### Important behavior note
This is a cooperative stop, not an immediate hard interruption.
The engine stops at the next safe checkpoint.

---

## Recommended status-code policy for production
The current codebase does not yet define a full custom error envelope, but for a production-grade API the documented target should be:
- `200` successful response
- `400` invalid input
- `401` upstream authentication failure
- `502` upstream Tracker failure
- `504` upstream timeout

Until that error model is implemented, consumers should expect FastAPI default error behavior in edge cases.
