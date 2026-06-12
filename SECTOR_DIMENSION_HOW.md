# Sector Dimension: Current Implementation

Compact technical note for the current sector dimension.

Maintained docs:

- [Sector intelligence](docs/sector-intelligence.md)
- [Database](docs/database.md)
- [Statistics](docs/statistic.md)

Related issues: #44, #47, #48, #49, #52, #54.

## Goal

The sector dimension answers:

- what skills are requested in one sector,
- how one sector changes across years,
- how multiple sectors compare on selected skills,
- which job titles appear in a sector.

## Runtime Source

Current sector intelligence uses Tracker API fields:

```text
job["sectors"]
job["skills"]
job["title"]
job["location_code"]
```

Core mapping:

```text
Tracker job["sectors"] x Tracker job["skills"]
```

## Current Views

```text
Sector Overview
├── Snapshot
│   one sector, one year
│
└── Sector Evolution
    one sector, two years

Sector Skills Comparison
└── Heatmap
    many sectors x many skills
```

## Static Snapshot Flow

```text
Tracker API
 -> scripts/refresh_sectoral_snapshot.py
 -> PostgreSQL
 -> /projector/sectoral-snapshot
 -> dashboard
```

The dashboard reads pre-aggregated yearly snapshots. Heavy Tracker aggregation should happen in refresh jobs, not live dashboard requests.

## Excluded Legacy Runtime

The current sector dashboard flow does not use:

- ISCO comparison
- NACE hierarchy files
- ESCO-NACE crosswalk
- canonical ESCO occupation-skill relations
- ESCO skill groups
- official ESCO matrix

These can remain in the repository for historical compatibility, but they are not part of the current sector intelligence runtime.

## Interpretation Caveat

Sector totals are relationship-oriented.

If one job has multiple sectors, it contributes to each listed sector.

If one job has multiple sectors and multiple skills, every sector-skill pair contributes to the sector-skill matrix.
