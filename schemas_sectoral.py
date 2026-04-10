from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class SkillRankingItem(BaseModel):
    name: str = Field(..., description="The readable label of the skill (e.g., Python)")
    count: int = Field(..., description="Absolute number of occurrences in the analyzed jobs")
    frequency: float = Field(..., description="Percentage of jobs requiring this skill relative to the total batch")
    is_digital: bool = Field(..., description="Twin Transition tag: identifies if the skill is related to digital transformation")
    is_green: bool = Field(..., description="Twin Transition tag: identifies if the skill is related to sustainability/green economy")
    primary_sector: Optional[str] = Field(None, description="The most frequent sector associated with this skill")


class MarketHealth(BaseModel):
    status: str = Field(..., description="Overall market dynamic (e.g., expanding, stable, contracting)")
    volume_growth_percentage: float = Field(..., description="Percentage change in job posting volume compared to the previous period")


class TrendItem(BaseModel):
    name: str = Field(..., description="Name of the skill being analyzed for trends")
    trend_type: str = Field(..., description="Categorization: emerging, declining or stable")
    growth: Any = Field(..., description="Growth velocity. Can be a percentage or new_entry")


class TrendsContainer(BaseModel):
    market_health: MarketHealth = Field(..., description="High-level market indicator")
    trends: List[TrendItem] = Field(..., description="Detailed list of skills showing significant market movement")


class RegionalSkill(BaseModel):
    skill: str = Field(..., description="Name of the skill")
    count: int = Field(..., description="Number of occurrences within this specific geographic area")
    specialization: float = Field(..., description="Location quotient for the skill in the area")


class RegionalArea(BaseModel):
    code: str = Field(..., description="Geographic identifier")
    total_jobs: int = Field(..., description="Total job postings identified in this specific area")
    market_share: float = Field(..., description="Percentage of total jobs located in this area")
    top_skills: List[RegionalSkill] = Field(..., description="Most relevant skills for this territory")


class RegionalProjections(BaseModel):
    raw: List[RegionalArea]
    nuts1: List[RegionalArea]
    nuts2: List[RegionalArea]
    nuts3: List[RegionalArea]


class SectoralSkill(BaseModel):
    name: str = Field(..., description="Readable skill label")
    count: float = Field(..., description="Observed or weighted count")
    frequency: float = Field(..., description="Relative frequency inside the sector")
    is_digital: bool = Field(..., description="Twin Transition digital tag")
    is_green: bool = Field(..., description="Twin Transition green tag")
    skill_group: Optional[str] = Field(None, description="ESCO skill group label at the selected hierarchy level")


class SectoralArea(BaseModel):
    sector_code: str = Field(..., description="Selected occupation hierarchy group URI or code")
    sector_label: str = Field(..., description="Readable sector label derived from the occupation hierarchy")
    total_jobs: int = Field(..., description="How many jobs contributed to this sector profile")
    market_share: float = Field(..., description="Percentage of analyzed jobs touching this sector")
    top_observed_skills: List[SectoralSkill] = Field(..., description="Skills observed in tracker jobs for this sector")
    top_canonical_skills: List[SectoralSkill] = Field(..., description="Skills linked to occupations in ESCO CSV relations")
    observed_skill_groups: List[Dict[str, Any]] = Field(..., description="Observed ESCO skill-group distribution for this sector")
    matrix_skill_groups: List[Dict[str, Any]] = Field(..., description="Official ESCO matrix profile for the selected occupation group")
    twin_transition_summary: Dict[str, Any] = Field(..., description="Shares of digital and green skills")
    alignment_score: Optional[float] = Field(None, description="Cosine similarity between observed and matrix skill-group profiles")
    sample_occupations: List[Dict[str, Any]] = Field(..., description="Most common occupations contributing to the sector")


class SectoralProjections(BaseModel):
    occupation_level: int = Field(..., description="Selected ISCO hierarchy level used as sector definition")
    skill_group_level: int = Field(..., description="Selected ESCO skill hierarchy level used for grouped profiles")
    sectors: List[SectoralArea] = Field(..., description="Sectoral intelligence profiles")


class DimensionSummary(BaseModel):
    jobs_analyzed: int = Field(..., description="The total number of job postings processed in this analysis")
    geo_breakdown: List[Dict[str, Any]] = Field(..., description="Distribution of job postings by country of origin")


class ProjectorInsights(BaseModel):
    ranking: List[SkillRankingItem]
    sectors: List[Dict[str, Any]]
    job_titles: List[Dict[str, Any]]
    employers: List[Dict[str, Any]]
    trends: TrendsContainer
    regional: RegionalProjections
    sectoral: Optional[SectoralProjections] = None


class ProjectorResponse(BaseModel):
    status: str = Field(..., description="Process status: completed or stopped")
    dimension_summary: DimensionSummary
    insights: ProjectorInsights
