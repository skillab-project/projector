
# SKILLAB Projector API Documentation
**Version:** based on the current `main.py` and `schemas.py` in this repository  
**Audience:** developers, integrators, dashboard authors, QA, and stakeholders who have never seen the project before  
**Scope:** documents the behavior exposed by `main.py`, the meaning of each endpoint, the request and response fields, and the important implementation details that affect consumers

---

## 1. What this service is

The **SKILLAB Projector** is a FastAPI microservice that sits on top of the SKILLAB Tracker and converts raw job-posting records into **market intelligence**. Its current purpose is to take filtered job data and return:
- a ranked list of requested skills,
- sector, employer, and job-title summaries,
- time-based trend signals,
- geographic decompositions by raw location code and by NUTS-like levels.

In SKILLAB terms, this service is the “projection” layer: it filters and restructures labor-market evidence by **region**, **sector**, and **time** so that downstream tools can show shortages, emerging skills, and local specialization patterns.

---

## 2. Runtime and dependencies

### 2.1 Technology stack
- **Framework:** FastAPI
- **HTTP client:** `httpx.AsyncClient(timeout=None)`
- **Concurrency model:** async / await
- **Data exchange format:** `application/x-www-form-urlencoded` for incoming requests
- **Primary external dependency:** SKILLAB Tracker API

### 2.2 Environment variables
The service expects the following environment variables:
- `TRACKER_API`: base URL of the Tracker API
- `TRACKER_USERNAME`: username used to authenticate against Tracker
- `TRACKER_PASSWORD`: password used to authenticate against Tracker

### 2.3 External Tracker endpoints used internally
The Projector itself exposes only 3 endpoints, but internally it depends on Tracker endpoints:
- `POST /login`
- `POST /jobs`
- `POST /skills`
- `POST /occupations`

These are not part of the Projector public contract, but they affect Projector behavior, latency, and failure modes.

---

## 3. High-level processing flow

### 3.1 Authentication
When the engine has no token, it sends credentials to Tracker `/login` and stores the returned bearer token in memory.

### 3.2 Job retrieval
For analysis endpoints, the engine builds a filter payload and calls Tracker `/jobs` page by page until:
- all pages have been downloaded,
- no items are returned,
- or a stop signal is received.

### 3.3 Local caching
The engine hashes the filter payload using MD5 and stores the raw Tracker result in:
`cache_data/search_<hash>.json`

This means:
- identical filters reuse cached data,
- cache is keyed by exact payload content,
- there is currently no cache expiration policy.

### 3.4 Enrichment
After jobs are retrieved, the engine:
1. extracts occupation identifiers from the jobs,
2. resolves occupations to readable labels through Tracker `/occupations`,
3. extracts skill URIs,
4. resolves skill URIs to readable labels through Tracker `/skills`,
5. applies heuristic twin-transition tagging:
   - `is_green`
   - `is_digital`

### 3.5 Analytics
The engine then computes:
- skill ranking,
- sector distribution,
- employer ranking,
- job-title ranking,
- geo breakdown,
- temporal trend comparison,
- regional projections.

### 3.6 Cooperative stop
The engine supports a “stop requested” flag. The stop is not a hard kill. Instead, long operations periodically check the flag and stop gracefully at safe checkpoints.

---

## 4. Public API overview

### Base path
All public endpoints are rooted under `/projector`.

### Public endpoints
1. `POST /projector/analyze-skills`
2. `POST /projector/emerging-skills`
3. `POST /projector/stop`

---

## 5. Endpoint documentation

# 5.1 POST /projector/analyze-skills

## Purpose
This is the main endpoint. It performs a **single full analysis run** over the selected job-posting dataset and returns:
- contextual summary of the batch,
- ranked skills,
- macro-sector counts,
- top job titles,
- top employers,
- in-memory trend comparison over the selected period,
- regional projections.

It is the endpoint a dashboard or an intelligent agent would normally call first.

## Content type
`application/x-www-form-urlencoded`

## Input fields

### `keywords`
- **Type:** list of strings
- **Required:** no
- **Meaning:** free-text filtering terms forwarded to Tracker `/jobs`.
- **How it is used:** these keywords narrow the set of job postings analyzed.
- **Example meaning:** if `keywords=["data scientist"]`, the service tries to analyze only jobs matching that expression.

