# SKILLAB Projector

SKILLAB Projector is a FastAPI analytics service that sits on top of the SKILLAB Tracker and turns raw job postings into labor-market intelligence.

It provides:
- top requested skills
- sector distribution
- top employers and job titles
- emerging and declining skill trends
- geographic and NUTS-like regional projections
- optional sectoral intelligence for ISCO and NACE views

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
 -> TrackerClient / analytics modules / ESCO loaders
 -> app.schemas.responses
```

## Public API

The current public endpoints are:

- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

All endpoints currently accept `application/x-www-form-urlencoded` form data.

### Main Analysis

`POST /projector/analyze-skills` fetches jobs from Tracker, enriches skills and occupations, computes rankings, trends, regional projections and optional sectoral intelligence.

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
- `sector_system`: `isco`, `nace`, or `both`
- `sector_level`: `isco_group`, `nace_section`, `nace_division`, `nace_group`, `nace_class`, or technical compatibility value `nace_code`
- `skill_group_level`: ESCO skill group level used for group aggregation
- `occupation_level`: ESCO occupation level used for official matrix lookup

Example:

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "include_sectoral=true" \
  -d "sector_system=both" \
  -d "sector_level=nace_section"
```

## Sector Systems

The service supports two sector interpretation systems.

- ISCO: occupation-based. The path is `job -> occupation -> isco_group -> ISCO label`.
- NACE: economic-activity-based. The path is `job -> occupation -> ESCO-NACE crosswalk -> NACE code/title`.

When sectoral intelligence is enabled, the service builds:
- `insights.sectoral`: backward-compatible selected/default sectoral payload
- `insights.sectoral_mode`: requested mode
- `insights.sectoral_views`: dual ISCO and NACE payloads
- `insights.sector_view_names`: display names for observed, canonical and matrix views

NACE is relation-oriented in this implementation. One ESCO occupation may map to multiple NACE codes, so the same job-derived skill evidence may appear in multiple NACE sectors. This is intentional for skill-sector discovery and should not be read as strict one-to-one job accounting.

For the detailed ISCO/NACE view definitions, including Observed, Canonical, Official Matrix, Derived Canonical and Aggregated Official Matrix semantics, see [Sector intelligence](docs/sector-intelligence.md).

## Documentation

Start here:
- [Documentation index](docs/README.md)
- [Overview](docs/overview.md)
- [Endpoint cheatsheet](docs/endpoint-cheatsheet.md)
- [API reference](docs/api-reference.md)
- [Data model](docs/data-model.md)
- [Architecture](docs/architecture.md)
- [Examples](docs/examples.md)
- [Sector intelligence](docs/sector-intelligence.md)
- [Data sources](docs/data-sources.md)

Historical or sprint-specific notes remain in the repository only when useful for context, and they are marked as historical when they no longer describe the current implementation.
