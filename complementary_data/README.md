# Complementary Data

This folder contains local ESCO and NACE support files used by the current `app/` implementation.

The canonical data-source documentation is [../docs/data-sources.md](../docs/data-sources.md).

## Files Used At Runtime

| File | Use |
| --- | --- |
| `occupations_en.csv` | Occupation metadata and ISCO fallback values |
| `ISCOGroups_en.csv` | ISCO group labels |
| `occupationSkillRelations_en.csv` | Canonical occupation-skill relations |
| `skillsHierarchy_en.csv` | Skill-to-skill-group hierarchy |
| `skillGroups_en.csv` | Skill group labels |
| `Skills_Occupations Matrix Tables_ESCOv1.2.0_1.xlsx` | Official ESCO occupation-group to skill-group matrix |
| `ESCO-NACE rev. 2.1 crosswalk (1).xlsx` | Preferred ESCO occupation to NACE mapping |
| `nace_codes_2_1.csv` | NACE label fallback |

## Loading Path

Files are loaded by:

```text
app.core.container
 -> app.services.esco_loader.EscoLoader
```

The loader calls:

```text
load_local_esco_support()
load_official_esco_matrix()
```

## Conceptual Roles

Observed layer:

```text
Tracker jobs -> occupations + skills
```

Canonical layer:

```text
occupationSkillRelations_en.csv -> occupation -> canonical skills
```

Skill-group layer:

```text
skillsHierarchy_en.csv -> skill -> ESCO skill group
```

Official matrix layer:

```text
ESCO matrix workbook -> occupation group -> skill group shares
```

NACE layer:

```text
ESCO-NACE crosswalk -> occupation -> one or more NACE codes/titles
```

## Current NACE Rule

The ESCO-NACE crosswalk is the preferred source for NACE-facing semantics because it supports one-to-many mappings and titles.

`occupations_en.csv` may still expose a single `naceCode`, but it is treated as fallback support when crosswalk data is unavailable.
