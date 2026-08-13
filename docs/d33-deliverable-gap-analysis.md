# D3.3 Deliverable Gap Analysis

This checklist compares the D3.3 "Skills Analytics & Forecasting" deliverable wording with the current SKILLAB Projector implementation.

Related issue: #62.

## Overall Status

The Projector implementation supports descriptive labour-market analytics, observed trend monitoring, regional intelligence, sector intelligence, yearly sector snapshots, sector evolution, sector-skills comparison, and regional-sectoral distribution.

The main gap is not descriptive analytics. The main gap is wording and scope alignment around forecasting, empirical studies, production deployment, and operational hardening.

## Section-Level Gap Matrix

| Deliverable area | Current implementation | Gap / action |
| --- | --- | --- |
| Descriptive skill-demand analytics | Implemented through `POST /projector/analyze-skills`. | Keep wording. |
| Skill ranking and market indicators | Implemented with observed skill counts/frequencies and dashboard tables. | Clarify that green/digital flags are weak or placeholder unless backed by reliable metadata. |
| Job title and employer analysis | Implemented in main analysis and sector snapshots. | Keep wording. |
| Emerging/declining/stable skills | Implemented as observed period comparison. | Avoid calling this predictive forecasting. |
| Regional raw aggregation | Implemented from Tracker `location_code`. | Keep wording. |
| NUTS-like projections | Implemented as code-derived or demo projection where possible. | Clarify this is NUTS-like and source-dependent, not guaranteed official NUTS mapping. |
| Regional skill specialization | Implemented with Location Quotient-like indicators. | Keep caveat for low-volume regions. |
| Sector intelligence | Implemented from Tracker `job.sectors x job.skills`. | Explicitly state no runtime local ISCO/NACE files or ESCO-NACE crosswalk. |
| Sector-skill co-occurrence | Implemented as relationship counts. | Clarify multi-sector jobs contribute to multiple sector counts. |
| Yearly sector snapshots | Implemented with PostgreSQL store, migrations, refresh/backfill, scheduler and validation. | Production DB still needs real snapshot bootstrap. See #61. |
| Sector evolution | Implemented through target/reference yearly snapshot comparison. | Requires real multi-year snapshots in production. |
| Sector skills comparison | Implemented through `POST /projector/sector-skills-comparison`. | Keep wording. |
| Regional-sectoral distribution | Implemented through `POST /projector/regional-sectoral`. | Keep wording after PR #57 / main merge. |
| Multidimensional interpretation | Implemented across skill, region, sector and time views. | Keep wording, but avoid implying a single predictive model. |
| Forecasting | Implemented only as trend-based monitoring and period comparison. | Decide future forecasting scope. See #59. |
| Predictive ML / XAI | Not implemented in Projector runtime. | Remove from implemented claims or mark as future work. |
| Supply-side analytics | Not implemented in current Projector runtime. | Remove from implemented claims unless covered by another component. |
| Empirical case studies | Features exist, but real case-study outputs/figures are not in the repo. | Add real outputs or frame as validation/demo scenarios. |
| Production deployment | Partial: DB/scheduler Docker support exists. | Complete production bootstrap/runbook. See #61 and #13. |
| API hardening | Partial: functional API exists. | Add error envelope, stronger validation, readiness checks and versioning decision. See #60. |

## Required Deliverable Edits

- Replace accidental `D3.2` references with `D3.3`.
- Use "trend-based monitoring" or "period comparison" for current forecasting.
- Do not claim predictive ML forecasting as implemented.
- Do not claim XAI modules as implemented.
- Do not claim supply-side analytics unless another component provides it.
- Mark NUTS outputs as NUTS-like/source-dependent.
- Describe sector data source as Tracker `job.sectors`.
- Explain sector counts as relationship counts when jobs contain multiple sectors.
- Either add real case-study outputs or label case studies as demonstration scenarios.
- Add production caveat: real snapshots must be bootstrapped and scheduler monitored.

## Open Follow-Up Issues

- #59: decide forecasting beyond trend monitoring.
- #60: harden API and readiness behaviour.
- #61: bootstrap production sector snapshots.
- #13: complete system Dockerization.
- #1, #7, #8: keep docs/API docs aligned as implementation evolves.