### `locations`
- **Type:** list of strings
- **Required:** no
- **Meaning:** raw geographic codes passed to Tracker as `location_code`.
- **How it is used:** filters the dataset to one or more countries/areas before analysis.
- **Example values:** `["IT"]`, `["EL"]`, `["IT", "ES"]`

### `min_date`
- **Type:** string in `YYYY-MM-DD`
- **Required:** yes
- **Meaning:** lower bound of the selected time window.
- **How it is used:** sent to Tracker as `min_upload_date`; also used locally for trend segmentation.

### `max_date`
- **Type:** string in `YYYY-MM-DD`
- **Required:** yes
- **Meaning:** upper bound of the selected time window.
- **How it is used:** sent to Tracker as `max_upload_date`; also used locally for trend segmentation.

### `page`
- **Type:** integer
- **Required:** no
- **Default:** `1`
- **Meaning:** pagination index for the **returned ranking list only**.
- **Important:** it does **not** paginate Tracker fetching. The service still downloads and analyzes the full matching dataset, then slices only the `insights.ranking` array.

### `page_size`
- **Type:** integer
- **Required:** no
- **Default:** `50`
- **Meaning:** number of items returned in `insights.ranking`.
- **Important:** it does **not** limit analysis volume. It only limits how many ranked skills are returned to the caller.

### `demo`
- **Type:** boolean
- **Required:** no
- **Default:** `False`
- **Meaning:** enables synthetic sub-national NUTS-like decomposition when the original location code is only national.
- **Why it exists:** many job postings only carry a country-level code. In demo mode, the engine deterministically spreads those jobs across pseudo NUTS1/2/3 codes to demonstrate the regional-analysis capability.
- **Warning:** when `demo=true`, NUTS1/2/3 results are **synthetic**, not real observed geography.

## Effective filter payload sent to Tracker
The endpoint constructs:
- `keywords` -> Tracker `keywords`
- `locations` -> Tracker `location_code`
- `min_date` -> Tracker `min_upload_date`
- `max_date` -> Tracker `max_upload_date`

Any field not provided is omitted from the outbound payload.

## Output structure

### Root object
- `status`: processing status
- `dimension_summary`: context about the analyzed batch
- `insights`: the actual intelligence payload

### `status`
Possible values in practice:
- `completed`
- `stopped`

**Meaning:**
- `completed`: the run reached its normal end.
- `stopped`: the run was interrupted after a stop signal.

### `dimension_summary`
#### `jobs_analyzed`
- **Meaning:** total number of job postings actually processed after filters.

#### `geo_breakdown`
- **Type:** array
- **Meaning:** distribution of job postings by raw location code found in the retrieved jobs.
- **Each item contains:**
  - `location`: raw location code
  - `job_count`: number of jobs from that area in the retrieved batch

### `insights.ranking`
A paginated list of ranked skills.

Each item currently contains:

#### `name`
Readable skill label.

#### `frequency`
Number of occurrences of the skill in the analyzed jobs.

> Important: despite the schema file calling this a percentage in one place, the actual code currently uses it as an **absolute occurrence count**.

#### `skill_id`
Original skill identifier/URI.

#### `is_green`
Boolean heuristic flag. `true` means the label matched green-transition keywords such as `renewable`, `energy`, `recycling`, `climate`, etc.

#### `is_digital`
Boolean heuristic flag. `true` means the label matched digital keywords such as `software`, `cloud`, `data`, `automation`, `programming`, etc.

#### `sector_spread`
Number of distinct sectors in which the skill appeared in the analyzed batch.

#### `primary_sector`
The most common sector associated with that skill in the batch.

### `insights.sectors`
Distribution of demand by sector label.

Each item:
- `name`: readable sector label, resolved from occupation metadata when available
- `count`: number of jobs counted under that sector

### `insights.job_titles`
Top job titles as written in ads.

Each item:
- `name`: exact job title string
- `count`: number of occurrences

### `insights.employers`
Top organizations by hiring volume.

Each item:
- `name`: organization name
- `count`: number of occurrences

### `insights.trends`
Trend analysis computed **from the same fetched dataset**, not via a second tracker download.

#### `market_health.status`
Current implementation returns:
- `expanding`
- `shrinking`

Interpretation:
- `expanding`: the second half of the selected period contains more jobs than the first half
- `shrinking`: otherwise

