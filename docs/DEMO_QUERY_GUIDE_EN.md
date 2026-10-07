# Projector Demo Query Guide

This guide provides repeatable queries for every dashboard section. Its purpose is to present a clear story about the synthetic labour-market dataset without relying on random filter combinations.

## 1. Dataset scope

The synthetic dataset contains 8,000 job postings between January 1, 2020 and October 7, 2026.

| Year | Expected postings |
|---|---:|
| 2020 | 640 |
| 2021 | 720 |
| 2022 | 800 |
| 2023 | 960 |
| 2024 | 1,280 |
| 2025 | 1,600 |
| 2026 | 2,000 |

The dataset contains six NUTS2 regions:

| Country | NUTS1 | NUTS2 | Available NUTS3 | Region | Main characterisation |
|---|---|---|---|---|---|
| `IT` | `ITF` | `ITF4` | `ITF47`, `ITF45`, `ITF43` | Puglia | tourism, healthcare, public administration |
| `IT` | `ITC` | `ITC4` | `ITC4C`, `ITC46`, `ITC47` | Lombardia | software, finance, manufacturing |
| `DE` | `DE3` | `DE30` | `DE300` | Berlin | software, artificial intelligence, cloud |
| `DE` | `DE2` | `DE21` | `DE212`, `DE211`, `DE213` | Oberbayern | automotive, manufacturing, automation |
| `FR` | `FR1` | `FR10` | `FR101`, `FR105` | Île-de-France | finance, data, consulting |
| `FR` | `FRK` | `FRK2` | `FRK26`, `FRK24`, `FRK25` | Rhône-Alpes | manufacturing, sustainability, renewable energy |

Every sector is present in every region. Regional characterisation is based only on relative frequency.

## 2. General query rules

- Keywords are case-insensitive.
- Keyword matching covers the job title, description, employer and location.
- Every assigned skill is also included in the job description, so it can be found through keyword search.
- Prefer one meaningful keyword at a time.
- Avoid very short abbreviations such as `AI` or `IT`, because substring matching can produce ambiguous results.
- Use `artificial intelligence` instead of `AI`.
- Use the NUTS2 codes in the table for regional analysis.
- Each posting preserves the complete hierarchy: `location_code`/`country_code`, `nuts1`, `nuts2` and `nuts3`.
- Leave Location empty when the goal is to compare all regions.
- When comparing two regions, use the same NUTS level and the same date range.
- Dates are inclusive.

## 3. Recommended keywords

### Digital and data

- `software development`
- `Python`
- `SQL`
- `data analysis`
- `artificial intelligence`
- `machine learning`
- `PyTorch`
- `cloud computing`
- `Docker`
- `Kubernetes`
- `cybersecurity`

### Industry

- `manufacturing processes`
- `automotive engineering`
- `industrial automation`
- `quality control`
- `computer-aided design`

### Green transition

- `sustainability`
- `renewable energy`
- `carbon accounting`
- `circular economy`

### Services and the public sector

- `financial analysis`
- `management consulting`
- `healthcare management`
- `patient care`
- `public administration`
- `policy analysis`
- `tourism management`
- `hospitality operations`

### Cross-sector skills

- `project management`
- `stakeholder management`
- `communication`
- `teamwork`
- `problem solving`
- `Microsoft Excel`

## 4. Job Demand Overview

This section answers: **which skills, job titles, sectors and employers characterise the selected subset?**

### Query A — overall digital demand

| Field | Value |
|---|---|
| Keyword | `software development` |
| Location | Leave empty |
| Period | `2024-01-01` – `2026-10-07` |

Expected result: Berlin and Lombardia should be prominent, with Python, Git, Docker and agile methods among the leading skills.

### Query B — Puglia's tourism economy

| Field | Value |
|---|---|
| Keyword | `tourism management` |
| Location | `ITF4` |
| Period | `2024-01-01` – `2026-10-07` |

Expected result: Tourism Operations Manager, hospitality, customer service, English and project management.

### Query C — Bavarian industry

| Field | Value |
|---|---|
| Keyword | `industrial automation` |
| Location | `DE21` |
| Period | `2024-01-01` – `2026-10-07` |

Expected result: Automotive Engineer and Manufacturing Engineer, with quality control, CAD and manufacturing processes.

### Query D — cross-regional sustainability

| Field | Value |
|---|---|
| Keyword | `sustainability` |
| Location | Leave empty |
| Period | `2022-01-01` – `2026-10-07` |

Expected result: a higher concentration in Rhône-Alpes, without complete absence in the other regions.

## 5. Temporal Analysis

This section answers: **how do posting and skill volumes change over time?**

Use yearly or quarterly granularity for periods longer than two years. Monthly granularity is more useful for a single year.

### Query A — artificial intelligence growth

