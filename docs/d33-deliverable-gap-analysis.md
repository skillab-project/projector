# D3.3 Deliverable Gap Analysis

This checklist compares the D3.3 "Skills Analytics & Forecasting" deliverable with the current SKILLAB Projector implementation.

Related issue: #62.

## Overall Status

The Projector currently supports descriptive labour-market analytics, observed trend monitoring, skill-first exploration, regional intelligence, regional-temporal analysis, sector intelligence, yearly sector snapshots, sector evolution, sector-skills comparison, regional-sectoral distribution, and an inferential validation layer.

The main remaining gap is not core descriptive analytics. It is scope alignment: the deliverable must not claim predictive ML forecasting, XAI forecasting, supply-side analytics, or production-loaded real snapshots as already implemented in the Projector runtime.

## Status Legend

| Status | Meaning |
| --- | --- |
| Implemented | Runtime API and/or documented workflow exists and is tested. |
| Partial | A compatible baseline exists, but wording needs caveats or production data. |
| Out of scope | Should be removed from Projector runtime claims. |
| Needs decision | Scope or data ownership is not clear yet. |
| Documentation only | No runtime change needed; update deliverable wording. |

## Scope Decisions From The D3.3 Source

| Area | Decision |
| --- | --- |
| Predictive forecasting | Out of current D3.3 runtime scope. The deliverable explicitly limits forecasting to trend-based monitoring and period comparison. |
| Confidence intervals | Not evidenced in the D3.3 source and out of current runtime scope. |
| XAI forecasting | Out of current D3.3 runtime scope. XAI appears as glossary/context, not as an implemented Projector forecasting feature. |
| Scenario simulation | Out of current D3.3 runtime scope. The source mentions validation/demonstration scenarios, not a runtime simulation feature. |
| Supply-side analytics | Out of current Projector runtime scope. The source title mentions demand and supply, but the Projector implementation described is based on Tracker job advertisements. |
| Real case-study outputs/figures | Out of scope for this implementation track. |
| Production real snapshots | Deferred to #61 and server deployment. |

## Micro-Section Matrix

