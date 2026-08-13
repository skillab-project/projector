# Implementation Note

Sector resolution currently supports two systems:

- ISCO: `job -> occupation -> isco_group`
- NACE: `job -> occupation -> ESCO-NACE crosswalk -> NACE code/title`

NACE allows one occupation to map to multiple sectors. This is intentional for skill-sector relationship discovery and should not be interpreted as strict one-to-one job accounting.
