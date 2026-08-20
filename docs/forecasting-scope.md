# Forecasting Scope

Related issues: #59, #3, #4, #50, #62.

## Decision

Current Projector forecasting scope is:

```text
observed trend monitoring + period comparison
```

Predictive forecasting is deferred until the data, validation and model requirements are explicitly approved.

## Implemented Now

`Job Demand Overview`

- compares skills inside the selected job/date slice
- returns emerging, declining, stable and new-entry skill signals
- uses observed job postings only

`Emerging Skills`

- compares two internal periods in the requested date range
- reports market volume growth and skill growth

`Temporal Analysis`

- aggregates jobs by `upload_date`
- supports monthly, quarterly and yearly granularity
- reports period-level job growth and skill-level growth
- returns a short-term baseline projection using recent count deltas

`Sector Evolution`

- compares one sector between two selected years
- reports job delta, job growth, new skills, disappeared skills, growing skills, declining skills and churn

`Sector Skills Comparison`

- compares sectors x skills for one year
- optionally compares skill counts between two selected years

## Not Implemented Yet

- predictive time-series forecasting
- ML demand forecasting
- XAI forecasting explanations
- scenario simulation
- confidence intervals for future demand
- statistical hypothesis testing with p-values

## Language To Use

Use:

- `trend monitoring`
- `observed change`
- `period comparison`
- `year-over-year evolution`
- `growth between selected periods`
- `short-term baseline projection`

Avoid for current implementation:

- `predictive forecasting`
- `future demand prediction`
- `AI forecasting model`
- `XAI forecast`
- `statistically significant shortage`

## If Predictive Forecasting Is Required

Open implementation issues for:

- data coverage and minimum history requirements
- baseline statistical model
- model validation and backtesting
- API response contract
- dashboard visualization
- uncertainty and explanation format

Do not add predictive claims to D3.3 until those items are implemented and validated.
