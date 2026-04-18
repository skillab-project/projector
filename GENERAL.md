
# SKILLAB Projector

The **SKILLAB Projector** is a microservice-based analytics component that transforms raw job-posting data into structured labor-market intelligence.

It is composed of:
- a **FastAPI backend** exposing the Projector API
- a **Streamlit dashboard** for interactive exploration of results

The service sits on top of the **SKILLAB Tracker** and provides:
- top requested skills
- sector distribution
- top employers
- top job titles
- emerging and declining skill trends
- geographic breakdown
- NUTS-like regional projections
- specialization indicators by area

---

## Index
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Environment configuration](#environment-configuration)
- [Install dependencies](#install-dependencies)
- [Run the backend service](#run-the-backend-service)
- [Run the Streamlit dashboard](#run-the-streamlit-dashboard)
- [How the frontend connects to the backend](#how-the-frontend-connects-to-the-backend)
- [Available API endpoints](#available-api-endpoints)
- [Typical local workflow](#typical-local-workflow)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)

---

## Project structure

Repository layout:

```text
repo-root/
├── main.py
├── test.py
├── schemas.py
├── demo_dashboard.py           # Streamlit frontend
└── docs/
    ├── README.md
    ├── overview.md
    ├── api-reference.md
    ├── data-model.md
    ├── architecture.md
    ├── [User Story{...}.md]
    └── examples.md
   
````

---

## Requirements

Recommended:

* Python 3.10 or newer
* access to a running **SKILLAB Tracker**
* valid Tracker credentials

---

## Environment configuration

Create a `.env` file in the project root with the credentials used by the backend to talk to the Tracker.

```env
TRACKER_API=https://your-tracker-url
TRACKER_USERNAME=your_username
TRACKER_PASSWORD=your_password
```

### Meaning of the variables

* `TRACKER_API`: base URL of the Tracker service
* `TRACKER_USERNAME`: username used for Tracker login
* `TRACKER_PASSWORD`: password used for Tracker login

The backend reads these variables at startup through `python-dotenv`.

---

## Install dependencies

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

If you do not yet have a `requirements.txt`, make sure at least these packages are installed:

```bash
pip install fastapi uvicorn httpx python-dotenv pydantic streamlit requests pandas plotly
```

---

## Run the backend service

Start the FastAPI backend from the project root.

### Recommended command

```bash
uvicorn main:app --reload
```

### Alternative

```bash
python main.py
```

If the application is configured normally, the backend will be available at:

* API base URL: `http://127.0.0.1:8000`
* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc: `http://127.0.0.1:8000/redoc`

### What the backend does

The backend:

1. receives filters from the client
2. authenticates against the Tracker
3. fetches job postings
4. enriches skills and occupation labels
5. computes rankings, trends, sectors, employers, and regional projections
6. returns structured JSON responses

---

## Run the Streamlit dashboard

Your frontend is implemented in **Streamlit**.

Assuming the file is named `demo_dashboard.py`, start it with:

```bash
streamlit run demo_dashboard.py
```

Streamlit will usually open automatically in your browser.
If it does not, open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

### What the dashboard provides

The dashboard includes:

* language switcher (Italian / English)
* search filters in the sidebar
* stop button for long-running analyses
* optional NUTS demo mode
* four main tabs:

  * Skill Analysis
  * Emerging Trends
  * Geographic Distribution
  * Sectors & Employers

---

## How the frontend connects to the backend

In the current frontend code, the backend base URL is hardcoded as:

```python
API_BASE_URL = "http://127.0.0.1:8000/projector"
```

This means:

* the FastAPI backend must be running locally on port `8000`
* the frontend will call:

  * `POST /projector/analyze-skills`
  * `POST /projector/stop`

### Important note

If you change backend host or port, you must also update this value in the Streamlit code.

For example, if the backend runs on another machine:

```python
API_BASE_URL = "http://<server-ip>:8000/projector"
```

---

## Available API endpoints

The current dashboard uses the following backend endpoints:

### `POST /projector/analyze-skills`

Main analysis endpoint used by the dashboard.

It receives filters such as:

* `keywords`
* `locations`
* `min_date`
* `max_date`
* `demo`

and returns:

* `dimension_summary`
* `ranking`
* `trends`
* `regional`
* `sectors`
* `job_titles`
* `employers`

### `POST /projector/stop`

Used by the dashboard stop button.

It sends a cooperative stop signal to the engine.

### `POST /projector/emerging-skills`

This endpoint exists in the backend but is not directly called by the current dashboard code, because trend information is already rendered from the response of `analyze-skills`.

---

## Typical local workflow

### 1. Start the backend

```bash
uvicorn main:app --reload
```

### 2. Start the dashboard

```bash
streamlit run dashboard.py
```

### 3. Open the dashboard

Usually at:

```text
http://localhost:8501
```

### 4. Configure filters

From the sidebar, set:

* keywords
* location code
* date range
* optional demo mode

### 5. Launch projection

Click:

```text
Lancia Proiezione 🚀
```

or

```text
Launch Projection 🚀
```

### 6. Explore the tabs

Use the four dashboard tabs to inspect:

* top skills
* market trends
* geography
* sectors, job titles, and employers

---

## Dashboard behavior details

### Search filters

The Streamlit sidebar collects:

* free-text keywords
* optional location code
* date range
* demo mode flag

These are sent to the backend as form data.

### Caching

The frontend uses:

```python
@st.cache_data(ttl=600)
```

for analysis requests.

That means repeated requests with the same parameters may be cached by Streamlit for 10 minutes.

### Session state

The dashboard stores the latest successful response in:

```python
st.session_state.all_data
```

This allows the interface to keep showing results even after the request has completed.

### Stop button

The stop button sends:

```python
requests.post(f"{API_BASE_URL}/stop")
```

This is a **cooperative stop**, not an immediate process kill.

The backend stops at the next safe checkpoint.

---

## Troubleshooting

## Backend does not start

Check:

* Python version
* dependencies installed
* `.env` file exists
* `TRACKER_API`, `TRACKER_USERNAME`, and `TRACKER_PASSWORD` are valid

## Dashboard shows “Server unreachable”

This usually means one of these:

* FastAPI backend is not running
* backend is running on a different host/port
* `API_BASE_URL` in the Streamlit file is wrong

## No data returned

Possible causes:

* Tracker returned no matching jobs
* filters are too restrictive
* Tracker credentials are invalid
* upstream Tracker is unavailable or slow

## Dashboard starts but charts are empty

Check the backend response first in Swagger:

```text
http://127.0.0.1:8000/docs
```

Try `POST /projector/analyze-skills` manually to verify that the backend is returning data.

## Tracker-related failures

The Projector depends on the Tracker for:

* authentication
* job retrieval
* skill metadata
* occupation metadata

If Tracker is down or slow, Projector behavior will also be affected.

---

## Documentation

Detailed documentation is available in the `/docs` folder:

* `docs/overview.md`
* `docs/api-reference.md`
* `docs/data-model.md`
* `docs/architecture.md`
* `docs/examples.md`

Swagger is available at:

```text
http://127.0.0.1:8000/docs
```

Use Swagger for interactive endpoint testing.
Use `/docs` for semantic and architectural explanations.

---

## Recommended development setup

For local development, keep two terminals open.

### Terminal 1 — backend

```bash
uvicorn main:app --reload
```

### Terminal 2 — dashboard

```bash
streamlit run dashboard.py
```

This is the simplest and most practical setup for day-to-day work.

---

## Notes on current implementation

The current dashboard is designed around the existing backend contract and expects:

* `dimension_summary`
* `insights`
* trend data inside `insights.trends`
* regional data inside `insights.regional`

If backend payloads change, the dashboard may need to be updated accordingly.

The frontend also assumes that geographic raw codes can be mapped manually to ISO-3 codes for the world map.

---

## Future improvements

Recommended next steps:

* move frontend backend URL to configuration instead of hardcoding it
* add health endpoint to the backend
* define a standard error response model
* align code and schema fully
* version the API under `/api/v1/...`
## Sector dimension modes

- **ISCO mode**: occupation-based sectors (ISCO groups), native ESCO views.
- **NACE mode**: activity-based sectors resolved via ESCO-NACE crosswalk.
- Dashboard selector controls the active sector system for charts/tables.
- NACE view naming:
  - Observed
  - Derived Canonical
  - Aggregated Official Matrix
