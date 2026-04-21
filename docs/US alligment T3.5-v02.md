# Task 3.5 User Story Alignment

This document maps Task 3.5 user-story expectations to the current Projector implementation.

## Regional Intelligence

Current support:
- raw geographic aggregation from Tracker `location_code`,
- NUTS-like projections by string slicing,
- optional synthetic NUTS-like projection with `demo=true`,
- specialization score using a Location Quotient-like calculation.

Relevant response field:

```text
insights.regional
```

## Sectoral Intelligence

Current support:
- ISCO sector view,
- NACE sector view through ESCO-NACE crosswalk,
- NACE levels: section, division, group, class,
- observed skills,
- canonical ESCO skills,
- observed skill groups,
- canonical skill groups,
- official ESCO matrix groups,
- skill breadth and concentration metrics,
- ISCO observed/canonical gap interpretation.

Relevant response fields:

```text
insights.sectoral
insights.sectoral_mode
insights.sectoral_views
insights.sector_view_names
```

## Temporal Projections

Current support:
- splits the selected period into two halves,
- compares skill frequency between the two periods,
- reports emerging, declining, stable and new-entry skills,
- reports volume growth at market level.

Relevant response field:

```text
insights.trends
```

## Statistical Interpretation

Current support:
- skill frequency counts,
- market share by region,
- Location Quotient-like specialization,
- sector breadth,
- dominant sector share,
- top-10 sector dominance,
- observed/canonical overlap for ISCO.

## Current Gaps

- Error responses are not standardized.
- Date ordering is not explicitly validated.
- Green and digital flags are currently placeholders in runtime enrichment.
- Automated test coverage should be expanded for all NACE levels and no-data branches.
