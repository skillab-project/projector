from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal


# -----------------------------
# Shared simple items
# -----------------------------
class CountItem(BaseModel):
    name: str = Field(..., description="Display label shown in rankings or aggregates.")
    count: int = Field(..., description="Absolute number of occurrences in the analyzed batch.")


class GeoBreakdownItem(BaseModel):
    location: str = Field(..., description="Original location code found in the Tracker data (e.g. country ISO code).")
    job_count: int = Field(..., description="Number of job postings associated with this location.")


# -----------------------------
# Analyze-skills ranking models
# -----------------------------
class SkillRankingItem(BaseModel):
    name: str = Field(..., description="Human-readable skill label.")
    frequency: int = Field(..., description="Absolute number of times this skill appears in the analyzed postings.")
    skill_id: str = Field(..., description="Original skill identifier/URI returned by the Tracker.")
    is_green: bool = Field(..., description="Heuristic Twin Transition flag for green/sustainability-related skills.")
    is_digital: bool = Field(..., description="Heuristic Twin Transition flag for digital/ICT-related skills.")
    sector_spread: int = Field(..., description="Number of distinct sectors in which the skill appears within the analyzed batch.")
    primary_sector: str = Field(..., description="Most frequent sector associated with this skill in the analyzed batch.")


# -----------------------------
# Trends models
# -----------------------------
class MarketHealth(BaseModel):
    status: str = Field(..., description="Overall market direction inferred from posting volume between the two compared periods.")
    volume_growth_percentage: float = Field(..., description="Percentage change in job-posting volume between the two compared periods.")


class TrendItem(BaseModel):
    name: str = Field(..., description="Human-readable skill label.")
    growth: Union[float, Literal["new_entry"]] = Field(
        ...,
        description="Growth rate of the skill between the two compared periods, or 'new_entry' when the skill did not exist in the earlier period."
    )
    trend_type: Literal["emerging", "declining", "stable"] = Field(
        ...,
        description="Trend classification derived from the growth value."
    )
    primary_sector: str = Field(..., description="Most frequent sector associated with the skill in the newer period.")
    is_green: bool = Field(..., description="Heuristic Twin Transition flag for green/sustainability-related skills.")
    is_digital: bool = Field(..., description="Heuristic Twin Transition flag for digital/ICT-related skills.")


class TrendsContainer(BaseModel):
    market_health: MarketHealth = Field(..., description="Macro-level trend of the analyzed labor-market slice.")
    trends: List[TrendItem] = Field(..., description="Skill-level trend items sorted by descending growth.")


class TemporalPeriodItem(BaseModel):
    period: str = Field(..., description="Period label in the selected granularity.")
    start_date: str = Field(..., description="First date included in the period.")
    end_date: str = Field(..., description="Last date included in the period.")
    job_count: int = Field(..., description="Number of postings uploaded in the period.")
    growth_vs_previous: Optional[Union[float, Literal["new_entry"]]] = Field(
        None,
        description="Job-count growth versus the previous period."
    )


class TemporalSkillSeriesItem(BaseModel):
    period: str
    start_date: str
    end_date: str
    count: int = Field(..., description="Skill mentions in the period.")
    share: float = Field(..., description="Skill mentions divided by period job count.")
    growth_vs_previous: Optional[Union[float, Literal["new_entry"]]] = None


class TemporalSkillForecastItem(BaseModel):
    period: str
    projected_count: float
    method: Literal["last_delta_baseline"]


class TemporalSkillProjectionItem(BaseModel):
    skill_id: str
    name: str
    total_count: int
    latest_count: int
    growth_rate: Optional[Union[float, Literal["new_entry"]]]
    trend_type: Literal["emerging", "declining", "stable"]
    is_green: bool
    is_digital: bool
    series: List[TemporalSkillSeriesItem]
    forecast: List[TemporalSkillForecastItem]


class TemporalProjectionsInsights(BaseModel):
    window: dict[str, str]
    granularity: Literal["monthly", "quarterly", "yearly"]
    forecast_method: Literal["last_delta_baseline"]
    periods: List[TemporalPeriodItem]
    skills: List[TemporalSkillProjectionItem]


class TemporalProjectionsResponse(BaseModel):
    status: str
    total_jobs: int
    insights: TemporalProjectionsInsights


class RegionalTemporalPeriodItem(BaseModel):
    period: str = Field(..., description="Period label in the selected granularity.")
    start_date: str = Field(..., description="First date included in the period.")
    end_date: str = Field(..., description="Last date included in the period.")
    job_count: int = Field(..., description="Number of postings for the region in the period.")
    growth_vs_previous: Optional[Union[float, Literal["new_entry"]]] = Field(
        None,
        description="Regional job-count growth versus the previous period."
    )


