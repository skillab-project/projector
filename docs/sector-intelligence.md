# Sector Intelligence

Sector intelligence is now built from Tracker API job payloads only.

The preferred endpoint for the default frontend sector overview is:

```text
POST /projector/sectoral-snapshot
```

It returns one annual aggregate row per sector:

- `job_count`: jobs linked to that sector
- `job_share`: sector jobs / all sector assignments
- `total_skill_mentions`: skill occurrences in that sector
- `unique_skills`: distinct skills in that sector
- `top_skills`: most requested skills in that sector
- `top_job_titles`: most frequent titles in that sector

Use the detailed endpoint only for drill-downs:

```text
POST /projector/sectoral-intelligence
```

`POST /projector/analyze-skills` still supports `include_sectoral=true` for compatibility.

Default sectoral reads are static-first:

- `data_source=cache`: read local `cache_data/` only. No live Tracker fetch.
- `data_source=live`: fetch Tracker and refresh local cache.

Use `sectors` for sector-first exploration. Use `keywords` only as optional job-text filter.

## Source

Each job can contain:

```text
job["skills"]  -> ESCO skill ids
job["sectors"] -> sector labels from Tracker
```

The sector-skill matrix is built by co-occurrence inside the same job:

```text
for each job:
  for each sector in job["sectors"]:
    for each skill in job["skills"]:
      sector_skill_count[sector][skill] += 1
```

If a job has no sectors, it is assigned to `Sector not specified`.

## Yearly Static Dataset

`/projector/sectoral-snapshot` is a read-only endpoint for the dashboard. It should read the latest completed annual snapshot from PostgreSQL.

Runtime requests do not fetch Tracker for this view when `DATABASE_URL` is configured.

Refresh command:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024
```

Optional location-specific refresh:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024 --location-code IT
```

Storage tables:

- `sector_snapshot_runs`: immutable refresh runs and status
- `sector_yearly_snapshots`: one row per sector for a completed run

API reads only the latest `completed` run for `(year, location_code)`. Failed or running refreshes do not affect users.

If no completed snapshot exists, the API returns `status=not_available` and a clear message.

## Current Scope

Only observed sectoral evidence is used.

Included:
- Tracker jobs
- Tracker skills
- Tracker job sectors

Excluded from runtime:
- ISCO comparison
- ESCO-NACE crosswalk
- local NACE labels
- canonical ESCO occupation-skill relations
- ESCO skill groups
- official ESCO matrix

## Payload

When `include_sectoral=true`, `/projector/analyze-skills` returns:

```json
{
  "sectoral_mode": "nace",
  "sectoral": [],
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
  }
}
```

Sectoral intelligence has an independent time mode:

- `latest`: last six months, default.
- `selected_period`: same window as the main dashboard request.
- `year`: full calendar year snapshot.
- `comparison`: two explicit windows plus sector deltas.

Each item contains:
- `sector`
- `sector_label`
- `observed_skills`
- `observed_groups`
- `sector_metrics`
- `skill_transversal_insights`

## Interpretation

Sector totals are relationship counts, not unique job counts.

One job with 3 sectors and 10 skills contributes 30 sector-skill events.

This is intentional: the dashboard answers which skills are associated with which Tracker sectors in the analyzed batch.
