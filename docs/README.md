# SKILLAB Projector Documentation

This folder contains the maintained documentation for the current `app/` implementation of SKILLAB Projector.

## Reading Order

1. [Quick start](quick-start.md) gives the short operational guide, intelligence design and final navigation.
2. [Overview](overview.md) explains what the service does and who it is for.
3. [Endpoint cheatsheet](endpoint-cheatsheet.md) gives a compact consumer-facing schema of what each endpoint returns.
4. [API reference](api-reference.md) documents current public endpoints and form fields.
5. [Data model](data-model.md) explains response fields.
6. [Statistics](statistic.md) explains metric formulas.
7. [Forecasting scope](forecasting-scope.md) defines current trend monitoring vs deferred predictive forecasting.
8. [D3.3 deliverable gap analysis](d33-deliverable-gap-analysis.md) maps deliverable wording to implemented scope.
9. [Sector intelligence](sector-intelligence.md) explains Tracker API sector analytics and yearly snapshots.
10. [Database](database.md) documents PostgreSQL sector snapshot storage.
11. [Production snapshots](production-snapshots.md) explains bootstrap, scheduled refresh, validation and recovery.
12. [Data sources](data-sources.md) explains Tracker API data usage.
13. [Architecture](architecture.md) maps the runtime flow to the current code.
14. [Examples](examples.md) provides request examples and frontend integration patterns.
15. [Issue management](issue-management.md) defines issue labels, Project statuses and decision/implementation flows.
16. [Contributing and quality workflow](../CONTRIBUTING.md) explains Jenkins, quality gates and generated reports.

## Issue Coverage

- #1: quick start and demo launch instructions.
- #7: architecture, data flow and maintainability notes.
- #8: endpoint cheatsheet and API reference.
- #59: forecasting scope and predictive forecasting deferral.
- #62: D3.3 deliverable wording and section-level scope alignment.
- #44, #54: PostgreSQL sector snapshot storage and refresh pipeline.
- #47, #48, #49, #52: sector-first yearly views, detailed skills, redesign and comparison heatmap.

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
│   ├── services/sector_snapshot_store.py
│   └── services/analytics/
├── migrations/
├── scripts/
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
