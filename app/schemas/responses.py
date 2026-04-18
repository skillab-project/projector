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


class SectorGroupSummary(BaseModel):
    total_group_mentions: float
    unique_groups: int
    top_groups: List[SkillGroupEntry]


class SectoralSectorItem(BaseModel):
    sector: str
    sector_label: str
    observed_skills: SectorSkillSummary
    canonical_skills: SectorSkillSummary
    observed_groups: SectorGroupSummary
    canonical_groups: SectorGroupSummary
    matrix_groups: SectorGroupSummary


class SectoralView(BaseModel):
    sector_level: str
    items: List[SectoralSectorItem]


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
        description="Sectoral intelligence combining observed, canonical, and official ESCO matrix profiles"
    )
    sectoral_mode: Optional[Literal["isco", "nace", "both"]] = Field(
        default=None,
        description="Selected sector segmentation mode for the response payload."
    )
    sectoral_views: Optional[dict[Literal["isco", "nace"], SectoralView | NaceSectoralViews]] = Field(
        default=None,
        description="Dual sectoral payloads for ISCO and NACE segmentation modes. NACE includes all hierarchy levels."
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
