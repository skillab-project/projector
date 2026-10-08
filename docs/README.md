# SKILLAB Projector Documentation

This folder contains the maintained documentation for the current `app/` implementation of SKILLAB Projector.

The maintained API uses an asynchronous task contract for every analysis endpoint: `POST` returns `202` plus `task_id`, and `GET /projector/tasks/{task_id}` returns progress and the final result. The [API reference](api-reference.md#asynchronous-task-contract) is authoritative for this lifecycle.

## Reading Order

1. [Quick start](quick-start.md) gives the short operational guide, intelligence design and final navigation.
2. [Configuration and Docker Compose](configuration.md) documents services, ports, environment files and runtime flags.
3. [Self-contained demo query guide](DEMO_QUERY_GUIDE_EN.md) provides ready-to-run queries, filters and expected results for the synthetic demo.
4. [Demo dashboard guide](dashboard-demo.md) maps each demo view to parameters, endpoints, fields and data sources.
5. [Overview](overview.md) explains what the service does and who it is for.
6. [Endpoint cheatsheet](endpoint-cheatsheet.md) gives a compact consumer-facing schema of what each endpoint returns.
7. [API reference](api-reference.md) documents current public endpoints and form fields.
8. [Data model](data-model.md) explains response fields.
9. [Statistics](statistic.md) explains metric formulas.
10. [Forecasting scope](forecasting-scope.md) defines current trend monitoring vs deferred predictive forecasting.
11. [Sector intelligence](sector-intelligence.md) explains Tracker API sector analytics and yearly snapshots.
12. [Database](database.md) documents PostgreSQL sector snapshot storage.
13. [Production snapshots](production-snapshots.md) explains bootstrap, scheduled refresh, validation and recovery.
14. [D3.3 gap analysis](d33-deliverable-gap-analysis.md) maps deliverable sections to implemented runtime evidence.
15. [D3.3 edit plan](d33-deliverable-edit-plan.md) gives concise wording changes for the `.docx`.
16. [Data sources](data-sources.md) explains Tracker API data usage.
17. [Architecture](architecture.md) maps the runtime flow to the current code.
18. [Internal method map](internal-methods.md) maps service methods, helper groups and maintenance rules.
19. [Examples](examples.md) provides request examples and frontend integration patterns.
20. [Issue management](issue-management.md) defines issue labels, Project statuses and decision/implementation flows.
21. [Contributing and quality workflow](../CONTRIBUTING.md) explains Jenkins, quality gates and generated reports.

## Self-Contained Synthetic Demo

Use the standalone demo when production Tracker access or credentials are not available. The stack contains PostgreSQL, the Projector API, the Streamlit dashboard, a Tracker-compatible mock API and the snapshot refresh service.

Start all demo services from the repository root:

```bash
docker compose -f demo-docker-compose.yml up --build -d
```

Open:

- Dashboard: `http://localhost:8501`
- Projector API documentation: `http://localhost:8000/projector/docs`
- Mock Tracker API documentation: `http://localhost:8001/docs`

The synthetic dataset is generated automatically and contains a complete country/NUTS1/NUTS2/NUTS3 hierarchy. Use the [English demo query guide](DEMO_QUERY_GUIDE_EN.md) for recommended scenarios, exact filters and expected results. An [Italian version](DEMO_QUERY_GUIDE_IT.md) is also available.

Stop the stack:

```bash
docker compose -f demo-docker-compose.yml down
```

Reset all demo-only data and rebuild it:

```bash
docker compose -f demo-docker-compose.yml down -v
docker compose -f demo-docker-compose.yml up --build -d
```

The demo stack does not replace production Tracker configuration. The mock Tracker is selected only by `demo-docker-compose.yml`.

## Issue Coverage

- #1: quick start and demo launch instructions.
- #3: temporal projections by upload date, growth rates and short-term baseline projection.
- #7: architecture, data flow, internal method map and maintainability notes.
- #8: endpoint cheatsheet and API reference.
- #59: forecasting scope and predictive forecasting deferral.
- #4: inferential layer for selected observed comparisons.
- #44, #54: PostgreSQL sector snapshot storage and refresh pipeline.
- #47, #48, #49, #52: sector-first yearly views, detailed skills, redesign and comparison heatmap.
- #62: D3.3 scope alignment, gap analysis and deliverable edit plan.
- #94: demo dashboard endpoint wiring and view documentation.

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

The legacy root files (`main.py`, `schemas.py`, `demo_dashboard.py`, `main_sectoral.py`) are still present in the repository, but they do not implement the asynchronous task contract. The maintained backend path is the package entrypoint:

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
