from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union

# --- 1. SKILL RANKING & TWIN TRANSITION ---
class SkillRankingItem(BaseModel):
    name: str = Field(..., description="The readable label of the skill (e.g., Python)")
    count: int = Field(..., description="Absolute number of occurrences in the analyzed jobs")
    frequency: float = Field(..., description="Percentage of jobs requiring this skill relative to the total batch")
    is_digital: bool = Field(..., description="Twin Transition tag: identifies if the skill is related to digital transformation")
    is_green: bool = Field(..., description="Twin Transition tag: identifies if the skill is related to sustainability/green economy")
    primary_sector: Optional[str] = Field(None, description="The most frequent ESCO sector associated with this skill")

# --- 2. MARKET TRENDS & HEALTH ---
class MarketHealth(BaseModel):
    status: str = Field(..., description="Overall market dynamic (e.g., 'expanding', 'stable', 'contracting')")
    volume_growth_percentage: float = Field(..., description="Percentage change in job posting volume compared to the previous period")

class TrendItem(BaseModel):
    name: str = Field(..., description="Name of the skill being analyzed for trends")
    trend_type: str = Field(..., description="Categorization: 'emerging' (growing demand) or 'declining' (falling demand)")
    growth: Any = Field(..., description="Growth velocity. Can be a percentage (float) or 'new_entry' for skills with no prior data")

class TrendsContainer(BaseModel):
    market_health: MarketHealth = Field(..., description="High-level macroeconomic indicators of the analyzed batch")
    trends: List[TrendItem] = Field(..., description="Detailed list of skills showing significant market movement")

# --- 3. TASK 3.5 REGIONAL DECOMPOSITION (NUTS) ---
class RegionalSkill(BaseModel):
    skill: str = Field(..., description="Name of the skill")
    count: int = Field(..., description="Number of occurrences within this specific geographic area")
    specialization: float = Field(..., description="Location Quotient (LQ). Values > 1.0 indicate that the skill is more concentrated in this region than the national average.")

class RegionalArea(BaseModel):
    code: str = Field(..., description="Geographic identifier (e.g., Country ISO code or NUTS 1/2/3 code)")
    total_jobs: int = Field(..., description="Total job postings identified in this specific area")
    market_share: float = Field(..., description="The percentage of the total job batch located in this area")
    top_skills: List[RegionalSkill] = Field(..., description="List of most relevant skills for this territory, weighted by specialization")

class RegionalProjections(BaseModel):
    raw: List[RegionalArea] = Field(..., description="Data grouped by original location codes as stored in the database")
    nuts1: List[RegionalArea] = Field(..., description="Task 3.5: Socio-economic projections at Macro-region level")
    nuts2: List[RegionalArea] = Field(..., description="Task 3.5: Socio-economic projections at Regional level")
    nuts3: List[RegionalArea] = Field(..., description="Task 3.5: Socio-economic projections at Provincial/Small area level")

# --- 4. GLOBAL RESPONSE SCHEMA ---
class DimensionSummary(BaseModel):
    jobs_analyzed: int = Field(..., description="The total number of job postings processed in this analysis")
    geo_breakdown: List[Dict[str, Any]] = Field(..., description="Distribution of job postings by country of origin")

class ProjectorInsights(BaseModel):
    ranking: List[SkillRankingItem] = Field(..., description="List of top skills filtered by the current view/page")
    sectors: List[Dict[str, Any]] = Field(..., description="Distribution of demand across ESCO Macro-sectors")
    job_titles: List[Dict[str, Any]] = Field(..., description="Frequency of actual job titles as written by employers")
    employers: List[Dict[str, Any]] = Field(..., description="Ranking of companies with the highest hiring volume")
    trends: TrendsContainer = Field(..., description="Analysis of emerging and declining skills over time")
    regional: RegionalProjections = Field(..., description="Task 3.5: Granular geographic decomposition and specialization analysis")

class ProjectorResponse(BaseModel):
    """Official Data Contract for the SKILLAB Projector Intelligence API"""
    status: str = Field(..., description="Process status: 'completed' or 'stopped' if manually interrupted")
    dimension_summary: DimensionSummary = Field(..., description="Batch context and volume indicators")
    insights: ProjectorInsights = Field(..., description="The core intelligence data containing rankings, regionality, and trends")