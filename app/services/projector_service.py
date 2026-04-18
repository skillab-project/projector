from typing import Optional, List

from fastapi import Form


class ProjectorService:
    def __init__(self, engine, tracker, occupations, regional, market, trends, sectoral):
        self.engine = engine
        self.tracker = tracker
        self.occupations = occupations
        self.regional = regional
        self.market = market
        self.trends = trends
        self.sectoral = sectoral

    async def analyze_skills(self,   keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        min_date: str = Form(...),
        max_date: str = Form(...),
        page: int = Form(1),
        page_size: int = Form(50),
        demo: bool = Form(False),
        include_sectoral: bool = Form(False),
        sector_level: str = Form("isco_group"),
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

        # Traduzione settori (Phase 1)
        all_occs = []
        all_skills = []
        for j in raw:
            all_occs.extend(self.occupations.get_occupation_ids(j))
            all_skills.extend(j.get("skills", []))  # <--- Aggiungiamo questo!

        # Add canonical ESCO skills from occupation-skill relations so their labels are resolved too
        canonical_skill_ids = set()
        for occ_id in set(all_occs):
            canonical_skill_ids.update(self.engine.occ_skill_relations.get(occ_id, set()))

        all_skills.extend(list(canonical_skill_ids))

        occ_uris = list(set(all_occs))  # Rimuove i duplicati

        await self.tracker.fetch_occupation_labels(occ_uris)
        await self.tracker.fetch_skill_names(list(set(all_skills)))  # Traduciamo una sola volta il set complessivo
        # Analisi globale
        analysis = await self.market.analyze_market_data(raw)

        # Trend in memoria (Single Fetch optimization)
        trend = await self.trends.calculate_trends_from_data(raw, min_date, max_date)

        regional_projections = self.regional.get_regional_projections(raw, demo=demo)

        sectoral_data = None
        if include_sectoral:
            allowed_sector_levels = {
                "isco_group",
                "nace_code",
                "nace_division",
                "nace_group",
                "nace_class"
            }
            normalized_sector_level = str(sector_level or "isco_group").strip().lower()
            if normalized_sector_level not in allowed_sector_levels:
                normalized_sector_level = "isco_group"

            sectoral_data = self.sectoral.build_sectoral_intelligence(
                jobs=raw,
                sector_level=normalized_sector_level,
                skill_group_level=skill_group_level,
                occupation_level=occupation_level,
                resolve_labels=True,
                top_k_skills=10,
                top_k_groups=10,
                reset=True
            )

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
                "sectoral": sectoral_data
            }
        }

    async def emerging_skills(self, min_date: str = Form(...), max_date: str = Form(...),
                          keywords: Optional[List[str]] = Form(None)):
        self.engine.stop_requested = False
        res = await self.trends.calculate_smart_trends({"keywords": keywords} if keywords else {}, min_date, max_date)
        return {"status": "completed" if not self.engine.stop_requested else "stopped", "insights": res}


    def stop(self):
        self.engine.request_stop()
        return {"status": "signal_sent"}
