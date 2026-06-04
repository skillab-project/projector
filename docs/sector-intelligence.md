# Sector Intelligence

Sector intelligence is Tracker API only.

Related issues: #44, #47, #48, #49, #52, #54.

## Source

Each job can contain:

```text
job["skills"]  -> ESCO skill ids
job["sectors"] -> Tracker sector labels
```

The sector-skill matrix is built by co-occurrence inside the same job:

```text
for each job:
  for each sector in job["sectors"]:
    for each skill in job["skills"]:
      sector_skill_count[sector][skill] += 1
```

If a job has no sectors, it is assigned to `Sector not specified`.

## Dashboard Views

```text
Sector Overview
├── Snapshot
│   [Sector] [Region] [Year]
│
│   Use when:
│   understand one sector in one year
│
│   Shows:
│   - sector KPIs
│   - top-10 skills
│   - all skills
│   - skill portfolio bubble chart
│   - top job titles
│
└── Sector Evolution
    [Sector] [Region] [From year] -> [To year]

    Use when:
    understand how one sector changed

    Shows:
    - job delta
    - job growth
    - new skills
    - disappeared skills
    - growing skills
    - declining skills
    - skill churn

Sector Skills Comparison
└── Heatmap
    [Year or From/To] [Region] [Sectors] [Skills] [Metric]

    Use when:
    compare multiple sectors against multiple skills
```

## Main Endpoints

| View | Endpoint |
| --- | --- |
| Sector Overview / Snapshot | `POST /projector/sectoral-snapshot` |
| Sector Overview / Evolution | `POST /projector/sectoral-snapshot` with `reference_year` |
| Sector Skills Comparison | `POST /projector/sector-skills-comparison` |
| Legacy/drill-down sectoral detail | `POST /projector/sectoral-intelligence` |
| Keyword-driven skill overview with sector distribution | `POST /projector/analyze-skills` |

## Yearly Static Dataset

`/projector/sectoral-snapshot` is static-first.

When `DATABASE_URL` is configured:

- the API reads PostgreSQL
- it returns the latest completed snapshot for `(year, location_code)`
- it does not call Tracker during dashboard requests
- missing snapshots return `status=not_available`

Local DB:

```bash
docker compose up -d projector-db
```

Connection:

```text
DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
```

Refresh:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024
python scripts/refresh_sectoral_snapshot.py --year 2024 --location-code IT
```

Backfill all available regions for a year range:

```bash
python scripts/backfill_sectoral_snapshots.py --start-year 2020 --end-year 2024
```

Recurring refresh:

```bash
python scripts/schedule_sectoral_snapshot_refresh.py --interval-months 3
```

## PostgreSQL Tables

`sector_snapshot_runs`

| Column | Meaning |
| --- | --- |
| `id` | run id |
| `year` | snapshot year |
| `location_code` | optional regional filter |
| `version` | monotonically increasing version for year/location |
| `status` | `running`, `completed`, etc. |
| `period_start`, `period_end` | yearly window |
| `total_jobs` | Tracker jobs used by the run |
| `created_at`, `completed_at` | run timestamps |
| `message` | optional run note |

`sector_yearly_snapshots`

| Column | Meaning |
| --- | --- |
| `run_id` | parent refresh run |
| `year` | snapshot year |
| `location_code` | optional region |
| `sector`, `sector_label` | Tracker sector |
| `job_count` | jobs linked to the sector |
| `job_share` | sector share within the snapshot |
| `total_skill_mentions` | sector-skill co-occurrence count |
| `unique_skills` | distinct skills in sector |
| `top_skills` | top-10 skill JSON |
| `all_skills` | full skill JSON |
| `top_job_titles` | top job-title JSON |

Read rule:

```text
latest completed run by year + location_code
```

## Current Scope

Included:

- Tracker jobs
- Tracker skills
- Tracker sectors
- Tracker locations
- Tracker job titles

Excluded from runtime:

- ISCO comparison
- ESCO-NACE crosswalk
- local NACE files
- canonical ESCO occupation-skill relations
- ESCO skill groups
- official ESCO matrix

## Interpretation

Sector totals are relationship counts, not always unique job counts.

One job with 3 sectors and 10 skills contributes:

```text
3 sector assignments
30 sector-skill events
```

This is intentional: the sector views answer which skills are associated with which Tracker sectors.
