"""Small Tracker-compatible API backed by the synthetic demo dataset."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterable

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request

from demo.generate_synthetic_jobs import SKILLS, occupation_catalog


DATASET_PATH = Path(os.getenv("DEMO_DATASET_PATH", "/data/synthetic_jobs.json"))
ACCESS_TOKEN = os.getenv("DEMO_TRACKER_TOKEN", "demo-tracker-token")
OCCUPATIONS = occupation_catalog()


def load_jobs() -> list[dict]:
    with DATASET_PATH.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if isinstance(payload, dict):
        payload = payload.get("items", [])
    return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.jobs = load_jobs()
    yield


app = FastAPI(
    title="SKILLAB Mock Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)


def require_token(authorization: str | None = Header(default=None)) -> None:
    if authorization != f"Bearer {ACCESS_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid or missing demo token")


def expand_values(values: Iterable[object]) -> list[str]:
    expanded = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                expanded.extend(str(item).strip() for item in parsed if str(item).strip())
                continue
        if "," in text:
            expanded.extend(part.strip() for part in text.split(",") if part.strip())
        else:
            expanded.append(text)
    return expanded


def form_values(form, *names: str) -> list[str]:
    values = []
    for name in names:
        values.extend(form.getlist(name))
    return expand_values(values)


def matches_location(job: dict, requested_locations: list[str]) -> bool:
    if not requested_locations:
        return True
    job_codes = {
        str(job.get(key) or "").strip().upper()
        for key in ("location_code", "nuts1", "nuts2", "nuts3")
    }
    for requested in requested_locations:
        code = requested.strip().upper()
        if code in job_codes:
            return True
        if any(job_code.startswith(code) for job_code in job_codes if job_code):
            return True
    return False


def matches_keywords(job: dict, keywords: list[str], logic: str) -> bool:
    if not keywords:
        return True
    haystack = " ".join(
        str(job.get(field) or "")
        for field in ("title", "description", "organization_name", "location")
    ).casefold()
    checks = [keyword.casefold() in haystack for keyword in keywords]
    return all(checks) if logic == "and" else any(checks)


def matches_list(job_values: Iterable[object], requested: list[str], logic: str = "or") -> bool:
    if not requested:
        return True
    available = {str(value).strip() for value in job_values}
    checks = [value in available for value in requested]
    return all(checks) if logic == "and" else any(checks)


@app.get("/health")
@app.get("/api/health")
async def health(request: Request):
    return {
        "status": "ok",
        "dataset": str(DATASET_PATH),
        "jobs": len(request.app.state.jobs),
    }


@app.post("/api/login")
async def login(_request: Request):
    return ACCESS_TOKEN


@app.post("/api/jobs", dependencies=[Depends(require_token)])
async def jobs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1),
):
    form = await request.form()
    keywords = form_values(form, "keywords")
    skill_ids = form_values(form, "skill_ids")
    occupation_ids = form_values(form, "occupation_ids")
    organization_ids = form_values(form, "organization_ids")
    locations = form_values(form, "location_code", "locations")
    sources = form_values(form, "sources", "source")
    keyword_logic = str(form.get("keywords_logic") or "or").strip().lower()
    skill_logic = str(form.get("skill_ids_logic") or "or").strip().lower()
    occupation_logic = str(form.get("occupation_ids_logic") or "or").strip().lower()
    min_upload_date = str(form.get("min_upload_date") or "").strip()
    max_upload_date = str(form.get("max_upload_date") or "").strip()

    filtered = []
    for job in request.app.state.jobs:
        upload_date = str(job.get("upload_date") or "")
        if min_upload_date and upload_date < min_upload_date:
            continue
        if max_upload_date and upload_date > max_upload_date:
            continue
        if not matches_location(job, locations):
            continue
        if not matches_keywords(job, keywords, keyword_logic):
            continue
        if not matches_list(job.get("skills", []), skill_ids, skill_logic):
            continue
        if not matches_list(job.get("occupations", []), occupation_ids, occupation_logic):
            continue
        if organization_ids and str(job.get("organization")) not in organization_ids:
            continue
        if sources and str(job.get("source") or "") not in sources:
            continue
        filtered.append(job)

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start : start + page_size]
    return {
        "items": items,
        "count": total,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def catalog_response(request: Request, catalog: dict[str, str], page: int, page_size: int):
    form = await request.form()
    requested_ids = form_values(form, "ids")
    keywords = form_values(form, "keywords")
    items = [
        {"id": item_id, "label": label}
        for item_id, label in catalog.items()
        if (not requested_ids or item_id in requested_ids)
        and (not keywords or any(keyword.casefold() in label.casefold() for keyword in keywords))
    ]
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "count": total,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.post("/api/skills", dependencies=[Depends(require_token)])
async def skills(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1),
):
    return await catalog_response(request, SKILLS, page, page_size)


@app.post("/api/occupations", dependencies=[Depends(require_token)])
async def occupations(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1),
):
    return await catalog_response(request, OCCUPATIONS, page, page_size)
