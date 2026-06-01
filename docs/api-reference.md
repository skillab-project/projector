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
| `include_sectoral` | boolean | no | `false` | Enables sectoral intelligence payload |
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
