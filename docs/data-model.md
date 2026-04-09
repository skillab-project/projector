# Data Model and Metric Semantics

This document explains the business meaning of the fields returned by the SKILLAB Projector.

## Root response structure

### `status`
Processing status for the request.

Observed values in practice:
- `completed`
- `stopped`

### `dimension_summary`
Contextual information about the batch that was analyzed.

### `insights`
The actual intelligence payload returned by the engine.

---

## `dimension_summary`

### `jobs_analyzed`
Total number of job postings processed after all filters.

### `geo_breakdown`
A simple distribution by raw location code.

Typical item:
```json
{ "location": "IT", "job_count": 820 }
```

Meaning:
- `location`: source geographic code from the retrieved jobs
- `job_count`: how many jobs in the batch belong to that code

---

## `insights.ranking`
This is the top-skills ranking.

Typical item in the current implementation:
```json
{
  "name": "Python",
  "frequency": 312,
  "skill_id": "http://data.europa.eu/esco/skill/...",
  "is_green": false,
  "is_digital": true,
  "sector_spread": 4,
  "primary_sector": "Information technology"
}
```

### `name`
Readable skill label.

### `frequency`
Current implementation meaning: **absolute occurrence count** in the analyzed batch.

Important note:
The name `frequency` can be misleading. In the current code it behaves like a count, not a normalized percentage.

### `skill_id`
Original skill identifier or URI.

### `is_green`
Boolean flag assigned heuristically from the resolved skill label.

Interpretation:
- `true`: the label matched green-transition keywords such as `renewable`, `climate`, `recycling`, `energy`
- `false`: no green keyword match was found

### `is_digital`
Boolean flag assigned heuristically from the resolved skill label.

Interpretation:
- `true`: the label matched digital keywords such as `software`, `cloud`, `data`, `programming`, `automation`
- `false`: no digital keyword match was found

### `sector_spread`
Number of distinct sectors in which the skill appears within the analyzed batch.

Interpretation:
- higher value = more transversal skill
- lower value = more sector-specific skill

### `primary_sector`
The most common sector associated with the skill in the analyzed batch.

---

## `insights.sectors`
Distribution of jobs by sector label.

Typical item:
```json
{ "name": "Information technology", "count": 640 }
```

### `name`
Readable sector label.

### `count`
Number of jobs counted under that sector.

Fallback values may appear when occupation metadata is missing.

---

## `insights.job_titles`
Top job titles as written in source vacancies.

Typical item:
```json
{ "name": "Data Engineer", "count": 88 }
```

### `name`
Title string extracted from the vacancy.

### `count`
Number of occurrences in the analyzed batch.

---

## `insights.employers`
Ranking of organizations by hiring volume.

Typical item:
```json
{ "name": "Example Corp", "count": 41 }
```

### `name`
Organization name from the vacancy.

### `count`
Number of occurrences in the analyzed batch.

---

## `insights.trends`
Trend analysis object.

### `market_health`
High-level movement of the market between the two compared sub-periods.

#### `market_health.status`
Observed values in the current implementation:
- `expanding`
- `shrinking`

Interpretation:
- `expanding`: the second period contains more jobs than the first period
- `shrinking`: otherwise

Important note:
At the moment, the implementation does not expose a dedicated `stable` state at market level.

#### `market_health.volume_growth_percentage`
Percentage change in job volume between period A and period B.

### `trends`
List of skill-level trend items.

Typical item:
```json
{
  "name": "Python",
  "growth": 25.0,
  "trend_type": "emerging",
  "primary_sector": "Information technology",
  "is_green": false,
  "is_digital": true
}
```

#### `name`
Skill label.

#### `growth`
Can be:
- a positive numeric percentage,
- a negative numeric percentage,
- `0.0`,
- the string `"new_entry"`.

Interpretation:
- positive number = stronger demand in the second period
- negative number = weaker demand in the second period
- `0.0` = unchanged
- `new_entry` = the skill appears in the second period but not in the first

#### `trend_type`
Observed values:
- `emerging`
- `declining`
- `stable`

#### `primary_sector`
Most common sector associated with the skill in the compared data.

#### `is_green` / `is_digital`
Twin-transition flags copied into the trend output to make interpretation easier.

---

## `insights.regional`
Regional decomposition of the analyzed batch.

Contains four lists:
- `raw`
- `nuts1`
- `nuts2`
- `nuts3`

### `raw`
Based directly on original `location_code` values found in the source jobs.

### `nuts1`, `nuts2`, `nuts3`
Derived NUTS-like levels built from string slicing, optionally with synthetic expansion when `demo=true`.

Important note:
When `demo=true`, NUTS-like sub-national distributions are **not observed geography**. They are generated to simulate granular regional analytics.

### Area item structure
Typical item:
```json
{
  "code": "ITC4",
  "total_jobs": 120,
  "market_share": 9.6,
  "top_skills": [
    {
      "skill": "Python",
      "count": 33,
      "specialization": 1.78
    }
  ]
}
```

#### `code`
Geographic identifier for the area.

#### `total_jobs`
How many jobs were assigned to that area.

#### `market_share`
Percentage of the analyzed batch represented by that area.

#### `top_skills`
Top local skills for the area.

##### `skill`
Readable skill label.

##### `count`
Occurrences of the skill in that specific area.

##### `specialization`
Location Quotient (LQ).

Formula used by the code:
```text
(skill_count_in_area / jobs_in_area) / (global_skill_count / total_jobs)
```

Interpretation:
- `> 1.0` = the skill is more concentrated in this area than in the full analyzed market
- `= 1.0` = the area follows the overall market average
- `< 1.0` = the skill is less concentrated there than in the overall market

Business reading:
- high value = local specialization or local hub
- low value = relatively lower priority in that territory

---

## Contract caveat
There is currently a mismatch between some declared Pydantic schema fields and the payload produced by the code.

Example:
- the schema suggests `count` in some places,
- the runtime payload currently returns `frequency` for ranked skills,
- the runtime payload also includes fields like `skill_id` and `sector_spread`.

Before treating this API as a strict external contract, code and schema should be aligned.
