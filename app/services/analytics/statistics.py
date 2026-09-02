"""Reusable statistical helpers for Projector comparison endpoints."""

from math import erfc, sqrt
from typing import Literal, Optional


ComparisonType = Literal[
    "temporal",
    "sector_skill",
    "regional_skill",
    "regional_sector",
    "sector_evolution",
    "generic",
]


METHOD_DESCRIPTION = (
    "2x2 chi-square test on observed counts. It checks whether two observed shares differ "
    "more than expected under an independence baseline. It does not prove causality, shortage, "
    "or future demand."
)


ASSUMPTIONS = [
    "Each observation contributes independently to the compared groups.",
    "Counts represent the same event definition in both groups.",
    "The comparison is descriptive/inferential over observed data, not a causal estimate.",
]


LIMITATIONS = [
    "The test is sensitive to sample size: very large samples can make small differences significant.",
    "Low expected cell counts make chi-square evidence less reliable.",
    "The result does not adjust for multiple comparisons.",
]


def run_statistical_comparison(
    comparison_type: ComparisonType,
    group_a_label: str,
    group_a_count: int,
    group_a_total: int,
    group_b_label: str,
    group_b_count: int,
    group_b_total: int,
    alpha: float = 0.05,
):
    a_absent = max(group_a_total - group_a_count, 0)
    b_absent = max(group_b_total - group_b_count, 0)
    observed_counts = [
        [group_a_count, a_absent],
        [group_b_count, b_absent],
    ]
    row_totals = [sum(row) for row in observed_counts]
    col_totals = [
        observed_counts[0][0] + observed_counts[1][0],
        observed_counts[0][1] + observed_counts[1][1],
    ]
    grand_total = sum(row_totals)
    warnings = []

    if grand_total == 0:
        expected_counts = [[0.0, 0.0], [0.0, 0.0]]
        statistic = 0.0
        p_value = 1.0
        warnings.append("No observations available for statistical comparison.")
    else:
        expected_counts = [
            [
                round(row_total * col_total / grand_total, 4)
                for col_total in col_totals
            ]
            for row_total in row_totals
        ]
        statistic = _chi_square_statistic(observed_counts, expected_counts)
        p_value = round(erfc(sqrt(statistic / 2)), 6)

    minimum_expected_count = min(value for row in expected_counts for value in row)
    if minimum_expected_count < 5:
        warnings.append("At least one expected cell count is below 5; interpret the test cautiously.")
    if 0 < grand_total < 30:
        warnings.append("Total observations are below 30; treat the result as weak evidence.")
    if _is_imbalanced(group_a_total, group_b_total):
        warnings.append("Group totals are highly imbalanced; compare shares more carefully than raw counts.")

    group_a_share = round(group_a_count / group_a_total, 4) if group_a_total else 0.0
    group_b_share = round(group_b_count / group_b_total, 4) if group_b_total else 0.0
    share_difference = round(group_a_share - group_b_share, 4)
    share_difference_percentage_points = round(share_difference * 100, 2)
    relative_risk = _safe_ratio(group_a_share, group_b_share)
    odds_ratio = _odds_ratio(group_a_count, a_absent, group_b_count, b_absent)
    if relative_risk is None:
        warnings.append("Relative risk is not computable because the comparison share is zero.")
    if odds_ratio is None:
        warnings.append("Odds ratio is not computable because at least one odds cell is zero.")

    effect_size = round(sqrt(statistic / grand_total), 4) if grand_total else 0.0
    practical_relevance = _effect_label(effect_size)
    significant = p_value < alpha
    evidence_level = _evidence_level(p_value, alpha)
    interpretation = _interpret_result(
        alpha=alpha,
        effect_label=practical_relevance,
        evidence_level=evidence_level,
        group_a_label=group_a_label,
        group_a_share=group_a_share,
        group_b_label=group_b_label,
        group_b_share=group_b_share,
        significant=significant,
    )

    return {
        "status": "completed",
        "comparison_type": comparison_type,
        "comparison_question": _comparison_question(comparison_type, group_a_label, group_b_label),
        "method": "chi_square_2x2",
        "method_description": METHOD_DESCRIPTION,
        "alpha": alpha,
        "significant": significant,
        "statistic": statistic,
        "p_value": p_value,
        "effect_size": effect_size,
        "effect_size_label": practical_relevance,
        "practical_relevance": practical_relevance,
        "evidence_level": evidence_level,
        "interpretation": interpretation,
        "groups": [
            {
                "label": group_a_label,
                "count": group_a_count,
                "total": group_a_total,
                "share": group_a_share,
            },
            {
                "label": group_b_label,
                "count": group_b_count,
                "total": group_b_total,
                "share": group_b_share,
            },
        ],
        "group_a_share": group_a_share,
        "group_b_share": group_b_share,
        "share_difference": share_difference,
        "share_difference_percentage_points": share_difference_percentage_points,
        "relative_risk": relative_risk,
        "odds_ratio": odds_ratio,
        "degrees_of_freedom": 1,
        "minimum_expected_count": round(minimum_expected_count, 4),
        "observed_table": _table(
            group_a_label,
            group_a_count,
            a_absent,
            group_a_total,
            group_a_share,
            group_b_label,
            group_b_count,
            b_absent,
            group_b_total,
            group_b_share,
        ),
        "expected_counts": expected_counts,
        "expected_table": _expected_table(group_a_label, group_b_label, expected_counts),
        "assumptions": ASSUMPTIONS,
        "limitations": LIMITATIONS,
        "warnings": warnings,
    }


