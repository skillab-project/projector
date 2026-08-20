from datetime import date
from typing import Optional, List, Literal

from fastapi import APIRouter, HTTPException
from fastapi import Form

from app.schemas.responses import (
    EmergingSkillsResponse,
    ProjectorResponse,
    RegionalSectoralResponse,
    SectoralIntelligenceResponse,
    SectorSkillsComparisonResponse,
    SectoralSnapshotResponse,
    StatisticalComparisonResponse,
    StopResponse,
    TemporalProjectionsResponse,
)
from app.core.container import service

router = APIRouter(prefix="/projector", tags=["Projector"])


def error_detail(code: str, message: str, field: Optional[str] = None):
    return {
        "error": {
            "code": code,
            "message": message,
            "field": field,
        }
    }


def parse_iso_date(value: Optional[str], field: str):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=error_detail(
                "invalid_date",
                f"{field} must use YYYY-MM-DD format",
                field,
            ),
        ) from exc


def validate_date_range(min_value: Optional[str], max_value: Optional[str], min_field: str, max_field: str):
    min_parsed = parse_iso_date(min_value, min_field)
    max_parsed = parse_iso_date(max_value, max_field)
    if min_parsed and max_parsed and min_parsed > max_parsed:
        raise HTTPException(
            status_code=422,
            detail=error_detail(
                "invalid_date_range",
                f"{min_field} must be less than or equal to {max_field}",
                min_field,
            ),
        )


def validate_year(value: int, field: str):
    if value < 2000 or value > 2100:
        raise HTTPException(
            status_code=422,
            detail=error_detail(
                "invalid_year",
                f"{field} must be between 2000 and 2100",
                field,
            ),
        )


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/readiness")
async def readiness():
    tracker = getattr(service, "tracker", None)
    snapshot_store = getattr(service, "sector_snapshot_store", None)
    tracker_configured = bool(
        getattr(tracker, "api_url", None)
        and getattr(tracker, "username", None)
        and getattr(tracker, "password", None)
    )
    database_configured = bool(getattr(snapshot_store, "enabled", False))
    database_available = None
    database_error = None
    if database_configured:
        try:
            snapshot_store.ensure_schema()
            database_available = True
        except Exception as exc:
            database_available = False
            database_error = str(exc)

    dependencies = {
        "tracker": {
            "configured": tracker_configured,
        },
        "sector_snapshot_db": {
            "configured": database_configured,
            "available": database_available,
        },
    }
    if database_error:
        dependencies["sector_snapshot_db"]["error"] = database_error

    ready = tracker_configured and (not database_configured or database_available is True)
    return {
        "status": "ready" if ready else "degraded",
        "dependencies": dependencies,
    }


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
    validate_date_range(min_date, max_date, "min_date", "max_date")
    return await service.emerging_skills(min_date, max_date,
                                 keywords)


@router.post("/temporal-projections", response_model=TemporalProjectionsResponse)
async def temporal_projections(
        min_date: str = Form(...),
        max_date: str = Form(...),
        keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        granularity: Literal["monthly", "quarterly", "yearly"] = Form("monthly"),
        forecast_periods: int = Form(1),
        top_k: int = Form(10),
):
    """
       Aggregates observed skill demand by upload date and returns short-term baseline projections.

       Granularity can be monthly, quarterly, or yearly. Forecast values use a simple
       last-delta baseline over observed counts; they are not predictive ML outputs.
    """
    validate_date_range(min_date, max_date, "min_date", "max_date")
    if forecast_periods < 0 or forecast_periods > 12:
        raise HTTPException(
            status_code=422,
            detail=error_detail(
                "invalid_forecast_periods",
                "forecast_periods must be between 0 and 12",
                "forecast_periods",
            ),
        )
    if top_k < 1 or top_k > 100:
        raise HTTPException(
            status_code=422,
            detail=error_detail(
                "invalid_top_k",
                "top_k must be between 1 and 100",
                "top_k",
            ),
        )
    return await service.temporal_projections(
        min_date=min_date,
        max_date=max_date,
        keywords=keywords,
        locations=locations,
        granularity=granularity,
        forecast_periods=forecast_periods,
        top_k=top_k,
    )


