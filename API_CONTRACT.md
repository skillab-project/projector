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

## Asynchronous Execution

Every analysis `POST` validates the submitted form and returns immediately with `HTTP 202 Accepted`:

```json
{
  "task_id": "4dd9955b-a23e-4db7-aa16-ff749b576f0a",
  "status": "queued",
  "status_url": "/projector/tasks/4dd9955b-a23e-4db7-aa16-ff749b576f0a",
  "created_at": "2026-10-08T10:00:00Z"
}
```

Read the task with `GET /projector/tasks/{task_id}`. Its state is `queued`, `running`, `completed`, or `failed`. A completed task exposes the original endpoint payload in `result`; a failed task exposes `error.type` and `error.message`.

Health, readiness, task status, stop and documentation endpoints remain synchronous. Input validation errors are still returned synchronously as `HTTP 422` and do not create a task.

Execution uses a bounded, process-local worker queue. When the queue is full, submission returns `HTTP 503` with error code `task_queue_full`. Failure messages are sanitized; full exception details are logged server-side with the task ID.

## Public Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /projector/analyze-skills` | keyword/job-search skill intelligence |
| `POST /projector/compare-regions` | direct comparison of two NUTS regions |
| `POST /projector/temporal-projections` | period series and baseline projections |
| `POST /projector/regional-temporal` | regional demand through time |
| `POST /projector/skill-explorer` | one skill across sectors, regions and time |
| `POST /projector/statistical-comparison` | 2x2 inferential evidence |
| `POST /projector/sectoral-snapshot` | yearly sector snapshot and one-sector evolution |
| `POST /projector/sector-skills-comparison` | sectors x skills heatmap |
| `POST /projector/regional-sectoral` | yearly regional sector distribution |
| `POST /projector/sectoral-intelligence` | legacy/drill-down observed sector detail |
| `POST /projector/emerging-skills` | trend-only analysis |
| `GET /projector/tasks/{task_id}` | task state, completed result or failure |
| `GET /projector/health` | service reachability |
| `GET /projector/readiness` | dependency readiness |
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
- Task state and results are process-local and are lost when the API process restarts.
- Clients must reach the same API process that accepted the task; the current deployment runs one Uvicorn worker.
- Only the most recent terminal task records are retained; `PROJECTOR_TASK_MAX_RECORDS` controls the limit.
- The historical root `main:app` entrypoint does not implement this contract; use `app.main:app`.
- Snapshot refresh scheduling is external/not automated in-process.
