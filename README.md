
---

# Sector Dimension Implementation

This document explains how the **Sector Dimension** was implemented in the SKILLAB Projector, step by step.

## Quick local run (API + Dashboard)

- Start FastAPI (from repo root):
  - `uvicorn app.main:app --reload` (recommended app package entrypoint)
  - `uvicorn main:app --reload` (legacy root entrypoint)
- Start Streamlit demo (new terminal):
  - `streamlit run app/example_dashboard/demo_dashboard.py`

> Note: Uvicorn expects `<module>:<attribute>` syntax (for example `app.main:app` or `main:app`), not file paths like `main.py:app` or `app/main.py`.

## Sector classification systems: ISCO vs NACE

- **ISCO** is occupation-based (`job -> occupation -> isco_group -> ISCO label`).
- **NACE** is economic-activity-based (`job -> occupation -> ESCO-NACE crosswalk -> nace_code -> NACE label`).
- Both systems are selectable in the sector dimension.
- ISCO labels come from ISCO metadata; NACE labels are resolved through the **ESCO-NACE rev. 2.1 crosswalk** (preferred source).

## NACE mode semantics

- One ESCO occupation may map to multiple NACE codes through the crosswalk.
- Multi-mapping is intentionally allowed in this phase.
- Current objective is **sector-skill relation discovery**, not strict one-to-one job accounting.
- Therefore the same observed skill evidence can appear in more than one NACE sector.

## NACE view semantics

- **Observed**: skills observed in jobs mapped to the NACE sector.
- **Derived Canonical**: ESCO canonical occupation-skill relations re-aggregated by NACE through the ESCO-NACE crosswalk.
- **Aggregated Official Matrix**: ESCO official matrix profiles aggregated by NACE through the ESCO-NACE crosswalk.

The goal of this dimension is to move from a simple list of occupations or skills to a **sector-oriented intelligence layer** that can answer questions such as:

- which skills are observed in a given sector,
- which skills are canonically associated with that sector according to ESCO,
- how the observed market differs from the ESCO reference structure,
- how sector profiles can be aggregated at skill-group level.

The implementation is incremental and combines three sources:

1. **Tracker job postings** → observed labor market signal  
2. **Local ESCO CSV files** → canonical occupation-skill and hierarchy support  
3. **Official ESCO matrix workbook** → aggregated occupation-group ↔ skill-group profiles :contentReference[oaicite:0]{index=0} :contentReference[oaicite:1]{index=1}

---

## 1. Conceptual model

The sector dimension is based on the following logic:

