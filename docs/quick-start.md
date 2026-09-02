# Quick Start

Concise guide for developers working on the Projector API, dashboard, sector snapshots and documentation.

Related issues: #1, #3, #4, #7, #8, #33, #44, #47, #48, #49, #50, #52, #54, #73, #74, #88, #89, #90, #94.

## Intelligence Design

```text
Job Demand
├── Job Demand Overview
│   [Keyword] [Date range] [Region]
│
│   question:
│   what does this selected job-market slice look like?
│
│   outputs:
│   - top skills
│   - job titles
│   - employers
│   - regional distribution
│   - sector distribution
│   - compact trend summary
│
├── Temporal Analysis
│   [Keyword] [Date range] [Region] [Granularity]
│
│   question:
│   how does this selected job-market slice evolve over time?
│
│   outputs:
│   - period job counts
│   - skill time series
│   - growth rates
│   - short-term baseline projection

Sector Intelligence
├── Sector Overview
│   [Sector] [Region]
│
│   1. Snapshot
│      [Year]
│
│      question:
│      what does this sector look like in a selected year?
│
│      outputs:
│      - yearly sector metrics
│      - top-10 skills
│      - all skills table
│      - skill portfolio
│      - job titles
│
│   2. Sector Evolution
│      [From year] -> [To year]
│
│      question:
│      how did this sector change between two years?
│
│      outputs:
│      - job delta
│      - job growth
│      - new skills
│      - disappeared skills
│      - growing skills
│      - declining skills
│      - skill churn

├── Sector Skills Comparison
│   [Year] [Region] [Sectors] [Skills] [Metric]
│
│   question:
│   how do multiple sectors compare on selected skills?
│
│   heatmap sectors x skills
│
│   metrics:
│   - count
│   - share in sector
│   - rank
│   - growth between years

└── Skill Explorer
    [Skill] [Year / Range] [Region]
    └── skill-first sectors, regions and time series

Cross-Dimension Analysis
├── Sector Skills Comparison
│   └── inferential layer
├── Regional Sector Distribution
│   └── inferential layer
├── Regional Sectoral Temporal Evolution
│   [Year / Range] [Region] [Level] [Sectors] [Metric]
│   └── sector distribution by region through time
├── Regional Temporal Analysis
│   [Keyword] [Date range] [Region] [Granularity]
│   └── regional demand and top skills through time
├── Temporal Analysis
│   └── inferential layer
├── Sector Evolution
│   └── inferential layer
└── future skill/region/time combinations
```

## Final Navigation

```text
Job Demand Overview
= composition of a job-market slice
= maps to D3.3 4.1.1

Temporal Analysis
= evolution of the same job-market slice
= maps to D3.3 4.1.1.4, 4.2.1 and 4.2.2

Sector Overview
= start from one sector
= inspect snapshot or evolution

Sector Skills Comparison
= compare many sectors against many skills

Inferential Layer
= p-value and effect size attached to comparison views
= not a standalone navigation item
= maps to D3.3 Dimension 4

Skill Explorer
= start from one skill
= maps Skill x Sector, Skill x Regional and Skill x Temporal
```

## Run Locally

Full Docker stack:

```bash
docker compose up -d projector-db projector-api projector-dashboard
```

Open:

```text
API: http://127.0.0.1:8000/projector/health
Dashboard: http://127.0.0.1:8501
```

Python local stack:

```bash
docker compose up -d projector-db
```

```bash
export DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
uvicorn app.main:app --reload
```

```bash
streamlit run app/example_dashboard/demo_dashboard.py
```

## Dashboard Views

| View | Start from | Main controls | Main endpoint | Data source |
| --- | --- | --- | --- | --- |
| Job Demand Overview | keyword/job search | keyword, date range, region | `POST /projector/analyze-skills` | Tracker API/cache |
| Temporal Analysis | same job-market slice | keyword, date range, region, granularity | `POST /projector/temporal-projections` | Tracker API/cache |
| Regional Temporal Analysis | region/time comparison | keyword, date range, region, granularity | `POST /projector/regional-temporal` | Tracker API/cache |
| Statistical evidence boxes | comparison views | two groups with count/total values | `POST /projector/statistical-comparison` | derived from active view |
| Sector Overview / Snapshot | one sector | sector, region, year | `POST /projector/sectoral-snapshot` | PostgreSQL snapshots |
| Sector Overview / Evolution | one sector | sector, region, from year, to year | `POST /projector/sectoral-snapshot` | PostgreSQL snapshots |
| Sector Skills Comparison | many sectors x skills | year or from/to, region, sectors, skills, metric | `POST /projector/sector-skills-comparison` | PostgreSQL snapshots |
| Regional Sector Distribution | region/sector matrix | mode, year/range, region, level, sectors, metric | `POST /projector/regional-sectoral` | PostgreSQL snapshots |
| Skill Explorer | one skill | skill, snapshot/live mode, year or date range, region | `POST /projector/skill-explorer` | PostgreSQL snapshots or Tracker API/cache |

Statistical evidence boxes are collapsed by default inside comparison views. They are not a standalone navigation area.

## Static Sector Snapshots

Start only the database:

```bash
docker compose up -d projector-db
```

The local DB is seeded with demo sector snapshots for 2020-2024 and demo regions.

Refresh a real yearly snapshot from Tracker:

```bash
export DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
python scripts/refresh_sectoral_snapshot.py --year 2024
```

Refresh a regional snapshot:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024 --location-code IT
```

Backfill all available regions for multiple years:

```bash
python scripts/bootstrap_sectoral_snapshots.py --start-year 2020 --end-year 2024
```

Validate the DB snapshot pipeline after a refresh/backfill:

```bash
python scripts/validate_sectoral_snapshot_pipeline.py --year 2024
```

Validate DB plus running API:

```bash
python scripts/validate_sectoral_snapshot_pipeline.py \
  --year 2024 \
  --api-base-url http://127.0.0.1:8000
```

Run a recurring refresh every 3 months:

```bash
python scripts/schedule_sectoral_snapshot_refresh.py --interval-months 3
```

## API Smoke Tests

```bash
curl -X POST http://127.0.0.1:8000/projector/sectoral-snapshot \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024"
```

```bash
curl -X POST http://127.0.0.1:8000/projector/sector-skills-comparison \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "year=2024" \
  -d "metric=share"
```

```bash
curl -X POST http://127.0.0.1:8000/projector/temporal-projections \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "granularity=monthly" \
  -d "forecast_periods=2"
```

```bash
curl -X POST http://127.0.0.1:8000/projector/regional-temporal \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "granularity=monthly"
```

```bash
curl -X POST http://127.0.0.1:8000/projector/skill-explorer \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "skill_label=Python" \
  -d "mode=snapshot" \
  -d "start_year=2023" \
  -d "end_year=2024"
```

## Data Sources

Runtime sector intelligence uses Tracker API only:

```text
job["sectors"] x job["skills"]
```

No ISCO/NACE files, ESCO-NACE crosswalk, canonical occupation-skill relations or official matrix are used in the current sector flow.

## Useful Docs

- [API reference](api-reference.md)
- [Demo dashboard guide](dashboard-demo.md)
- [Data model](data-model.md)
- [Statistics](statistic.md)
- [Sector intelligence](sector-intelligence.md)
- [Database](database.md)
- [Architecture](architecture.md)
- [Data sources](data-sources.md)
