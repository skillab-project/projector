# Internal Method Map

Related issues: #7, #10.

This document maps the maintained internal methods by responsibility.

## Runtime Path

```text
app.main
 -> app.api.routes.projector
 -> app.core.container.service
 -> app.services.projector_service.ProjectorService
    -> app.client.tracker_client.TrackerClient
    -> app.services.analytics/*
    -> app.services.sector_snapshot_store.SectorSnapshotStore
```

## Route Layer

File: `app/api/routes/projector.py`

Responsibilities:

- define public `/projector/*` endpoints
- validate dates, years and request shape before service calls
- translate service exceptions into HTTP errors
- keep business logic out of FastAPI route functions

Main helpers:

| Method | Role |
| --- | --- |
| `error_detail` | Standard error body fragment. |
| `parse_iso_date` | Parses optional ISO dates. |
| `validate_date_range` | Rejects invalid date windows. |
| `validate_year` | Rejects unsupported snapshot years. |

## Projector Service

File: `app/services/projector_service.py`

`ProjectorService` is the orchestration layer. It coordinates Tracker reads, analytics modules, snapshot storage and response shaping.

Public methods:

| Method | Role |
| --- | --- |
| `analyze_skills` | Live keyword/date/region analysis from Tracker jobs. Builds skill, trend, regional and optional sector distributions. |
| `emerging_skills` | Trend-only analysis over a date window. |
| `sectoral_intelligence` | Live sector drill-down for the current sector-skill model. |
| `sectoral_snapshot` | Yearly sector overview from PostgreSQL snapshots. |
| `sector_skills_comparison` | Sector x skill heatmap data from PostgreSQL snapshots. |
| `regional_sectoral` | Regional sector distribution from PostgreSQL snapshots. |
| `stop` | Sets cooperative stop behavior for long requests. |

Internal method groups:

| Group | Methods | Role |
| --- | --- | --- |
| Snapshot store reads | `_read_sector_snapshot_store`, `_read_sector_refresh_status`, `_sector_snapshot_store_enabled` | Isolate optional DB access and fallback behavior. |
| Snapshot enrichment | `_enrich_sector_snapshot_payload`, `_enrich_sector_skill_metrics`, `_build_sector_evolution` | Add growth and evolution metrics using a reference year. |
| Comparison data | `_select_comparison_sectors`, `_select_comparison_skills`, `_index_snapshot_skill_counts`, `_build_sector_skill_comparison_matrix` | Build heatmap rows for selected sectors, skills and metrics. |
| Fetch windows | `_today`, `_latest_window`, `_year_window`, `_fetch_jobs_for_window` | Normalize date windows and Tracker fetch calls. |
| Sector extraction | `_normalize_sector_filter`, `_job_sector_labels`, `_filter_jobs_by_sector`, `_build_sector_snapshot_rows` | Build observed sector-skill rows from `job["sectors"]` and `job["skills"]`. |
| Label enrichment | `_skill_meta`, `_ensure_skill_labels` | Resolve skill labels and metadata through Tracker-backed state. |
| Legacy-compatible payloads | `_build_sectoral_items`, `_sectoral_window_meta`, `_compare_sectoral_items`, `_build_temporal_sectoral_payload` | Keep live sectoral endpoint response shape stable. |

Maintenance rule: dashboard snapshot endpoints should read PostgreSQL snapshots, not fetch long Tracker windows live.

## Tracker Client

File: `app/client/tracker_client.py`

`TrackerClient` owns Tracker HTTP communication and file cache behavior.

| Method | Role |
| --- | --- |
| `_get_token` | Loads or requests the Tracker access token. |
| `fetch_all_jobs` | Fetches all matching Tracker jobs, with pagination, cache and checkpoint support. |
| `_fetch_jobs_page` | Fetches one Tracker jobs page. |
| `fetch_skill_names` | Resolves skill URI labels through Tracker. |
| `fetch_occupation_labels` | Resolves occupation URI labels through Tracker. |
| `load_cached_jobs` / `write_completed_jobs_cache` | Read/write complete job result caches. |
| `load_job_fetch_checkpoint` / `write_job_fetch_checkpoint` | Resume interrupted paginated fetches. |
| `clear_completed_jobs_cache` / `clear_job_fetch_checkpoint` | Manual cache cleanup helpers. |

Maintenance rule: cache keys are based on normalized filters. Any new filter field must be included in the filters passed to `fetch_all_jobs`.

## Snapshot Store

File: `app/services/sector_snapshot_store.py`

`SectorSnapshotStore` is the PostgreSQL boundary for yearly sector intelligence.

| Method | Role |
| --- | --- |
| `enabled` | Reports whether `DATABASE_URL` is configured. |
| `ensure_schema` | Creates required tables and indexes. |
| `write_snapshot` | Stores one completed snapshot run and its sector rows. |
| `write_refresh_status` | Stores running, failed or completed refresh metadata. |
| `read_latest` | Reads the latest completed snapshot for year and optional location. |
| `read_regional_sectoral` | Reads regional sector summaries for a year. |
| `read_refresh_status` | Reads latest refresh status for dashboard/API messaging. |
| `latest_completed_at` | Supports scheduler due-target checks. |

Maintenance rule: failed and running runs must never replace the latest completed snapshot shown to users.

## Analytics Modules

Folder: `app/services/analytics/`

| Module | Role |
| --- | --- |
| `market.py` | Skill ranking, counts and dashboard intelligence fields. |
| `trends.py` | Trend comparison across periods. |
| `regional.py` | Regional and NUTS-like projections. |
| `sectoral.py` | Observed sector-skill aggregations and compatibility helpers. |
| `occupations.py` | Occupation and older sector mapping helpers retained for compatibility. |

Maintenance rule: current sector intelligence uses Tracker `job["sectors"]`. Do not reintroduce ISCO/NACE file-derived sectors into current sector views.

## Snapshot Scripts

Folder: `scripts/`

| Script | Role |
| --- | --- |
| `refresh_sectoral_snapshot.py` | Refresh one year/location snapshot. |
| `backfill_sectoral_snapshots.py` | Fetch years and regions, then populate PostgreSQL snapshots. |
| `schedule_sectoral_snapshot_refresh.py` | Periodically refresh stale snapshot targets. |
| `bootstrap_sectoral_snapshots.py` | Production bootstrap command wrapper for initial population. |
| `validate_sectoral_snapshot_pipeline.py` | Validate DB, service and optional HTTP snapshot behavior. |

Maintenance rule: large historical windows belong in scripts/scheduler, not normal dashboard request paths.

## Change Checklist

When changing endpoint contracts:

- update `docs/api-reference.md`
- update `docs/endpoint-cheatsheet.md`
- update dashboard API info examples
- update response tests

When changing metrics:

- update `docs/statistic.md`
- update dashboard metric tooltips
- update snapshot comparison tests

When changing snapshot storage:

- update migrations
- update `docs/database.md`
- update `docs/production-snapshots.md`
- validate with `scripts/validate_sectoral_snapshot_pipeline.py`