> Note: there is no explicit `stable` value in the current implementation of `_compare_periods`; zero growth also becomes `shrinking`.

#### `market_health.volume_growth_percentage`
Percentage growth of job volume between the first half and second half of the selected date interval.

#### `trends`
Array of skill trend items.

Each item:
- `name`: skill label
- `growth`: percentage growth, `-100.0`, or `"new_entry"`
- `trend_type`: `emerging`, `declining`, or `stable`
- `primary_sector`: most common sector in the second period
- `is_green`: twin-transition tag
- `is_digital`: twin-transition tag

Meaning of `growth`:
- numeric positive value: the skill increased
- numeric negative value: the skill decreased
- `0.0`: no change
- `"new_entry"`: the skill appears in the second half but not in the first

### `insights.regional`
Geographic decomposition of the dataset.

Contains four arrays:
- `raw`
- `nuts1`
- `nuts2`
- `nuts3`

Each area object contains:

#### `code`
The geographic identifier:
- in `raw`: usually the original location code from the jobs
- in `nuts1`, `nuts2`, `nuts3`: projected NUTS-like codes

#### `total_jobs`
Number of jobs assigned to that area.

#### `market_share`
Percentage of the analyzed batch located in that area.

#### `top_skills`
Top skills for that area.

Each `top_skills` item contains:
- `skill`: readable skill label
- `count`: occurrences inside that area
- `specialization`: location quotient (LQ)

## Meaning of `specialization` (Location Quotient)
This is one of the most important business fields in the response.

The code computes:

`(skill_count_in_area / jobs_in_area) / (global_skill_count / total_jobs)`

Interpretation:
- `> 1.0`: the skill is more concentrated in that area than in the overall analyzed market
- `= 1.0`: area concentration equals the overall market
- `< 1.0`: the skill is less concentrated there than in the overall market

Typical business reading:
- high LQ -> local specialization or local hub
- low LQ -> lower local priority relative to the full dataset

## Example request
```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills"   -H "Content-Type: application/x-www-form-urlencoded"   -d "keywords=software engineer"   -d "locations=IT"   -d "min_date=2024-01-01"   -d "max_date=2024-12-31"   -d "page=1"   -d "page_size=20"   -d "demo=false"
```

## Example response shape
```json
{
  "status": "completed",
  "dimension_summary": {
    "jobs_analyzed": 1250,
    "geo_breakdown": [
      { "location": "IT", "job_count": 820 },
      { "location": "ES", "job_count": 430 }
    ]
  },
  "insights": {
    "ranking": [
      {
        "name": "Python",
        "frequency": 312,
        "skill_id": "http://data.europa.eu/esco/skill/...",
        "is_green": false,
        "is_digital": true,
        "sector_spread": 4,
        "primary_sector": "Information technology"
      }
    ],
    "sectors": [
      { "name": "Information technology", "count": 640 }
    ],
    "job_titles": [
      { "name": "Data Engineer", "count": 88 }
    ],
    "employers": [
      { "name": "Example Corp", "count": 41 }
    ],
    "trends": {
      "market_health": {
        "status": "expanding",
        "volume_growth_percentage": 12.5
      },
      "trends": [
        {
          "name": "Python",
          "growth": 25.0,
          "trend_type": "emerging",
          "primary_sector": "Information technology",
          "is_green": false,
          "is_digital": true
        }
      ]
    },
    "regional": {
      "raw": [],
      "nuts1": [],
      "nuts2": [],
      "nuts3": []
    }
  }
}
```

## When to use this endpoint
Use `/projector/analyze-skills` when you need a **complete projection snapshot** over one filtered batch.

Typical use cases:
- dashboard initial load,
- “top requested skills in area X during period Y”,
- “which employers and job titles dominate this market slice?”,
- “which areas are specialized in skill Z?”,
- “what changed within the selected period?”

---

# 5.2 POST /projector/emerging-skills

## Purpose
This endpoint performs a **standalone trend analysis** between two sub-periods inside the selected date window.

Unlike `/projector/analyze-skills`, it is specialized: it returns only status plus `insights`, where `insights` is the trend payload.

## Content type
`application/x-www-form-urlencoded`

## Input fields

### `min_date`
- **Type:** string `YYYY-MM-DD`
- **Required:** yes
- **Meaning:** start of the analysis window.

