# Sector Intelligence

Sector intelligence extends the base skills analysis with sector-oriented views built from occupations, skills and ESCO support files.

## Sector Systems

The implementation supports two complementary sector systems.

| System | Meaning | Resolution path |
| --- | --- | --- |
| ISCO | Occupation-group view | `job -> occupation -> isco_group -> ISCO label` |
| NACE | Economic-activity view | `job -> occupation -> ESCO-NACE crosswalk -> NACE code/title` |

ISCO is native to the ESCO occupation structure. NACE is a projection through the ESCO-NACE crosswalk.

ISCO classifies jobs and occupations. It answers: "What kind of job is this?"

Examples:
- Software Developer
- Civil Engineer
- Nurse

NACE classifies economic sectors and industries. It answers: "In which industry does this job operate?"

Examples:
- Information and communication
- Construction
- Healthcare

## ISCO Views

ISCO sectoral intelligence currently uses Tracker occupations and ESCO support files to build three views.

| View | Occupation Source | ISCO Group Source | Skill Source | Skill Granularity | Aggregation Level |
| --- | --- | --- | --- | --- | --- |
| Observed | Tracker | ESCO CSV | Tracker | skill | ISCO group |
| Canonical | Tracker | ESCO CSV | ESCO CSV relations | skill | ISCO group |
| Official Matrix | Tracker | ESCO CSV | ESCO Matrix XLSX | skill group | ISCO group |

The Tracker can resolve occupation labels through an endpoint that accepts occupation ids and returns labels. The implementation can also use ESCO CSV files directly for ISCO labels and group metadata. Since those CSV files come from ESCO, they are acceptable as local support data and avoid repeated Tracker calls for static metadata.

The current ISCO grouping path relies on occupation metadata from ESCO CSV files, especially the occupation's ISCO group. Preferred occupation labels are useful for display, but they are not by themselves enough to define the ISCO group unless paired with the explicit group metadata.

## NACE Views

NACE sectoral intelligence uses Tracker occupations, the ESCO-NACE crosswalk and ESCO skill sources to build three corresponding views.

| View | Occupation Source | NACE Source | Skill Source | Skill Granularity | Aggregation Level |
| --- | --- | --- | --- | --- | --- |
| Observed | Tracker | ESCO-NACE Crosswalk XLSX | Tracker | skill | NACE selected level |
| Derived Canonical | Tracker | ESCO-NACE Crosswalk XLSX | ESCO CSV relations | skill | NACE selected level |
| Aggregated Official Matrix | Tracker | ESCO-NACE Crosswalk XLSX | ESCO Matrix XLSX | skill group | NACE selected level |

## NACE Levels

The API accepts these dashboard-facing NACE levels:

- `nace_section`
- `nace_division`
- `nace_group`
- `nace_class`

`nace_code` remains accepted as a technical compatibility value in the route signature, but the service builds dashboard NACE views for section, division, group and class.

`nace_section` is derived from official division ranges `A` through `U`.

## Multi-Mapping Semantics

One ESCO occupation may map to more than one NACE code. The current implementation keeps all mappings.

This means NACE mode is relation-oriented:
- it is useful for discovering skill-sector relationships,
- it is not strict one-to-one job accounting,
- one job-derived skill can contribute to multiple NACE sectors when its occupation has multiple crosswalk mappings.

## Sectoral Payload

When `include_sectoral=true`, `/projector/analyze-skills` returns sectoral data in:

- `insights.sectoral`
- `insights.sectoral_mode`
- `insights.sectoral_views`
- `insights.sector_view_names`

`insights.sectoral` is kept for backward compatibility. In the current service:
- if `sector_system=nace`, it contains the selected NACE level,
- otherwise it contains the ISCO payload.

`insights.sectoral_views` contains both systems:

```json
{
  "isco": {
    "sector_level": "isco_group",
    "items": []
  },
  "nace": {
    "selected_level": "nace_section",
    "levels": {
      "nace_section": { "sector_level": "nace_section", "items": [] },
      "nace_division": { "sector_level": "nace_division", "items": [] },
      "nace_group": { "sector_level": "nace_group", "items": [] },
      "nace_class": { "sector_level": "nace_class", "items": [] }
    }
  }
}
```

## Analytical Layers

