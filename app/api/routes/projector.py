from typing import Optional, List, Literal
from fastapi import APIRouter
from fastapi import Form

from app.schemas.responses import EmergingSkillsResponse, ProjectorResponse, StopResponse
from app.core.container import service

router = APIRouter(prefix="/projector", tags=["Projector"])


@router.post("/emerging-skills", response_model=EmergingSkillsResponse)
async def emerging_skills(min_date: str = Form(...), max_date: str = Form(...),
                          keywords: Optional[List[str]] = Form(None)):
    """
       Computes emerging and declining skill trends over a time period.

       The analysis splits the time window into two segments:
           - Period A (past)
           - Period B (recent)

       It then computes growth rates to identify:
           - Emerging skills (increasing demand)
           - Declining skills (decreasing demand)
           - New entries (not present in previous period)

       Args:
           min_date (str): Start date (YYYY-MM-DD).
           max_date (str): End date (YYYY-MM-DD).

       Returns:
           EmergingSkillsResponse:
               - market_health (global trend)
               - trends (per-skill analysis)

       Key Metric:
           Growth % = (B - A) / A * 100
       """
    return await service.emerging_skills(min_date, max_date,
                                 keywords)


@router.post("/analyze-skills", response_model=ProjectorResponse)
async def analyze_skills(
        keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        min_date: str = Form(...),
        max_date: str = Form(...),
        page: int = Form(1),
        page_size: int = Form(50),
        demo: bool = Form(False),
        include_sectoral: bool = Form(False),
        sector_level: Literal["isco_group", "nace_code", "nace_division", "nace_group", "nace_class"] = Form("isco_group"),
        skill_group_level: int = Form(1),
        occupation_level: int = Form(1),
):
    """
       Executes a full labor market analysis based on user-defined filters.

       This endpoint orchestrates the entire pipeline:
           1. Fetch job postings from Tracker API
           2. Enrich skills and sectors
           3. Compute aggregated statistics
           4. Generate structured insights

       Args:
           keywords (List[str], optional): Search keywords for job filtering.
           min_date (str, optional): Start date (YYYY-MM-DD).
           max_date (str, optional): End date (YYYY-MM-DD).
           location_code (str, optional): Geographic filter (ISO/NUTS).
           occupation_ids (List[str], optional): Sector filter (ESCO).
           sector_level (str, optional): Sector taxonomy level. Supported values:
               `isco_group`, `nace_code`, `nace_division`, `nace_group`, `nace_class`.

       Returns:
           ProjectorResponse:
               - status
               - dimension_summary
               - insights (skills, employers, job titles, etc.)

       Notes:
           - Supports large-scale analysis (tens of thousands of jobs)
           - Uses caching for performance
           - Can be interrupted via `/projector/stop`
       """

    return await service.analyze_skills(keywords,
                                 locations,
                                 min_date,
                                 max_date,
                                 page,
                                 page_size,
                                 demo,
                                 include_sectoral,
                                 sector_level,
                                 skill_group_level,
                                 occupation_level)


@router.post("/stop", response_model=StopResponse)
async def stop():
    """
        Sends a stop signal to interrupt ongoing analysis tasks.

        This endpoint triggers a cooperative stop mechanism in the engine.
        The running process will terminate at the next safe checkpoint.

        Returns:
            dict:
                {"status": "stopping"}

        Notes:
            - Does not immediately kill execution
            - Safe for long-running operations
    """

    return service.stop()
