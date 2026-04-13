import asyncio
from collections import Counter
from typing import List


class MarketAnalytics:
    def __init__(self, engine, tracker, occupations):
        self.engine = engine
        self.tracker = tracker
        self.occupations = occupations

    def _empty_res(self):
        return {
            "total_jobs": 0,
            "rankings": {
                "skills": [],
                "employers": [],
                "job_titles": [],
                "sectors": []  # Consistenza Phase 1
            },
            "geo": []
        }

    def _empty_insights_p1(self):
        return {
            "ranking": [],
            "sectors": [],
            "job_titles": [],
            "employers": [],
            "trends": {
                "market_health": {
                    "status": "stable",
                    "volume_growth_percentage": 0.0
                },
                "trends": []
            },
            "regional": {
                "raw": [],
                "nuts1": [],
                "nuts2": [],
                "nuts3": []
            },
            "sectoral": None
        }

    async def analyze_market_data(self, raw_jobs: List[dict]):
        """
           Performs multi-dimensional aggregation of job market data.

           This method is the core analytical engine of the Projector. It processes
           raw job postings and extracts structured intelligence across multiple dimensions:
               - Skills demand
               - Employers
               - Job titles
               - Geographic distribution
               - Sector distribution

           Args:
               raw_jobs (List[dict]): Raw job postings retrieved from the Tracker API.

           Returns:
               dict:
                   {
                       "total_jobs": int,
                       "rankings": {
                           "skills": [...],
                           "employers": [...],
                           "job_titles": [...],
                           "locations": [...],
                           "sectors": [...]
                       }
                   }

           Behavior:
               - Uses Counter-based aggregation for performance
               - Builds skill-to-sector relationships
               - Enriches skills using `fetch_skill_names`
               - Computes frequency and sector spread

           Performance Notes:
               - Includes async checkpoints to avoid blocking event loop
               - Handles large datasets (40k+ jobs)

           Early Exit:
               - Stops processing if `stop_requested` is True
           """
        if not raw_jobs: return self._empty_res()

        s_cnt, e_cnt, t_cnt, l_cnt, sec_cnt = Counter(), Counter(), Counter(), Counter(), Counter()
        skill_sector_map = {}  # La matrice Skill -> [Settori]

        for i, job in enumerate(raw_jobs):
            if self.engine.stop_requested: break
            if i > 0 and i % 2000 == 0: await asyncio.sleep(0)

            # 1. Occupation -> sector
            occ_ids = self.occupations.get_occupation_ids(job)

            for occ_id in occ_ids:
                sector_name = self.occupations.get_sector_from_occupation(occ_id, level="isco_group")
                sec_cnt[sector_name] += 1

            for s_uri in job.get("skills", []):
                s_uri = str(s_uri).strip()
                s_cnt[s_uri] += 1
                if s_uri not in skill_sector_map:
                    skill_sector_map[s_uri] = Counter()

                for occ_id in occ_ids:
                    sector_name = self.occupations.get_sector_from_occupation(occ_id, level="isco_group")
                    skill_sector_map[s_uri][sector_name] += 1

            e_cnt[job.get("organization_name") or "N/D"] += 1
            t_cnt[job.get("title") or "N/D"] += 1
            l_cnt[job.get("location_code") or "N/D"] += 1

        # 4. Arricchimento nomi (Skill + Settori)
        await self.tracker.fetch_skill_names(list(s_cnt.keys()))

        # 5. Output con Intelligence
        enriched_ranking = []
        for k, v in s_cnt.most_common():
            skill_info = self.engine.skill_map.get(k, {"label": k.split('/')[-1], "is_green": False, "is_digital": False})

            # Intelligence: Calcolo trasversalità (Phase 1 core)
            sectors_involved = skill_sector_map[k]

            enriched_ranking.append({
                "name": skill_info["label"],
                "frequency": v,
                "skill_id": k,
                "is_green": skill_info["is_green"],
                "is_digital": skill_info["is_digital"],
                "sector_spread": len(sectors_involved),  # Quanti settori la cercano?
                "primary_sector": sectors_involved.most_common(1)[0][0] if sectors_involved else "N/D"
            })

        return {
            "total_jobs": len(raw_jobs),
            "rankings": {
                "skills": enriched_ranking,
                "employers": [{"name": k, "count": v} for k, v in e_cnt.most_common(10)],
                "job_titles": [{"name": k, "count": v} for k, v in t_cnt.most_common(10)],
                "sectors": [{"name": k, "count": v} for k, v in sec_cnt.most_common(10)]  # NUOVO
            },
            "geo": [{"location": k, "job_count": v} for k, v in l_cnt.most_common()]
        }