# Focus analysis: GitHub issues #14 → #20 (NACE sector mode)

Date of analysis: 2026-04-18
Repository: `skillab-project/projector`

## Scope
This note maps each issue (#14 to #20) to the current repository status, with a practical implementation order.

## Executive summary
- **Partially available already**:
  - `occupation_id -> nace_code` is already loaded from CSV (`occupations_en.csv`).
  - Occupation analytics can already return `nace_code` as sector key.
- **Main gaps**:
  - API/service still hardcode ESCO/ISCO sector mode (`sector_level="isco_group"`).
  - Missing NACE hierarchy handling (`division/group/class`) as selectable levels.
  - Output schemas/docs do not expose the selected sector system/level.
  - Test suite for NACE mode is incomplete and not auto-discovered by `pytest` default run.

---

## Issue-by-issue status

### #14 — NACE Code for Sector (instead of ISCO)
**Status:** 🟡 Partial

**What exists now**
- NACE code is already loaded into `engine.occupation_meta[occ_id]["nace_code"]` from `occupations_en.csv`.
- Sector resolver supports `level="nace_code"`.

**Gap**
- The primary analysis path (`/projector/analyze-skills`) still calls sectoral intelligence with fixed `sector_level="isco_group"`, so NACE mode is not user-selectable end-to-end.

---

### #15 — Caricare mapping occupation_id → NACE code dai CSV
**Status:** 🟢 Largely done

**What exists now**
- CSV loader already ingests `naceCode` into occupation metadata.

**Residual gap**
- No explicit validation/reporting on coverage quality (e.g., percentage of occupations with missing NACE code).

---

### #16 — Implementare gerarchia selezionabile NACE (division, group, class)
**Status:** 🔴 Missing

**Gap**
- There is no utility that normalizes NACE to hierarchical levels (e.g., section/division/group/class) in API-facing code.
- There is no API parameter for selecting the NACE hierarchy level.

---

### #17 — Mantenere doppio sistema ESCO/ISCO e NACE
**Status:** 🔴 Missing (end-to-end)

**Gap**
- No request-level switch for choosing sector taxonomy (`isco_group` vs `nace_*`).
- Current default path is mono-system (ISCO group) during sectoral build.

---

### #18 — Logica aggregazione e dashboard duale ESCO/ISCO vs NACE
**Status:** 🔴 Missing

**Gap**
- Service layer does not expose dual-mode aggregation selection.
- Demo/dashboard payload defaults are still aligned to current fixed ISCO-sector flow.

---

### #19 — Aggiornare schemi di output e documentazione per NACE
**Status:** 🔴 Missing

**Gap**
- Response schemas do not include metadata about the selected sector taxonomy and hierarchy level.
- Documentation does not provide NACE-mode request/response examples.

---

### #20 — Aggiornare i test per coprire la modalità NACE
**Status:** 🟡 Partial

**What exists now**
- There are NACE-related unit tests in `app/test.py` (e.g., checks on `nace_code` and `get_sector_from_occupation(..., level="nace_code")`).

**Gap**
- Coverage is not complete for hierarchical NACE modes (because those modes are not implemented yet).
- Test discovery is non-standard (`pytest -q` currently reports no tests run), so CI quality gates are weak.

---

## Proposed implementation order (aligned to dependencies)
1. **Issue #16 first**: add NACE hierarchy resolver and API-selectable level.
2. **Issue #17**: add dual-system request parameter and service wiring.
3. **Issue #18**: update aggregation + dashboard client payload/UI switch.
4. **Issue #19**: update schemas and docs once payload is stable.
5. **Issue #20**: finalize tests for all new branches and ensure discoverability in CI.

Issue #15 can be considered already implemented functionally; issue #14 becomes fully done when #17 wiring is complete.

---

## Suggested acceptance checks (quick)
- API request with `sector_system=isco` and `sector_system=nace` returns coherent but different sector keys.
- NACE level switch changes aggregation granularity deterministically.
- Response includes explicit metadata (`sector_system`, `sector_level`) for auditability.
- CI runs tests automatically and includes at least one integration test per sector mode.