@router.post("/statistical-comparison", response_model=StatisticalComparisonResponse)
async def statistical_comparison(
        comparison_type: Literal[
            "temporal",
            "sector_skill",
            "regional_skill",
            "regional_sector",
            "sector_evolution",
            "generic",
        ] = Form("generic"),
        group_a_label: str = Form(...),
        group_a_count: int = Form(...),
        group_a_total: int = Form(...),
        group_b_label: str = Form(...),
        group_b_count: int = Form(...),
        group_b_total: int = Form(...),
        alpha: float = Form(0.05),
):
    """
       Runs a baseline 2x2 chi-square comparison over observed count distributions.

       This is an inferential evidence layer for comparison views. It does not prove
       shortages or causality; it reports statistical evidence for an observed difference.
    """
    if group_a_count < 0 or group_b_count < 0 or group_a_total < 0 or group_b_total < 0:
        raise HTTPException(
            status_code=422,
            detail=error_detail("invalid_counts", "counts and totals must be non-negative"),
        )
    if group_a_count > group_a_total:
        raise HTTPException(
            status_code=422,
            detail=error_detail("invalid_group_a", "group_a_count cannot exceed group_a_total", "group_a_count"),
        )
    if group_b_count > group_b_total:
        raise HTTPException(
            status_code=422,
            detail=error_detail("invalid_group_b", "group_b_count cannot exceed group_b_total", "group_b_count"),
        )
    if alpha <= 0 or alpha >= 1:
        raise HTTPException(
            status_code=422,
            detail=error_detail("invalid_alpha", "alpha must be greater than 0 and lower than 1", "alpha"),
        )
    return service.statistical_comparison(
        comparison_type=comparison_type,
        group_a_label=group_a_label,
        group_a_count=group_a_count,
        group_a_total=group_a_total,
        group_b_label=group_b_label,
        group_b_count=group_b_count,
        group_b_total=group_b_total,
        alpha=alpha,
    )


