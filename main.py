import logging
import asyncio
import httpx
import os
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from fastapi import FastAPI, Form
from typing import List, Optional
from dotenv import load_dotenv

from schemas import ProjectorResponse, EmergingSkillsResponse, StopResponse

# Configurazione Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("SKILLAB-Projector")

load_dotenv()
app = FastAPI(title="SKILLAB Projector Microservice")


class ProjectorEngine:
    def __init__(self):
        self.api_url = os.getenv("TRACKER_API")
        self.username = os.getenv("TRACKER_USERNAME")
        self.password = os.getenv("TRACKER_PASSWORD")
        self.token = None
        self.skill_map = {}
        self.sector_map = {}  # Cache specifica per le occupazioni/settori
        self.stop_requested = False
        # Timeout impostato a None per evitare ReadTimeout su query pesanti
        self.client = httpx.AsyncClient(timeout=None)

    def request_stop(self):
        """
           Requests a cooperative stop of all ongoing operations.

           This method sets an internal flag (`stop_requested`) that is periodically
           checked by long-running asynchronous processes (e.g., data fetching,
           skill translation, analysis loops). When the flag is detected, the engine
           gracefully interrupts execution at the next safe checkpoint.

           This avoids abrupt termination and ensures partial results can still be returned.

           Side Effects:
               - Sets `self.stop_requested = True`
           """
        self.stop_requested = True
        logger.warning("!!! STOP RILEVATO !!! Interruzione programmata dei processi.")

    async def _get_token(self):
        """
            Authenticates with the external Tracker API and retrieves an access token.

            The token is required for all subsequent API calls (jobs, skills, occupations).
            It is stored internally and reused until expiration.

            Returns:
                Optional[str]: Bearer token string if authentication succeeds,
                               None if authentication fails.

            External Dependencies:
                - POST {TRACKER_API}/login

            Failure Handling:
                - Logs error and returns None without raising exception.
            """
        try:
            resp = await self.client.post(
                f"{self.api_url}/login",
                json={"username": self.username, "password": self.password}
            )
            self.token = resp.text.replace('"', '')
            return self.token
        except Exception as e:
            logger.error(f"Errore Login: {e}")
            return None



    async def fetch_occupation_labels(self, occ_uris: List[str], page_size: int = 500):
        """
           Resolves occupation URIs into human-readable sector labels.

           This method enriches job data by mapping ESCO occupation identifiers
           to their corresponding sector names. The results are cached in `self.sector_map`
           to avoid redundant API calls.

           Args:
               occ_uris (List[str]): List of occupation identifiers (ESCO URIs).
               page_size (int): Pagination size for API requests.

           Behavior:
               - Filters out already known URIs using internal cache.
               - Fetches data in batches (size=40).
               - Updates `self.sector_map` with {occupation_id: label}.

           External Dependencies:
               - POST {TRACKER_API}/occupations

           Side Effects:
               - Modifies `self.sector_map`

           Early Exit:
               - Returns immediately if `stop_requested` is True.
           """

        uris = [str(u).strip() for u in occ_uris if u and str(u).strip() not in self.sector_map]

        if not uris or self.stop_requested: return

        if not self.token: await self._get_token()

        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.stop_requested: break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/occupations",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"ids": batch}
                )
                if res.status_code == 200:
                    for o in res.json().get("items", []):
                        # Salviamo l'ID e la label (Preferred Label)
                        self.sector_map[str(o.get("id")).strip()] = str(o.get("label", ""))
            except:
                continue

    def get_regional_projections(self, jobs: List[dict], demo: bool = False):
        """
           Computes geographical projections of job data across NUTS hierarchy levels.

           This method aggregates job postings by location and derives regional
           intelligence using both raw location codes and hierarchical NUTS levels
           (NUTS1, NUTS2, NUTS3).

           It also calculates the Location Quotient (LQ) to measure skill specialization.

           Args:
               jobs (List[dict]): List of job postings.
               demo (bool): If True, simulates NUTS-level granularity when only
                            national codes are available.

           Returns:
               dict:
                   {
                       "raw": [...],
                       "nuts1": [...],
                       "nuts2": [...],
                       "nuts3": [...]
                   }

           Key Concepts:
               - Market Share: % of total jobs in a region
               - Specialization (LQ): relative concentration of a skill in a region

           Behavior:
               - Aggregates job counts per region
               - Aggregates skill counts per region
               - Computes LQ per skill
               - Returns top skills per region

           Note:
               In demo mode, NUTS codes are synthetically generated using index-based distribution.
           """
        raw_map = {}
        nuts_map = {"NUTS1": {}, "NUTS2": {}, "NUTS3": {}}
        global_counts = {}
        total_jobs = len(jobs) if jobs else 1
        for idx, job in enumerate(jobs):
            # Prendiamo il location_code originale (es. "IT", "SE", "FR")
            loc_original = str(job.get("location_code", "EU")).strip()

            # Estraiamo il prefisso nazione (primi 2 caratteri)

            # Se il codice è solo nazionale (lungo 2), generiamo un NUTS3 dinamico
            if demo and len(loc_original) <= 2:
                country_prefix = loc_original[:2].upper() if len(loc_original) >= 2 else "EU"

                # Creiamo una scomposizione "pseudo-reale" usando l'indice
                # NUTS structure: [CC][Level1][Level2][Level3] -> ES: IT 1 2 1
                l1 = (idx % 3) + 1  # Varia tra 1 e 3
                l2 = (idx % 4) + 1  # Varia tra 1 e 4
                l3 = (idx % 5)  # Varia tra 0 e 4
                loc_projected = f"{country_prefix}{l1}{l2}{l3}"
            else:
                loc_projected = loc_original

            # -----------------------

            nuts_levels = {
                "NUTS1": loc_projected[:3],  # Es: ITC
                "NUTS2": loc_projected[:4] if len(loc_projected) >= 4 else None,  # Es: ITC4
                "NUTS3": loc_projected if len(loc_projected) >= 5 else None  # Es: ITC4C

            }

            # 2. INCREMENTO JOB COUNT (Una sola volta per job!)
            # Strategia RAW
            if loc_original not in raw_map: raw_map[loc_original] = {"count": 0, "skills": {}}
            raw_map[loc_original]["count"] += 1

            # Strategia NUTS
            for level, code in nuts_levels.items():
                if code:
                    if code not in nuts_map[level]: nuts_map[level][code] = {"count": 0, "skills": {}}
                    nuts_map[level][code]["count"] += 1

            # 3. AGGREGAZIONE SKILLS
            for s_uri in job.get("skills", []):
                label = self.skill_map.get(s_uri, {}).get("label", s_uri)

                # Update globale per LQ
                global_counts[label] = global_counts.get(label, 0) + 1

                # Update RAW
                raw_map[loc_original]["skills"][label] = raw_map[loc_original]["skills"].get(label, 0) + 1

                # Update NUTS
                for level, code in nuts_levels.items():
                    if code:
                        node_skills = nuts_map[level][code]["skills"]
                        node_skills[label] = node_skills.get(label, 0) + 1

        # --- FORMATTAZIONE FINALE (Invariata) ---
        def format_output(source_map):
            formatted = []
            for code, data in source_map.items():
                skills_list = []
                for s_name, count in data["skills"].items():
                    # Calcolo Location Quotient (Specializzazione)
                    lq = (count / data["count"]) / (global_counts[s_name] / total_jobs)
                    skills_list.append({
                        "skill": s_name,
                        "count": count,
                        "specialization": round(lq, 2)
                    })
                formatted.append({
                    "code": code,
                    "total_jobs": data["count"],
                    "market_share": round((data["count"] / total_jobs) * 100, 2),
                    "top_skills": sorted(skills_list, key=lambda x: x["count"], reverse=True)[:10]
                })
            return sorted(formatted, key=lambda x: x["total_jobs"], reverse=True)

        return {
            "raw": format_output(raw_map),
            "nuts1": format_output(nuts_map["NUTS1"]),
            "nuts2": format_output(nuts_map["NUTS2"]),
            "nuts3": format_output(nuts_map["NUTS3"])
        }

    async def fetch_all_jobs(self, filters: dict, page_size: int=500):
        """
           Fetches all job postings from the Tracker API using pagination and caching.

           This method orchestrates the retrieval of job data based on user-defined filters.
           It supports persistent caching to avoid redundant API calls for identical queries.

           Args:
               filters (dict): Query parameters (keywords, date range, etc.).
               page_size (int): Number of records per API request.

           Returns:
               List[dict]: List of job postings retrieved from the API or cache.

           Behavior:
               - Generates a hash signature for the query
               - Checks disk cache (`cache_data/`)
               - If cache miss:
                   - Fetches paginated results from API
                   - Stores results in cache
               - Supports cooperative stop via `stop_requested`

           External Dependencies:
               - POST {TRACKER_API}/jobs

           Failure Handling:
               - Handles ReadTimeout gracefully
               - Logs errors and returns partial results if interrupted

           Side Effects:
               - Writes cache files to disk
           """
        # Non resettiamo stop_requested qui, lo facciamo negli endpoint all'inizio
        query_sig = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()
        cache_dir, cache_file = "cache_data", f"cache_data/search_{query_sig}.json"

        if os.path.exists(cache_file):
            logger.info(f"Cache Hit: {query_sig}")
            with open(cache_file, 'r') as f: return json.load(f)

        if not self.token: await self._get_token()

        all_jobs, page = [], 1
        headers = {"Authorization": f"Bearer {self.token}"}

        while True:
            if self.stop_requested:
                logger.warning("Fetch fermato per stop richiesto.")
                break

            try:
                res = await self.client.post(
                    f"{self.api_url}/jobs",
                    headers=headers,
                    data=filters,
                    params={"page": page, "page_size": page_size}
                )

                if res.status_code != 200: break
                data = res.json()
                items = data.get("items", [])
                all_jobs.extend(items)

                total = data.get("count", 0)
                logger.info(f"Fetching: {len(all_jobs)}/{total} (Pagina {page})")

                if len(all_jobs) >= total or not items: break
                page += 1
                await asyncio.sleep(0.01)  # Checkpoint per event loop

            except httpx.ReadTimeout:
                logger.error("Timeout durante il fetch. L'API Tracker è lenta.")
                break
            except Exception as e:
                logger.error(f"Errore fetch: {e}")
                break

        if not self.stop_requested and all_jobs:
            if not os.path.exists(cache_dir): os.makedirs(cache_dir)
            with open(cache_file, 'w') as f:
                json.dump(all_jobs, f)

        return all_jobs

    async def fetch_skill_names(self, skill_uris: List[str], page_size : int = 500):
        """
            Resolves skill URIs into enriched skill metadata (label + Twin Transition tags).

            This method translates ESCO skill identifiers into human-readable labels
            and assigns semantic tags for:
                - Digital skills
                - Green skills

            Args:
                skill_uris (List[str]): List of skill identifiers.
                page_size (int): Pagination size for API requests.

            Behavior:
                - Filters already known skills using cache
                - Fetches data in batches
                - Applies heuristic keyword matching to classify:
                    - is_digital
                    - is_green
                - Stores results in `self.skill_map`

            External Dependencies:
                - POST {TRACKER_API}/skills

            Side Effects:
                - Modifies `self.skill_map`

            Early Exit:
                - Returns immediately if `stop_requested` is True.
            """
        uris = [u for u in skill_uris if u not in self.skill_map]
        if not uris or self.stop_requested: return

        if not self.token:
            await self._get_token()

        GREEN_KEYWORDS = {
            "sustainable", "sustainable", "ecology", "circular", "carbon", "renewable",
            "energy", "photovoltaic", "recycling", "environmental", "climate", "efficiency"
        }
        DIGITAL_KEYWORDS = {
            "software", "digital", "ai", "artificial intelligence", "coding", "cloud",
            "data", "computing", "cybersecurity", "web", "automation", "programming"
        }
        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.stop_requested: break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/skills",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"ids": batch, "keywords_logic": "or"},
                    params={"page": 1, "page_size": page_size}
                )
                if res.status_code == 200:
                    for s in res.json().get("items", []):
                        s_id = s.get("id")
                        label = s.get("label")

                        # Intelligence: Tagging Twin Transition (Logica euristica basata su metadati o URI)
                        # Nota: In produzione qui interrogheremmo i metadati ESCO
                        is_green = any(word in label for word in GREEN_KEYWORDS)
                        is_digital = any(word in label for word in DIGITAL_KEYWORDS)
                        self.skill_map[s_id] = {
                            "label": label,
                            "is_green": is_green,
                            "is_digital": is_digital
                        }
            except:
                continue

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
            if self.stop_requested: break
            if i > 0 and i % 2000 == 0: await asyncio.sleep(0)

            # 1. Identificazione Settore
            for i, job in enumerate(raw_jobs):
                # 1. Identificazione Settore (Retrocompatibile)
                job_occs = job.get("occupations", [])
                legacy_occ = job.get("occupation_id")

                if job_occs:
                    occ_id = str(job_occs[0]).strip()
                elif legacy_occ:
                    occ_id = str(legacy_occ).strip()
                else:
                    occ_id = "Unclassified"

                sector_name = self.sector_map.get(occ_id, "Settore non specificato")
                sec_cnt[sector_name] += 1

            # 2. Conteggio standard
            e_cnt[job.get("organization_name") or "N/D"] += 1
            t_cnt[job.get("title") or "N/D"] += 1
            l_cnt[job.get("location_code") or "N/D"] += 1

            # 3. Matrice Skill-Settore (Qui potresti voler associare la skill a TUTTI i settori del job)
            for s_uri in job.get("skills", []):
                s_uri = str(s_uri).strip()
                s_cnt[s_uri] += 1
                if s_uri not in skill_sector_map:
                    skill_sector_map[s_uri] = Counter()

                # Associamo la skill al settore principale trovato sopra
                skill_sector_map[s_uri][sector_name] += 1

        # 4. Arricchimento nomi (Skill + Settori)
        await self.fetch_skill_names(list(s_cnt.keys()))

        # 5. Output con Intelligence
        enriched_ranking = []
        for k, v in s_cnt.most_common():
            skill_info = self.skill_map.get(k, {"label": k.split('/')[-1], "is_green": False, "is_digital": False})

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
        """Restituisce la struttura vuota coerente con il contratto della Dashboard."""
        return {
            "ranking": [],
            "sectors": [],
            "job_titles": [],
            "employers": [],
            "trends": {
                "market_health": {"status": "no_data", "volume_growth_percentage": 0},
                "trends": []
            }
        }

    # --- METODO PRIVATO CONDIVISO (IL CERVELLO) ---
    def _compare_periods(self, res_a, res_b):
        """Calcola i delta e arricchisce con Intelligence (Phase 1)."""
        dict_a = {s["skill_id"]: s for s in res_a["rankings"]["skills"]}
        dict_b = {s["skill_id"]: s for s in res_b["rankings"]["skills"]}
        trends = []

        for s_id in set(list(dict_a.keys()) + list(dict_b.keys())):
            v_a = dict_a.get(s_id, {}).get("frequency", 0)
            info_b = dict_b.get(s_id, {})
            v_b = info_b.get("frequency", 0)

            name = info_b.get("name") or dict_a.get(s_id, {}).get("name")
            primary_sector = info_b.get("primary_sector", "N/D")

            if v_a == 0:
                growth, t_type = "new_entry", "emerging"
            elif v_b == 0:
                growth, t_type = -100.0, "declining"
            else:
                growth = round(((v_b - v_a) / v_a) * 100, 2)
                t_type = "emerging" if growth > 0 else "declining" if growth < 0 else "stable"



            trends.append({
                "name": name,
                "growth": growth,
                "trend_type": t_type,
                "primary_sector": primary_sector,
                "is_green": info_b.get("is_green", False),
                "is_digital": info_b.get("is_digital", False)
            })

        trends.sort(key=lambda x: float('inf') if x["growth"] == "new_entry" else x["growth"], reverse=True)
        vol_growth = round(((res_b["total_jobs"] - res_a["total_jobs"]) / res_a["total_jobs"] * 100), 2) if res_a[
                                                                                                                "total_jobs"] > 0 else 0

        return {
            "market_health": {
                "status": "expanding" if vol_growth > 0 else "shrinking",
                "volume_growth_percentage": vol_growth
            },
            "trends": trends
        }

    # --- METODO 1: OTTIMIZZATO (IN-MEMORY) ---
    async def calculate_trends_from_data(self, all_jobs: List[dict], min_date: str, max_date: str):
        mid = self._get_midpoint(min_date, max_date)
        jobs_a = [j for j in all_jobs if j.get("upload_date", "") <= mid]
        jobs_b = [j for j in all_jobs if j.get("upload_date", "") > mid]

        res_a = await self.analyze_market_data(jobs_a)
        res_b = await self.analyze_market_data(jobs_b)
        return self._compare_periods(res_a, res_b)

    # --- METODO 2: STANDALONE (CON FETCH) ---
    async def calculate_smart_trends(self, base_filters: dict, min_date: str, max_date: str):
        mid = self._get_midpoint(min_date, max_date)
        f_a = {**base_filters, "min_upload_date": min_date, "max_upload_date": mid}
        f_b = {**base_filters, "min_upload_date": mid, "max_upload_date": max_date}  # Semplificato per brevità

        res_a = await self.analyze_market_data(await self.fetch_all_jobs(f_a))
        if self.stop_requested: return self._stop_trend_res()

        res_b = await self.analyze_market_data(await self.fetch_all_jobs(f_b))
        return self._compare_periods(res_a, res_b)

    def _get_midpoint(self, d1, d2):
        dt1, dt2 = datetime.strptime(d1, "%Y-%m-%d"), datetime.strptime(d2, "%Y-%m-%d")
        return (dt1 + timedelta(days=(dt2 - dt1).days // 2)).strftime("%Y-%m-%d")


engine = ProjectorEngine()



@app.post("/projector/analyze-skills", response_model=ProjectorResponse)
async def analyze_skills(
        keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        min_date: str = Form(...),
        max_date: str = Form(...),
        page: int = Form(1),
        page_size: int = Form(50),
        demo: bool = Form(False)
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
    engine.stop_requested = False

    # Costruzione payload pulita
    payload = {
        "keywords": keywords,
        "location_code": locations,
        "min_upload_date": min_date,
        "max_upload_date": max_date
    }
    clean_payload = {k: v for k, v in payload.items() if v is not None}

    # FETCH UNICO
    raw = await engine.fetch_all_jobs(clean_payload)

    # FIX: Se non ci sono job, restituiamo subito la struttura coerente
    if not raw:
        return {
            "status": "completed",
            "dimension_summary": {"jobs_analyzed": 0, "geo_breakdown": []},
            "insights": engine._empty_insights_p1()  # <--- Coerenza qui
        }

    # Traduzione settori (Phase 1)
    all_occs = []
    all_skills = []
    for j in raw:
        all_occs.extend(j.get("occupations", []))
        all_skills.extend(j.get("skills", []))  # <--- Aggiungiamo questo!

    occ_uris = list(set(all_occs))  # Rimuove i duplicati

    await engine.fetch_occupation_labels(occ_uris)
    await engine.fetch_skill_names(list(set(all_skills)))  # <--- Traduciamo tutto il set

    # Analisi globale
    analysis = await engine.analyze_market_data(raw)

    # Trend in memoria (Single Fetch optimization)
    trends = await engine.calculate_trends_from_data(raw, min_date, max_date)

    regional_projections = engine.get_regional_projections(raw, demo=demo)

    start = (page - 1) * page_size

    return {
        "status": "completed" if not engine.stop_requested else "stopped",
        "dimension_summary": {
            "jobs_analyzed": analysis["total_jobs"],
            "geo_breakdown": analysis["geo"]
        },
        "insights": {
            "ranking": analysis["rankings"]["skills"][start: start + page_size],
            "sectors": analysis["rankings"]["sectors"],
            "job_titles": analysis["rankings"]["job_titles"],
            "employers": analysis["rankings"]["employers"],
            "trends": trends,
            "regional": regional_projections  # <--- Inserito qui
        }
    }
@app.post("/projector/emerging-skills", response_model=EmergingSkillsResponse)
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
    engine.stop_requested = False
    res = await engine.calculate_smart_trends({"keywords": keywords} if keywords else {}, min_date, max_date)
    return {"status": "completed" if not engine.stop_requested else "stopped", "insights": res}


@app.post("/projector/stop",response_model=StopResponse )
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

    engine.request_stop()
    return {"status": "signal_sent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
