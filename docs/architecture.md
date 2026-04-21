# Architecture and Operational Notes

This document describes the maintained `app/` implementation.

## Runtime Stack

- FastAPI for the HTTP API
- `httpx.AsyncClient` for Tracker communication
- Pydantic response models
- file-based JSON cache for Tracker job batches
- Streamlit dashboard for local exploration
- `openpyxl` for ESCO workbook loading

## Current Module Flow

```text
app.main
 -> app.api.routes.projector
 -> app.core.container.service
 -> app.services.projector_service.ProjectorService
    -> app.client.tracker_client.TrackerClient
    -> app.services.analytics.market.MarketAnalytics
    -> app.services.analytics.trends.TrendAnalytics
    -> app.services.analytics.regional.RegionalAnalytics
    -> app.services.analytics.sectoral.SectoralAnalytics
    -> app.services.analytics.occupations.OccupationAnalytics
```

Shared runtime state lives in `app.core.state.ProjectorEngine`.

Dependency wiring and local ESCO loading happen in `app.core.container`:

```text
ProjectorEngine
TrackerClient
EscoLoader.load_local_esco_support()
EscoLoader.load_official_esco_matrix()
analytics services
ProjectorService
```

## External Tracker Dependency

The Projector depends on the SKILLAB Tracker for raw job data and metadata enrichment.

Tracker endpoints used internally:
- `POST /login`
- `POST /jobs`
- `POST /skills`
- `POST /occupations`

Projector latency and failure modes are therefore partly determined by Tracker availability and response time.

## Main Analysis Flow

`POST /projector/analyze-skills` currently follows this flow:

1. Reset the cooperative stop flag.
2. Build a clean Tracker filter payload.
3. Fetch all matching jobs from Tracker or `cache_data/`.
4. Return an empty but structured payload if no jobs are found.
5. Extract all occupations and observed skills from jobs.
6. Add canonical ESCO skills linked to observed occupations so labels can be resolved.
7. Resolve occupation labels and skill labels.
8. Compute market rankings.
9. Compute trends from the already fetched in-memory job batch.
10. Compute regional projections.
11. If `include_sectoral=true`, build ISCO and all NACE sectoral views.
12. Return the Pydantic-modeled response.

## Caching

Tracker job batches are cached in:

```text
cache_data/search_<md5-filter-hash>.json
```

The cache key is derived from the cleaned Tracker filter payload.

Important behavior:
- repeated identical filters reuse the cache,
- cache entries do not currently expire,
- changing Tracker data is not reflected until matching cache files are removed or invalidated.

## Stop Behavior

`POST /projector/stop` sets `engine.stop_requested=True`.

This is cooperative interruption:
- it does not kill the Python process,
- long-running code checks the flag at safe points,
- final endpoint status can become `stopped` if the running request observes the flag.

## Trend Strategy

The code supports two trend paths:

- `calculate_trends_from_data`: compares two halves of the already fetched job batch.
- `calculate_smart_trends`: fetches two sub-periods independently.

`/projector/analyze-skills` uses the in-memory path. `/projector/emerging-skills` uses the trend-only path.

## Regional Strategy

Regional analytics use:

- `raw`: original `location_code`
- `nuts1`, `nuts2`, `nuts3`: string-sliced NUTS-like projections

When `demo=true`, country-level location codes can be expanded into synthetic NUTS-like codes to demonstrate regional drill-down behavior.

## Sector-Resolution Strategy

ISCO path:

```text
occupation -> isco_group -> ISCO label
```

NACE path:

```text
occupation -> ESCO-NACE crosswalk -> NACE code/title
```

One occupation can map to multiple NACE codes. All mappings are currently kept.

## Current Caveats

- There is no standardized error response model.
- Date ordering is not explicitly validated.
- Cache invalidation is manual.
- Green and digital flags are currently false by default in runtime enrichment.
- NACE mode is relation-oriented, so NACE counts should not be interpreted as strict one-job-one-sector accounting.
- The shared `ProjectorEngine` state is process-local and in-memory.

## Production Hardening Priorities

1. Add input validation for date ranges and bounded page sizes.
2. Define a standard error envelope.
3. Add explicit cache invalidation or TTL.
4. Add versioning, for example `/api/v1/projector/...`.
5. Add health/readiness endpoints for Tracker and local ESCO resources.
6. Expand automated tests for ISCO/NACE sectoral payloads and no-data responses.