@router.post("/analyze-skills", response_model=ProjectorResponse, response_model_exclude_none=True)
async def analyze_skills(
        keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        min_date: str = Form(...),
        max_date: str = Form(...),
        page: int = Form(1),
        page_size: int = Form(50),
        demo: bool = Form(False),
        include_sectoral: bool = Form(False),
        sector_system: Literal["isco", "nace", "both"] = Form("isco"),
        sector_level: Literal["isco_group", "nace_section", "nace_division", "nace_group", "nace_class", "nace_code"] = Form("isco_group"),
        sectoral_time_mode: Literal["latest", "selected_period", "year", "comparison"] = Form("latest"),
        sectoral_snapshot_year: Optional[int] = Form(None),
        sectoral_compare_a_min_date: Optional[str] = Form(None),
        sectoral_compare_a_max_date: Optional[str] = Form(None),
        sectoral_compare_b_min_date: Optional[str] = Form(None),
        sectoral_compare_b_max_date: Optional[str] = Form(None),
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
           sector_system (str, optional): Compatibility field. Runtime uses Tracker sectors under `nace`.
           sector_level (str, optional): Compatibility field. Runtime uses Tracker sector labels.

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

    validate_date_range(min_date, max_date, "min_date", "max_date")
    validate_date_range(
        sectoral_compare_a_min_date,
        sectoral_compare_a_max_date,
        "sectoral_compare_a_min_date",
        "sectoral_compare_a_max_date",
    )
    validate_date_range(
        sectoral_compare_b_min_date,
        sectoral_compare_b_max_date,
        "sectoral_compare_b_min_date",
        "sectoral_compare_b_max_date",
    )
    if sectoral_snapshot_year is not None:
        validate_year(sectoral_snapshot_year, "sectoral_snapshot_year")
    return await service.analyze_skills(keywords,
                                 locations,
                                 min_date,
                                 max_date,
                                 page,
                                 page_size,
                                 demo,
                                 include_sectoral,
                                 sector_system,
                                 sector_level,
                                 sectoral_time_mode,
                                 sectoral_snapshot_year,
                                 sectoral_compare_a_min_date,
                                 sectoral_compare_a_max_date,
                                 sectoral_compare_b_min_date,
                                 sectoral_compare_b_max_date,
                                 skill_group_level,
                                 occupation_level)


@router.post(
    "/sectoral-intelligence",
    response_model=SectoralIntelligenceResponse,
    response_model_exclude_none=True,
)
async def sectoral_intelligence(
        keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        sectors: Optional[List[str]] = Form(None),
        data_source: Literal["cache", "live"] = Form("cache"),
        mode: Literal["latest", "selected_period", "year", "comparison"] = Form("latest"),
        min_date: Optional[str] = Form(None),
        max_date: Optional[str] = Form(None),
        snapshot_year: Optional[int] = Form(None),
        compare_a_min_date: Optional[str] = Form(None),
        compare_a_max_date: Optional[str] = Form(None),
        compare_b_min_date: Optional[str] = Form(None),
        compare_b_max_date: Optional[str] = Form(None),
        skill_group_level: int = Form(1),
        occupation_level: int = Form(1),
):
    """
       Computes Tracker API sector intelligence as a dedicated sector dimension.

       The endpoint is independent from `/projector/analyze-skills` and supports
       latest, selected-period, yearly snapshot, and two-period comparison modes.
    """
    validate_date_range(min_date, max_date, "min_date", "max_date")
    validate_date_range(compare_a_min_date, compare_a_max_date, "compare_a_min_date", "compare_a_max_date")
    validate_date_range(compare_b_min_date, compare_b_max_date, "compare_b_min_date", "compare_b_max_date")
    if snapshot_year is not None:
        validate_year(snapshot_year, "snapshot_year")
    return await service.sectoral_intelligence(
        keywords=keywords,
        locations=locations,
        sectors=sectors,
        data_source=data_source,
        mode=mode,
        min_date=min_date,
        max_date=max_date,
        snapshot_year=snapshot_year,
        compare_a_min_date=compare_a_min_date,
        compare_a_max_date=compare_a_max_date,
        compare_b_min_date=compare_b_min_date,
        compare_b_max_date=compare_b_max_date,
        skill_group_level=skill_group_level,
        occupation_level=occupation_level,
    )


@router.post(
    "/sectoral-snapshot",
    response_model=SectoralSnapshotResponse,
    response_model_exclude_none=True,
)
async def sectoral_snapshot(
        year: int = Form(...),
        reference_year: Optional[int] = Form(None),
        locations: Optional[List[str]] = Form(None),
):
    """
       Computes a simple yearly sector overview for the final frontend.

       This endpoint is intentionally aggregated: one row per Tracker sector,
       with job volume, share, top skills, and top job titles.
    """
    validate_year(year, "year")
    if reference_year is not None:
        validate_year(reference_year, "reference_year")
    return await service.sectoral_snapshot(
        year=year,
        reference_year=reference_year,
        locations=locations,
        data_source="cache",
    )


@router.post(
    "/sector-skills-comparison",
    response_model=SectorSkillsComparisonResponse,
    response_model_exclude_none=True,
)
async def sector_skills_comparison(
        year: int = Form(...),
        reference_year: Optional[int] = Form(None),
        locations: Optional[List[str]] = Form(None),
        sectors: Optional[List[str]] = Form(None),
        skills: Optional[List[str]] = Form(None),
        metric: Literal["count", "share", "rank", "growth"] = Form("share"),
):
    """
       Compares sectors through a sectors x skills matrix for a yearly snapshot.

       The selected metric controls the heatmap value:
       count, share in sector, rank score, or growth vs previous year.
    """
    validate_year(year, "year")
    if reference_year is not None:
        validate_year(reference_year, "reference_year")
    return await service.sector_skills_comparison(
        year=year,
        reference_year=reference_year,
        locations=locations,
        sectors=sectors,
        skills=skills,
        metric=metric,
    )


@router.post(
    "/regional-sectoral",
    response_model=RegionalSectoralResponse,
    response_model_exclude_none=True,
)
async def regional_sectoral(
        year: int = Form(...),
        locations: Optional[List[str]] = Form(None),
        top_k: int = Form(10),
):
    """
       Returns yearly sector distribution grouped by raw and NUTS-like regions.

       This endpoint reads precomputed PostgreSQL sector snapshots and does not
       perform live Tracker aggregation.
    """
    validate_year(year, "year")
    return await service.regional_sectoral(
        year=year,
        locations=locations,
        top_k=top_k,
    )


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
