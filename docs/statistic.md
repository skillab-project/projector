# Statistics

Concise formulas for current API-only metrics.

Related issues: #3, #7, #8, #33, #47, #48, #52, #88, #89, #90, #94.

## Core Source

```text
jobs = Tracker jobs after filters
skills = job["skills"]
sectors = job["sectors"]
```

## Jobs

`jobs_analyzed`

```text
count(jobs)
```

## Job Demand Overview

`frequency`

```text
count(skill mentions in jobs)
```

`sector_spread`

```text
count(distinct sectors where skill appears)
```

`primary_sector`

```text
sector with max count for that skill
```

## Temporal Analysis

`period`

```text
bucket(upload_date, granularity)
```

Granularity can be monthly, quarterly or yearly.

`period_job_count`

```text
count(jobs where upload_date in period)
```

`skill_period_count`

```text
count(skill mentions where upload_date in period)
```

`growth_vs_previous`

```text
(count_current_period - count_previous_period) / count_previous_period * 100
```

If previous count is `0` and current count is greater than `0`, growth is `new_entry`.

`forecast.projected_count`

```text
latest_count + average(last up to 3 period deltas) * forecast_step
```

This is a short-term baseline projection, not an ML forecast.

## Regional Temporal Analysis

`regional_period_job_count`

```text
count(jobs where location_code maps to region and upload_date maps to period)
```

`regional_market_share`

```text
regional_jobs / total_jobs * 100
```

`regional_skill_count`

```text
count(skill mentions in jobs mapped to the region)
```

`regional_skill_specialization`

```text
(skill_count_in_region / region_jobs) / (skill_count_all_regions / total_jobs)
```

Values above `1` indicate above-average regional concentration.

## Skill Explorer

`total_mentions`

```text
count(selected skill mentions)
```

Snapshot mode reads `sector_yearly_snapshots.all_skills`.

Live mode filters fetched Tracker jobs:

```text
job is selected when selected_skill in job["skills"]
```

`sector_count`

```text
count(selected skill mentions mapped to each sector in job["sectors"])
```

A multi-sector job contributes once to each sector-skill relationship.

`region_count`

```text
count(selected skill mentions by location_code)
```

`skill_time_series`

```text
count(selected skill mentions by year or upload_date bucket)
```

## Inferential Layer

`chi_square_2x2`

```text
observed = [
  [group_a_count, group_a_total - group_a_count],
  [group_b_count, group_b_total - group_b_count]
]
```

Expected counts:

```text
expected_cell = row_total * column_total / grand_total
```

Statistic:

```text
sum((observed_cell - expected_cell)^2 / expected_cell)
```

`p_value`

```text
chi-square survival probability with df = 1
```

`effect_size`

```text
sqrt(chi_square / grand_total)
```

This is an inferential evidence layer for observed differences. It does not prove shortage, causality, or future demand.

## Sector Counts

`job_count`

```text
count(jobs where sector in job["sectors"])
```

If a job has multiple sectors, each sector gets one count.

`job_share`

```text
job_count_sector / sum(job_count_all_sectors)
```

## Sector-Skill Matrix

```text
for each job:
  for each sector in job["sectors"]:
    for each skill in job["skills"]:
      sector_skill_count[sector][skill] += 1
```

If a job has no sector, sector is `Sector not specified`.

## Sector Overview / Snapshot

`count`

```text
sector_skill_count[sector][skill]
```

`total_skill_mentions`

```text
sum(sector_skill_count[sector].values())
```

`unique_skills`

```text
count(distinct skills in sector)
```

`share_in_sector`

```text
skill_count_in_sector / total_skill_mentions_in_sector
```

`rank`

```text
position of skill in sector sorted by count desc
```

## Skill Portfolio Bubble Chart

`sector_breadth`

```text
count(sectors where skill appears)
```

`importance`

```text
skill_count_in_selected_sector / total_skill_mentions_in_selected_sector
```

`size`

```text
skill_count_in_selected_sector
```

`color`

```text
digital if is_digital
green if is_green
other otherwise
```

## Sector Overview / Evolution

`job_delta`

```text
job_count_to_year - job_count_from_year
```

`job_growth_percentage`

```text
(job_count_to_year - job_count_from_year) / job_count_from_year
```

If `job_count_from_year = 0` and `job_count_to_year > 0`, value is `new_entry`.

`new_skill_count`

```text
count(skills_to_year - skills_from_year)
```

`disappeared_skill_count`

```text
count(skills_from_year - skills_to_year)
```

`growing_skill_count`

```text
count(shared skills where count_to_year > count_from_year)
```

`declining_skill_count`

```text
count(shared skills where count_to_year < count_from_year)
```

`skill_churn`

```text
count(new skills + disappeared skills) / count(union skills across both years)
```

`evolution skill delta`

```text
skill_count_to_year - skill_count_from_year
```

## Regional Sectoral Temporal Evolution

`regional_sector_count`

```text
count(jobs in region where sector appears)
```

`share_in_region`

```text
regional_sector_count / total_jobs_in_region * 100
```

`regional_sector_delta`

```text
count_to_year - count_from_year
```

`regional_sector_growth`

```text
(count_to_year - count_from_year) / count_from_year * 100
```

If `count_from_year = 0` and `count_to_year > 0`, growth is `new_entry`.

The selected `metric` controls the frontend value:

```text
count  = count
share  = share_in_region
growth = growth_vs_previous
```

## Sector Skills Comparison

Heatmap rows are sectors. Columns are skills.

`count`

```text
sector_skill_count[sector][skill]
```

`share`

```text
skill_count_in_sector / total_skill_mentions_in_sector
```

`rank`

```text
position of skill in sector sorted by count desc
```

`rank_score`

```text
1 / rank
```

`growth between years`

```text
(skill_count_to_year - skill_count_from_year) / skill_count_from_year
```

If `skill_count_from_year = 0` and `skill_count_to_year > 0`, value is `new_entry`.

## Regional

`total_jobs`

```text
count(jobs in area)
```

`market_share`

```text
jobs in area / all jobs
```

`specialization`

```text
(skill count in area / jobs in area) / (skill count globally / all jobs)
```

Above `1` means the skill is more concentrated in that area than in the full analyzed market.

## Dashboard Label Map

| Dashboard label | Metric |
| --- | --- |
| Job volume by period | `period_job_count` |
| Area trend over time | `regional_period_job_count` |
| Top skills in area | `regional_skill_count`, `regional_skill_specialization` |
| Sectors where it appears | `sector_count`, `skill_explorer_share` |
| Regions where it appears | `region_count`, `skill_explorer_share` |
| Skill trend | `skill_time_series`, `growth_vs_previous` |
| Region-sector evolution | `regional_sector_delta`, `regional_sector_growth` |
| Region-sector time series | `regional_sector_count`, `share_in_region`, `growth_vs_previous` |

## Trends

The selected date range is split in two halves.

`growth`

```text
(count in second half - count in first half) / count in first half
```

If first-half count is `0` and second-half count is positive, growth is `new_entry`.

`trend_type`

```text
growth > 0 -> emerging
growth < 0 -> declining
growth = 0 -> stable
```

`volume_growth_percentage`

```text
(jobs in second half - jobs in first half) / jobs in first half
```