| Field | Value |
|---|---|
| Keyword | `artificial intelligence` |
| Location | Leave empty |
| Period | `2020-01-01` – `2026-10-07` |
| Granularity | Yearly |
| Forecast periods | `1` |
| Number of skills | `10` |

Expected result: progressive growth in artificial intelligence, machine learning, Python, PyTorch and cloud computing.

### Query B — cloud demand in Berlin

| Field | Value |
|---|---|
| Keyword | `cloud computing` |
| Location | `DE30` |
| Period | `2022-01-01` – `2026-10-07` |
| Granularity | Quarterly |
| Forecast periods | `2` |
| Number of skills | `10` |

Expected result: growth in cloud computing, Docker, Kubernetes, cybersecurity and Python.

### Query C — green transformation

| Field | Value |
|---|---|
| Keyword | `renewable energy` |
| Location | `FRK2` |
| Period | `2020-01-01` – `2026-10-07` |
| Granularity | Yearly |
| Forecast periods | `1` |

Expected result: growth in sustainability, renewable energy, carbon accounting and circular economy.

### Query D — a mature automotive market

| Field | Value |
|---|---|
| Keyword | `automotive engineering` |
| Location | `DE21` |
| Period | `2020-01-01` – `2026-10-07` |
| Granularity | Yearly |

Expected result: absolute growth due to overall market expansion, but slower relative growth than AI, cloud and sustainability.

## 6. Regional Temporal Analysis

This section answers: **in which regions and periods does demand associated with a keyword grow?**

Leave Location empty to compare all six regions.

### Query A — software diffusion

| Field | Value |
|---|---|
| Keyword | `software development` |
| Location | Leave empty |
| Period | `2023-01-01` – `2026-10-07` |
| Granularity | Quarterly |
| Number of regions | `6` |
| Number of skills | `10` |

Expected result: Berlin and Lombardia should lead, with lower but non-zero demand in the other regions.

### Query B — sustainability geography

| Field | Value |
|---|---|
| Keyword | `sustainability` |
| Location | Leave empty |
| Period | `2020-01-01` – `2026-10-07` |
| Granularity | Yearly |
| Number of regions | `6` |

Expected result: Rhône-Alpes and Oberbayern should be more specialised, with demand increasing across all regions.

### Query C — tourism recovery

| Field | Value |
|---|---|
| Keyword | `tourism management` |
| Location | Leave empty |
| Period | `2020-01-01` – `2026-10-07` |
| Granularity | Yearly |
| Number of regions | `6` |

Expected result: Puglia should lead, with growth after the early years in the selected period.

## 7. Region Comparison

This section answers: **how do two regions differ over the same period in postings, skills, sectors, job titles and employers?**

Use two four-character NUTS2 codes. Do not compare, for example, `ITF` with `DE30`, because they represent different NUTS levels.

### Query A — software: Puglia versus Berlin

| Field | Value |
|---|---|
| Region A | `ITF4` |
| Region B | `DE30` |
| Period | `2024-01-01` – `2026-10-07` |
| Keyword | `software development` |

Expected result: greater digital volume and specialisation in Berlin, while software demand remains visible in Puglia.

### Query B — finance: Lombardia versus Île-de-France

| Field | Value |
|---|---|
| Region A | `ITC4` |
| Region B | `FR10` |
| Period | `2024-01-01` – `2026-10-07` |
| Keyword | `financial analysis` |

Expected result: both regions should be relevant, with differences in associated skills and employers.

### Query C — manufacturing: Oberbayern versus Rhône-Alpes

| Field | Value |
|---|---|
| Region A | `DE21` |
| Region B | `FRK2` |
| Period | `2024-01-01` – `2026-10-07` |
| Keyword | `manufacturing processes` |

Expected result: a stronger automotive component in Oberbayern and a stronger green component in Rhône-Alpes.

### Query D — overall comparison without a keyword

| Field | Value |
|---|---|
| Region A | `ITF4` |
| Region B | `ITC4` |
| Period | `2024-01-01` – `2026-10-07` |
| Keyword | Leave empty |

Expected result: comparison of the full regional economic mix rather than a single professional market.

## 8. Sector Overview

This section uses yearly PostgreSQL snapshots and answers: **which sectors dominate in a year, and how do they change compared with the previous year?**

Before using this view, wait for `projector-snapshot-refresh` to populate the snapshots.

For the demo, prefer `GLOBAL`. Detailed territorial analysis is better handled by Regional Sector Distribution.

### Query A — 2024 snapshot

| Field | Value |
|---|---|
| Sector view | Snapshot |
| Year | `2024` |
| Region | `GLOBAL` |

Use the complete table to identify the sectors actually present and their leading skills.

### Query B — 2020–2024 evolution

| Field | Value |
|---|---|
| Sector view | Sector Evolution |
| From | `2020` |
| To | `2024` |
| Region | `GLOBAL` |

