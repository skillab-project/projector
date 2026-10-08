# SKILLAB Projector

SKILLAB Projector is a FastAPI analytics service that sits on top of the SKILLAB Tracker and turns raw job postings into labor-market intelligence.

It provides:
- top requested skills
- sector distribution
- top employers and job titles
- emerging and declining skill trends
- geographic and NUTS-like regional projections
- optional sectoral intelligence from Tracker API sectors

The project also includes a Streamlit dashboard for exploring the API output.

Start from [docs/quick-start.md](docs/quick-start.md) for the current intelligence design, local run commands and dashboard navigation.

For environment variables, service ports and Docker Compose flags, see the
[configuration guide](docs/configuration.md).

For frontend handoff, see the [demo dashboard guide](docs/dashboard-demo.md).

## Current Runtime Entry Points

Start the API from the repository root:

```bash
uvicorn app.main:app --reload
```

Start the dashboard in a second terminal:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

Run API, dashboard and PostgreSQL with Docker:

```bash
docker compose -f docker-compose.dev.yml up -d \
  projector-db projector-api projector-dashboard
```

The API is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Projector base path: `http://127.0.0.1:8000/projector`

Analysis endpoints use an asynchronous job contract: every analysis `POST` returns `202 Accepted` with a unique `task_id`; poll `GET /projector/tasks/{task_id}` until it returns `completed` with `result` or `failed` with `error`. Health, readiness, stop and documentation endpoints remain synchronous. The Streamlit dashboard performs this polling automatically.

`uvicorn main:app --reload` still exists as a historical root entrypoint, but it does not implement the asynchronous task contract. `app.main:app` is the only maintained package entrypoint.

## Self-Contained Synthetic Demo

The repository includes a standalone demo stack that does not require access to the production SKILLAB Tracker. It runs the complete Projector workflow against a local Tracker-compatible mock API and a deterministic synthetic dataset.

The demo architecture is:

```text
Streamlit dashboard
        |
        v
Projector API --------> PostgreSQL sector snapshots
        |
        v
Mock Tracker API -----> synthetic_jobs.json
```

The synthetic dataset contains 8,000 postings from 2020 through October 7, 2026. It covers six NUTS2 regions, preserves the full country/NUTS1/NUTS2/NUTS3 hierarchy, includes every sector in every region, and uses controlled regional and temporal distributions.

### Start the demo

From the repository root, build and start the complete stack:

```bash
docker compose -f demo-docker-compose.yml up --build -d
```

This starts:

| Service | Address | Purpose |
|---|---|---|
| Demo dashboard | `http://localhost:8501` | Interactive Streamlit interface |
| Projector API | `http://localhost:8000/projector/docs` | Projector endpoints and Swagger UI |
| Mock Tracker API | `http://localhost:8001/docs` | Tracker-compatible demo API |
| PostgreSQL | `localhost:5433` | Sector snapshot storage |
| Snapshot refresh | background service | Builds yearly and regional sector snapshots |

The mock Tracker generates the synthetic dataset automatically on first startup. Snapshot-backed views may take longer to become available because `projector-snapshot-refresh` populates PostgreSQL after the database and mock Tracker are ready.

To follow startup and snapshot population:

```bash
docker compose -f demo-docker-compose.yml logs -f \
  mock-tracker projector-api projector-snapshot-refresh
```

### Use the demo

1. Open `http://localhost:8501`.
2. Select a dashboard view.
3. Use exact dates, keywords and NUTS codes from the [English demo query guide](docs/DEMO_QUERY_GUIDE_EN.md).
4. Use live views first: Job Demand Overview, Temporal Analysis, Regional Temporal Analysis and Region Comparison.
5. Use snapshot views after the snapshot refresh has populated PostgreSQL: Sector Overview, Sector Skills Comparison, Regional Sector Distribution and snapshot-mode Skill Explorer.

The available regional hierarchy includes:

```text
IT -> ITF -> ITF4 -> ITF47 / ITF45 / ITF43
IT -> ITC -> ITC4 -> ITC4C / ITC46 / ITC47
DE -> DE3 -> DE30 -> DE300
DE -> DE2 -> DE21 -> DE212 / DE211 / DE213
FR -> FR1 -> FR10 -> FR101 / FR105
FR -> FRK -> FRK2 -> FRK26 / FRK24 / FRK25
```

For ready-to-run scenarios and expected results, see:

- [English demo query guide](docs/DEMO_QUERY_GUIDE_EN.md)
- [Italian demo query guide](docs/DEMO_QUERY_GUIDE_IT.md)
- [Dashboard implementation guide](docs/dashboard-demo.md)

### Stop or reset the demo

Stop the demo while preserving generated data and snapshots:

```bash
docker compose -f demo-docker-compose.yml down
```

Delete the demo-only volumes and regenerate the dataset, caches and snapshots from scratch:

```bash
docker compose -f demo-docker-compose.yml down -v
docker compose -f demo-docker-compose.yml up --build -d
```

