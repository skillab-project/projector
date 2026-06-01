from collections import Counter, defaultdict
from typing import Optional, List, Literal
from datetime import date, timedelta

from fastapi import Form


class ProjectorService:
    def __init__(self, engine, tracker, occupations, regional, market, trends, sectoral, sector_snapshot_store=None):
        self.engine = engine
        self.tracker = tracker
        self.occupations = occupations
        self.regional = regional
        self.market = market
        self.trends = trends
        self.sectoral = sectoral
        self.sector_snapshot_store = sector_snapshot_store

    async def analyze_skills(self,   keywords: Optional[List[str]] = Form(None),
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
        occupation_level: int = Form(1),):
        self.engine.stop_requested = False

        # Costruzione payload pulita
        payload = {
            "keywords": keywords,
            "location_code": locations,
            "min_upload_date": min_date,
            "max_upload_date": max_date
        }
        clean_payload = {k: v for k, v in payload.items() if v is not None}

        # FETCH UNICO
        raw = await self.tracker.fetch_all_jobs(clean_payload)

        # FIX: Se non ci sono job, restituiamo subito la struttura coerente
        if not raw:
            return {
                "status": "completed",
                "dimension_summary": {"jobs_analyzed": 0, "geo_breakdown": []},
                "insights": self.market._empty_insights_p1()  # <--- Coerenza qui
            }

        all_skills = []
        for j in raw:
            all_skills.extend(j.get("skills", []))

        await self.tracker.fetch_skill_names(list(set(all_skills)))
        # Analisi globale
        analysis = await self.market.analyze_market_data(raw)

        # Trend in memoria (Single Fetch optimization)
        trend = await self.trends.calculate_trends_from_data(raw, min_date, max_date)

        regional_projections = self.regional.get_regional_projections(raw, demo=demo)

        sectoral_data = None
        sectoral_views = None
        sectoral_mode = None
        sector_view_names = None
        if include_sectoral:
            normalized_system = str(sector_system or "isco").strip().lower()
            if normalized_system != "nace":
                normalized_system = "nace"

            base_sectoral_payload = {
                k: v
                for k, v in payload.items()
                if k not in {"min_upload_date", "max_upload_date"} and v is not None
            }
            sectoral_payload = await self._build_temporal_sectoral_payload(
                base_payload=base_sectoral_payload,
                selected_jobs=raw,
                selected_min_date=min_date,
                selected_max_date=max_date,
                time_mode=sectoral_time_mode,
                snapshot_year=sectoral_snapshot_year,
                compare_a_min_date=sectoral_compare_a_min_date,
                compare_a_max_date=sectoral_compare_a_max_date,
                compare_b_min_date=sectoral_compare_b_min_date,
                compare_b_max_date=sectoral_compare_b_max_date,
                skill_group_level=skill_group_level,
                occupation_level=occupation_level,
            )

            sectoral_mode = normalized_system
            sectoral_views = {
                "nace": {
                    "sector_level": "tracker_sector",
                    **sectoral_payload
                }
            }

            sectoral_data = sectoral_payload["items"]

            sector_view_names = {
                "nace": {
                    "observed": "Observed",
                    "latest": "Last six months",
                    "selected_period": "Selected period",
                    "year": "Year snapshot",
                    "comparison": "Period comparison"
                }
            }

        safe_page = max(page, 1)
        safe_page_size = max(page_size, 1)
        start = (safe_page - 1) * safe_page_size

        return {
            "status": "completed" if not self.engine.stop_requested else "stopped",
            "dimension_summary": {
                "jobs_analyzed": analysis["total_jobs"],
                "geo_breakdown": analysis["geo"]
            },
            "insights": {
                "ranking": analysis["rankings"]["skills"][start: start + safe_page_size],
                "sectors": analysis["rankings"]["sectors"],
                "job_titles": analysis["rankings"]["job_titles"],
                "employers": analysis["rankings"]["employers"],
                "trends": trend,
                "regional": regional_projections,
                "sectoral": sectoral_data,
                "sectoral_mode": sectoral_mode,
                "sectoral_views": sectoral_views,
                "sector_view_names": sector_view_names
            }
        }

    async def emerging_skills(self, min_date: str = Form(...), max_date: str = Form(...),
                          keywords: Optional[List[str]] = Form(None)):
        self.engine.stop_requested = False
        res = await self.trends.calculate_smart_trends({"keywords": keywords} if keywords else {}, min_date, max_date)
        return {"status": "completed" if not self.engine.stop_requested else "stopped", "insights": res}

    async def sectoral_intelligence(
            self,
            keywords: Optional[List[str]] = None,
            locations: Optional[List[str]] = None,
            sectors: Optional[List[str]] = None,
            data_source: Literal["cache", "live"] = "cache",
            mode: Literal["latest", "selected_period", "year", "comparison"] = "latest",
            min_date: Optional[str] = None,
            max_date: Optional[str] = None,
            snapshot_year: Optional[int] = None,
            compare_a_min_date: Optional[str] = None,
            compare_a_max_date: Optional[str] = None,
            compare_b_min_date: Optional[str] = None,
            compare_b_max_date: Optional[str] = None,
            skill_group_level: int = 1,
            occupation_level: int = 1,
    ):
        self.engine.stop_requested = False

        latest_min, latest_max = self._latest_window()
        selected_min = min_date or latest_min
        selected_max = max_date or latest_max
        normalized_mode = str(mode or "latest").strip().lower()
        normalized_source = str(data_source or "cache").strip().lower()
        if normalized_source not in {"cache", "live"}:
            normalized_source = "cache"
        sector_filter = self._normalize_sector_filter(sectors)

        base_payload = {
            "keywords": keywords,
            "location_code": locations,
        }
        clean_base_payload = {k: v for k, v in base_payload.items() if v is not None}

        selected_jobs = []
        if normalized_mode == "selected_period":
            selected_jobs = await self._fetch_jobs_for_window(
                clean_base_payload,
                selected_min,
                selected_max,
                use_cache_only=normalized_source == "cache",
            )
            selected_jobs = self._filter_jobs_by_sector(selected_jobs, sector_filter)
            await self._ensure_skill_labels(selected_jobs)

        payload = await self._build_temporal_sectoral_payload(
            base_payload=clean_base_payload,
            selected_jobs=selected_jobs,
            selected_min_date=selected_min,
            selected_max_date=selected_max,
            time_mode=normalized_mode,
            snapshot_year=snapshot_year,
            compare_a_min_date=compare_a_min_date,
            compare_a_max_date=compare_a_max_date,
            compare_b_min_date=compare_b_min_date,
            compare_b_max_date=compare_b_max_date,
            sector_filter=sector_filter,
            use_cache_only=normalized_source == "cache",
            skill_group_level=skill_group_level,
            occupation_level=occupation_level,
        )

        return {
            "status": "completed" if not self.engine.stop_requested else "stopped",
            "mode": payload["time_mode"],
            "data_source": normalized_source,
            "sector_level": "tracker_sector",
            "window": payload["window"],
            "sector_filter": sector_filter,
            "items": payload["items"],
            "snapshots": payload.get("snapshots"),
            "comparison": payload.get("comparison"),
            "sector_view_names": {
                "latest": "Last six months",
                "selected_period": "Selected period",
                "year": "Year snapshot",
                "comparison": "Period comparison",
            },
        }

    async def sectoral_snapshot(
            self,
            year: int,
            keywords: Optional[List[str]] = None,
            locations: Optional[List[str]] = None,
            sectors: Optional[List[str]] = None,
            data_source: Literal["cache", "live"] = "cache",
    ):
        self.engine.stop_requested = False

        location_code = self._single_location(locations)
        sector_filter = self._normalize_sector_filter(sectors)
        min_date, max_date = self._year_window(year, f"{year}-12-31")
        store_payload = self._read_sector_snapshot_store(year, location_code)
        if store_payload:
            return store_payload
        if self._sector_snapshot_store_enabled():
            return self._empty_sector_snapshot(year, min_date, max_date, sector_filter, "postgres")

        normalized_source = str(data_source or "cache").strip().lower()
        if normalized_source not in {"cache", "live"}:
            normalized_source = "cache"

        base_payload = {
            "keywords": keywords,
            "location_code": locations,
        }
        clean_base_payload = {k: v for k, v in base_payload.items() if v is not None}

        jobs = await self._fetch_jobs_for_window(
            clean_base_payload,
            min_date,
            max_date,
            use_cache_only=normalized_source == "cache",
        )
        jobs = self._filter_jobs_by_sector(jobs, sector_filter)
        await self._ensure_skill_labels(jobs)
        sectors_payload = self._build_sector_snapshot_rows(jobs, sector_filter)

        if not sectors_payload:
            return self._empty_sector_snapshot(year, min_date, max_date, sector_filter, "cache", len(jobs))

        return {
            "status": "completed" if not self.engine.stop_requested else "stopped",
            "year": int(year),
            "data_source": normalized_source,
            "window": self._sectoral_window_meta(f"{year} snapshot", min_date, max_date),
            "total_jobs": len(jobs),
            "sector_filter": sector_filter,
            "sectors": sectors_payload,
        }

    def _single_location(self, locations: Optional[List[str]]):
        for location in locations or []:
            value = str(location or "").strip()
            if value:
                return value
        return None

    def _read_sector_snapshot_store(self, year: int, location_code: Optional[str]):
        store = self.sector_snapshot_store
        if not self._sector_snapshot_store_enabled():
            return None
        return store.read_latest(int(year), location_code)

    def _sector_snapshot_store_enabled(self):
        return bool(self.sector_snapshot_store and getattr(self.sector_snapshot_store, "enabled", False))

    def _empty_sector_snapshot(
            self,
            year: int,
            min_date: str,
            max_date: str,
            sector_filter: List[str],
            data_source: str,
            total_jobs: int = 0,
    ):
        return {
            "status": "not_available",
            "year": int(year),
            "data_source": data_source,
            "window": self._sectoral_window_meta(f"{year} snapshot", min_date, max_date),
            "total_jobs": total_jobs,
            "sector_filter": sector_filter,
            "sectors": [],
            "message": f"No static sector snapshot available for {year}. Run the snapshot refresh job first.",
        }

    def _today(self):
        return date.today()

    def _latest_window(self):
        end = self._today()
        start = end - timedelta(days=183)
        return start.isoformat(), end.isoformat()

    def _year_window(self, snapshot_year: Optional[int], fallback_date: str):
        year = snapshot_year
        if year is None:
            year = int(str(fallback_date)[:4])
        return f"{year:04d}-01-01", f"{year:04d}-12-31"

    async def _fetch_jobs_for_window(
            self,
            base_payload: dict,
            min_date: str,
            max_date: str,
            use_cache_only: bool = False,
    ):
        payload = {
            **base_payload,
            "min_upload_date": min_date,
            "max_upload_date": max_date,
        }
        if use_cache_only and hasattr(self.tracker, "load_cached_jobs"):
            return self.tracker.load_cached_jobs(payload) or []
        return await self.tracker.fetch_all_jobs(payload)

    def _normalize_sector_filter(self, sectors: Optional[List[str]]):
        return [
            str(sector).strip()
            for sector in (sectors or [])
            if str(sector).strip()
        ]

    def _job_sector_labels(self, job: dict):
        labels = []
        for sector in job.get("sectors", []) or []:
            if isinstance(sector, dict):
                value = sector.get("label") or sector.get("name") or sector.get("code")
            else:
                value = sector
            value = str(value or "").strip()
            if value:
                labels.append(value)
        return labels

    def _filter_jobs_by_sector(self, jobs: List[dict], sectors: List[str]):
        if not sectors:
            return jobs
        wanted = {sector.lower() for sector in sectors}
        return [
            job for job in jobs
            if any(label.lower() in wanted for label in self._job_sector_labels(job))
        ]

    def _skill_meta(self, skill_id: str):
        meta = getattr(self.engine, "skill_map", {}).get(skill_id, {}) or {}
        return {
            "label": meta.get("label") or skill_id,
            "is_green": meta.get("is_green"),
            "is_digital": meta.get("is_digital"),
        }

    def _build_sector_snapshot_rows(self, jobs: List[dict], sector_filter: Optional[List[str]] = None):
        sector_jobs = Counter()
        sector_skills = defaultdict(Counter)
        sector_titles = defaultdict(Counter)
        wanted = {sector.lower() for sector in (sector_filter or [])}

        for job in jobs:
            labels = list(dict.fromkeys(self._job_sector_labels(job)))
            if wanted:
                labels = [label for label in labels if label.lower() in wanted]
            if not labels:
                continue

            skills = [
                str(skill_id).strip()
                for skill_id in dict.fromkeys(job.get("skills", []) or [])
                if str(skill_id).strip()
            ]
            title = str(job.get("title") or "").strip()

            for sector in labels:
                sector_jobs[sector] += 1
                if title:
                    sector_titles[sector][title] += 1
                for skill_id in skills:
                    sector_skills[sector][skill_id] += 1

        total_sector_jobs = sum(sector_jobs.values()) or 1
        rows = []
        for sector, job_count in sector_jobs.items():
            skill_counts = sector_skills[sector]
            total_skill_mentions = sum(skill_counts.values())
            top_skills = []
            for skill_id, count in skill_counts.most_common(10):
                meta = self._skill_meta(skill_id)
                top_skills.append({
                    "skill_id": skill_id,
                    "label": meta["label"],
                    "count": count,
                    "frequency": round(count / total_skill_mentions, 4) if total_skill_mentions else 0.0,
                    "is_green": meta["is_green"],
                    "is_digital": meta["is_digital"],
                })

            rows.append({
                "sector": sector,
                "sector_label": sector,
                "job_count": job_count,
                "job_share": round(job_count / total_sector_jobs, 4),
                "total_skill_mentions": total_skill_mentions,
                "unique_skills": len(skill_counts),
                "top_skills": top_skills,
                "top_job_titles": [
                    {"name": title, "count": count}
                    for title, count in sector_titles[sector].most_common(5)
                ],
            })

        return sorted(rows, key=lambda row: (row["job_count"], row["total_skill_mentions"]), reverse=True)

    async def _ensure_skill_labels(self, jobs: List[dict]):
        skill_ids = {
            str(skill_id).strip()
            for job in jobs
            for skill_id in job.get("skills", [])
            if str(skill_id).strip()
        }
        if skill_ids:
            await self.tracker.fetch_skill_names(list(skill_ids))

    def _build_sectoral_items(self, jobs: List[dict], skill_group_level: int, occupation_level: int):
        return self.sectoral.build_sectoral_intelligence(
            jobs=jobs,
            sector_level="nace_section",
            skill_group_level=skill_group_level,
            occupation_level=occupation_level,
            resolve_labels=True,
            top_k_skills=10,
            top_k_groups=10,
            reset=True
        )

    def _sectoral_window_meta(self, label: str, min_date: str, max_date: str):
        return {
            "label": label,
            "min_date": min_date,
            "max_date": max_date,
        }

    def _compare_sectoral_items(self, period_a_items: List[dict], period_b_items: List[dict]):
        by_a = {item["sector"]: item for item in period_a_items}
        by_b = {item["sector"]: item for item in period_b_items}
        rows = []

        for sector in sorted(set(by_a) | set(by_b)):
            item_a = by_a.get(sector, {})
            item_b = by_b.get(sector, {})
            count_a = item_a.get("observed_skills", {}).get("total_skill_mentions", 0)
            count_b = item_b.get("observed_skills", {}).get("total_skill_mentions", 0)
            delta = count_b - count_a
            if count_a == 0 and count_b > 0:
                growth = "new_entry"
            elif count_a:
                growth = round((delta / count_a) * 100, 2)
            else:
                growth = 0.0
            rows.append({
                "sector": sector,
                "sector_label": item_b.get("sector_label") or item_a.get("sector_label") or sector,
                "period_a_total_skill_mentions": count_a,
                "period_b_total_skill_mentions": count_b,
                "delta_total_skill_mentions": delta,
                "growth_percentage": growth,
            })

        return sorted(rows, key=lambda row: row["period_b_total_skill_mentions"], reverse=True)

    async def _build_temporal_sectoral_payload(
            self,
            base_payload: dict,
            selected_jobs: List[dict],
            selected_min_date: str,
            selected_max_date: str,
            time_mode: str,
            snapshot_year: Optional[int],
            compare_a_min_date: Optional[str],
            compare_a_max_date: Optional[str],
            compare_b_min_date: Optional[str],
            compare_b_max_date: Optional[str],
            sector_filter: Optional[List[str]] = None,
            use_cache_only: bool = False,
            skill_group_level: int = 1,
            occupation_level: int = 1,
    ):
        mode = str(time_mode or "latest").strip().lower()
        if mode not in {"latest", "selected_period", "year", "comparison"}:
            mode = "latest"

        if mode == "selected_period":
            items = self._build_sectoral_items(selected_jobs, skill_group_level, occupation_level)
            return {
                "time_mode": mode,
                "window": self._sectoral_window_meta("Selected period", selected_min_date, selected_max_date),
                "items": items,
            }

        if mode == "year":
            min_date, max_date = self._year_window(snapshot_year, selected_max_date)
            jobs = await self._fetch_jobs_for_window(base_payload, min_date, max_date, use_cache_only=use_cache_only)
            jobs = self._filter_jobs_by_sector(jobs, sector_filter or [])
            await self._ensure_skill_labels(jobs)
            items = self._build_sectoral_items(jobs, skill_group_level, occupation_level)
            return {
                "time_mode": mode,
                "window": self._sectoral_window_meta(f"{min_date[:4]} snapshot", min_date, max_date),
                "items": items,
            }

        if mode == "comparison":
            a_min = compare_a_min_date or selected_min_date
            a_max = compare_a_max_date or selected_max_date
            b_min = compare_b_min_date
            b_max = compare_b_max_date
            if not b_min or not b_max:
                b_min, b_max = self._latest_window()

            jobs_a = await self._fetch_jobs_for_window(base_payload, a_min, a_max, use_cache_only=use_cache_only)
            jobs_b = await self._fetch_jobs_for_window(base_payload, b_min, b_max, use_cache_only=use_cache_only)
            jobs_a = self._filter_jobs_by_sector(jobs_a, sector_filter or [])
            jobs_b = self._filter_jobs_by_sector(jobs_b, sector_filter or [])
            await self._ensure_skill_labels(jobs_a + jobs_b)
            items_a = self._build_sectoral_items(jobs_a, skill_group_level, occupation_level)
            items_b = self._build_sectoral_items(jobs_b, skill_group_level, occupation_level)
            return {
                "time_mode": mode,
                "window": self._sectoral_window_meta("Comparison current", b_min, b_max),
                "items": items_b,
                "snapshots": {
                    "period_a": {
                        "window": self._sectoral_window_meta("Comparison baseline", a_min, a_max),
                        "items": items_a,
                    },
                    "period_b": {
                        "window": self._sectoral_window_meta("Comparison current", b_min, b_max),
                        "items": items_b,
                    },
                },
                "comparison": {
                    "period_a": self._sectoral_window_meta("Comparison baseline", a_min, a_max),
                    "period_b": self._sectoral_window_meta("Comparison current", b_min, b_max),
                    "sectors": self._compare_sectoral_items(items_a, items_b),
                },
            }

        min_date, max_date = self._latest_window()
        jobs = await self._fetch_jobs_for_window(base_payload, min_date, max_date, use_cache_only=use_cache_only)
        jobs = self._filter_jobs_by_sector(jobs, sector_filter or [])
        await self._ensure_skill_labels(jobs)
        items = self._build_sectoral_items(jobs, skill_group_level, occupation_level)
        return {
            "time_mode": "latest",
            "window": self._sectoral_window_meta("Last six months", min_date, max_date),
            "items": items,
        }


    def stop(self):
        self.engine.request_stop()
        return {"status": "signal_sent"}
