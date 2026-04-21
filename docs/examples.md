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
- `insights.sectors`: ISCO-oriented sector bar chart
- `insights.job_titles`: title leaderboard
- `insights.employers`: employer leaderboard
- `insights.trends`: trend tab
- `insights.regional`: map and specialization widgets

## Example 2: Full Snapshot With ISCO/NACE Sectoral Views

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "include_sectoral=true" \
  -d "sector_system=both" \
  -d "sector_level=nace_section" \
  -d "skill_group_level=1" \
  -d "occupation_level=1"
```

Frontend usage:
- read ISCO from `insights.sectoral_views.isco.items`
- read NACE levels from `insights.sectoral_views.nace.levels`
- use `insights.sectoral_views.nace.selected_level` as the default NACE tab or selector value
- use `insights.sector_view_names` for display labels

## Example 3: NACE Class View

```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=data" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "include_sectoral=true" \
  -d "sector_system=nace" \
  -d "sector_level=nace_class"
```

`insights.sectoral` will contain the selected NACE class payload. `insights.sectoral_views` will still contain the full ISCO and NACE level map.

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
- show a stopping state,
- do not assume instant interruption,
- inspect the final analysis `status` when the running request returns.

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
- the area represents `9.6%` of the analyzed batch,
- `Python` appears 33 times in that area,
- `specialization = 1.78` means Python is more concentrated there than in the full analyzed market.

Do not read specialization as raw popularity alone.

## Example 7: Demo Regional Mode

If `demo=true` and the source jobs only carry country-level location codes, the service distributes jobs across synthetic NUTS-like areas.

Recommended UI wording:

```text
Regional detail shown in demonstration mode. Sub-national distribution is simulated from country-level data.
```

## Recommended Frontend Strategy

- Initial page load: call `/projector/analyze-skills`.
- Sector dashboard: call `/projector/analyze-skills` with `include_sectoral=true`.
- Dedicated trend widget: call `/projector/emerging-skills`.
- Cancel button: call `/projector/stop`.
- Ranking pagination: use `page` and `page_size`, but remember they only slice returned ranking items.
