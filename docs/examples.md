# Examples and Integration Patterns

## Example 1: Full Dashboard Snapshot

Use this when the interface needs a complete market summary.

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "page=1" \
  -d "page_size=20" \
  -d "demo=false"
```

Use the response like this:

- `dimension_summary.jobs_analyzed`: KPI tile
- `insights.ranking`: top-skills chart
- `insights.sectors`: Tracker sector bar chart
- `insights.job_titles`: title leaderboard
- `insights.employers`: employer leaderboard
- `insights.trends`: trend tab
- `insights.regional`: map and specialization widgets

## Example 2: Snapshot With Sector Intelligence

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "include_sectoral=true" \
  -d "sector_system=nace" \
  -d "skill_group_level=1" \
  -d "occupation_level=1"
```

Frontend usage:

- read sectors from `insights.sectors`
- read sector details from `insights.sectoral_views.nace.items`
- display `observed_skills` for the selected sector
- display `skill_transversal_insights` to show where selected-sector skills also appear

## Example 3: Backend Health Check

```bash
curl "http://127.0.0.1:8000/projector/health"
```

Use this before running a long dashboard request.

## Example 4: Trend-Only Widget

Use this when the UI only needs to know what is rising or declining.

```bash
curl -X POST "http://127.0.0.1:8000/projector/emerging-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31"
```

Interpretation:

- `market_health.status = expanding`: job volume grew in the second half of the window
- `trend_type = emerging`: the skill gained relevance
- `growth = "new_entry"`: the skill was absent in the first half and present in the second

## Example 5: Cancel Button

```bash
curl -X POST "http://127.0.0.1:8000/projector/stop"
```

Treat this as cooperative cancel:

- show a stopping state
- do not assume instant interruption
- inspect the final analysis `status` when the running request returns

## Example 6: Reading Specialization

Suppose a regional item contains:

```json
{
  "code": "ITC4",
  "total_jobs": 120,
  "market_share": 9.6,
  "top_skills": [
    { "skill": "Python", "count": 33, "specialization": 1.78 }
  ]
}
```

Correct interpretation:

- the area represents `9.6%` of the analyzed batch
- `Python` appears 33 times in that area
- `specialization = 1.78` means Python is more concentrated there than in the full analyzed market

Do not read specialization as raw popularity alone.

## Recommended Frontend Strategy

- Initial page load: call `/projector/analyze-skills`.
- Sector dashboard: call `/projector/analyze-skills` with `include_sectoral=true`.
- Dedicated trend widget: call `/projector/emerging-skills`.
- Cancel button: call `/projector/stop`.
- Ranking pagination: use `page` and `page_size`, but remember they only slice returned ranking items.
