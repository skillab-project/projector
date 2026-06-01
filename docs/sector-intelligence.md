# Sector Intelligence

Sector intelligence is now built from Tracker API job payloads only.

The preferred endpoint for frontend sector views is:

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
