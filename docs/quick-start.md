# Quick Start

Concise guide for developers working on the Projector API, dashboard, sector snapshots and documentation.

Related issues: #1, #7, #8, #44, #47, #48, #49, #52, #54.

## Intelligence Design

```text
Skill Intelligence
├── Skill Analyzer (already implemented)
│   [Keyword] [Date range] [Region]
│
│   question:
│   given a job/search keyword, which skills emerge?
│
│   outputs:
│   - top skills
│   - trends
│   - regional distribution
│   - sector distribution

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
```

## Final Navigation

```text
Skill Analyzer
= start from a job/search keyword
= already implemented

Sector Overview
= start from one sector
= inspect snapshot or evolution

Sector Skills Comparison
= compare many sectors against many skills

Skill Explorer
= start from one skill
```

## Run Locally

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

| View | Start from | Main controls | Main endpoint |
| --- | --- | --- | --- |
| Skill Analyzer | keyword/job search | keyword, date range, region | `POST /projector/analyze-skills` |
| Sector Overview / Snapshot | one sector | sector, region, year | `POST /projector/sectoral-snapshot` |
| Sector Overview / Evolution | one sector | sector, region, from year, to year | `POST /projector/sectoral-snapshot` |
| Sector Skills Comparison | many sectors x skills | year or from/to, region, sectors, skills, metric | `POST /projector/sector-skills-comparison` |

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

## Data Sources

Runtime sector intelligence uses Tracker API only:

```text
job["sectors"] x job["skills"]
```

No ISCO/NACE files, ESCO-NACE crosswalk, canonical occupation-skill relations or official matrix are used in the current sector flow.

## Useful Docs

- [API reference](api-reference.md)
- [Data model](data-model.md)
- [Statistics](statistic.md)
- [Sector intelligence](sector-intelligence.md)
- [Database](database.md)
- [Architecture](architecture.md)
- [Data sources](data-sources.md)