The demo stack is isolated from production configuration. Only `demo-docker-compose.yml` points `TRACKER_API` to the local mock Tracker; the regular Compose files and production Tracker settings are unchanged.

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file for direct Python execution, or `dev.env` for the local
Docker stack:

```env
TRACKER_API=https://your-tracker-url
TRACKER_USERNAME=your_username
TRACKER_PASSWORD=your_password
TRACKER_CACHE_TTL_DAYS=30
DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
```

The complete variable reference and the distinction between the two files are
documented in [docs/configuration.md](docs/configuration.md).

## Local Database

Start only PostgreSQL:

```bash
docker compose -f docker-compose.dev.yml up -d projector-db
```

The container applies `migrations/*.sql` on first boot and seeds demo sector snapshots for 2020-2024, including demo/regional data.

To reseed from scratch:

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d projector-db
```

## Repository Layout

```text
repo-root/
├── app/
│   ├── main.py
│   ├── api/routes/projector.py
│   ├── client/tracker_client.py
│   ├── core/
│   ├── schemas/responses.py
│   ├── services/
│   │   ├── projector_service.py
│   │   ├── esco_loader.py
│   │   └── analytics/
│   └── example_dashboard/demo_dashboard.py
├── complementary_data/
├── docs/
├── migrations/
├── scripts/
├── cache_data/
└── requirements.txt
```

The active backend flow is:

```text
app.main
 -> app.api.routes.projector
 -> app.services.projector_service.ProjectorService
 -> TrackerClient / analytics modules
 -> app.schemas.responses
```

## Public API

The current public endpoints are:

- `POST /projector/analyze-skills`
- `POST /projector/compare-regions`
- `POST /projector/temporal-projections`
- `POST /projector/regional-temporal`
- `POST /projector/skill-explorer`
- `POST /projector/statistical-comparison`
- `POST /projector/sectoral-snapshot`
- `POST /projector/sector-skills-comparison`
- `POST /projector/regional-sectoral`
- `POST /projector/sectoral-intelligence`
- `POST /projector/emerging-skills`
- `GET /projector/tasks/{task_id}`
- `GET /projector/health`
- `GET /projector/readiness`
- `POST /projector/stop`

Analysis `POST` endpoints accept `application/x-www-form-urlencoded` form data and return a task acknowledgement. See [API reference](docs/api-reference.md) for the task lifecycle and final result envelopes.

### Main Analysis

`POST /projector/analyze-skills` fetches jobs from Tracker, enriches skill labels, computes rankings, trends, regional projections and optional sectoral intelligence.

The direct response is a task acknowledgement. The analysis structure described below is available under `result` after polling the returned `status_url`.

Common fields:
- `keywords`: optional list of search keywords
- `locations`: optional list of Tracker location codes
- `min_date`: required date, `YYYY-MM-DD`
- `max_date`: required date, `YYYY-MM-DD`
- `page`: ranking output page, default `1`
- `page_size`: ranking output size, default `50`
- `demo`: enables synthetic NUTS-like projection when only country-level locations are available
- `include_sectoral`: enables sectoral intelligence

Sectoral fields:
- `sector_system`: accepted for compatibility; current runtime uses `nace`
- `sector_level`: accepted for compatibility; current runtime uses Tracker sector labels
- `skill_group_level`: accepted for compatibility
- `occupation_level`: accepted for compatibility

Example:

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "include_sectoral=true" \
  -d "sector_system=nace"
```

## Sector Intelligence

Sector intelligence is API-only and observed-only.

Current path:

```text
Tracker job["sectors"] x Tracker job["skills"]
```

When sectoral intelligence is enabled, the service builds:
- `insights.sectoral`: observed sector-skill payload
- `insights.sectoral_mode`: `nace`
- `insights.sectoral_views.nace`: dashboard wrapper with `sector_level=tracker_sector`

Sectors are Tracker labels, not derived NACE hierarchy levels. Sector totals are relationship counts: one job with multiple sectors contributes to each listed sector.

See [Sector intelligence](docs/sector-intelligence.md) and [Statistics](docs/statistic.md).

## Documentation

Start here:
- [Contributing and quality workflow](CONTRIBUTING.md)
- [Documentation index](docs/README.md)
- [Self-contained demo query guide](docs/DEMO_QUERY_GUIDE_EN.md)
- [Overview](docs/overview.md)
- [Endpoint cheatsheet](docs/endpoint-cheatsheet.md)
- [API reference](docs/api-reference.md)
- [Data model](docs/data-model.md)
- [Statistics](docs/statistic.md)
- [Architecture](docs/architecture.md)
- [Examples](docs/examples.md)
- [Sector intelligence](docs/sector-intelligence.md)
- [Data sources](docs/data-sources.md)

Swagger is available at `http://127.0.0.1:8000/docs` for interactive endpoint testing.

Historical or sprint-specific notes remain in the repository only when useful for context, and they are marked as historical when they no longer describe the current implementation.