def _chi_square_statistic(
    observed_counts: list[list[int]],
    expected_counts: list[list[float]],
) -> float:
    statistic = 0.0
    for row_idx, row in enumerate(observed_counts):
        for col_idx, value in enumerate(row):
            expected_value = expected_counts[row_idx][col_idx]
            if expected_value > 0:
                statistic += ((value - expected_value) ** 2) / expected_value
    return round(statistic, 4)


def _safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _odds_ratio(
    a_present: int,
    a_absent: int,
    b_present: int,
    b_absent: int,
) -> Optional[float]:
    if a_absent == 0 or b_absent == 0 or b_present == 0:
        return None
    return round((a_present / a_absent) / (b_present / b_absent), 4)


def _is_imbalanced(group_a_total: int, group_b_total: int) -> bool:
    smaller = min(group_a_total, group_b_total)
    larger = max(group_a_total, group_b_total)
    return smaller > 0 and larger / smaller >= 10


def _effect_label(effect_size: float) -> str:
    if effect_size < 0.1:
        return "negligible"
    if effect_size < 0.3:
        return "small"
    if effect_size < 0.5:
        return "medium"
    return "large"


def _evidence_level(p_value: float, alpha: float) -> str:
    if p_value >= alpha:
        return "none"
    if p_value < 0.001:
        return "strong"
    if p_value < 0.01:
        return "moderate"
    return "weak"


def _interpret_result(
    alpha: float,
    effect_label: str,
    evidence_level: str,
    group_a_label: str,
    group_a_share: float,
    group_b_label: str,
    group_b_share: float,
    significant: bool,
) -> str:
    direction = group_a_label if group_a_share >= group_b_share else group_b_label
    if significant:
        return (
            f"Observed difference is statistically significant at alpha={alpha}; "
            f"{direction} has the higher observed share. Evidence level is {evidence_level} "
            f"and practical relevance is {effect_label}."
        )
    return (
        f"Observed difference is not statistically significant at alpha={alpha}. "
        f"Evidence level is {evidence_level} and practical relevance is {effect_label}."
    )


def _comparison_question(comparison_type: ComparisonType, group_a_label: str, group_b_label: str) -> str:
    templates = {
        "temporal": "Did the observed share change between the two periods?",
        "sector_skill": "Is the selected skill more concentrated in one sector than the other?",
        "regional_skill": "Is the selected skill over-represented in one region relative to the comparison group?",
        "regional_sector": "Is the selected sector over-represented in one region relative to the comparison group?",
        "sector_evolution": "Did the observed sector share change between the two years?",
        "generic": "Do the two observed groups have different shares?",
    }
    return f"{templates.get(comparison_type, templates['generic'])} ({group_a_label} vs {group_b_label})"


def _table(
    group_a_label: str,
    group_a_count: int,
    a_absent: int,
    group_a_total: int,
    group_a_share: float,
    group_b_label: str,
    group_b_count: int,
    b_absent: int,
    group_b_total: int,
    group_b_share: float,
) -> dict:
    return {
        "columns": ["group", "present", "absent", "total", "share"],
        "rows": [
            {
                "group": group_a_label,
                "present": group_a_count,
                "absent": a_absent,
                "total": group_a_total,
                "share": group_a_share,
            },
            {
                "group": group_b_label,
                "present": group_b_count,
                "absent": b_absent,
                "total": group_b_total,
                "share": group_b_share,
            },
        ],
    }


def _expected_table(group_a_label: str, group_b_label: str, expected_counts: list[list[float]]) -> dict:
    return {
        "columns": ["group", "expected_present", "expected_absent"],
        "rows": [
            {
                "group": group_a_label,
                "expected_present": expected_counts[0][0],
                "expected_absent": expected_counts[0][1],
            },
            {
                "group": group_b_label,
                "expected_present": expected_counts[1][0],
                "expected_absent": expected_counts[1][1],
            },
        ],
    }