| D3.3 subsection | Status | Current evidence | Action for deliverable |
| --- | --- | --- | --- |
| Executive Summary | Partial | Projector has analytics, trend monitoring and inferential layer. | Replace accidental `D3.2` references with `D3.3`; avoid predictive ML/XAI claims. |
| 2.1 Purpose and Scope | Partial | Scope is API + demo dashboard for demand-side analytics. | State current scope as demand-side analytics plus trend monitoring. |
| 2.2 Deliverable Structure | Documentation only | No runtime dependency. | Keep, but align section names with final implementation. |
| 3.1 Input from Description of Action | Documentation only | Projector implements a subset of the broader framework. | Separate implemented Projector runtime from broader research ambitions. |
| 3.2 Input from SKILLAB Requirements | Partial | API, dashboard, docs and tests exist. | Map requirements to implemented endpoints; avoid unimplemented forecasting claims. |
| 3.3 Design of Science Framework | Partial | Trend monitoring and chi-square evidence exist; ML lifecycle is not fully implemented. | Present current work as baseline statistical/analytical framework. |
| 4.1 Skills Analytics | Implemented | Main analytics endpoints and dashboard views exist. | Keep as implemented. |
| 4.1.1 Analysis of Skill Demand in Online Job Advertisements | Implemented | `POST /projector/analyze-skills`. | Keep as implemented. |
| 4.1.1.1 Descriptive and Exploratory Analytics | Implemented | Counts, rankings, geo/sector/job-title/employer summaries. | Keep as implemented. |
| 4.1.1.2 Skill Ranking and Market Demand Indicators | Implemented | Skill count/frequency, green/digital flags, sector spread. | Clarify green/digital flags are heuristic unless reliable metadata is available. |
| 4.1.1.3 Job Title and Employer Analysis | Implemented | Job titles/employers returned by main analysis and snapshots. | Keep as implemented. |
| 4.1.1.4 Emerging, Declining and Stable Skill Trends | Implemented | Observed period comparison and trend labels. | Call this observed trend analysis, not predictive forecasting. |
| 4.1.2 Regional Analysis of Skills and Labour-Market Demand | Implemented | Regional analytics from Tracker location fields. | Keep with caveats on source quality. |
| 4.1.2.1 Geographic Aggregation from Tracker Data | Implemented | Raw `location_code` aggregation. | Keep as implemented. |
| 4.1.2.2 NUTS-like Regional Projections | Partial | Code-derived/demo NUTS-like slicing. | State "NUTS-like/source-dependent", not official NUTS mapping. |
| 4.1.2.3 Regional Skill Specialisation Indicators | Implemented | Location Quotient-like specialization. | Add low-count caveat. |
| 4.1.2.4 Regional Comparison of Skill Demand | Implemented | Regional skill comparison and inferential `regional_skill` type. | Keep as implemented. |
| 4.1.3 Sectoral Analysis of Skills and Job Demand | Implemented | Tracker `job["sectors"] x job["skills"]`. | State sector source is Tracker API sectors, not local ISCO/NACE files. |
| 4.1.3.1 Tracker-Based Sectoral Intelligence | Implemented | Sectoral API and snapshot views. | Keep as implemented. |
| 4.1.3.2 Sector-Skill Co-occurrence Matrix | Implemented | Sector-skill counts from job co-occurrence. | Explain multi-sector jobs contribute to multiple sector-skill events. |
| 4.1.3.3 Sector Snapshot Analysis | Implemented | PostgreSQL snapshot schema and APIs. | Keep; note production DB bootstrap is server-side work. |
| 4.1.3.4 Sector Evolution across Years | Implemented | Snapshot reference-year comparison. | Keep; requires real multi-year snapshots in production. |
| 4.1.3.5 Sector Skills Comparison | Implemented | Heatmap endpoint and metrics: count/share/rank/growth. | Keep as implemented. |
| 4.1.4 Multidimensional Skills Analytics | Implemented | Skill, time, region and sector views are connected. | Keep as implemented; avoid implying one monolithic model. |
| 4.1.4.1 Temporal Dimension within Skill Demand Analysis | Implemented | `POST /projector/temporal-projections`. | Keep as trend monitoring. |
| 4.1.4.2 Regional Dimension within Skill Demand Analysis | Implemented | Regional distribution and regional skill evidence. | Keep with NUTS caveat. |
| 4.1.4.3 Sectoral Dimension within Skill Demand Analysis | Implemented | Sector distribution and sector intelligence. | Keep with Tracker-sector source caveat. |
| 4.1.4.4 Combined Interpretation of Skills, Regions, Sectors and Time | Partial | Cross-dimension views exist; Regional x Temporal and Skill x Sector/Regional/Temporal are implemented. Regional x Sectoral x Temporal completion is tracked in #33. | State implemented combinations explicitly. |
| Dimension 4: Statistical Inferential Mechanisms | Implemented | `POST /projector/statistical-comparison`, chi-square, p-value, effect size. | Describe as inferential layer attached to comparison views, not standalone dashboard area. |
| 4.2 Skills Forecasting | Implemented | Trend monitoring and baseline projection exist; the D3.3 source explicitly excludes predictive forecasting engines from the current runtime. | Keep current wording honest: forecasting means trend-based monitoring and period comparison here. |
| 4.2.1 Current Scope: Trend-Based Skill Monitoring | Implemented | Period job counts, skill time series, baseline projection. | Keep as implemented. |
| 4.2.2 Emerging-Skills Endpoint and Period Comparison | Implemented | `POST /projector/emerging-skills` and temporal endpoints. | Keep as observed period comparison. |
| 4.2.3 Forecasting-Related Limitations | Implemented as documentation | `docs/forecasting-scope.md` documents current limits. | Keep limits explicit; do not convert excluded methods into implementation requirements. |
| 5.1 Technology Stack | Implemented | FastAPI, Streamlit demo, PostgreSQL, pytest, Jenkins. | Keep current stack. |
| 5.2.1 Projector Architecture | Implemented | `app/` package architecture and docs. | Keep as implemented. |
| 5.2.2 Integration with SKILLAB Tracker | Implemented | Tracker client and API-only job processing. | Keep; mention job sectors and skills come from Tracker API. |
| 5.2.3 Data Retrieval and Tracker Job Processing | Implemented | Fetch, pagination/cache, filters, timeout handling. | Keep with cache caveat. |
| 5.2.4 Skill Label Enrichment | Partial | Labels resolved from API/helpers; local support is not analytical source. | Avoid claiming local ESCO files drive sector mapping. |
| 5.2.5 Descriptive Exploratory Analysis | Implemented | Main analysis endpoint. | Keep. |
| 5.2.6 Skill Ranking and Market Analytics | Implemented | Ranking and metrics. | Keep with heuristic flag caveat. |
| 5.2.7 Trend and Emerging Skills Analysis | Implemented | Emerging/trend endpoints. | Keep as observed trends. |
| 5.2.8 Regional Analytics | Implemented | Regional projections and specialization. | Keep with source-dependent NUTS caveat. |
| 5.2.9 Sectoral Intelligence | Implemented | Tracker sector API workflow. | Keep with no local ISCO/NACE mapping claim. |
| 5.2.10 Sector Snapshot Store | Implemented | DB schema, scripts, Docker DB. | Keep; real production bootstrap deferred to server deployment. |
| 5.2.11 Sector Skills Comparison | Implemented | Endpoint and dashboard heatmap. | Keep. |
| 5.2.12 Dashboard Views and API Interfaces | Implemented | Demo dashboard and endpoint docs. | Clarify dashboard is demo/integration guide for final frontend. |
| 5.2.13 Cooperative Stop Mechanism | Implemented | Stop endpoint/state. | Keep. |
| 5.2.14 Caching Strategy | Partial | Cache exists; TTL cleanup issue remains separate. | Mention operational cache policy separately if needed. |
| 5.3 Skills Forecasting | Implemented | Baseline trend projection only. | Avoid claiming predictive forecasting, XAI, confidence intervals or scenario forecasting. |
| 5.3.1 Implemented Trend-Based Temporal Analysis | Implemented | Temporal projections endpoint. | Keep. |
| 5.3.2 Emerging and Declining Skill Detection | Implemented | Period comparison. | Keep. |
| 5.3.3 Current Gaps and Production Hardening Priorities | Implemented as documentation | Forecasting scope + production docs exist. | Keep limitations explicit and focus hardening on implemented runtime features. |
| 6.1 Skills Analytics case studies | Out of scope | Features exist; repo does not contain real case-study outputs/figures. | Do not implement real case-study outputs in Projector; label any examples as demonstration scenarios. |
| 6.1.1.1 Case Study 1 | Out of scope | Skill demand API exists. | Do not add real output artifacts here. |
| 6.1.1.2 Case Study 2 | Out of scope | Emerging/declining API exists. | Do not add real output artifacts here. |
| 6.1.1.3 Case Study 3 | Out of scope | Job title/employer analytics exist. | Do not add real output artifacts here. |
| 6.1.2.1 Case Study 4 | Out of scope | Raw regional demand exists. | Do not add real output artifacts here. |
| 6.1.2.2 Case Study 5 | Out of scope | NUTS-like projections exist. | Do not add real output artifacts here. |
| 6.1.2.3 Case Study 6 | Out of scope | Regional comparison exists. | Do not add real output artifacts here. |
| 6.1.3.1 Case Study 7 | Out of scope | Tracker sector-skill analysis exists. | Do not add real output artifacts here. |
| 6.1.3.2 Case Study 8 | Out of scope | Yearly snapshots exist. | Do not add real output artifacts here; server bootstrap remains #61. |
| 6.1.3.3 Case Study 9 | Out of scope | Sector evolution exists. | Do not add real output artifacts here. |
| 6.1.3.4 Case Study 10 | Out of scope | Heatmap comparison exists. | Do not add real output artifacts here. |
| 6.1.3.5 Case Study 11 | Out of scope | Skill portfolio exists in dashboard. | Do not add real output artifacts here. |
| 6.1.3.6 Case Study 12 | Out of scope | Sector job titles exist. | Do not add real output artifacts here. |
| 6.2 Skill Forecasting case studies | Out of scope | Trend monitoring exists; predictive forecasting does not. | Do not implement real case-study outputs in Projector. |
| 6.2.1 Case Study 13 | Out of scope | Emerging skills through time-window comparison exists. | Keep only as an example if needed. |
| 6.2.2 Case Study 14 | Out of scope | Sector evolution through yearly snapshots exists. | Keep only as an example if needed. |

