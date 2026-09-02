# D3.3 Deliverable Edit Plan

Practical edit plan for aligning the D3.3 `.docx` with the implemented Projector runtime.

Related issue: #62.

## Global Replacements

| Find / claim | Replace with |
| --- | --- |
| `D3.2` when referring to this deliverable | `D3.3` |
| predictive forecasting implemented | trend-based monitoring and period comparison implemented |
| AI/ML forecasting model implemented | baseline projection / observed trend analysis implemented |
| XAI forecasting explanations implemented | not part of the current Projector runtime |
| official NUTS mapping | NUTS-like projection, source-dependent |
| NACE/ISCO sector mapping | Tracker API `job["sectors"]` |
| shortage proof | observed statistical evidence |

## Executive Summary Patch

Use this meaning:

```text
The current Projector prototype provides demand-side labour-market analytics over Tracker job data. It supports descriptive skill-demand analytics, regional and sectoral views, temporal trend monitoring, yearly sector snapshots, sector evolution, sector-skills comparison, and an inferential evidence layer for selected observed comparisons.
```

Avoid:

```text
The Projector implements predictive ML forecasting and XAI explanations.
```

## Forecasting Wording

Use:

```text
The implemented forecasting-related functionality is currently limited to trend-based monitoring and short-term baseline projection from observed counts. Predictive ML forecasting, confidence intervals, XAI explanations and scenario simulation are not part of the current Projector runtime described by D3.3.
```

## Sectoral Wording

Use:

```text
Sectoral analytics use the `sectors` field returned by Tracker jobs. Sector-skill relations are derived by co-occurrence: each job contributes its observed skills to each sector listed on the same job.
```

Add caveat:

```text
When a job contains multiple sectors, it contributes to multiple sector counts and sector-skill events. Sector counts are relationship counts, not necessarily mutually exclusive job counts.
```

## Regional Wording

Use:

```text
Regional analytics aggregate Tracker location fields and, where possible, derive NUTS-like projections from available location codes.
```

Add caveat:

```text
NUTS-like outputs depend on source-code quality and should not be described as official NUTS mapping unless official mapping data is introduced.
```

## Inferential Layer Wording

Use:

```text
The statistical inferential mechanisms are implemented as an explainable inferential layer attached to comparison views. The current endpoint runs a baseline 2x2 chi-square comparison and reports p-value, effect size, observed and expected 2x2 tables, share difference, relative risk, odds ratio, interpretation, assumptions, limitations and warnings.
```

Add caveat:

```text
The statistical evidence indicates whether an observed difference is unlikely under the baseline test. It does not prove causality, shortage or future demand.
```

## Case Studies

For every D3.3 case-study section, use this framing:

```text
Label the section as a demonstration scenario rather than empirical validation.
```

Do not present demo/fake snapshot data as production evidence.

## Production Caveat

Use:

```text
The PostgreSQL snapshot store, refresh scripts, scheduler and validation scripts are implemented. Production snapshot bootstrap with real Tracker data is a deployment-time operation and will be executed on the target server.
```
