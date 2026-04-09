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
        self.stop_requested = True
        logger.warning("!!! STOP RILEVATO !!! Interruzione programmata dei processi.")

    async def _get_token(self):
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

    # In ProjectorEngine.__init__

    # Nuovo metodo per tradurre le occupazioni (Settori)
    async def fetch_occupation_labels(self, occ_uris: List[str], page_size: int = 500):
        uris = [u for u in occ_uris if u not in self.sector_map]
        if not uris or self.stop_requested: return

        if not self.token:
            await self._get_token()

        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.stop_requested: break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/occupations",  # Endpoint specifico per occupazioni
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"ids": batch},
                    params={"page_size": page_size}


                )
                if res.status_code == 200:
                    for o in res.json().get("items", []):
                        self.sector_map[o.get("id")] = o.get("label")
            except:
                continue

    async def fetch_all_jobs(self, filters: dict, page_size: int=500):
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
        if not raw_jobs: return self._empty_res()

        s_cnt, e_cnt, t_cnt, l_cnt, sec_cnt = Counter(), Counter(), Counter(), Counter(), Counter()
        skill_sector_map = {}  # La matrice Skill -> [Settori]

        for i, job in enumerate(raw_jobs):
            if self.stop_requested: break
            if i > 0 and i % 2000 == 0: await asyncio.sleep(0)

            # 1. Identificazione Settore
            job_occs = job.get("occupations", [])
            if job_occs:
                # Prendiamo la prima occupazione come riferimento per il settore principale del job
                occ_id = str(job_occs[0]).strip()
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
                "name": name, "growth": growth, "trend_type": t_type,
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


@app.post("/projector/analyze-skills")
async def analyze_skills(
        keywords: Optional[List[str]] = Form(None),
        locations: Optional[List[str]] = Form(None),
        min_date: str = Form(...),
        max_date: str = Form(...),
        page: int = Form(1),
        page_size: int = Form(50)
):
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
    for j in raw:
        all_occs.extend(j.get("occupations", []))
    occ_uris = list(set(all_occs))  # Rimuove i duplicati

    await engine.fetch_occupation_labels(occ_uris)

    # Analisi globale
    analysis = await engine.analyze_market_data(raw)

    # Trend in memoria (Single Fetch optimization)
    trends = await engine.calculate_trends_from_data(raw, min_date, max_date)

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
            "trends": trends
        }
    }
@app.post("/projector/emerging-skills")
async def emerging_skills(min_date: str = Form(...), max_date: str = Form(...),
                          keywords: Optional[List[str]] = Form(None)):
    engine.stop_requested = False
    res = await engine.calculate_smart_trends({"keywords": keywords} if keywords else {}, min_date, max_date)
    return {"status": "completed" if not engine.stop_requested else "stopped", "insights": res}


@app.post("/projector/stop")
async def stop():
    engine.request_stop()
    return {"status": "signal_sent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