Each sector item can include:

- observed skills: skills found directly in Tracker jobs
- canonical skills: ESCO occupation-skill relations aggregated by sector
- observed groups: observed skills aggregated into ESCO skill groups
- canonical groups: canonical skills aggregated into ESCO skill groups
- matrix groups: official ESCO matrix profiles aggregated by sector
- sector metrics: coverage and top-skill dominance
- skill transversality: sector breadth and concentration for top skills
- ISCO interpretation: observed/canonical gap and overlap, only for ISCO views

## Naming Semantics

For ISCO:
- Observed
- Canonical
- Official Matrix

For NACE:
- Observed
- Derived Canonical
- Aggregated Official Matrix

The NACE canonical and matrix views are ESCO-derived projections aggregated through the crosswalk; they are not native NACE ontologies.

## NACE Derivation Process

The derived NACE views are built by joining occupation-level evidence to NACE mappings, then aggregating into the selected NACE level.

| Step | Derived Canonical (NACE) | Aggregated Official Matrix (NACE) |
| --- | --- | --- |
| 1. Job input | Fetch job postings from Tracker | Fetch job postings from Tracker |
| 2. Occupation extraction | Extract ESCO occupation ids from jobs | Extract ESCO occupation ids from jobs |
| 3. Sector mapping | Map each occupation to one or more NACE codes using the ESCO-NACE crosswalk | Map each occupation to one or more NACE codes using the ESCO-NACE crosswalk |
| 4. Skill source | Retrieve canonical skills linked to each occupation from ESCO relations CSV | Retrieve official ESCO skill-group profile from ESCO Matrix XLSX |
| 5. Skill transformation | Keep skill-level granularity as individual ESCO skills | Keep skill-group level using ESCO matrix definitions |
| 6. Aggregation logic | For each job occurrence of an occupation, assign all its canonical skills to each mapped NACE sector | For each job occurrence of an occupation, assign its ESCO matrix profile to each mapped NACE sector |
| 7. Counting mechanism | Each canonical skill contributes `+1` per job occurrence per sector | Each skill group contributes its matrix share as a float per job occurrence per sector |
| 8. Multi-mapping handling | If an occupation maps to multiple NACE sectors, all sectors receive the same skill contributions | If an occupation maps to multiple NACE sectors, all sectors receive the same matrix profile contributions |
| 9. Sector aggregation | Aggregate skill counts per NACE sector | Aggregate skill-group shares per NACE sector |
| 10. Output structure | `sector -> skills -> counts / frequency` | `sector -> skill groups -> aggregated shares / frequency` |

## Derived Canonical NACE Pipeline

```text
job
 -> occupation (ESCO)
    -> canonical skills from ESCO relations
    -> NACE sectors from ESCO-NACE crosswalk
 -> assign each canonical skill to each mapped NACE sector
 -> aggregate counts by selected NACE level
```

Expanded logic:

```text
job
 -> occupation_id
    -> ESCO skills
    -> NACE mappings
 -> join skills to mapped NACE sectors
 -> each skill contributes +1 per job occurrence per sector
 -> counts per NACE sector
```

## Aggregated Official Matrix NACE Pipeline

```text
job
 -> occupation (ESCO)
    -> ESCO matrix profile (skill groups and shares)
    -> NACE sectors from ESCO-NACE crosswalk
 -> assign each matrix skill-group share to each mapped NACE sector
 -> aggregate weighted shares by selected NACE level
```

Expanded logic:

```text
job
 -> occupation_id
    -> ESCO matrix profile
    -> NACE mappings
 -> join matrix groups to mapped NACE sectors
 -> each group contributes its share per job occurrence per sector
 -> weighted aggregation by NACE sector
```

## Key Difference Between Derived NACE Views

```text
Derived Canonical:
+1 per canonical skill

Aggregated Official Matrix:
+share per skill group
```

Derived Canonical:
- represents ESCO-defined occupation-skill relationships,
- is re-aggregated by NACE sectors,
- keeps skill-level granularity,
- treats each skill as equally relevant in the current implementation.

Aggregated Official Matrix:
- represents official ESCO skill-group profiles,
- is aggregated by NACE sectors,
- uses skill-group granularity,
- preserves relative importance values from the ESCO matrix.
