# Data Sources

SKILLAB Projector uses Tracker API data for the current dashboard flow.

Related issues: #44, #54.

## Runtime Sources

| Source | Endpoint / field | Use |
| --- | --- | --- |
| Jobs | `POST {TRACKER_API}/jobs` | Raw job records |
| Skills | `job["skills"]` | Observed skill ids |
| Sectors | `job["sectors"]` | Observed sector labels |
| Locations | `job["location_code"]`, `nuts1`, `nuts2`, `nuts3` | Regional breakdown |
| Job titles | `job["title"]` | Job-title ranking |
| Employers | `job["organization"]` / fallback fields | Employer ranking |
| Skill labels | `POST {TRACKER_API}/skills` | Skill id to readable label |

## Stored Analytical Data

PostgreSQL stores pre-aggregated yearly sector snapshots.

| Table | Use |
| --- | --- |
| `sector_snapshot_runs` | refresh run metadata and latest completed lookup |
| `sector_yearly_snapshots` | one sector row per yearly/location snapshot |

The database is storage, not a separate source of truth. Snapshot rows are derived from Tracker jobs.

Local DB:

```bash
docker compose up -d projector-db
```

Refresh from Tracker:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024
```

## Not Loaded In Runtime

The current API-only flow does not load:

- `occupationSkillRelations_en.csv`
- `skillGroups_en.csv`
- `skillsHierarchy_en.csv`
- `occupations_en.csv`
- `ISCOGroups_en.csv`
- ESCO-NACE crosswalk workbook
- NACE labels CSV
- official ESCO matrix workbook

## Sector-Skill Source

Sector-skill statistics are built only from job co-occurrence:

```text
job["sectors"] x job["skills"]
```

No occupation-to-sector mapping is used.
