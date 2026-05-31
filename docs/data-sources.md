# Data Sources

SKILLAB Projector runtime uses Tracker API data for the current dashboard flow.

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
