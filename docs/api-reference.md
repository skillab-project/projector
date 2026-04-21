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
| `sector_system` | enum | no | `isco` | `isco`, `nace`, or `both` |
| `sector_level` | enum | no | `isco_group` | `isco_group`, `nace_section`, `nace_division`, `nace_group`, `nace_class`, `nace_code` |
| `skill_group_level` | integer | no | `1` | ESCO skill group level used in sector group aggregation |
| `occupation_level` | integer | no | `1` | ESCO occupation level used for official matrix lookup |

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
  -d "sector_system=both" \
  -d "sector_level=nace_section" \
  -d "skill_group_level=1" \
  -d "occupation_level=1"
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
        "primary_sector": "Software developers"
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
    "sectoral_mode": "both",
    "sectoral_views": {
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
    },
    "sector_view_names": {
      "isco": {
        "observed": "Observed",
        "canonical": "Canonical",
        "matrix": "Official Matrix"
      },
      "nace": {
        "observed": "Observed",
        "canonical": "Derived Canonical",
        "matrix": "Aggregated Official Matrix"
      }
    }
  }
}
```

When `include_sectoral=false`, `sectoral`, `sectoral_mode`, `sectoral_views` and `sector_view_names` are returned as `null`.

When no jobs are found, the service returns a completed response with `jobs_analyzed=0` and empty insight lists.

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
