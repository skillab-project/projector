# API Reference

The current API is defined in `app/api/routes/projector.py` and uses form-encoded requests.

## Base Path

All public endpoints are exposed under:

```text
/projector
```

## Content Type

```http
Content-Type: application/x-www-form-urlencoded
```

## POST `/projector/analyze-skills`

Runs the main labor-market analysis.

### Request Fields

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `keywords` | list of strings | no | `null` | Search terms forwarded to Tracker |
| `locations` | list of strings | no | `null` | Tracker location codes, forwarded as `location_code` |
| `min_date` | string | yes | none | Start date, `YYYY-MM-DD` |
| `max_date` | string | yes | none | End date, `YYYY-MM-DD` |
| `page` | integer | no | `1` | Page for returned `insights.ranking` only |
| `page_size` | integer | no | `50` | Number of ranking items returned |
| `demo` | boolean | no | `false` | Enables synthetic NUTS-like projection for country-level locations |
| `include_sectoral` | boolean | no | `false` | Compatibility field. New frontend should call `/projector/sectoral-intelligence` |
| `sector_system` | enum | no | `isco` | Accepted for compatibility; runtime uses `nace` |
| `sector_level` | enum | no | `isco_group` | Accepted for compatibility; runtime uses Tracker sector labels |
| `sectoral_time_mode` | enum | no | `latest` | Sectoral window: `latest`, `selected_period`, `year`, or `comparison` |
| `sectoral_snapshot_year` | integer | no | year of `max_date` | Year used when `sectoral_time_mode=year` |
| `sectoral_compare_a_min_date` | string | no | `min_date` | Baseline start for `comparison` |
| `sectoral_compare_a_max_date` | string | no | `max_date` | Baseline end for `comparison` |
| `sectoral_compare_b_min_date` | string | no | last six months start | Current start for `comparison` |
| `sectoral_compare_b_max_date` | string | no | today | Current end for `comparison` |
| `skill_group_level` | integer | no | `1` | Accepted for compatibility |
| `occupation_level` | integer | no | `1` | Accepted for compatibility |

`page` and `page_size` do not paginate Tracker fetching. They only slice the returned top-skill ranking.

### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "page=1" \
  -d "page_size=20" \
  -d "demo=false" \
  -d "include_sectoral=true" \
  -d "sector_system=nace"
```

### Response Shape

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
    "ranking": [
      {
        "name": "Python",
        "frequency": 120,
        "skill_id": "http://data.europa.eu/esco/skill/...",
        "is_green": false,
        "is_digital": false,
        "sector_spread": 4,
        "primary_sector": "Information and communication"
      }
    ],
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
    },
    "sectoral": [],
    "sectoral_mode": "nace",
    "sectoral_views": {
      "nace": {
        "sector_level": "tracker_sector",
        "time_mode": "latest",
        "window": {
          "label": "Last six months",
          "min_date": "2025-11-30",
          "max_date": "2026-06-01"
        },
        "items": []
      }
    },
    "sector_view_names": {
      "nace": {
        "observed": "Observed"
      }
    }
  }
}
```

When `include_sectoral=false`, `sectoral`, `sectoral_mode`, `sectoral_views` and `sector_view_names` are returned as `null`.

When `include_sectoral=true`, sectoral intelligence uses its own time window:

- `latest`: last six months, default.
- `selected_period`: uses the main `min_date` / `max_date`.
- `year`: uses `sectoral_snapshot_year`, or the year from `max_date`.
- `comparison`: fetches two independent periods and returns `sectoral_views.nace.comparison`.

When no jobs are found, the service returns a completed response with `jobs_analyzed=0` and empty insight lists.

## POST `/projector/sectoral-snapshot`

Reads an annual sector snapshot.

Use it for:

- Sector Overview / Snapshot
- Sector Overview / Sector Evolution

When `DATABASE_URL` is configured, this endpoint reads the latest completed PostgreSQL snapshot for the requested year. It does not call Tracker during user requests.

### Request Fields

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `year` | integer | yes | none | Calendar year to aggregate |
| `reference_year` | integer | no | `year - 1` | Comparison year used to enrich sector evolution and skill growth |
| `locations` | list of strings | no | `null` | Tracker location codes, forwarded as `location_code` |

Data source is internal. The public dashboard does not expose cache/live selection.

Refresh snapshots with:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024
```

### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/sectoral-snapshot" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "reference_year=2023" \
  -d "locations=IT"
```

### Response Shape

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
  "sectors": [
    {
      "sector": "Education",
      "sector_label": "Education",
      "job_count": 220,
      "job_share": 0.18,
      "total_skill_mentions": 510,
      "unique_skills": 85,
      "evolution": {
        "reference_year": 2023,
        "job_count_current": 220,
        "job_count_reference": 180,
        "job_delta": 40,
        "job_growth_percentage": 0.2222,
        "job_growth_value": 0.2222,
        "new_skill_count": 4,
        "disappeared_skill_count": 2,
        "growing_skill_count": 12,
        "declining_skill_count": 7,
        "skill_churn": 0.1579,
        "top_new_skills": [],
        "top_disappeared_skills": [],
        "top_growing_skills": [],
        "top_declining_skills": []
      },
      "top_skills": [],
      "all_skills": [],
      "top_job_titles": []
    }
  ]
}
```

## POST `/projector/sector-skills-comparison`

Builds a sectors x skills heatmap from yearly PostgreSQL snapshots.

Use it for Sector Skills Comparison.

### Request Fields

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `year` | integer | yes | none | Target year |
| `reference_year` | integer | no | `year - 1` | Comparison year for `metric=growth` |
| `locations` | list of strings | no | `null` | Optional Tracker location code |
| `sectors` | list of strings | no | top sectors | Sectors to compare |
| `skills` | list of strings | no | top skills | Skills to compare |
| `metric` | enum | no | `share` | `count`, `share`, `rank`, or `growth` |

### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/sector-skills-comparison" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "reference_year=2023" \
  -d "metric=share"
```

