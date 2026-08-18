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
| Forecasting | Implemented only as trend-based monitoring and period comparison. | Predictive forecasting is deferred. See [Forecasting scope](forecasting-scope.md) and #59. |
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

## Micro-Section Editing Checklist

Use this table when editing `D3.3_SKILLAB Analytics & Forecasting v1.0.docx`.

| Section | Keep / change | Implementation status |
| --- | --- | --- |
| Executive Summary | Say descriptive analytics and trend monitoring. Avoid predictive ML/XAI claims. | Implemented scope documented. |
| 2.1 Purpose and Scope | State D3.3 scope as Projector analytics over Tracker jobs. | Implemented. |
| 2.2 Deliverable Structure | Keep if section names match final document. | Document-only. |
| 3.1 Input from Description of Action | Keep high-level goals, but avoid claiming all goals are fully implemented. | Context only. |
| 3.2 Input from SKILLAB Requirements | Map requirements to implemented API/dashboard features. | Partially implemented. |
| 3.3 Design of Science Framework | Frame as analytical design, not validated predictive science. | Conceptual. |
| 4.1.1.1 Descriptive and Exploratory Analytics | Keep. Link to `analyze-skills`. | Implemented. |
| 4.1.1.2 Skill Ranking and Market Demand Indicators | Keep counts/frequencies. Caveat green/digital metadata if needed. | Implemented with caveats. |
| 4.1.1.3 Job Title and Employer Analysis | Keep. | Implemented. |
| 4.1.1.4 Emerging, Declining and Stable Skill Trends | Rename as observed period comparison/trend monitoring. | Implemented, not predictive. |
| 4.1.2.1 Geographic Aggregation from Tracker Data | Fix title typo if present. Raw location aggregation is supported. | Implemented. |
| 4.1.2.2 NUTS-like Regional Projections | Say NUTS-like/source-dependent, with demo projection limitations. | Implemented with caveats. |
| 4.1.2.3 Regional Skill Specialisation Indicators | Keep, with low-volume caveat. | Implemented. |
| 4.1.2.4 Regional Comparison of Skill Demand | Keep. | Implemented. |
| 4.1.3.1 Tracker-Based Sectoral Intelligence | Explicitly state source is Tracker `job.sectors`. | Implemented. |
| 4.1.3.2 Sector-Skill Co-occurrence Matrix | Clarify one multi-sector job contributes multiple sector-skill relationships. | Implemented. |
| 4.1.3.3 Sector Snapshot Analysis | Keep, but add production bootstrap caveat. | Implemented; production data pending #61. |
| 4.1.3.4 Sector Evolution across Years | Keep as snapshot comparison, not live forecasting. | Implemented; needs multi-year data. |
| 4.1.3.5 Sector Skills Comparison | Keep heatmap language and metrics. | Implemented. |
| 4.1.4.1 Temporal Dimension within Skill Demand Analysis | Keep as date filtering and period comparison. | Implemented. |
| 4.1.4.2 Regional Dimension within Skill Demand Analysis | Keep as raw/NUTS-like regional analytics. | Implemented. |
| 4.1.4.3 Sectoral Dimension within Skill Demand Analysis | Keep as observed Tracker sector distribution. | Implemented. |
| 4.1.4.4 Combined Interpretation of Skills, Regions, Sectors and Time | Keep as dashboard interpretation across views, not one unified model. | Implemented. |
| 4.2.1 Current Scope: Trend-Based Skill Monitoring | Keep. This is the correct forecasting framing. | Implemented. |
| 4.2.2 Emerging-Skills Endpoint and Period Comparison | Keep. | Implemented. |
| 4.2.3 Forecasting-Related Limitations | Keep explicit limitations. | Required caveat. |
| 5.1 Technology Stack | Match current stack: FastAPI, Streamlit, PostgreSQL, Docker, Tracker API. | Implemented. |
| 5.2.1 SKILLAB Projector Architecture | Match `docs/architecture.md`. | Implemented. |
| 5.2.2 Integration with the SKILLAB Tracker | Keep Tracker login/jobs/skills integration. | Implemented. |
| 5.2.3 Data Retrieval and Tracker Job Processing | Keep cache/checkpoint behavior. | Implemented. |
| 5.2.4 Integration of Skill Data from Multiple Sources | Rename or rewrite: current runtime uses Tracker API for sector flow. | Needs wording change. |
| 5.2.5 Descriptive Exploratory Analysis | Keep. | Implemented. |
| 5.2.6 Skill Ranking and Market Analytics | Keep. | Implemented. |
| 5.2.7 Trend and Emerging Skills Analysis | Keep as observed comparison. | Implemented. |
| 5.2.8 Regional Analytics | Keep. | Implemented. |
| 5.2.9 Sectoral Intelligence | Keep with `job.sectors x job.skills` source. | Implemented. |
| 5.2.10 Sector Snapshot Store | Keep PostgreSQL run/row model. | Implemented. |
| 5.2.11 Sector Skills Comparison | Keep. | Implemented. |
| 5.2.12 Dashboard Views and API Interfaces | Match current navigation and endpoints. | Implemented. |
| 5.2.13 Cooperative Stop Mechanism | Keep. | Implemented. |
| 5.2.14 Caching Strategy | Keep; mention no TTL yet. | Implemented; TTL pending follow-up. |
| 5.3.1 Implemented Trend-Based Temporal Analysis | Keep. | Implemented. |
| 5.3.2 Emerging and Declining Skill Detection | Keep as descriptive detection. | Implemented. |
| 5.3.3 Current Gaps and Production Hardening Priorities | Keep and align with open issues. | Required caveat. |
| 6.1.1.1 Case Study 1 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.1.2 Case Study 2 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.1.3 Case Study 3 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.2.1 Case Study 4 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.2.2 Case Study 5 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.2.3 Case Study 6 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.3.1 Case Study 7 | Add real output or mark as demonstration scenario. | Needs evidence. |
| 6.1.3.2 Case Study 8 | Add real output or mark as demonstration scenario. | Needs production/demo snapshot evidence. |
| 6.1.3.3 Case Study 9 | Add real output or mark as demonstration scenario. | Needs multi-year evidence. |
| 6.1.3.4 Case Study 10 | Add heatmap output or mark as demonstration scenario. | Needs evidence. |
| 6.1.3.5 Case Study 11 | Add skill portfolio output or mark as demonstration scenario. | Needs evidence. |
| 6.1.3.6 Case Study 12 | Add top job-title output or mark as demonstration scenario. | Needs evidence. |
| 6.2.1 Case Study 13 | Keep only as trend-monitoring case study. | Implemented with caveat. |
| 6.2.2 Case Study 14 | Keep only as sector-evolution snapshot comparison. | Implemented with caveat. |
| 7 Conclusion | Summarize implemented analytics and clearly separate future work. | Needs wording alignment. |

## Canonical Names to Use

Dashboard views:

- `Skill Analyzer`
- `Sector Overview`
- `Sector Skills Comparison`
- `Regional Sector Distribution`

API endpoints:

- `POST /projector/analyze-skills`
- `POST /projector/emerging-skills`
- `POST /projector/sectoral-intelligence`
- `POST /projector/sectoral-snapshot`
- `POST /projector/sector-skills-comparison`
- `POST /projector/regional-sectoral`
- `POST /projector/stop`
- `GET /projector/health`
- `GET /projector/readiness`

Preferred wording:

- Use: "trend-based monitoring", "period comparison", "observed growth".
- Avoid as implemented claims: "predictive forecasting", "ML forecast", "XAI forecast explanation".
- Use: "Tracker `job.sectors`".
- Avoid for current sector runtime: "ISCO/NACE file mapping", "ESCO-NACE crosswalk".

## Open Follow-Up Issues

- #61: bootstrap production sector snapshots.
- #1, #7, #8: keep docs/API docs aligned as implementation evolves.