### `max_date`
- **Type:** string `YYYY-MM-DD`
- **Required:** yes
- **Meaning:** end of the analysis window.

### `keywords`
- **Type:** list of strings
- **Required:** no
- **Meaning:** optional keyword filtering forwarded to Tracker.

## Internal behavior
The endpoint:
1. resets stop state,
2. computes the midpoint between `min_date` and `max_date`,
3. fetches jobs for period A,
4. fetches jobs for period B,
5. analyzes both separately,
6. compares them and returns trend results.

This endpoint is useful when you only care about change over time and do not need the full ranking/employer/regional package.

## Output structure
```json
{
  "status": "completed",
  "insights": {
    "market_health": {
      "status": "expanding",
      "volume_growth_percentage": 8.3
    },
    "trends": [
      {
        "name": "Cloud computing",
        "growth": "new_entry",
        "trend_type": "emerging",
        "primary_sector": "Information technology",
        "is_green": false,
        "is_digital": true
      }
    ]
  }
}
```

## Meaning of the returned fields
Same meanings as `insights.trends` inside `/projector/analyze-skills`.

## Example request
```bash
curl -X POST "http://127.0.0.1:8000/projector/emerging-skills"   -H "Content-Type: application/x-www-form-urlencoded"   -d "keywords=software"   -d "min_date=2024-01-01"   -d "max_date=2024-12-31"
```

## When to use this endpoint
Use it when:
- you need a lighter trend-only request,
- you want to compare two time slices repeatedly,
- you do not need employer, title, sector, or regional detail.

---

# 5.3 POST /projector/stop

## Purpose
Sends a cooperative stop signal to the in-memory engine.

## Input
No body parameters.

## Output
```json
{
  "status": "signal_sent"
}
```

## Meaning
The endpoint does **not** guarantee that computation stops instantly. It only sets `engine.stop_requested = True`. Long-running logic will stop at the next checkpoint.

## When to use it
Use it when:
- the UI launched a very large analysis and the user wants to cancel,
- a batch is taking too long,
- you want to avoid continuing an analysis that is no longer relevant.

---

## 6. Detailed semantics of the analytics

### 6.1 Skills ranking
The ranking is built by counting every skill URI occurrence found in `job["skills"]`.

Important consequences:
- if the same skill appears multiple times across many jobs, frequency increases accordingly;
- the current implementation is closer to **occurrence count** than to “percentage of jobs containing the skill”.

### 6.2 Sector distribution
Sector counts are derived from occupation identifiers and then translated to readable labels through the occupations endpoint.

Fallback behavior:
- if no occupation is available, sector becomes `"Settore non specificato"` or an internal unclassified fallback.

### 6.3 Employers
Employers are counted by `organization_name`.
If missing, the code uses `"N/D"`.

### 6.4 Job titles
Titles are counted by `title`.
If missing, the code uses `"N/D"`.

### 6.5 Geo breakdown
Geo breakdown uses raw `location_code` from the original jobs.

### 6.6 Trend logic
The service splits the requested time window into:
- Period A: from `min_date` to midpoint
- Period B: from midpoint onward

Then it compares the two.

### 6.7 Regional decomposition
The service produces two kinds of geography:
1. **Raw geography**: based directly on original `location_code`
2. **Derived NUTS-like hierarchy**: based on string slicing, optionally with synthetic expansion when demo mode is enabled

---

## 7. Internal methods in `ProjectorEngine`

This section is useful for maintainers and for documenting the service beyond the public endpoints.

### `request_stop()`
Sets the stop flag and logs a warning.

### `_get_token()`
Authenticates against Tracker and stores bearer token.

### `fetch_occupation_labels(occ_uris, page_size=500)`
Resolves occupation IDs to readable labels and stores them in `sector_map`.

### `fetch_all_jobs(filters, page_size=500)`
Downloads all matching Tracker jobs using pagination and cache.

### `fetch_skill_names(skill_uris, page_size=500)`
Resolves skill URIs to labels and applies green/digital heuristic tags.

### `analyze_market_data(raw_jobs)`
Generates the aggregated skill/sector/employer/title/geo outputs.

### `get_regional_projections(jobs, demo=False)`
Builds raw and NUTS-like regional outputs with specialization scores.

### `_compare_periods(res_a, res_b)`
Compares two aggregated result objects and produces trend intelligence.

