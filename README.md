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

## Current Runtime Entry Points

Start the API from the repository root:

```bash
uvicorn app.main:app --reload
```

Start the dashboard in a second terminal:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

The API is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Projector base path: `http://127.0.0.1:8000/projector`

`uvicorn main:app --reload` still exists as a legacy root entrypoint, but `app.main:app` is the package entrypoint aligned with the current code layout.

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

Create a `.env` file in the repository root:

```env
TRACKER_API=https://your-tracker-url
TRACKER_USERNAME=your_username
TRACKER_PASSWORD=your_password
DATABASE_URL=postgresql://skillab:skillab@localhost:5432/skillab_projector
```

## Local Database

Only PostgreSQL is dockerized for now:

```bash
docker compose up -d projector-db
```

The container applies `migrations/*.sql` on first boot and seeds a fake 2024 sector snapshot. Use the dashboard's "demo sector snapshot" flag to read the seeded `DEMO` dataset.

To reseed from scratch:

```bash
docker compose down -v
docker compose up -d projector-db
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
- `POST /projector/emerging-skills`
- `POST /projector/stop`

All endpoints currently accept `application/x-www-form-urlencoded` form data.

### Main Analysis

`POST /projector/analyze-skills` fetches jobs from Tracker, enriches skill labels, computes rankings, trends, regional projections and optional sectoral intelligence.

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
- [Documentation index](docs/README.md)
- [Overview](docs/overview.md)
- [Endpoint cheatsheet](docs/endpoint-cheatsheet.md)
- [API reference](docs/api-reference.md)
- [Data model](docs/data-model.md)
- [Statistics](docs/statistic.md)
- [Architecture](docs/architecture.md)
- [Examples](docs/examples.md)
- [Sector intelligence](docs/sector-intelligence.md)
- [Data sources](docs/data-sources.md)

Historical or sprint-specific notes remain in the repository only when useful for context, and they are marked as historical when they no longer describe the current implementation.
