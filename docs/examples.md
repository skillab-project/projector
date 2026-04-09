# Examples and Integration Patterns

## Example 1 — Full snapshot for a dashboard
Use this when the interface needs a complete market summary.

### Request
```bash
curl -X POST "http://127.0.0.1:8000/projector/analyze-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software engineer" \
  -d "locations=IT" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31" \
  -d "page=1" \
  -d "page_size=20" \
  -d "demo=false"
```

### Use the response like this
- `dimension_summary.jobs_analyzed` → KPI tile
- `insights.ranking` → top-skills chart
- `insights.sectors` → sector bar chart
- `insights.job_titles` → title leaderboard
- `insights.employers` → employer leaderboard
- `insights.trends` → trend tab
- `insights.regional` → map and specialization widgets

---

## Example 2 — Trend-only widget
Use this when the UI only needs to know what is rising or declining.

### Request
```bash
curl -X POST "http://127.0.0.1:8000/projector/emerging-skills" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "keywords=software" \
  -d "min_date=2024-01-01" \
  -d "max_date=2024-12-31"
```

### Interpretation pattern
- if `market_health.status = expanding`, the overall selected labor-market slice grew in the second half of the window
- if a skill has `trend_type = emerging`, it gained relevance
- if `growth = "new_entry"`, it was absent before and appeared only in the second half

---

## Example 3 — Cancel button behavior
When a user launches a heavy request and wants to stop it:

### Stop request
```bash
curl -X POST "http://127.0.0.1:8000/projector/stop"
```

### UI recommendation
Treat this as a cooperative cancel:
- show “stopping analysis…”
- do not assume instant interruption
- when the final payload arrives, inspect `status`

---

## Example 4 — Reading specialization correctly
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

### Correct interpretation
- the area represents `9.6%` of the analyzed batch
- `Python` appears 33 times in that area
- `specialization = 1.78` means Python is significantly more concentrated there than in the full analyzed market

### Wrong interpretation to avoid
Do not read specialization as raw popularity alone.
A smaller territory can still have a high specialization value if a skill is unusually concentrated there.

---

## Example 5 — Demo mode explanation for stakeholders
If the request uses:
```text
demo=true
```

and the source jobs only carry country-level location codes, the engine distributes jobs across synthetic NUTS-like areas to simulate regional analysis.

### Best practice wording in UI
Use a label such as:
> Regional detail shown in demonstration mode. Sub-national distribution is simulated from country-level data.

---

## Example 6 — Recommended frontend call strategy
### Initial page load
Call `/projector/analyze-skills`.

### Dedicated trend page or trend popup
Call `/projector/emerging-skills`.

### User aborts a long process
Call `/projector/stop`.

### Pagination note
Do not treat `page` and `page_size` as upstream fetch pagination.
They only paginate the returned ranking list, not the internal data retrieval.
