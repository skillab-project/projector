# Sector Dimension: Current Implementation

This document is a compact technical note for the current sector dimension.

The maintained, reader-facing sector documentation is [docs/sector-intelligence.md](docs/sector-intelligence.md).

## Goal

The sector dimension connects jobs, occupations and skills so the API can answer:

- which skills appear in a sector,
- which skills are canonically associated with that sector according to ESCO,
- how observed market evidence differs from ESCO references,
- how skills aggregate into ESCO skill groups,
- how ISCO and NACE views differ.

## Runtime Flow

```text
Tracker job
 ├── occupations
 └── skills
      ↓
occupation -> ISCO sector
occupation -> NACE sector through ESCO-NACE crosswalk
occupation -> canonical ESCO skills
skill -> ESCO skill group
      ↓
sector -> observed skills
sector -> canonical skills
sector -> observed skill groups
sector -> canonical skill groups
sector -> official ESCO matrix groups
```

## Systems

ISCO:

```text
job -> occupation -> isco_group -> ISCO label
```

NACE:

```text
job -> occupation -> ESCO-NACE crosswalk -> NACE code/title
```

NACE supports:
- `nace_section`
- `nace_division`
- `nace_group`
- `nace_class`

`nace_code` remains accepted by the route for technical compatibility, but dashboard-facing views are built for section, division, group and class.

## Analytical Layers

Observed:
- built from Tracker job skills,
- represents current market evidence.

Canonical:
- built from `occupationSkillRelations_en.csv`,
- represents ESCO occupation-skill reference knowledge.

Skill groups:
- built from `skillsHierarchy_en.csv`,
- aggregates skills into higher-level ESCO groups.

Official matrix:
- built from `Skills_Occupations Matrix Tables_ESCOv1.2.0_1.xlsx`,
- represents official occupation-group to skill-group profiles.

## API Output

When `include_sectoral=true`, `/projector/analyze-skills` returns:

- `insights.sectoral`
- `insights.sectoral_mode`
- `insights.sectoral_views`
- `insights.sector_view_names`

`insights.sectoral_views` contains both ISCO and NACE payloads. NACE includes all supported hierarchy levels.

## Interpretation Caveat

NACE is relation-oriented in the current implementation. If one occupation maps to multiple NACE sectors, all mappings are kept and the same skill evidence can appear in multiple NACE sectors.

Use NACE totals for relationship discovery, not strict one-job-one-sector accounting.
