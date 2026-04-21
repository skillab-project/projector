# SKILLAB Projector API Contract

This file is a root-level summary of the maintained API contract.

The canonical detailed reference is [docs/api-reference.md](docs/api-reference.md). Field meanings and metrics are documented in [docs/data-model.md](docs/data-model.md).

## Runtime

Current maintained backend entrypoint:

```bash
uvicorn app.main:app --reload
```

The API is defined in:
- `app/api/routes/projector.py`
- `app/services/projector_service.py`
- `app/schemas/responses.py`

## Content Type

All public endpoints currently accept:

```http
application/x-www-form-urlencoded
```

## Public Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/projector/analyze-skills` | `POST` | Full labor-market analysis |
| `/projector/emerging-skills` | `POST` | Trend-only analysis |
| `/projector/stop` | `POST` | Cooperative stop signal |

## `POST /projector/analyze-skills`

Request fields:

| Field | Required | Default |
| --- | --- | --- |
| `keywords` | no | `null` |
| `locations` | no | `null` |
| `min_date` | yes | none |
| `max_date` | yes | none |
| `page` | no | `1` |
| `page_size` | no | `50` |
| `demo` | no | `false` |
| `include_sectoral` | no | `false` |
| `sector_system` | no | `isco` |
| `sector_level` | no | `isco_group` |
| `skill_group_level` | no | `1` |
| `occupation_level` | no | `1` |

Supported `sector_system` values:
- `isco`
- `nace`
- `both`

Supported `sector_level` values:
- `isco_group`
- `nace_section`
- `nace_division`
- `nace_group`
- `nace_class`
- `nace_code`

Response root:

```json
{
  "status": "completed",
  "dimension_summary": {},
  "insights": {}
}
```

Sectoral response fields, when enabled:
- `insights.sectoral`
- `insights.sectoral_mode`
- `insights.sectoral_views`
- `insights.sector_view_names`

## `POST /projector/emerging-skills`

Request fields:
- `min_date`
- `max_date`
- `keywords`

Response root:

```json
{
  "status": "completed",
  "insights": {
    "market_health": {},
    "trends": []
  }
}
```

## `POST /projector/stop`

Request fields: none.

Response:

```json
{
  "status": "signal_sent"
}
```

## Sector Semantics

ISCO is occupation-based:

```text
job -> occupation -> isco_group -> ISCO label
```

NACE is economic-activity-based:

```text
job -> occupation -> ESCO-NACE crosswalk -> NACE code/title
```

NACE keeps multiple mappings when the crosswalk links one occupation to more than one economic activity. Treat NACE totals as relationship counts, not strict unique-job totals.

## Known Contract Caveats

- No versioned API prefix yet.
- No standardized error envelope yet.
- Date ordering is not explicitly validated.
- Cache invalidation is manual.