```text
job posting
 ├─ occupation(s)
 └─ skills
      ↓
occupation → sector
occupation → canonical skills
skill → ESCO skill group
      ↓
sector → observed skills
sector → canonical skills
sector → observed skill groups
sector → canonical skill groups
sector → official ESCO matrix profile
````

A sector is therefore **not extracted directly from a skill**.
Instead, the sector is derived from the **occupation context**, and skills are then aggregated inside that sector.

---

## 2. Data sources used

### 2.1 Tracker API

The Tracker API provides the live job-level signal:

* occupations in each job posting
* skills in each job posting
* temporal and geographic filters

This is the source used for the **observed** part of the sector analysis. 

### 2.2 Local complementary ESCO CSV files

The following local CSV files are used:

* `complementary_data/occupations_en.csv`
* `complementary_data/skillsHierarchy_en.csv`
* `complementary_data/occupationSkillRelations_en.csv`
* `complementary_data/ISCOGroups_en.csv`

These files are loaded at startup through `load_local_esco_support()` and populate internal support maps.

### 2.3 Official ESCO matrix workbook

The file:

* `Skills_Occupations Matrix Tables_ESCOv1.2.0_1.xlsx`

is used to load official occupation-group ↔ skill-group profiles from the ESCO matrix tables. The ESCO technical report explains that these matrix tables connect ISCO occupation groups and ESCO skill groups after hierarchical aggregation and row normalization. 

---

## 3. Internal support structures

The sector dimension relies on the following in-memory maps.

### 3.1 Occupation metadata

Loaded from `occupations_en.csv` into:

```python
self.occupation_meta
```

Structure:

```python
occ_id -> {
    "label": ...,
    "isco_group": ...,
    "nace_code": ...,
    "raw": ...
}
```

Used for:

* occupation label resolution
* sector derivation from occupation
* matrix lookup through ISCO group codes

### 3.2 Skill hierarchy

Loaded from `skillsHierarchy_en.csv` into:

```python
self.skill_hierarchy
```

Structure:

```python
skill_id -> {
    "level_1": ...,
    "level_2": ...,
    "level_3": ...,
    "raw": ...
}
```

Used for:

* mapping granular skills to ESCO skill groups
* building sector skill-group profiles

### 3.3 Canonical occupation-skill relations

Loaded from `occupationSkillRelations_en.csv` into:

```python
self.occ_skill_relations
```

Structure:

```python
occ_id -> set(skill_id)
```

Used for:

* canonical ESCO skill profiles per occupation
* canonical sector skill aggregation

### 3.4 Occupation group labels

Loaded from `ISCOGroups_en.csv` into:

```python
self.occupation_group_labels
```

Used for:

* human-readable labels of ISCO groups
* sector label enrichment

### 3.5 Official matrix profiles

Loaded from the ESCO workbook into:

```python
self.esco_matrix_profiles
```

Structure:

```python
(sheet_name, occupation_group_id) -> {
    "occupation_group_label": ...,
    "profile": {
        skill_group_id: share
    }
}
```

Used for:

* official sector/group reference profiles

---

## 4. How sectors are derived

The sector dimension starts from occupations, not from skills.

### 4.1 Primary occupation extraction

For each job posting, the system extracts the main occupation with:

```python
get_primary_occupation_id(job)
```

Resolution order:

1. `job["occupations"][0]`
2. fallback to `job["occupation_id"]`
3. empty string if missing

### 4.2 Sector resolution from occupation

The function:

```python
get_sector_from_occupation(occ_id, level="isco_group")
```

derives a sector from an occupation.

Resolution order:

1. **Local CSV metadata**

   * if `level == "nace_code"` → return NACE code
   * if `level == "label"` → return occupation label
   * otherwise → return `isco_group`, optionally mapped to a readable label

2. **Tracker fallback**

   * if local metadata is missing, use `self.sector_map`

3. **Safe fallback**

   * `"Sector not specified"`

In practice, the default sector resolution uses the **ISCO group** because it provides a stable professional grouping and is compatible with the ESCO matrix logic.

---

## 5. Observed sector intelligence

Observed sector intelligence is built directly from Tracker job postings.

### 5.1 Occupation → observed skill matrix

The method:

```python
build_observed_occupation_skill_matrix(jobs)
```

creates:

```python
self.occ_skill_observed
```

Structure:

```python
occ_id -> Counter(skill_id -> count)
```

This captures how often each skill is observed in jobs belonging to that occupation.

### 5.2 Sector → observed skill matrix

The method:

```python
build_observed_sector_skill_matrix(jobs, sector_level="isco_group")
```

creates:

```python
self.sector_skill_observed
```

Structure:

```python
sector -> Counter(skill_id -> count)
```

This aggregates observed skills at sector level.

### 5.3 Human-readable summaries

The following methods summarize observed skills:

* `get_observed_skills_for_occupation(...)`
* `get_observed_skills_for_sector(...)`
* `summarize_observed_sector_skills(...)`
* `summarize_single_sector(...)`

These return:

* `total_skill_mentions`
* `unique_skills`
* top skills
* relative frequencies
* optional label, green, and digital flags when available

---

## 6. Canonical sector intelligence

Canonical sector intelligence is derived from ESCO occupation-skill relations.

### 6.1 Occupation → canonical skills

The method:

```python
get_canonical_skills_for_occupation(occ_id)
```

returns ESCO skills linked to an occupation through the local CSV relations.

At this stage, canonical relations are treated as **unweighted**:

* each skill contributes `count = 1`

### 6.2 Sector → canonical skill matrix

The method:

```python
build_canonical_sector_skill_matrix(jobs, sector_level="isco_group")
```

creates:

```python
self.sector_skill_canonical
```

Structure:

```python
sector -> Counter(skill_id -> count)
```

For each job:

* the occupation is resolved,
* the sector is resolved,
* all canonical ESCO skills for that occupation are added to the sector.

This means that canonical skill counts are influenced by how often an occupation appears in the filtered job dataset.

### 6.3 Canonical summaries

The following methods summarize canonical skills:

* `get_canonical_skills_for_sector(...)`
* `summarize_canonical_sector_skills(...)`

These produce the same structure as the observed summaries, enabling direct comparison.

---

## 7. Skill-group aggregation

The ESCO matrix logic is defined at **skill-group level**, not only at raw skill level. The ESCO report explicitly describes the matrix as linking ISCO occupation groups and ESCO skill groups across multiple hierarchy levels. 

### 7.1 Skill → ESCO group mapping

The method:

```python
get_skill_group(skill_id, level=1|2|3)
```

maps a granular skill to an ESCO hierarchy group using `self.skill_hierarchy`.

If the group cannot be resolved, the system falls back to:

* skill label if available
* `"Skill group not specified"`

### 7.2 Observed sector → skill-group matrix

The method:

```python
build_observed_sector_skillgroup_matrix(...)
```

creates:

```python
self.sector_skillgroup_observed
```

Structure:

```python
sector -> Counter(skill_group_id -> count)
```

### 7.3 Canonical sector → skill-group matrix

The method:

```python
build_canonical_sector_skillgroup_matrix(...)
```

creates:

```python
self.sector_skillgroup_canonical
```

Structure:

```python
sector -> Counter(skill_group_id -> count)
```

### 7.4 Skill-group summaries

The following methods provide readable summaries:

* `summarize_observed_sector_skillgroups(...)`
* `summarize_canonical_sector_skillgroups(...)`

Both return:

* `total_group_mentions`
* `unique_groups`
* top groups with frequencies

---

## 8. Official ESCO matrix integration

The official ESCO matrix provides a third, already-aggregated structural layer.

### 8.1 Workbook loader

The method:

```python
load_official_esco_matrix(...)
```

loads:

* the `Overview` sheet
* all `Matrix x.y` sheets

Each matrix sheet is indexed as:

```python
(sheet_name, occupation_group_id) -> profile
```

where `profile` is a distribution over ESCO skill groups.

### 8.2 Sheet resolution

The method:

```python
get_esco_matrix_sheet_name(skill_group_level, occupation_level)
```

builds the correct sheet identifier, for example:

* `Matrix 1.1`
* `Matrix 2.3`

### 8.3 Occupation → matrix occupation group

The method:

```python
get_occupation_group_id_for_matrix(occ_id, occupation_level)
```

maps an occupation to the ISCO group code required by the workbook.

### 8.4 Official profile lookup

The method:

```python
get_official_esco_profile_for_occupation(...)
```

returns the official ESCO matrix profile for the occupation’s group.

### 8.5 Sector → official matrix profile

The method:

```python
build_official_matrix_sector_skillgroup_profile(...)
```

aggregates official matrix profiles at sector level:

```python
self.matrix_profiles
```

Structure:

```python
sector -> Counter(skill_group_id -> aggregated_share)
```

This provides the **official structural reference** for a sector.

---

## 9. Unified sectoral intelligence output

Once all layers are built, the method:

```python
build_sectoral_intelligence(...)
```

returns a unified payload for each sector with:

* `observed_skills`
* `canonical_skills`
* `observed_groups`
* `canonical_groups`
* `official_matrix_groups`

This is the main output consumed by the API when sectoral intelligence is requested.

The helper:

```python
build_single_sector_intelligence(...)
```

returns the same structure for one single sector only.

---

## 10. API integration

The `/projector/analyze-skills` endpoint was extended with:

* `include_sectoral`
* `skill_group_level`
* `occupation_level`

When `include_sectoral=True`, the endpoint calls:

```python
engine.build_sectoral_intelligence(...)
```

and adds the result under:

```json
insights.sectoral
```

This extension is **non-destructive**:

* existing Phase 1 fields remain unchanged
* sectoral intelligence is optional
* backward compatibility is preserved 

---

## 11. Summary of the three analytical layers

The implemented sector dimension combines three complementary views:

### 11.1 Observed

Derived from real Tracker job postings.

Use:

* current market demand
* empirical evidence
* live signal

### 11.2 Canonical

Derived from ESCO occupation-skill relations.

Use:

* structural ESCO reference
* canonical expectations per occupation
* more stable semantic baseline

### 11.3 Official matrix

Derived from the official ESCO aggregated workbook.

Use:

* occupation-group ↔ skill-group distributions
* official structural profile
* high-level comparison and validation 

---

## 12. Current limitations

The implementation works, but there are still some known limitations.

### 12.1 Human-readable labels are not fully resolved everywhere

Some outputs may still expose:

* raw ESCO skill URIs
* raw sector codes such as `C2`
* raw skill-group ids such as `S1` or `S5.1`

This happens when:

* skill labels were not pre-resolved through the Tracker
* group labels were not available in the loaded hierarchy files
* official matrix keys remain code-based

### 12.2 Canonical skill weights are still simple

Canonical skills are currently counted with a uniform weight of `1` per job occurrence of the corresponding occupation.

More advanced weighting schemes could later differentiate:

* essential vs optional skills
* frequency-adjusted occupation weights
* normalized occupation contributions

### 12.3 Sector labeling is still code-heavy internally

The internal pipeline uses stable codes for correctness and reproducibility, but the presentation layer still needs a stronger label enrichment phase.

### 12.4 Official matrix and sector keys are not yet fully harmonized for presentation

The official matrix layer is structurally correct, but its labels still need better UI-friendly decoding.

---

## 13. Why this implementation is useful

Even with the current label limitations, the sector dimension already provides a powerful structure:

* it connects jobs, occupations, skills, and sectors
* it combines empirical market evidence with ESCO knowledge
* it supports comparison across observed, canonical, and official profiles
* it creates a foundation for explainable sector-oriented labor market intelligence

This makes it possible to answer not only:

* “Which skills appear in the data?”

but also:

* “Which skills characterize this sector?”
* “How does the observed market differ from the ESCO canonical profile?”
* “How does the sector compare with the official ESCO structural matrix?”

---

## 14. Implementation status

Implemented:

* sector derivation from occupation
* observed occupation-skill matrix
* observed sector-skill matrix
* canonical sector-skill matrix
* skill-group aggregation
* official ESCO matrix loading and lookup
* unified `sectoral` API payload
* dashboard integration scaffolding

Still to improve:

* sector labels
* skill-group labels
* canonical weighting refinement
* alignment score
* cleaner dashboard representation of codes vs labels

```