### `calculate_trends_from_data(all_jobs, min_date, max_date)`
Computes trends from an already downloaded in-memory batch.

### `calculate_smart_trends(base_filters, min_date, max_date)`
Computes trends by doing two independent fetches for the two sub-periods.

### `_get_midpoint(d1, d2)`
Returns the midpoint date used to split the window.

---

## 8. Current implementation caveats and contract mismatches

This section is intentionally blunt. For production-grade API documentation, these points should be visible.

### 8.1 Response model vs actual payload mismatch
`/projector/analyze-skills` declares `response_model=ProjectorResponse`, but the actual code currently returns skill items with:
- `frequency`
- `skill_id`
- `sector_spread`

while the schema file defines `SkillRankingItem` with:
- `count`
- `frequency` described as percentage
- no `skill_id`
- no `sector_spread`

So there is currently a gap between:
- **declared contract** in `schemas.py`
- **effective payload** built in `main.py`

### 8.2 Empty-response structure mismatch
When `/projector/analyze-skills` finds no jobs, it returns `engine._empty_insights_p1()`, which currently includes:
- `ranking`
- `sectors`
- `job_titles`
- `employers`
- `trends`

but **does not include `regional`**, even though `ProjectorResponse` requires `insights.regional`.

### 8.3 Missing `_stop_trend_res()`
`calculate_smart_trends()` calls `self._stop_trend_res()` when stop is requested after period A, but no such method is defined in `main.py`.

That means a stop in that code path would currently cause a runtime failure unless this is fixed elsewhere.

### 8.4 Trend status has no explicit stable state at market level
`market_health.status` in `_compare_periods()` is only:
- `expanding` if volume growth > 0
- `shrinking` otherwise

So zero growth becomes `shrinking`, which is probably not the intended business meaning.

### 8.5 Sector counting logic should be reviewed
Inside `analyze_market_data()`, there is a nested loop that re-iterates over `raw_jobs` while already iterating over `raw_jobs`. This risks inflating `sec_cnt` and is likely a logic bug.

### 8.6 Heuristic twin-transition tagging
Green/digital tagging is keyword-based on the resolved skill label. It is useful for demos and first-cut analytics, but it is **not** the same as a canonical ESCO classification.

### 8.7 No documented error envelope
The public API currently does not return a custom standardized error object. Operational failures will mostly surface as default FastAPI/exception behavior.

### 8.8 No validation on date ordering
The code expects valid `YYYY-MM-DD` strings but does not explicitly validate that:
- `min_date <= max_date`
- the range is meaningful for trend splitting.

### 8.9 Cache invalidation is absent
The raw job cache is persistent and payload-based, but there is no built-in TTL or invalidation strategy. Repeated queries can therefore return stale data if Tracker changes.

---

## 9. What this means for API consumers

### Safe assumptions consumers can make
- endpoints are POST-based;
- inputs are form-urlencoded;
- main analysis endpoint returns summary + multi-dimensional insights;
- stop is cooperative, not immediate;
- trend growth can be numeric or `"new_entry"`.

### Assumptions consumers should **not** make yet
- that schema.py fully matches the live payload;
- that `frequency` always means percentage;
- that NUTS1/2/3 is real observed geography when `demo=true`;
- that all empty responses match the documented response model perfectly.

---

## 10. Production-grade documentation package: what should exist

If you want this to look like a real production API, the documentation set should be split into these deliverables:

### A. API Reference
Per-endpoint documentation with:
- method and path,
- request parameters,
- validation rules,
- response schema,
- example requests,
- example responses,
- error responses,
- status codes.

### B. Concept Dictionary
Explains business meaning of:
- skill frequency,
- sector spread,
- market health,
- specialization / LQ,
- emerging vs declining,
- raw vs NUTS geography,
- demo mode.

### C. Integration Guide
Explains:
- auth expectations,
- content type,
- pagination behavior,
- caching behavior,
- how dashboards should call the API,
- cancellation behavior.

### D. Operational Notes
Explains:
- dependencies on Tracker,
- performance implications of large queries,
- stop semantics,
- cache location and maintenance,
- known limitations.

### E. Changelog / Contract Versioning
Documents breaking changes such as:
- renaming `frequency` to `count`,
- adding/removing fields,
- aligning schema.py and actual payload.

---

