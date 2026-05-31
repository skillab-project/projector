# Statistics

Concise formulas for current API-only metrics.

## Jobs

`jobs_analyzed`

```text
count(jobs)
```

Number of Tracker jobs processed after filters.

## Skills

`frequency`

```text
count(skill mentions in all jobs)
```

One job can contribute multiple skills.

`sector_spread`

```text
count(distinct sectors where skill appears)
```

Uses Tracker `job["sectors"]`.

`primary_sector`

```text
sector with max count for that skill
```

## Sectors

Sector counts are relationship counts.

```text
for each job:
  for each sector in job["sectors"]:
    sector_count[sector] += 1
```

If a job has multiple sectors, each sector gets one count.

## Sector-Skill Matrix

Core matrix:

```text
for each job:
  for each sector in job["sectors"]:
    for each skill in job["skills"]:
      sector_skill_count[sector][skill] += 1
```

If a job has no sector, sector is `Sector not specified`.

## Observed Skills In Sector

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

`frequency`

```text
skill count in sector / total_skill_mentions in sector
```

## Sector Metrics

`coverage_unique_skills`

```text
unique_skills in sector
```

`dominance_top10_share`

```text
sum(top 10 skill counts in sector) / total_skill_mentions in sector
```

High value means demand is concentrated in few skills.

## Skill Importance

`importance_in_sector`

```text
skill count in selected sector / total_skill_mentions in selected sector
```

It answers: how important is this skill inside the selected sector?

## Skill Transversality

`sector_breadth`

```text
count(sectors where skill appears)
```

It answers: how many sectors use this skill?

`dominant_sector`

```text
sector with highest count for the skill
```

`dominant_share`

```text
skill count in dominant sector / total skill count across all sectors
```

It is linked to `dominant_sector_label`.

## Regional

`total_jobs`

```text
count(jobs in area)
```

`market_share`

```text
jobs in area / all jobs * 100
```

`specialization`

```text
(skill count in area / jobs in area) / (skill count globally / all jobs)
```

Above `1` means the skill is more concentrated in that area than in the full analyzed market.

## Trends

The selected date range is split in two halves.

`growth`

```text
(count in second half - count in first half) / count in first half * 100
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
(jobs in second half - jobs in first half) / jobs in first half * 100
```