## Deliverable Edits Checklist

- Replace accidental `D3.2` references with `D3.3`.
- Use "trend monitoring", "observed change", "period comparison" and "baseline projection".
- Do not claim predictive ML forecasting as implemented or required for the current D3.3 runtime.
- Do not claim XAI forecasting explanations as implemented or required for the current D3.3 runtime.
- Do not add confidence intervals or scenario simulation as D3.3 runtime requirements unless a later scope decision changes this.
- Treat supply-side analytics as outside the current Projector runtime unless a supply-side data source and owner are identified.
- Mark NUTS outputs as NUTS-like and source-dependent.
- Describe sector data source as Tracker `job["sectors"]`.
- Explain sector counts as relationship counts when jobs contain multiple sectors.
- Describe statistical inference as an inferential layer, not as a standalone dimension view.
- State that p-values/effect sizes validate observed differences; they do not prove shortage, causality or future demand.
- Do not implement real case-study outputs/figures in Projector; label any examples as demonstration scenarios.
- Add production caveat: real snapshots must be bootstrapped on the deployed server.

## Recommended Wording

Use:

- "observed skill demand"
- "trend-based monitoring"
- "short-term baseline projection"
- "year-to-year sector evolution"
- "Tracker-sector co-occurrence"
- "inferential evidence for observed differences"

Avoid:

- "predictive ML forecasting"
- "AI forecasting model"
- "XAI forecast explanation"
- "statistically significant shortage"
- "official NUTS mapping" unless backed by official mapping data
- "NACE/ISCO-derived sectors" for the current sector workflow

## Follow-Up Issues

- #4: can be closed if the merged inferential layer is accepted as the first implementation of Dimension 4.
- #50: keep open as broader conceptual-design tracking unless the full design is accepted.
- #62: use this checklist to align the deliverable wording with runtime evidence.
- #61: leave for server deployment, as production snapshot bootstrap is intentionally deferred.