## 11. Recommended next steps to make this a “real production API”

### Priority 1 — Align the contract
- make the actual response match `schemas.py`, or
- update `schemas.py` to match the real payload.

This is the single most important action.

### Priority 2 — Add explicit error models
Return a consistent error envelope, for example:
```json
{
  "status": "error",
  "error_code": "INVALID_DATE_RANGE",
  "message": "min_date must be less than or equal to max_date"
}
```

### Priority 3 — Validate input properly
Add validation for:
- date format,
- date ordering,
- positive page/page_size,
- maximum page_size,
- supported location format.

### Priority 4 — Fix stop and empty payload edge cases
- implement `_stop_trend_res()`
- include `regional` in empty insights
- define behavior for partially stopped requests

### Priority 5 — Add versioning
Adopt a versioned path such as:
- `/api/v1/projector/analyze-skills`

### Priority 6 — Improve semantic naming
Today the ranking field name `frequency` is misleading in code. If it is a count, call it `count`. If you also need a normalized metric, add `job_share` or `frequency_pct`.

### Priority 7 — Document status codes
Explicitly define:
- 200 success
- 400 validation errors
- 401/403 auth dependency failures
- 502 upstream Tracker failure
- 504 upstream timeout

### Priority 8 — Add OpenAPI descriptions directly in code
Use:
- endpoint summaries,
- detailed descriptions,
- Pydantic field examples,
- example responses.

This will make `/docs` much more useful.

---

## 12. Suggested consumer examples

### Dashboard scenario
Call `/projector/analyze-skills` with:
- selected keywords,
- country or region,
- date interval.

Use:
- `dimension_summary.jobs_analyzed` for headline KPIs,
- `insights.ranking` for top skills,
- `insights.sectors` for macro-sector chart,
- `insights.job_titles` for title frequency,
- `insights.employers` for employer leaderboard,
- `insights.trends` for emerging/declining tab,
- `insights.regional` for map and specialization charts.

### Trend-only widget
Call `/projector/emerging-skills` when the UI needs only “what is rising or falling?” without the heavier full snapshot.

### Cancel button
Bind the cancel action to `POST /projector/stop`.

---

## 13. Executive summary

The current `main.py` already exposes a useful analytics API:
- it retrieves Tracker job data,
- enriches skills and sectors,
- produces multi-dimensional intelligence,
- supports geographic specialization and temporal trends,
- and includes a cooperative stop mechanism.

However, if the goal is a truly production-grade API, the most urgent work is not adding more features; it is **making the contract exact and trustworthy**:
- align code and schema,
- define errors,
- validate inputs,
- fix stop/empty-edge defects,
- and version the API.

Once those are done, this service can be documented and consumed as a stable external API instead of a code-level prototype.
## /projector/analyze-skills - Sector parameters

- `sector_system`:
  - `isco` (occupation-based)
  - `nace` (economic-activity-based)
  - `both` (returns both systems for comparison)
- `sector_level`:
  - ISCO path: `isco_group`
  - NACE path (conceptual levels): `nace_section`, `nace_division`, `nace_group`, `nace_class`
  - `nace_code` remains a technical compatibility level (not a primary dashboard selector)

### Sector system semantics

- In **ISCO** mode, sector views are native occupation-group views.
- In **NACE** mode, sector views are aggregated through the ESCO-NACE crosswalk.
- In NACE mode, labels are NACE labels (or NACE code fallback), never ISCO labels.

### NACE view naming

- `Observed`
- `Derived Canonical`
- `Aggregated Official Matrix`

### Response metadata (sectoral payload)

- active mode: `insights.sectoral_mode`
- dual views: `insights.sectoral_views`
- selected NACE level and level map under `insights.sectoral_views.nace`
- in dashboard mode, NACE labels are shown as conceptual levels (Section/Division/Group/Class), and switching level updates all NACE views (not only comparison summaries)

### Sector interpretation metrics (payload)

- `sector_metrics.coverage_unique_skills`: unique observed skills in the sector.
- `sector_metrics.dominance_top10_share`: share of sector mentions captured by top-10 observed skills.
- `skill_transversal_insights[]`: per-skill in-sector importance, sector breadth, dominant sector/share, and top sectors.
- `isco_interpretation` (ISCO sectors): `emerging_skills`, `missing_skills`, and `stability_overlap`.