### Response Shape

```json
{
  "status": "completed",
  "year": 2024,
  "reference_year": 2023,
  "data_source": "postgres",
  "metric": "share",
  "window": {
    "label": "2024 snapshot",
    "min_date": "2024-01-01",
    "max_date": "2024-12-31"
  },
  "sectors": ["Education"],
  "skills": ["Python"],
  "matrix": [
    {
      "sector": "Education",
      "sector_label": "Education",
      "skill_id": "skill-python",
      "label": "Python",
      "count": 20,
      "share": 0.1,
      "rank": 1,
      "rank_score": 1.0,
      "growth": 0.25,
      "growth_value": 0.25,
      "value": 0.1,
      "display_value": "10.0%",
      "is_green": false,
      "is_digital": true
    }
  ]
}
```

If no static snapshot exists:

```json
{
  "status": "not_available",
  "year": 2024,
  "data_source": "cache",
  "sectors": [],
  "message": "No static sector snapshot available for 2024. Run the snapshot refresh job first."
}
```

## POST `/projector/sectoral-intelligence`

Computes detailed sector intelligence.

Use this endpoint for drill-downs. For the primary final-frontend overview, prefer `/projector/sectoral-snapshot`.

### Request Fields

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `keywords` | list of strings | no | `null` | Search terms forwarded to Tracker |
| `locations` | list of strings | no | `null` | Tracker location codes, forwarded as `location_code` |
| `sectors` | list of strings | no | `null` | Sector-first filter applied to Tracker `job["sectors"]` |
| `data_source` | enum | no | `cache` | `cache` reads local static cache only; `live` fetches Tracker and refreshes cache |
| `mode` | enum | no | `latest` | `latest`, `selected_period`, `year`, or `comparison` |
| `min_date` | string | no | latest window start | Used by `selected_period`, and as comparison baseline fallback |
| `max_date` | string | no | latest window end | Used by `selected_period`, and as comparison baseline fallback |
| `snapshot_year` | integer | no | year of `max_date` | Full calendar year for `mode=year` |
| `compare_a_min_date` | string | no | `min_date` | Baseline start for `comparison` |
| `compare_a_max_date` | string | no | `max_date` | Baseline end for `comparison` |
| `compare_b_min_date` | string | no | last six months start | Current start for `comparison` |
| `compare_b_max_date` | string | no | today | Current end for `comparison` |
| `skill_group_level` | integer | no | `1` | Skill group aggregation level |
| `occupation_level` | integer | no | `1` | Compatibility field |

### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/sectoral-intelligence" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sectors=Education" \
  -d "locations=IT" \
  -d "data_source=cache" \
  -d "mode=latest"
```

### Response Shape

```json
{
  "status": "completed",
  "mode": "latest",
  "data_source": "cache",
  "sector_level": "tracker_sector",
  "sector_filter": ["Education"],
  "window": {
    "label": "Last six months",
    "min_date": "2025-11-30",
    "max_date": "2026-06-01"
  },
  "items": [],
  "sector_view_names": {
    "latest": "Last six months",
    "selected_period": "Selected period",
    "year": "Year snapshot",
    "comparison": "Period comparison"
  }
}
```

For `mode=comparison`, the response also includes:

```json
{
  "snapshots": {
    "period_a": { "window": {}, "items": [] },
    "period_b": { "window": {}, "items": [] }
  },
  "comparison": {
    "period_a": {},
    "period_b": {},
    "sectors": []
  }
}
```

## GET `/projector/health`

Checks whether the Projector app is reachable.

### Response Shape

```json
{
  "status": "ok"
}
```

## POST `/projector/emerging-skills`

Computes trend intelligence only. It splits the requested time window into two internal periods and compares skill frequencies.

### Request Fields

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `min_date` | string | yes | none | Start date, `YYYY-MM-DD` |
| `max_date` | string | yes | none | End date, `YYYY-MM-DD` |
| `keywords` | list of strings | no | `null` | Optional search terms |

### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/projector/emerging-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31"
```

### Response Shape

```json
{
  "status": "completed",
  "insights": {
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
}
```

## POST `/projector/stop`

Sends a cooperative stop signal to the shared engine state.

### Request Fields

None.

### Response Shape

```json
{
  "status": "signal_sent"
}
```

This endpoint does not kill a process immediately. Long-running operations check the stop flag at safe points and return `status="stopped"` when the stop was observed by the running analysis.

## Current Caveats

- There is no versioned `/api/v1` prefix yet.
- There is no standardized error envelope yet.
- Date ordering is not explicitly validated before analysis.
- Tracker and ESCO file availability influence response completeness.
