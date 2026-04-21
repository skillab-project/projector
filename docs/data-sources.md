# Data Sources

SKILLAB Projector combines external Tracker data with local ESCO support files.

## Source Summary

| Source | File or endpoint | Current use |
| --- | --- | --- |
| Tracker jobs | `POST {TRACKER_API}/jobs` | Raw job postings used for observed market evidence |
| Tracker skills | `POST {TRACKER_API}/skills` | Skill label enrichment |
| Tracker occupations | `POST {TRACKER_API}/occupations` | Occupation label fallback |
| ESCO occupations | `complementary_data/occupations_en.csv` | Occupation metadata and ISCO fallback data |
| ISCO groups | `complementary_data/ISCOGroups_en.csv` | ISCO group labels |
| ESCO occupation-skill relations | `complementary_data/occupationSkillRelations_en.csv` | Canonical skill relations |
| ESCO skill hierarchy | `complementary_data/skillsHierarchy_en.csv` | Skill group aggregation |
| ESCO skill groups | `complementary_data/skillGroups_en.csv` | Skill group labels |
| ESCO matrix workbook | `complementary_data/Skills_Occupations Matrix Tables_ESCOv1.2.0_1.xlsx` | Official matrix group profiles |
| ESCO-NACE crosswalk | `complementary_data/ESCO-NACE rev. 2.1 crosswalk (1).xlsx` | Preferred occupation-to-NACE mapping and NACE titles |
| NACE labels | `complementary_data/nace_codes_2_1.csv` | NACE label fallback |

## Runtime Loading

Local source loading happens during container setup:

```text
app.core.container
 -> EscoLoader.load_local_esco_support()
 -> EscoLoader.load_official_esco_matrix()
```

The service is tolerant of missing optional files. Missing resources are logged as warnings and the corresponding layer may be incomplete.

## Tracker vs Local ESCO Metadata

Some occupation metadata can be requested from Tracker at runtime. In particular, Tracker has an occupation endpoint that accepts ids and returns labels.

For static ESCO-derived metadata, the implementation can also use local CSV files instead of calling Tracker repeatedly. This is acceptable for ISCO support because the CSV files are ESCO sources and are stable enough to use as local reference data.

Important distinction:
- Tracker occupation labels are useful for display and fallback enrichment.
- ESCO CSV occupation metadata is used for stable ISCO group resolution.
- A preferred label alone should not be treated as the full ISCO mapping unless the explicit ISCO group metadata is also available.

## Observed vs Canonical vs Matrix

Observed data comes from Tracker jobs:

```text
job -> skills
job -> occupations
```

Canonical data comes from ESCO occupation-skill relations:

```text
occupation -> canonical skills
```

Skill group aggregation comes from ESCO hierarchy:

```text
skill -> skill group
```

Official matrix profiles come from the ESCO matrix workbook:

```text
occupation group -> skill group shares
```

NACE aggregation comes from the ESCO-NACE crosswalk:

```text
occupation -> one or more NACE codes/titles
```

## Important Semantics

`occupations_en.csv` may contain a single `naceCode`, but the preferred NACE-facing source is the ESCO-NACE crosswalk workbook because it supports one-to-many mappings and NACE titles.

When the crosswalk is available, NACE mode should be understood as:

```text
job -> occupation -> crosswalk mappings -> NACE sectors
```

When it is not available, the loader can fall back to `naceCode` values from `occupations_en.csv` where present.