class RegionalTemporalSkillSeriesItem(BaseModel):
    period: str
    start_date: str
    end_date: str
    count: int = Field(..., description="Skill mentions in the region and period.")
    share: float = Field(..., description="Skill mentions divided by regional period jobs.")
    growth_vs_previous: Optional[Union[float, Literal["new_entry"]]] = None


class RegionalTemporalSkill(BaseModel):
    skill_id: str
    label: str
    total_count: int
    latest_count: int
    growth_rate: Optional[Union[float, Literal["new_entry"]]]
    trend_type: Literal["emerging", "declining", "stable"]
    specialization: float = Field(..., description="Location Quotient-like skill concentration score.")
    series: List[RegionalTemporalSkillSeriesItem]


class RegionalTemporalArea(BaseModel):
    code: str = Field(..., description="Original or inferred geographic code.")
    total_jobs: int = Field(..., description="Number of postings associated with the area.")
    market_share: float = Field(..., description="Percentage of analyzed postings represented by the area.")
    periods: List[RegionalTemporalPeriodItem]
    top_skills: List[RegionalTemporalSkill]


class RegionalTemporalProjections(BaseModel):
    raw: List[RegionalTemporalArea]
    nuts1: List[RegionalTemporalArea]
    nuts2: List[RegionalTemporalArea]
    nuts3: List[RegionalTemporalArea]


class RegionalTemporalResponse(BaseModel):
    status: str
    total_jobs: int
    window: dict[str, str]
    granularity: Literal["monthly", "quarterly", "yearly"]
    regional_temporal: RegionalTemporalProjections
    message: Optional[str] = None


class SkillExplorerSkill(BaseModel):
    skill_id: Optional[str] = None
    label: str
    match_type: Literal["skill_id", "skill_label"]


class SkillExplorerSector(BaseModel):
    sector: str
    sector_label: str
    count: int
    share: float


class SkillExplorerRegion(BaseModel):
    code: str
    count: int
    share: float
    specialization: Optional[float] = None


class SkillExplorerTimePoint(BaseModel):
    period: str
    count: int
    growth_vs_previous: Optional[Union[float, Literal["new_entry"]]] = None


class SkillExplorerResponse(BaseModel):
    status: str
    mode: Literal["snapshot", "live"]
    data_source: Literal["postgres", "cache", "live"]
    skill: Optional[SkillExplorerSkill] = None
    total_mentions: int
    sectors: List[SkillExplorerSector]
    regions: List[SkillExplorerRegion]
    time_series: List[SkillExplorerTimePoint]
    warnings: List[str] = Field(default_factory=list)
    message: Optional[str] = None


class StatisticalComparisonGroup(BaseModel):
    label: str
    count: int
    total: int
    share: float


class StatisticalComparisonResponse(BaseModel):
    status: str
    comparison_type: Literal[
        "temporal",
        "sector_skill",
        "regional_skill",
        "regional_sector",
        "sector_evolution",
        "generic",
    ]
    method: Literal["chi_square_2x2"]
    alpha: float
    significant: bool
    statistic: float
    p_value: float
    effect_size: float
    effect_size_label: str
    interpretation: str
    groups: List[StatisticalComparisonGroup]
    expected_counts: List[List[float]]
    warnings: List[str] = Field(default_factory=list)


# -----------------------------
# Regional projection models
# -----------------------------
class RegionalSkill(BaseModel):
    skill: str = Field(..., description="Human-readable skill label.")
    count: int = Field(..., description="Number of occurrences of the skill inside the specific geographic area.")
    specialization: float = Field(..., description="Location Quotient-like specialization score. Values above 1 generally indicate above-average local concentration.")


class RegionalArea(BaseModel):
    code: str = Field(..., description="Original or inferred geographic code (raw ISO-like code or NUTS-like code).")
    total_jobs: int = Field(..., description="Number of postings associated with the area.")
    market_share: float = Field(..., description="Percentage of the full analyzed batch represented by the area.")
    top_skills: List[RegionalSkill] = Field(..., description="Most relevant skills for the area, returned with counts and specialization values.")


class RegionalProjections(BaseModel):
    raw: List[RegionalArea] = Field(..., description="Aggregation by original location code stored in Tracker jobs.")
    nuts1: List[RegionalArea] = Field(..., description="Projected aggregation at NUTS1-like level.")
    nuts2: List[RegionalArea] = Field(..., description="Projected aggregation at NUTS2-like level.")
    nuts3: List[RegionalArea] = Field(..., description="Projected aggregation at NUTS3-like level.")


