# D3.3 code compliance matrix

The delivered D3.3 is a frozen specification. This matrix tracks whether every promised workflow, output, metric, and mathematical rule is available from the existing API without client-side derivation.

Status values are `implemented`, `partial`, and `missing`. A row may be marked `implemented` only when the referenced contract test passes.

| D3 reference | Verifiable requirement | Formula or rule | Endpoint | Response field | Contract test | Status |
|---|---|---|---|---|---|---|
| CS1 | Jobs analyzed, skill ranking, frequency, market health | Absolute job and per-skill counts | `/analyze-skills` | `dimension_summary.jobs_analyzed`, `insights.ranking`, `insights.trends.market_health` | Existing analyze-skills contract tests | implemented |
| CS1 | Global share of every skill | `frequency / jobs_analyzed`, or `0.0` when denominator is zero | `/analyze-skills` | `insights.ranking[].share` | `test_d33_cs01_global_skill_ranking_share_and_one_count_per_job` | implemented |
| CS2 | Emerging, declining, stable, and percentage growth | `(B - A) / A * 100`; preserve `new_entry` when `A = 0 < B` | `/emerging-skills` | `insights.trends[].growth`, `trend_type` | `test_d33_cs02_trends_expose_counts_delta_and_classification` | implemented |
| CS2 | Previous/current counts and delta | `delta = current_count - previous_count` | `/emerging-skills` | `previous_count`, `current_count`, `delta` | `test_d33_cs02_trends_expose_counts_delta_and_classification` | implemented |
| CS2 | Explicit, non-overlapping A/B windows | Legacy window or all four A/B fields; `period_a_max_date < period_b_min_date` | `/emerging-skills` | Request fields `period_a_*`, `period_b_*` | `test_d33_cs14_explicit_period_contract_and_legacy_split_are_disjoint` | implemented |
| CS3 | Job-title and employer counts | Absolute posting counts | `/analyze-skills` | `insights.job_titles[].count`, `insights.employers[].count` | Existing analyze-skills contract tests | implemented |
| CS3 | Job-title and employer shares | `count / jobs_analyzed`, or `0.0` when denominator is zero | `/analyze-skills` | `insights.job_titles[].share`, `insights.employers[].share` | `test_d33_cs03_job_title_and_employer_shares_use_jobs_analyzed` | implemented |
| CS4 | Regional counts, market share, and skills | Regional job counts and existing percentage market share | `/analyze-skills` | `insights.regional.*[]` | Existing regional contract tests | implemented |
| CS5 | Raw/NUTS1/NUTS2/NUTS3 projections and specialization | `regional_share / baseline_share` | `/analyze-skills` | `insights.regional.raw`, `nuts1`, `nuts2`, `nuts3` | `test_d33_cs04_regional_output_exposes_share_baseline_and_specialization` | implemented |
| CS5 | Regional skill share and global baseline | `skill_count / regional_jobs`; `global_skill_count / total_jobs` | `/analyze-skills` | `top_skills[].share`, `baseline_share` | `test_d33_cs04_regional_output_exposes_share_baseline_and_specialization` | implemented |
| CS6 | Compare regional volume, share, rank, and specialization | Existing regional share remains percent; baseline is a `0..1` fraction | `/compare-regions` | `top_skills[].baseline_share`, `comparison.skills[].baseline_share` | `test_d33_cs06_region_comparison_exposes_combined_baseline` | implemented |
| CS6 | Combined skill, time window, and NUTS-level workflow | `region_level in {raw,nuts1,nuts2,nuts3}` | `/skill-explorer` | `region_level`, `regions[]` | `test_d33_cs05_skill_explorer_combines_skill_time_and_nuts_level` | implemented |
| CS7 | Tracker sectors, sector-skill co-occurrence, intensity, dominant skills | A skill contributes at most once per job-sector pair | `/sectoral-intelligence` | `items[].observed_skills`, `skill_transversal_insights` | `test_d33_cs07_sector_skill_cooccurrences_deduplicate_and_keep_fallback_sector` | implemented |
| §§3.1.3/4.2.9 | Preserve jobs with no sector | Assign `Sector not specified`; with a filter include it only when explicitly selected | `/sectoral-snapshot`, `/sectoral-intelligence` | `sectors[].sector`, sectoral item labels | `test_d33_cs08_annual_snapshot_contains_portfolio_titles_and_metadata` | implemented |
| CS8 | Annual snapshots, shares, unique skills, portfolio, titles, metadata | Existing annual aggregation contract | `/sectoral-snapshot` | `sectors[]` | `test_d33_cs08_annual_snapshot_contains_portfolio_titles_and_metadata` | implemented |
| CS9/CS14 | Job delta, growth, new/disappeared/growing/declining skills, churn | Existing evolution formulas | `/sectoral-snapshot` | `sectors[].evolution` | `test_d33_cs09_snapshot_evolution_reports_delta_growth_and_churn` | implemented |
| CS10 | Sector-skill matrix with count/share/rank/growth | Share by sector skill mentions; `rank_score = 1 / rank` | `/sector-skills-comparison` | `matrix[].count`, `share`, `rank`, `growth` | `test_d33_cs10_sector_skill_matrix_has_count_share_rank_and_growth` | implemented |
| CS11 | Portfolio count, share, rank, growth | Existing snapshot enrichment | `/sectoral-snapshot` | `all_skills[]`, `top_skills[]` | `test_d33_cs11_persisted_portfolio_is_enriched_with_rank_score_without_migration` | implemented |
| CS11 | Portfolio rank score | `rank_score = 1 / rank` | `/sectoral-snapshot` | `all_skills[].rank_score`, `top_skills[].rank_score` | `test_d33_cs11_persisted_portfolio_is_enriched_with_rank_score_without_migration` | implemented |
| CS12 | Sector job titles and counts | Absolute title counts by sector | `/sectoral-snapshot` | `top_job_titles[].count` | Existing sector snapshot contract tests | implemented |
| CS12 | Job-title share inside sector | `title_count / sector_job_count`, or `0.0` when denominator is zero | `/sectoral-snapshot` | `top_job_titles[].share` | `test_d33_cs12_persisted_sector_titles_receive_share_and_zero_denominator_guard` | implemented |
| CS13 | Growth, volume growth, trend class, and context | Existing percentage growth semantics | `/emerging-skills` | `market_health`, `trends[]` | Existing emerging-skills contract tests | implemented |
| CS13 | Explicit new-entry indicator | `previous_count = 0 and current_count > 0` | `/emerging-skills` | `trends[].is_new_entry` | `test_d33_cs13_new_entry_is_explicit_and_preserves_growth_sentinel` | implemented |
| §3.1.4 | Skill explorer across sectors, regions, and time | Aggregate selected skill at requested territorial level | `/skill-explorer` | `sectors[]`, `regions[]`, `time_series[]`, `region_level` | `test_d33_cs05_skill_explorer_combines_skill_time_and_nuts_level` | implemented |
| §3.2/4.3 | Time series and `last_delta` forecast baseline | Existing last-delta baseline | `/temporal-projections` | `insights.periods`, `skills[].forecast` | Existing temporal projection contract tests | implemented |
| Traceability | Chi-square, p-value, effect size, RR, OR, tables, warnings | Existing statistical comparison contract | `/statistical-comparison` | Statistical evidence fields | Existing statistical comparison contract tests | implemented |
| §6 | Health, readiness, validation, cache, cooperative stop | Existing operational contracts | `/health`, `/readiness`, `/stop`, task endpoints | Operational status fields | Existing health/readiness/task-manager tests | implemented |
| Formulas §§3–4 | One skill counts at most once per job | Normalize, trim, and deduplicate skill IDs before aggregation | All analytical endpoints | All skill counts | `test_d33_cs01_global_skill_ranking_share_and_one_count_per_job`, `test_d33_cs07_sector_skill_cooccurrences_deduplicate_and_keep_fallback_sector`, `test_d33_snapshot_skill_explorer_does_not_double_count_multi_sector_jobs` | implemented |
| Trend split | Implicit periods A and B are disjoint | `B.start = A.end + 1 day` | `/emerging-skills` | Internal request windows | `test_d33_cs14_explicit_period_contract_and_legacy_split_are_disjoint` | implemented |

## Change tracking

- D3-01: [issue #105](https://github.com/skillab-project/projector/issues/105)
- D3-02: [issue #110](https://github.com/skillab-project/projector/issues/110)
- D3-03: [issue #108](https://github.com/skillab-project/projector/issues/108)
- D3-04: [issue #112](https://github.com/skillab-project/projector/issues/112)
- D3-05: [issue #113](https://github.com/skillab-project/projector/issues/113)
- D3-06: [issue #107](https://github.com/skillab-project/projector/issues/107)
- D3-07: [issue #109](https://github.com/skillab-project/projector/issues/109)
- D3-08: [issue #111](https://github.com/skillab-project/projector/issues/111)
- D3-09: [issue #106](https://github.com/skillab-project/projector/issues/106)
