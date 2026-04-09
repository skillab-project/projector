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

    async def fetch_all_jobs(self, filters: dict):
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
                    params={"page": page, "page_size": 100}
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

    async def fetch_skill_names(self, skill_uris: List[str]):
        uris = [u for u in skill_uris if u not in self.skill_map]
        if not uris or self.stop_requested: return

        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.stop_requested: break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/skills",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"ids": batch, "keywords_logic": "or"},
                    params={"page": 1, "page_size": 50}
                )
                if res.status_code == 200:
                    for s in res.json().get("items", []):
                        self.skill_map[s.get("id")] = s.get("label")
            except:
                continue

    async def analyze_market_data(self, raw_jobs: List[dict]):
        if not raw_jobs: return self._empty_res()

        s_cnt, e_cnt, t_cnt, l_cnt = Counter(), Counter(), Counter(), Counter()
        for i, job in enumerate(raw_jobs):
            if self.stop_requested: break

            if i > 0 and i % 2000 == 0:
                await asyncio.sleep(0)  # Permette al segnale di stop di entrare

            e_cnt[job.get("organization_name") or "N/D"] += 1
            t_cnt[job.get("title") or "N/D"] += 1
            l_cnt[job.get("location_code") or "N/D"] += 1
            for s in job.get("skills", []): s_cnt[str(s).strip()] += 1

        await self.fetch_skill_names(list(s_cnt.keys()))

        return {
            "total_jobs": len(raw_jobs),
            "rankings": {
                "skills": [{"name": self.skill_map.get(k, k.split('/')[-1]), "frequency": v, "skill_id": k}
                           for k, v in s_cnt.most_common()],
                "employers": [{"name": k, "count": v} for k, v in e_cnt.most_common(10)],
                "job_titles": [{"name": k, "count": v} for k, v in t_cnt.most_common(10)]
            },
            "geo": [{"location": k, "job_count": v} for k, v in l_cnt.most_common()]
        }

    def _empty_res(self):
        return {"total_jobs": 0, "rankings": {"skills": [], "employers": [], "job_titles": []}, "geo": []}

    async def calculate_smart_trends(self, base_filters: dict, min_date: str, max_date: str):
        d1, d2 = datetime.strptime(min_date, "%Y-%m-%d"), datetime.strptime(max_date, "%Y-%m-%d")
        mid = d1 + timedelta(days=(d2 - d1).days // 2)

        f_a = {**base_filters, "min_upload_date": min_date, "max_upload_date": mid.strftime("%Y-%m-%d")}
        f_b = {**base_filters, "min_upload_date": (mid + timedelta(days=1)).strftime("%Y-%m-%d"),
               "max_upload_date": max_date}

        logger.info("Trend Periodo A...")
        jobs_a = await self.fetch_all_jobs(f_a)
        res_a = await self.analyze_market_data(jobs_a)

        # SHORT-CIRCUIT: Se è stato premuto stop, non facciamo il periodo B
        if self.stop_requested:
            return {"market_health": {"status": "interrupted", "volume_growth_percentage": 0}, "trends": []}

        logger.info("Trend Periodo B...")
        jobs_b = await self.fetch_all_jobs(f_b)
        res_b = await self.analyze_market_data(jobs_b)

        if self.stop_requested:
            return {"market_health": {"status": "interrupted", "volume_growth_percentage": 0}, "trends": []}

        # Calcolo delta
        dict_a = {s["skill_id"]: s for s in res_a["rankings"]["skills"]}
        dict_b = {s["skill_id"]: s for s in res_b["rankings"]["skills"]}
        trends = []

        for s_id in set(list(dict_a.keys()) + list(dict_b.keys())):
            v_a, v_b = dict_a.get(s_id, {}).get("frequency", 0), dict_b.get(s_id, {}).get("frequency", 0)
            name = dict_a.get(s_id, {}).get("name") or dict_b.get(s_id, {}).get("name")
            if v_a == 0:
                growth, t_type = "new_entry", "emerging"
            elif v_b == 0:
                growth, t_type = -100.0, "declining"
            else:
                growth = round(((v_b - v_a) / v_a) * 100, 2)
                t_type = "emerging" if growth > 0 else "declining" if growth < 0 else "stable"
            trends.append({"name": name, "growth": growth, "trend_type": t_type})

        trends.sort(key=lambda x: float('inf') if x["growth"] == "new_entry" else x["growth"], reverse=True)
        vol_growth = round(((res_b["total_jobs"] - res_a["total_jobs"]) / res_a["total_jobs"] * 100), 2) if res_a[
                                                                                                                "total_jobs"] > 0 else 0

        return {
            "market_health": {"status": "expanding" if vol_growth > 0 else "shrinking",
                              "volume_growth_percentage": vol_growth},
            "trends": trends
        }


engine = ProjectorEngine()


@app.post("/projector/analyze-skills")
async def analyze_skills(keywords: Optional[List[str]] = Form(None), locations: Optional[List[str]] = Form(None),
                         min_date: Optional[str] = Form(None), max_date: Optional[str] = Form(None),
                         page: int = Form(1), page_size: int = Form(50)):
    engine.stop_requested = False  # Resettiamo lo stato all'inizio di ogni richiesta
    payload = {k: v for k, v in {"keywords": keywords, "location_code": locations,
                                 "min_upload_date": min_date, "max_upload_date": max_date}.items() if v}
    raw = await engine.fetch_all_jobs(payload)
    analysis = await engine.analyze_market_data(raw)
    start = (page - 1) * page_size
    return {
        "status": "completed" if not engine.stop_requested else "stopped",
        "dimension_summary": {"jobs_analyzed": analysis["total_jobs"], "geo_breakdown": analysis["geo"]},
        "insights": {"ranking": analysis["rankings"]["skills"][start: start + page_size],
                     "job_titles": analysis["rankings"]["job_titles"], "employers": analysis["rankings"]["employers"]}
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