class RegionalSectorItem(BaseModel):
    sector: str = Field(..., description="Human-readable sector label.")
    sector_code: str = Field(..., description="Sector code or Tracker sector key used by the sectoral dimension.")
    count: int = Field(..., description="Number of postings in the geographic area associated with the sector.")
    share_in_region: float = Field(..., description="Percentage of area postings represented by this sector.")
    specialization: float = Field(..., description="Location Quotient-like score comparing area sector share with the full analyzed batch.")


class RegionalSectoralArea(BaseModel):
    code: str = Field(..., description="Original or inferred geographic code.")
    total_jobs: int = Field(..., description="Number of postings associated with the area.")
    top_sectors: List[RegionalSectorItem] = Field(..., description="Most represented sectors inside the area.")


class RegionalSectoralProjections(BaseModel):
    raw: List[RegionalSectoralArea] = Field(..., description="Sector distribution by original location code.")
    nuts1: List[RegionalSectoralArea] = Field(..., description="Sector distribution at NUTS1-like level.")
    nuts2: List[RegionalSectoralArea] = Field(..., description="Sector distribution at NUTS2-like level.")
    nuts3: List[RegionalSectoralArea] = Field(..., description="Sector distribution at NUTS3-like level.")


# -----------------------------
# Main endpoint response models
# -----------------------------
class DimensionSummary(BaseModel):
    jobs_analyzed: int = Field(..., description="Total number of job postings processed by the endpoint.")
    geo_breakdown: List[GeoBreakdownItem] = Field(..., description="Distribution of postings by original location code.")

class SkillEntry(BaseModel):
    skill_id: str
    count: int
    frequency: float
    label: Optional[str] = None
    is_green: Optional[bool] = None
    is_digital: Optional[bool] = None
    share_in_sector: Optional[float] = None
    rank: Optional[int] = None
    growth_vs_reference_year: Optional[Union[float, Literal["new_entry"]]] = None
    growth_value: Optional[float] = None
    sector_breadth: Optional[int] = None


class SkillGroupEntry(BaseModel):
    group_id: str
    group_label: str
    count: float
    frequency: float


class SectorSkillSummary(BaseModel):
    sector: str
    total_skill_mentions: int
    unique_skills: int
    top_skills: List[SkillEntry]
    all_skills: Optional[List[SkillEntry]] = None


class SectorGroupSummary(BaseModel):
    total_group_mentions: float
    unique_groups: int
    top_groups: List[SkillGroupEntry]


class SkillSectorShare(BaseModel):
    sector: str
    sector_label: str
    count: int
    share: float


class SkillTransversalInsight(BaseModel):
    skill_id: str
    label: str
    count: int
    importance_in_sector: float
    sector_breadth: int
    dominant_sector: str
    dominant_sector_label: str
    dominant_share: float
    top_sectors: List[SkillSectorShare]


class SectorMetrics(BaseModel):
    coverage_unique_skills: int
    dominance_top10_share: float


class IscoInterpretation(BaseModel):
    sector: str
    emerging_skills: List[str]
    missing_skills: List[str]
    stability_overlap: float
    observed_skill_count: int
    canonical_skill_count: int
    overlap_skill_count: int


class SectoralSectorItem(BaseModel):
    sector: str
    sector_label: str
    observed_skills: SectorSkillSummary
    observed_groups: SectorGroupSummary
    canonical_skills: Optional[SectorSkillSummary] = None
    canonical_groups: Optional[SectorGroupSummary] = None
    matrix_groups: Optional[SectorGroupSummary] = None
    sector_metrics: Optional[SectorMetrics] = None
    skill_transversal_insights: Optional[List[SkillTransversalInsight]] = None
    isco_interpretation: Optional[IscoInterpretation] = None


class SectoralView(BaseModel):
    sector_level: str
    items: List[SectoralSectorItem]
    time_mode: Optional[Literal["latest", "selected_period", "year", "comparison"]] = None
    window: Optional[dict[str, str]] = None
    snapshots: Optional[dict[str, dict]] = None
    comparison: Optional[dict] = None


class SectoralIntelligenceResponse(BaseModel):
    status: str
    mode: Literal["latest", "selected_period", "year", "comparison"]
    data_source: Literal["cache", "live"]
    sector_level: str
    window: dict[str, str]
    sector_filter: List[str] = Field(default_factory=list)
    items: List[SectoralSectorItem]
    snapshots: Optional[dict[str, dict]] = None
    comparison: Optional[dict] = None
    sector_view_names: dict[str, str]


class SectorSnapshotTitle(BaseModel):
    name: str
    count: int


class SectorEvolutionSkill(BaseModel):
    skill_id: str
    label: Optional[str] = None
    count: int
    reference_count: int
    delta: int


