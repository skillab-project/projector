# SKILLAB Projector General Guide

This guide summarizes how to run and operate the current SKILLAB Projector implementation.

For the full documentation set, start from [docs/README.md](docs/README.md).

## What The Service Does

SKILLAB Projector is composed of:
- a FastAPI backend in `app/`
- a Streamlit dashboard in `app/example_dashboard/`
- local ESCO support data in `complementary_data/`

It transforms Tracker job postings into:
- skill rankings,
- employers and job-title rankings,
- trend analysis,
- regional projections,
- ISCO and NACE sectoral intelligence.

## Current Project Structure

```text
repo-root/
├── app/
│   ├── main.py
│   ├── api/routes/projector.py
│   ├── client/tracker_client.py
│   ├── core/
│   ├── schemas/responses.py
│   ├── services/
│   └── example_dashboard/demo_dashboard.py
├── complementary_data/
├── docs/
├── cache_data/
└── requirements.txt
```

Legacy root files are still present for historical compatibility, but the maintained backend entrypoint is `app.main:app`.

## Requirements

- Python 3.10 or newer
- access to a running SKILLAB Tracker
- valid Tracker credentials
- dependencies from `requirements.txt`

## Environment Configuration

Create `.env` in the repository root:

```env
TRACKER_API=https://your-tracker-url
TRACKER_USERNAME=your_username
TRACKER_PASSWORD=your_password
```

## Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run The Backend

```bash
uvicorn app.main:app --reload
```

The backend is available at:
- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run The Dashboard

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

The dashboard keeps the backend URL in Streamlit session state and defaults to:

```text
http://127.0.0.1:8000/projector
```

## Available Endpoints

- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/stop`

See [docs/api-reference.md](docs/api-reference.md) for the full request and response contract.

## Typical Local Workflow

1. Start the backend with `uvicorn app.main:app --reload`.
2. Start the dashboard with `streamlit run app/example_dashboard/demo_dashboard.py`.
3. Open the Streamlit URL shown in the terminal.
4. Configure keywords, location, date range and optional demo mode.
5. Launch the projection.
6. Explore skills, trends, geography, employers and sectoral views.

## Sector Dimension Modes

The current service supports:

- ISCO mode: occupation-based sectors.
- NACE mode: economic-activity sectors resolved through the ESCO-NACE crosswalk.
- Both mode: builds both views for dashboard comparison.

When sectoral intelligence is enabled, the response includes `sectoral`, `sectoral_mode`, `sectoral_views` and `sector_view_names`.

## Troubleshooting

Backend does not start:
- check Python version,
- check dependencies,
- check `.env`,
- check Tracker credentials.

Dashboard shows server unreachable:
- ensure FastAPI is running,
- check the dashboard backend URL,
- verify port `8000` is available.

No data returned:
- filters may be too restrictive,
- Tracker may have no matching jobs,
- Tracker may be unavailable,
- cached responses may reflect an older identical query.

Sectoral data missing:
- ensure `include_sectoral=true`,
- check that local ESCO files are available,
- inspect backend logs for loader warnings.

## Current Caveats

- Cache invalidation is manual.
- Error responses are not standardized yet.
- Date ordering is not validated before analysis.
- NACE mode keeps all crosswalk mappings, so NACE sector totals are relation counts rather than strict unique job counts.
