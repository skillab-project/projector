# Architecture and Operational Notes

This document describes the maintained `app/` implementation.

## Runtime Stack

- FastAPI for the HTTP API
- `httpx.AsyncClient` for Tracker communication
- Pydantic response models
- file-based JSON cache for Tracker job batches
- PostgreSQL for yearly sector snapshots
- Streamlit dashboard for local exploration

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
    -> app.services.sector_snapshot_store.SectorSnapshotStore
```

Shared runtime state lives in `app.core.state.ProjectorEngine`.

Dependency wiring happens in `app.core.container`. Local ESCO loaders are not executed at startup for the current API-only sector workflow.

## External Tracker Dependency

The Projector depends on the SKILLAB Tracker for raw job data and metadata enrichment.

Tracker endpoints used internally:

- `POST /login`
- `POST /jobs`
- `POST /skills`

Projector latency and failure modes are determined mostly by Tracker availability and response time.

## Main Analysis Flow

`POST /projector/analyze-skills` follows this flow:

1. Reset the cooperative stop flag.
2. Build a clean Tracker filter payload.
3. Fetch all matching jobs from Tracker or `cache_data/`.
4. Return an empty structured payload if no jobs are found.
5. Extract observed skills and sectors from jobs.
6. Resolve skill labels from Tracker `/skills`.
7. Compute market rankings.
8. Compute trends from the fetched in-memory job batch.
9. Compute regional projections.
10. If `include_sectoral=true`, build the observed sector-skill view from `job["sectors"]` and `job["skills"]`.
11. Return the Pydantic-modeled response.

## Caching

Tracker job batches are cached in:

```text
cache_data/search_<md5-filter-hash>.json
```

Important behavior:

- repeated identical filters reuse the cache
- completed cache entries expire after `TRACKER_CACHE_TTL_DAYS` days, default `30`
- set `TRACKER_CACHE_TTL_DAYS=0` to disable TTL expiration
- cached job batches without `sectors` are treated as stale and refetched

## Stop Behavior

`POST /projector/stop` sets `engine.stop_requested=True`.

This is cooperative interruption:

- it does not kill the Python process
- long-running code checks the flag at safe points
- final endpoint status can become `stopped` if the running request observes the flag

## Trend Strategy

The code supports two trend paths:

- `calculate_trends_from_data`: compares two halves of the already fetched job batch
- `calculate_smart_trends`: fetches two sub-periods independently

`/projector/analyze-skills` uses the in-memory path. `/projector/emerging-skills` uses the trend-only path.

## Regional Strategy

Regional analytics use:

- `raw`: original `location_code`
- `nuts1`, `nuts2`, `nuts3`: string-sliced NUTS-like projections

When `demo=true`, country-level location codes can be expanded into synthetic NUTS-like codes to demonstrate regional drill-down behavior.

## Sector Strategy

Sector analytics use only Tracker job fields:

```text
job["sectors"] x job["skills"]
```

One job can contain multiple sectors and multiple skills. Every sector-skill pair in the same job contributes to the observed sector-skill matrix.

## Sector Snapshot Strategy

Sector Overview and Sector Skills Comparison are static-first.

```text
Tracker API
 -> scripts/refresh_sectoral_snapshot.py
 -> SectorSnapshotStore.write_snapshot()
 -> PostgreSQL
 -> /projector/sectoral-snapshot
 -> /projector/sector-skills-comparison
 -> Streamlit dashboard
```

Tables:

- `sector_snapshot_runs`: refresh metadata, status, version and year/location.
- `sector_yearly_snapshots`: one sector row per completed run.

Read rule:

```text
latest completed run for (year, location_code)
```

This keeps long Tracker aggregation out of normal dashboard requests.

## Current Caveats

- There is no standardized error response model.
- Date ordering is not explicitly validated.
- Cache invalidation is mostly manual.
- Green and digital flags are currently false by default in runtime enrichment.
- Sector counts are relationship-oriented when one job has many sectors.
- The shared `ProjectorEngine` state is process-local and in-memory.
- Real Tracker backfills still need operational validation before closing the refresh pipeline.

## Production Hardening

Implemented:

- validation errors use a stable `{detail: {error: {code, message, field}}}` envelope
- date formats, date ranges, statistical parameters, and snapshot years are validated
- completed Tracker cache entries use a configurable TTL
- `/projector/readiness` reports Tracker authentication and snapshot DB availability

Remaining priorities:

1. Extend cache invalidation controls beyond the default Tracker TTL.
2. Add versioning, for example `/api/v1/projector/...`.
3. Expand automated tests for API-only sectoral payloads and no-data responses.
4. Monitor scheduled snapshot refreshes in production and alert on repeated failures.
