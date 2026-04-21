# SKILLAB Projector Documentation

This folder contains the maintained documentation for the current `app/` implementation of SKILLAB Projector.

## Reading Order

1. [Overview](overview.md) explains what the service does and who it is for.
2. [Endpoint cheatsheet](endpoint-cheatsheet.md) gives a compact consumer-facing schema of what each endpoint returns.
3. [API reference](api-reference.md) documents current public endpoints and form fields.
4. [Data model](data-model.md) explains response fields and metric semantics.
5. [Architecture](architecture.md) maps the runtime flow to the current code.
6. [Examples](examples.md) provides request examples and frontend integration patterns.
7. [Sector intelligence](sector-intelligence.md) explains ISCO/NACE sectoral analytics.
8. [Data sources](data-sources.md) explains Tracker, ESCO CSV files, ESCO matrix and ESCO-NACE crosswalk usage.
9. [Issue management](issue-management.md) defines issue labels, Project statuses and decision/implementation flows.

## Current Code Layout

```text
repo-root/
├── app/
│   ├── main.py
│   ├── api/routes/projector.py
│   ├── client/tracker_client.py
│   ├── core/
│   ├── schemas/responses.py
│   ├── services/projector_service.py
│   ├── services/esco_loader.py
│   └── services/analytics/
├── complementary_data/
└── docs/
```

The legacy root files (`main.py`, `schemas.py`, `demo_dashboard.py`, `main_sectoral.py`) are still present in the repository, but the maintained backend path is the package entrypoint:

```bash
uvicorn app.main:app --reload
```

The maintained dashboard path is:

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

## Documentation Policy

Swagger/OpenAPI is useful for interactive endpoint testing. These Markdown documents are the semantic layer: they explain business meaning, metric interpretation, known caveats and integration expectations.

When code and documentation disagree, update the Markdown against:
- `app/api/routes/projector.py` for endpoint parameters
- `app/services/projector_service.py` for orchestration behavior
- `app/schemas/responses.py` for response fields
- `app/services/analytics/` for metric semantics
