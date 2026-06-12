# SKILLAB Projector API Contract

Root-level summary of the maintained API contract.

Canonical docs:

- [Quick start](docs/quick-start.md)
- [API reference](docs/api-reference.md)
- [Data model](docs/data-model.md)
- [Statistics](docs/statistic.md)

Related issues: #1, #8, #44, #52, #54.

## Runtime

```bash
uvicorn app.main:app --reload
```

Dashboard:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

Content type:

```http
application/x-www-form-urlencoded
```

## Public Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /projector/analyze-skills` | keyword/job-search skill intelligence |
| `POST /projector/sectoral-snapshot` | yearly sector snapshot and one-sector evolution |
| `POST /projector/sector-skills-comparison` | sectors x skills heatmap |
| `POST /projector/sectoral-intelligence` | legacy/drill-down observed sector detail |
| `POST /projector/emerging-skills` | trend-only analysis |
| `GET /projector/health` | service reachability |
| `POST /projector/stop` | cooperative stop signal |

## Sector Contract

Current sector intelligence uses Tracker API data only:

```text
job["sectors"] x job["skills"]
```

No ISCO file, NACE file, ESCO-NACE crosswalk, canonical occupation-skill relation, skill group file or official ESCO matrix is used in the current sector dashboard flow.

## Sector Snapshot Contract

When `DATABASE_URL` is configured:

```text
/projector/sectoral-snapshot
/projector/sector-skills-comparison
```

read PostgreSQL yearly snapshots.

Snapshot source tables:

- `sector_snapshot_runs`
- `sector_yearly_snapshots`

Read rule:

```text
latest completed run for (year, location_code)
```

## Known Caveats

- No versioned API prefix yet.
- No standardized error envelope yet.
- Date ordering is not explicitly validated.
- Snapshot refresh scheduling is external/not automated in-process.