Expected result: relative growth in digital sectors and engineering consulting, with more moderate dynamics in automotive and public administration.

The synthetic postings contain these ten sectors:

- Computer programming activities
- Computer consultancy activities
- Other monetary intermediation
- Business and other management consultancy activities
- Engineering activities and related technical consultancy
- Manufacture of motor vehicles
- Manufacture of other general-purpose machinery
- Hospital activities
- General public administration activities
- Hotels and similar accommodation

## 9. Sector Skills Comparison

This section answers: **which skills distinguish different sectors, and with what intensity?**

For the synthetic dataset, clear the default selections under **Sectors to compare**. When the field is empty, the backend automatically selects the five most represented sectors actually present in the snapshot.

### Query A — skill-share matrix

| Field | Value |
|---|---|
| Year | `2024` |
| Region | `GLOBAL` |
| Metric | Share in sector |
| Sectors | Leave empty |
| Skills | Leave empty |

Expected result: a heatmap of the 15 leading skills in the five most represented sectors.

### Query B — digital skills

| Field | Value |
|---|---|
| Year | `2024` |
| Region | `GLOBAL` |
| Metric | Count or Share in sector |
| Sectors | Leave empty |
| Skills | `Python`, `SQL`, `cloud computing` |

### Query C — skill growth

| Field | Value |
|---|---|
| From | `2023` |
| To | `2024` |
| Region | `GLOBAL` |
| Metric | Growth between years |
| Sectors | Leave empty |
| Skills | `artificial intelligence`, `cloud computing`, `sustainability` |

## 10. Regional Sector Distribution

This section answers: **which sectors are strongest in each region, and how does their weight change?**

Use the following settings to retrieve the six synthetic regions:

- Country filter: `ALL REGIONS`
- Region level: `nuts2`
- Sectors to include: leave empty
- Sectors per area: `10`

### Query A — 2024 regional distribution

| Field | Value |
|---|---|
| Mode | Snapshot |
| Year | `2024` |
| Country filter | `ALL REGIONS` |
| Level | `nuts2` |
| Metric | Share in region |
| Sectors | Leave empty |
| Top K | `10` |

Expected result: every region contains every sector, but the ordering and relative shares differ.

### Query B — regional evolution

| Field | Value |
|---|---|
| Mode | Evolution |
| From | `2020` |
| To | `2024` |
| Country filter | `ALL REGIONS` |
| Level | `nuts2` |
| Metric | Growth between years |
| Sectors | Leave empty |

### Query C — regional time series

| Field | Value |
|---|---|
| Mode | Time series |
| Start | `2020` |
| End | `2024` |
| Country filter | `ALL REGIONS` |
| Level | `nuts2` |
| Metric | Share in region |
| Top K | `10` |

## 11. Skill Explorer

This section answers: **in which sectors and regions does a skill appear, and how does it evolve over time?**

Searching by label requires the complete skill name and is the recommended mode.

### Query A — Python in snapshots

| Field | Value |
|---|---|
| Search by | Skill label |
| Value | `Python` |
| Source | Snapshot DB |
| Window | Year range |
| From | `2020` |
| To | `2024` |
| Location | Leave empty |

### Query B — live sustainability demand

| Field | Value |
|---|---|
| Search by | Skill label |
| Value | `sustainability` |
| Source | Tracker live |
| Period | `2020-01-01` – `2026-10-07` |
| Location | Leave empty |
| Granularity | Yearly |

Expected result: temporal growth and a higher concentration in `FRK2`.

### Query C — automotive in Oberbayern

| Field | Value |
|---|---|
| Search by | Skill label |
| Value | `automotive engineering` |
| Source | Tracker live |
| Period | `2020-01-01` – `2026-10-07` |
| Location | `DE21` |
| Granularity | Yearly |

### Query D — search by ID

| Field | Value |
|---|---|
| Search by | Skill ID |
| Value | `http://data.europa.eu/esco/skill/demo-python` |
| Source | Tracker live or Snapshot DB |

## 12. Recommended full-demo sequence

Run the views in this order to tell a coherent story:

1. **Job Demand Overview** — `software development`, all regions, 2024–2026.
2. **Temporal Analysis** — `artificial intelligence`, all regions, 2020–2026, yearly.
3. **Regional Temporal Analysis** — `sustainability`, all regions, 2020–2026, yearly.
4. **Region Comparison** — `DE21` versus `FRK2`, keyword `manufacturing processes`.
5. **Sector Overview** — global 2024 snapshot with 2023 as reference.
6. **Sector Skills Comparison** — global 2024, empty sector and skill filters, share metric.
7. **Regional Sector Distribution** — 2024, all regions, NUTS2, share metric.
8. **Skill Explorer** — `Python` or `sustainability`, 2020–2024.

This sequence moves from overall demand to temporal, geographical and sectoral differences, and finally to the trajectory of an individual skill.
