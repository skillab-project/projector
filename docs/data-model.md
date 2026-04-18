# Data Model and Metric Semantics

## Index
- [Response overview](#response-overview)
- [Dimension summary object](#dimension-summary-object)
- [Skill ranking object](#skill-ranking-object)
- [Sector distribution object](#sector-distribution-object)
- [Job titles object](#job-titles-object)
- [Employers object](#employers-object)
- [Trend analysis object](#trend-analysis-object)
- [Regional analysis object](#regional-analysis-object)
- [Contract caveat](#contract-caveat)

This document explains the business meaning of the fields returned by the SKILLAB Projector.

---

## Response overview

### Section index
- [Status field](#status-field)
- [Dimension summary field](#dimension-summary-field)
- [Insights field](#insights-field)

## Status field
Processing status for the request.

Observed values in practice:
- `completed`
- `stopped`

## Dimension summary field
Contextual information about the batch that was analyzed.

## Insights field
The actual intelligence payload returned by the engine.

---

## Dimension summary object

### Section index
- [Jobs analyzed field](#jobs-analyzed-field)
- [Geo breakdown field](#geo-breakdown-field)

## Jobs analyzed field
Total number of job postings processed after all filters.

## Geo breakdown field
A simple distribution by raw location code.

Typical item:
```json
{ "location": "IT", "job_count": 820 }
````

Meaning:

* `location`: source geographic code from the retrieved jobs
* `job_count`: how many jobs in the batch belong to that code

---

## Skill ranking object

### Section index

* [Ranking item example](#ranking-item-example)
* [Skill name field](#skill-name-field)
* [Skill frequency field](#skill-frequency-field)
* [Skill id field](#skill-id-field)
* [Green flag field](#green-flag-field)
* [Digital flag field](#digital-flag-field)
* [Sector spread field](#sector-spread-field)
* [Primary sector field](#primary-sector-field)

This is the top-skills ranking.

## Ranking item example

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

## Skill name field

Readable skill label.

## Skill frequency field

Current implementation meaning: **absolute occurrence count** in the analyzed batch.

Important note:
The name `frequency` can be misleading. In the current code it behaves like a count, not a normalized percentage.

## Skill id field

Original skill identifier or URI.

## Green flag field

Boolean flag assigned heuristically from the resolved skill label.

Interpretation:

* `true`: the label matched green-transition keywords such as `renewable`, `climate`, `recycling`, `energy`
* `false`: no green keyword match was found

## Digital flag field

Boolean flag assigned heuristically from the resolved skill label.

Interpretation:

* `true`: the label matched digital keywords such as `software`, `cloud`, `data`, `programming`, `automation`
* `false`: no digital keyword match was found

## Sector spread field

Number of distinct sectors in which the skill appears within the analyzed batch.

Interpretation:

* higher value = more transversal skill
* lower value = more sector-specific skill

## Primary sector field

The most common sector associated with the skill in the analyzed batch.

---

## Sector distribution object

### Section index

* [Sector item example](#sector-item-example)
* [Sector name field](#sector-name-field)
* [Sector count field](#sector-count-field)

Distribution of jobs by sector label.

## Sector item example

Typical item:

```json
{ "name": "Information technology", "count": 640 }
```

## Sector name field

Readable sector label.

## Sector count field

Number of jobs counted under that sector.

Fallback values may appear when occupation metadata is missing.

---

## Job titles object

### Section index

* [Job title item example](#job-title-item-example)
* [Job title name field](#job-title-name-field)
* [Job title count field](#job-title-count-field)

Top job titles as written in source vacancies.

## Job title item example

Typical item:

```json
{ "name": "Data Engineer", "count": 88 }
```

## Job title name field

Title string extracted from the vacancy.

## Job title count field

Number of occurrences in the analyzed batch.

---

## Employers object

### Section index

* [Employer item example](#employer-item-example)
* [Employer name field](#employer-name-field)
* [Employer count field](#employer-count-field)

Ranking of organizations by hiring volume.

## Employer item example

Typical item:

```json
{ "name": "Example Corp", "count": 41 }
```

## Employer name field

Organization name from the vacancy.

## Employer count field

Number of occurrences in the analyzed batch.

---

## Trend analysis object

### Section index

* [Market health object](#market-health-object)
* [Trend items list](#trend-items-list)

Trend analysis object.

## Market health object

### Section index

* [Market health status field](#market-health-status-field)
* [Market health growth field](#market-health-growth-field)

High-level movement of the market between the two compared sub-periods.

## Market health status field

Observed values in the current implementation:

* `expanding`
* `shrinking`

Interpretation:

* `expanding`: the second period contains more jobs than the first period
* `shrinking`: otherwise

Important note:
At the moment, the implementation does not expose a dedicated `stable` state at market level.

## Market health growth field

Percentage change in job volume between period A and period B.

## Trend items list

### Section index

* [Trend item example](#trend-item-example)
* [Trend name field](#trend-name-field)
* [Trend growth field](#trend-growth-field)
* [Trend type field](#trend-type-field)
* [Trend primary sector field](#trend-primary-sector-field)
* [Trend twin transition flags](#trend-twin-transition-flags)

List of skill-level trend items.

## Trend item example

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

## Trend name field

Skill label.

## Trend growth field

Can be:

* a positive numeric percentage,
* a negative numeric percentage,
* `0.0`,
* the string `"new_entry"`.

Interpretation:

* positive number = stronger demand in the second period
* negative number = weaker demand in the second period
* `0.0` = unchanged
* `new_entry` = the skill appears in the second period but not in the first

## Trend type field

Observed values:

* `emerging`
* `declining`
* `stable`

## Trend primary sector field

Most common sector associated with the skill in the compared data.

## Trend twin transition flags

Twin-transition flags copied into the trend output to make interpretation easier.

---

## Regional analysis object

### Section index

* [Regional lists](#regional-lists)
* [Regional area item](#regional-area-item)
* [Regional specialization field](#regional-specialization-field)

Regional decomposition of the analyzed batch.

## Regional lists

Contains four lists:

* `raw`
* `nuts1`
* `nuts2`
* `nuts3`

### Raw regional list

Based directly on original `location_code` values found in the source jobs.

### NUTS-like regional lists

Derived NUTS-like levels built from string slicing, optionally with synthetic expansion when `demo=true`.

Important note:
When `demo=true`, NUTS-like sub-national distributions are **not observed geography**. They are generated to simulate granular regional analytics.

## Regional area item

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

### Regional code field

Geographic identifier for the area.

### Regional total jobs field

How many jobs were assigned to that area.

### Regional market share field

Percentage of the analyzed batch represented by that area.

### Regional top skills field

Top local skills for the area.

#### Regional skill label field

Readable skill label.

#### Regional skill count field

Occurrences of the skill in that specific area.

## Regional specialization field

Location Quotient (LQ).

Formula used by the code:

```text
(skill_count_in_area / jobs_in_area) / (global_skill_count / total_jobs)
```

Interpretation:

* `> 1.0` = the skill is more concentrated in this area than in the full analyzed market
* `= 1.0` = the area follows the overall market average
* `< 1.0` = the skill is less concentrated there than in the overall market

Business reading:

* high value = local specialization or local hub
* low value = relatively lower priority in that territory

---

## Contract caveat

There is currently a mismatch between some declared Pydantic schema fields and the payload produced by the code.

Example:

* the schema suggests `count` in some places,
* the runtime payload currently returns `frequency` for ranked skills,
* the runtime payload also includes fields like `skill_id` and `sector_spread`.

Before treating this API as a strict external contract, code and schema should be aligned.
## Sector system object / semantics

- Active system: ISCO or NACE.
- Active level: `isco_group` or one of `nace_section`, `nace_division`, `nace_group`, `nace_class`.
- In ISCO mode, labels/codes are ISCO group values.
- In NACE mode, labels/codes are NACE values from crosswalk lookups.
- `nace_section` is derived from official NACE division-to-section ranges (A–U).

## Sector distribution semantics

- ISCO mode: native ESCO/ISCO sector labels.
- NACE mode: NACE labels from crosswalk; if label missing, code fallback.
- NACE canonical/matrix views are derived/aggregated through ESCO crosswalk logic.

## Metric definitions

- **Skill coverage**: number of unique skills in a sector.
- **Sector breadth**: number of sectors a skill appears in.
- **Skill concentration**: how much a skill is concentrated in dominant sectors (can be represented by top-sector share).
- **Skill gap** (ISCO): observed skills minus canonical skills (and vice versa).
- **Stability / overlap** (ISCO): overlap ratio between observed and canonical sets.
