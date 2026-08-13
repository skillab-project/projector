# Historical Note: GitHub Issues #14 to #20

Date of original analysis: 2026-04-18

This file is retained as historical sprint context. It no longer represents the current implementation status.

## Current Status Summary

The current `app/` implementation now includes the main NACE/ISCO alignment work that this note originally identified as missing:

- API fields exist for `sector_system`, `sector_level`, `skill_group_level` and `occupation_level`.
- `/projector/analyze-skills` can build ISCO and NACE sectoral views when `include_sectoral=true`.
- NACE hierarchy levels are supported for `nace_section`, `nace_division`, `nace_group` and `nace_class`.
- The response schema includes `sectoral`, `sectoral_mode`, `sectoral_views` and `sector_view_names`.
- The dashboard reads `sectoral_views` and lets the user switch ISCO/NACE and NACE levels.
- NACE labels and mappings prefer the ESCO-NACE rev. 2.1 crosswalk, with CSV fallback support.

## Remaining Useful Checks

The following checks are still relevant:

- Add or improve automated tests for all NACE levels.
- Ensure `pytest` discovers tests consistently.
- Add coverage reporting for occupations without NACE mappings.
- Keep documenting that NACE is relation-oriented and may duplicate skill evidence across multiple NACE sectors.

## Current Acceptance Criteria

- `sector_system=isco` returns ISCO sectoral data.
- `sector_system=nace` returns the selected NACE level in `insights.sectoral`.
- `sector_system=both` returns ISCO in `insights.sectoral` for backward compatibility and both systems in `insights.sectoral_views`.
- NACE level switching changes aggregation granularity.
- The response includes explicit sectoral metadata.