class SectorEvolution(BaseModel):
    reference_year: int
    job_count_current: int
    job_count_reference: int
    total_jobs_current: int
    total_jobs_reference: int
    job_delta: int
    job_growth_percentage: Union[float, Literal["new_entry"]]
    job_growth_value: float
    new_skill_count: int
    disappeared_skill_count: int
    growing_skill_count: int
    declining_skill_count: int
    skill_churn: float
    top_new_skills: List[SectorEvolutionSkill]
    top_disappeared_skills: List[SectorEvolutionSkill]
    top_growing_skills: List[SectorEvolutionSkill]
    top_declining_skills: List[SectorEvolutionSkill]


class SectorSnapshotRow(BaseModel):
    sector: str
    sector_label: str
    job_count: int
    job_share: float
    total_skill_mentions: int
    unique_skills: int
    evolution: Optional[SectorEvolution] = None
    top_skills: List[SkillEntry]
    all_skills: Optional[List[SkillEntry]] = None
    top_job_titles: List[SectorSnapshotTitle]


class SectoralSnapshotResponse(BaseModel):
    status: str
    year: int
    reference_year: Optional[int] = None
    data_source: Literal["postgres", "cache", "live"]
    window: dict[str, str]
    total_jobs: int
    sector_filter: List[str] = Field(default_factory=list)
    sectors: List[SectorSnapshotRow]
    message: Optional[str] = None


class SectorSkillComparisonCell(BaseModel):
    sector: str
    sector_label: str
    skill_id: str
    label: str
    count: int
    share: float
    rank: Optional[int] = None
    rank_score: float
    growth: Optional[Union[float, Literal["new_entry"]]] = None
    growth_value: Optional[float] = None
    value: float
    display_value: str
    is_green: Optional[bool] = None
    is_digital: Optional[bool] = None


class SectorSkillsComparisonResponse(BaseModel):
    status: str
    year: int
    reference_year: Optional[int] = None
    data_source: Literal["postgres", "cache", "live"]
    metric: Literal["count", "share", "rank", "growth"]
    window: dict[str, str]
    sectors: List[str]
    skills: List[str]
    matrix: List[SectorSkillComparisonCell]
    message: Optional[str] = None


class RegionalSectoralResponse(BaseModel):
    status: str
    year: int
    data_source: Literal["postgres", "cache", "live"]
    window: dict[str, str]
    refresh_status: Optional[dict] = None
    regional_sectoral: RegionalSectoralProjections
    message: Optional[str] = None


class NaceSectoralViews(BaseModel):
    selected_level: str
    levels: dict[str, SectoralView]


class ProjectorInsights(BaseModel):
    ranking: List[SkillRankingItem] = Field(..., description="Paginated list of enriched skill-ranking items.")
    sectors: List[CountItem] = Field(..., description="Top sectors found in the analyzed job batch.")
    job_titles: List[CountItem] = Field(..., description="Top job titles found in the analyzed job batch.")
    employers: List[CountItem] = Field(..., description="Top employers found in the analyzed job batch.")
    trends: TrendsContainer = Field(..., description="Trend analysis computed across two internal time slices of the requested date interval.")
    regional: Optional[RegionalProjections] = Field(
        None,
        description="Regional decomposition of the analyzed postings. Optional because the current no-data branch in main.py omits it."
    )
    sectoral: Optional[List[SectoralSectorItem]] = Field(
        default=None,
        description="Observed sectoral intelligence from Tracker job skills and sectors"
    )
    sectoral_mode: Optional[Literal["isco", "nace", "both"]] = Field(
        default=None,
        description="Compatibility field. Current runtime returns 'nace' for Tracker sector views."
    )
    sectoral_views: Optional[dict[Literal["isco", "nace"], SectoralView | NaceSectoralViews]] = Field(
        default=None,
        description="Sectoral payloads. Current runtime exposes the NACE key with Tracker sector labels."
    )
    sector_view_names: Optional[dict[str, dict[str, str]]] = Field(
        default=None,
        description="Display names for observed sectoral views."
    )


class ProjectorResponse(BaseModel):
    status: str = Field(..., description="Processing status. In current code it is typically 'completed' or 'stopped'.")
    dimension_summary: DimensionSummary = Field(..., description="Contextual counters for the analyzed batch.")
    insights: ProjectorInsights = Field(..., description="Main intelligence payload returned by /projector/analyze-skills.")


class EmergingSkillsResponse(BaseModel):
    status: str = Field(..., description="Processing status for the trend-only endpoint.")
    insights: TrendsContainer = Field(..., description="Trend-only payload returned by /projector/emerging-skills.")


class StopResponse(BaseModel):
    status: str = Field(..., description="Acknowledgement of the stop signal. In current code the value is 'signal_sent'.")
