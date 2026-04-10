import asyncio
import hashlib
import json
import logging
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Form

from schemas_sectoral import ProjectorResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
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
        self.stop_requested = False
        self.client = httpx.AsyncClient(timeout=None)

        self.skill_map: Dict[str, Dict] = {}
        self.occupation_api_map: Dict[str, Dict] = {}
        self.occupation_catalog: Dict[str, Dict] = {}
        self.isco_groups: Dict[str, Dict] = {}
        self.occupation_skill_relations: Dict[str, Counter] = defaultdict(Counter)
        self.skill_hierarchy: Dict[str, Dict] = {}
        self.matrix_profiles: Dict[str, Dict[str, Dict]] = {}

        self._load_local_resources()

    def request_stop(self):
        self.stop_requested = True
        logger.warning("Stop requested.")

    async def _get_token(self):
        try:
            resp = await self.client.post(
                f"{self.api_url}/login",
                json={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            self.token = resp.text.replace('"', "")
            return self.token
        except Exception as e:
            logger.error("Login error: %s", e)
            return None

    def _load_local_resources(self):
        base = Path("/mnt/data")
        try:
            occ_path = base / "occupations_lt.csv"
            if occ_path.exists():
                occ_df = pd.read_csv(occ_path)
                for _, row in occ_df.iterrows():
                    occ_uri = str(row.get("conceptUri", "")).strip()
                    if not occ_uri:
                        continue
                    isco_code = self._safe_int(row.get("iscoGroup"))
                    self.occupation_catalog[occ_uri] = {
                        "label": row.get("preferredLabel"),
                        "isco_code": isco_code,
                        "nace_code": row.get("naceCode"),
                    }

            isco_path = base / "ISCOGroups_lt.csv"
            if isco_path.exists():
                isco_df = pd.read_csv(isco_path)
                for _, row in isco_df.iterrows():
                    uri = str(row.get("conceptUri", "")).strip()
                    if not uri:
                        continue
                    self.isco_groups[uri] = {
                        "label": row.get("preferredLabel"),
                        "code": str(row.get("code")),
                    }

            rel_path = base / "occupationSkillRelations_lt.csv"
            if rel_path.exists():
                rel_df = pd.read_csv(rel_path)
                rel_df = rel_df[rel_df["skillType"] == "skill/competence"]
                for _, row in rel_df.iterrows():
                    occ_uri = str(row.get("occupationUri", "")).strip()
                    skill_uri = str(row.get("skillUri", "")).strip()
                    if not occ_uri or not skill_uri:
                        continue
                    weight = 1.0 if str(row.get("relationType", "")).lower() == "essential" else 0.5
                    self.occupation_skill_relations[occ_uri][skill_uri] += weight
                    if skill_uri not in self.skill_map:
                        self.skill_map[skill_uri] = {
                            "label": row.get("skillLabel", skill_uri.split("/")[-1]),
                            "is_green": False,
                            "is_digital": False,
                        }

            sh_path = base / "skillsHierarchy_lt.csv"
            if sh_path.exists():
                sh_df = pd.read_csv(sh_path)
                for _, row in sh_df.iterrows():
                    skill_uri = str(row.get("Level 0 URI", "")).strip()
                    if not skill_uri:
                        continue
                    self.skill_hierarchy[skill_uri] = {
                        1: {
                            "uri": self._as_uri(row.get("Level 1 URI")),
                            "label": self._as_str(row.get("Level 1 preferred term")),
                        },
                        2: {
                            "uri": self._as_uri(row.get("Level 2 URI")),
                            "label": self._as_str(row.get("Level 2 preferred term")),
                        },
                        3: {
                            "uri": self._as_uri(row.get("Level 3 URI")),
                            "label": self._as_str(row.get("Level 3 preferred term")),
                        },
                    }

            matrix_path = base / "Skills_Occupations Matrix Tables_ESCOv1.2.0_1.xlsx"
            if matrix_path.exists():
                for sheet in ["Matrix 1.1", "Matrix 2.2", "Matrix 2.3"]:
                    try:
                        df = pd.read_excel(matrix_path, sheet_name=sheet)
                        self.matrix_profiles[sheet] = self._parse_matrix_sheet(df)
                    except Exception as e:
                        logger.warning("Could not load sheet %s: %s", sheet, e)
        except Exception as e:
            logger.warning("Local resource loading failed: %s", e)

    @staticmethod
    def _safe_int(value):
        try:
            if pd.isna(value):
                return None
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _as_uri(value):
        if pd.isna(value):
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _as_str(value):
        if pd.isna(value):
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _parse_matrix_sheet(df: pd.DataFrame) -> Dict[str, Dict]:
        parsed: Dict[str, Dict] = {}
        if df.empty:
            return parsed

        skill_columns = list(df.columns[2:])
        skill_labels = {}
        if len(df) > 0:
            header_row = df.iloc[0]
            for col in skill_columns:
                skill_labels[col] = header_row.get(col)

        for idx in range(1, len(df)):
            row = df.iloc[idx]
            occ_group = row.iloc[0]
            occ_label = row.iloc[1]
            if pd.isna(occ_group):
                continue
            shares = {}
            for col in skill_columns:
                value = row.get(col)
                if pd.isna(value):
                    continue
                shares[col] = {
                    "label": skill_labels.get(col, col),
                    "share": float(value),
                }
            parsed[str(occ_group).strip()] = {
                "label": None if pd.isna(occ_label) else str(occ_label).strip(),
                "shares": shares,
            }
        return parsed

    async def fetch_occupation_details(self, occ_uris: List[str], page_size: int = 500):
        uris = [str(u).strip() for u in occ_uris if u and str(u).strip() not in self.occupation_api_map]
        if not uris or self.stop_requested:
            return
        if not self.token:
            await self._get_token()

        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.stop_requested:
                break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/occupations",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"ids": batch},
                    params={"page": 1, "page_size": page_size},
                )
                if res.status_code == 200:
                    for item in res.json().get("items", []):
                        occ_id = str(item.get("id", "")).strip()
                        if not occ_id:
                            continue
                        self.occupation_api_map[occ_id] = {
                            "label": item.get("label"),
                            "ancestors": item.get("ancestors") or {},
                            "levels": item.get("levels") or {},
                            "children": item.get("children") or {},
                        }
            except Exception:
                continue

    async def fetch_skill_names(self, skill_uris: List[str], page_size: int = 500):
        uris = [u for u in skill_uris if u and u not in self.skill_map]
        if not uris or self.stop_requested:
            return
        if not self.token:
            await self._get_token()

        green_keywords = {
            "sustainable", "ecology", "circular", "carbon", "renewable", "energy", "photovoltaic",
            "recycling", "environmental", "climate", "efficiency", "green",
        }
        digital_keywords = {
            "software", "digital", "ai", "artificial intelligence", "coding", "cloud", "data",
            "computing", "cybersecurity", "web", "automation", "programming", "python", "sql",
        }
        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.stop_requested:
                break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/skills",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"ids": batch, "keywords_logic": "or"},
                    params={"page": 1, "page_size": page_size},
                )
                if res.status_code == 200:
                    for s in res.json().get("items", []):
                        s_id = str(s.get("id", "")).strip()
                        label = str(s.get("label", s_id)).strip()
                        low = label.lower()
                        self.skill_map[s_id] = {
                            "label": label,
                            "is_green": any(w in low for w in green_keywords),
                            "is_digital": any(w in low for w in digital_keywords),
                        }
            except Exception:
                continue

    async def fetch_all_jobs(self, filters: dict, page_size: int = 500):
        query_sig = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()
        cache_dir, cache_file = "cache_data", f"cache_data/search_{query_sig}.json"
        if os.path.exists(cache_file):
            logger.info("Cache hit: %s", query_sig)
            with open(cache_file, "r") as f:
                return json.load(f)

        if not self.token:
            await self._get_token()
        all_jobs, page = [], 1
        headers = {"Authorization": f"Bearer {self.token}"}

        while True:
            if self.stop_requested:
                break
            try:
                res = await self.client.post(
                    f"{self.api_url}/jobs",
                    headers=headers,
                    data=filters,
                    params={"page": page, "page_size": page_size},
                )
                if res.status_code != 200:
                    break
                data = res.json()
                items = data.get("items", [])
                all_jobs.extend(items)
                total = data.get("count", 0)
                if len(all_jobs) >= total or not items:
                    break
                page += 1
                await asyncio.sleep(0.01)
            except httpx.ReadTimeout:
                logger.error("Timeout during fetch_all_jobs")
                break
            except Exception as e:
                logger.error("Fetch error: %s", e)
                break

        if not self.stop_requested and all_jobs:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(all_jobs, f)
        return all_jobs

    @staticmethod
    def _get_job_occupations(job: dict) -> List[str]:
        occs = [str(o).strip() for o in job.get("occupations", []) if str(o).strip()]
        legacy = str(job.get("occupation_id", "")).strip()
        if legacy and legacy not in occs:
            occs.append(legacy)
        return occs

    def _infer_sector_for_occupation(self, occ_id: str, occupation_level: int) -> Dict[str, str]:
        cat = self.occupation_catalog.get(occ_id, {})
        api = self.occupation_api_map.get(occ_id, {})
        occ_label = cat.get("label") or api.get("label") or occ_id.split("/")[-1]
        isco_code = cat.get("isco_code")

        if isco_code is not None:
            group_uri = self._isco_group_uri(isco_code, occupation_level)
            group_meta = self.isco_groups.get(group_uri, {})
            return {
                "occupation_label": occ_label,
                "sector_code": group_uri,
                "sector_label": group_meta.get("label") or group_uri.split("/")[-1],
            }

        ancestors = api.get("ancestors") or {}
        if ancestors:
            values = []
            if isinstance(ancestors, dict):
                for _, v in ancestors.items():
                    if isinstance(v, dict):
                        values.append(v.get("label") or v.get("preferredLabel") or v.get("id"))
                    else:
                        values.append(v)
            values = [str(v).strip() for v in values if v]
            if values:
                chosen = values[min(len(values) - 1, max(0, occupation_level - 1))]
                return {
                    "occupation_label": occ_label,
                    "sector_code": f"api::{chosen}",
                    "sector_label": chosen,
                }

        return {
            "occupation_label": occ_label,
            "sector_code": "unclassified",
            "sector_label": "Unclassified",
        }

    @staticmethod
    def _isco_group_uri(isco_code: int, level: int) -> str:
        code_str = str(int(isco_code))
        if code_str == "0":
            prefix = "0"
        else:
            prefix = code_str[: max(1, min(level, len(code_str)))]
        return f"http://data.europa.eu/esco/isco/C{prefix}"

    def _skill_group(self, skill_id: str, skill_group_level: int) -> Dict[str, Optional[str]]:
        hierarchy = self.skill_hierarchy.get(skill_id, {})
        meta = hierarchy.get(skill_group_level) or {}
        if meta.get("uri") or meta.get("label"):
            return {"uri": meta.get("uri"), "label": meta.get("label")}
        return {"uri": None, "label": None}

    def _matrix_sheet_name(self, skill_group_level: int, occupation_level: int) -> str:
        return f"Matrix {skill_group_level}.{occupation_level}"

    @staticmethod
    def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> Optional[float]:
        keys = set(vec_a) | set(vec_b)
        if not keys:
            return None
        dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in keys)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return None
        return round(dot / (norm_a * norm_b), 4)

    def get_sectoral_projections(
        self,
        jobs: List[dict],
        occupation_level: int = 1,
        skill_group_level: int = 1,
        top_k: int = 10,
    ) -> Dict:
        total_jobs = len(jobs)
        if total_jobs == 0:
            return {"occupation_level": occupation_level, "skill_group_level": skill_group_level, "sectors": []}

        sheet_name = self._matrix_sheet_name(skill_group_level, occupation_level)
        matrix = self.matrix_profiles.get(sheet_name, {})
        sectors = defaultdict(lambda: {
            "label": None,
            "jobs": 0,
            "occupations": Counter(),
            "observed_skills": Counter(),
            "canonical_skills": Counter(),
            "observed_groups": Counter(),
            "digital": 0,
            "green": 0,
            "skill_events": 0,
        })

        for job in jobs:
            occs = self._get_job_occupations(job)
            if not occs:
                occs = ["unclassified"]
            sector_infos = []
            for occ_id in occs:
                info = self._infer_sector_for_occupation(occ_id, occupation_level)
                sector_infos.append((occ_id, info))

            unique_sectors = {}
            for occ_id, info in sector_infos:
                unique_sectors[info["sector_code"]] = info["sector_label"]
                sectors[info["sector_code"]]["label"] = info["sector_label"]
                sectors[info["sector_code"]]["occupations"][info["occupation_label"]] += 1
                for skill_id, weight in self.occupation_skill_relations.get(occ_id, {}).items():
                    sectors[info["sector_code"]]["canonical_skills"][skill_id] += weight

            for sector_code in unique_sectors:
                sectors[sector_code]["jobs"] += 1

            for skill_id in [str(s).strip() for s in job.get("skills", []) if str(s).strip()]:
                skill_info = self.skill_map.get(skill_id, {"label": skill_id.split("/")[-1], "is_green": False, "is_digital": False})
                group = self._skill_group(skill_id, skill_group_level)
                for sector_code in unique_sectors:
                    sectors[sector_code]["observed_skills"][skill_id] += 1
                    if group["uri"]:
                        sectors[sector_code]["observed_groups"][group["uri"]] += 1
                    if skill_info.get("is_digital"):
                        sectors[sector_code]["digital"] += 1
                    if skill_info.get("is_green"):
                        sectors[sector_code]["green"] += 1
                    sectors[sector_code]["skill_events"] += 1

        formatted = []
        for sector_code, data in sorted(sectors.items(), key=lambda kv: kv[1]["jobs"], reverse=True):
            jobs_in_sector = data["jobs"]
            obs_total = sum(data["observed_skills"].values()) or 1
            can_total = sum(data["canonical_skills"].values()) or 1
            observed_top = []
            for skill_id, count in data["observed_skills"].most_common(top_k):
                info = self.skill_map.get(skill_id, {"label": skill_id.split("/")[-1], "is_green": False, "is_digital": False})
                group = self._skill_group(skill_id, skill_group_level)
                observed_top.append({
                    "name": info["label"],
                    "count": int(count),
                    "frequency": round(count / obs_total, 4),
                    "is_digital": info.get("is_digital", False),
                    "is_green": info.get("is_green", False),
                    "skill_group": group.get("label"),
                })

            canonical_top = []
            for skill_id, weight in data["canonical_skills"].most_common(top_k):
                info = self.skill_map.get(skill_id, {"label": skill_id.split("/")[-1], "is_green": False, "is_digital": False})
                group = self._skill_group(skill_id, skill_group_level)
                canonical_top.append({
                    "name": info["label"],
                    "count": round(float(weight), 3),
                    "frequency": round(float(weight) / can_total, 4),
                    "is_digital": info.get("is_digital", False),
                    "is_green": info.get("is_green", False),
                    "skill_group": group.get("label"),
                })

            observed_groups = []
            observed_group_dist = {}
            obs_group_total = sum(data["observed_groups"].values()) or 1
            for group_uri, count in data["observed_groups"].most_common(top_k):
                label = None
                for skill_id in data["observed_skills"]:
                    meta = self._skill_group(skill_id, skill_group_level)
                    if meta.get("uri") == group_uri:
                        label = meta.get("label")
                        break
                share = round(count / obs_group_total, 4)
                observed_group_dist[group_uri] = share
                observed_groups.append({"group_uri": group_uri, "label": label or group_uri, "share": share})

            matrix_groups = []
            matrix_dist = {}
            matrix_entry = matrix.get(sector_code)
            if matrix_entry:
                for g_uri, payload in sorted(matrix_entry["shares"].items(), key=lambda kv: kv[1]["share"], reverse=True)[:top_k]:
                    matrix_dist[g_uri] = payload["share"]
                    matrix_groups.append({"group_uri": g_uri, "label": payload.get("label") or g_uri, "share": round(payload["share"], 4)})

            formatted.append({
                "sector_code": sector_code,
                "sector_label": data["label"] or sector_code,
                "total_jobs": jobs_in_sector,
                "market_share": round(jobs_in_sector / total_jobs, 4),
                "top_observed_skills": observed_top,
                "top_canonical_skills": canonical_top,
                "observed_skill_groups": observed_groups,
                "matrix_skill_groups": matrix_groups,
                "twin_transition_summary": {
                    "digital_share_observed": round(data["digital"] / data["skill_events"], 4) if data["skill_events"] else 0.0,
                    "green_share_observed": round(data["green"] / data["skill_events"], 4) if data["skill_events"] else 0.0,
                },
                "alignment_score": self._cosine_similarity(observed_group_dist, matrix_dist),
                "sample_occupations": [
                    {"name": name, "count": count}
                    for name, count in data["occupations"].most_common(5)
                ],
            })

        return {
            "occupation_level": occupation_level,
            "skill_group_level": skill_group_level,
            "sectors": formatted,
        }

    async def analyze_market_data(self, raw_jobs: List[dict]):
        if not raw_jobs:
            return self._empty_res()

        s_cnt, e_cnt, t_cnt, l_cnt, sec_cnt = Counter(), Counter(), Counter(), Counter(), Counter()
        skill_sector_map = defaultdict(Counter)

        for idx, job in enumerate(raw_jobs):
            if self.stop_requested:
                break
            if idx > 0 and idx % 2000 == 0:
                await asyncio.sleep(0)

            occs = self._get_job_occupations(job)
            sector_labels = []
            for occ_id in occs or ["unclassified"]:
                info = self._infer_sector_for_occupation(occ_id, occupation_level=1)
                sector_labels.append(info["sector_label"])
                sec_cnt[info["sector_label"]] += 1
            primary_sector = sector_labels[0] if sector_labels else "Unclassified"

            e_cnt[job.get("organization_name") or "N/D"] += 1
            t_cnt[job.get("title") or "N/D"] += 1
            l_cnt[job.get("location_code") or "N/D"] += 1

            for s_uri in [str(s).strip() for s in job.get("skills", []) if str(s).strip()]:
                s_cnt[s_uri] += 1
                skill_sector_map[s_uri][primary_sector] += 1

        await self.fetch_skill_names(list(s_cnt.keys()))
        total_jobs = len(raw_jobs) or 1
        enriched_ranking = []
        for skill_id, count in s_cnt.most_common():
            skill_info = self.skill_map.get(skill_id, {"label": skill_id.split("/")[-1], "is_green": False, "is_digital": False})
            sectors_involved = skill_sector_map[skill_id]
            enriched_ranking.append({
                "name": skill_info["label"],
                "count": int(count),
                "frequency": round(count / total_jobs, 4),
                "skill_id": skill_id,
                "is_green": skill_info.get("is_green", False),
                "is_digital": skill_info.get("is_digital", False),
                "sector_spread": len(sectors_involved),
                "primary_sector": sectors_involved.most_common(1)[0][0] if sectors_involved else "N/D",
            })

        return {
            "total_jobs": len(raw_jobs),
            "rankings": {
                "skills": enriched_ranking,
                "employers": [{"name": k, "count": v} for k, v in e_cnt.most_common(10)],
                "job_titles": [{"name": k, "count": v} for k, v in t_cnt.most_common(10)],
                "sectors": [{"name": k, "count": v} for k, v in sec_cnt.most_common(10)],
            },
            "geo": [{"location": k, "job_count": v} for k, v in l_cnt.most_common()],
        }

    def get_regional_projections(self, jobs: List[dict], demo: bool = False):
        raw_map = {}
        nuts_map = {"NUTS1": {}, "NUTS2": {}, "NUTS3": {}}
        global_counts = {}
        total_jobs = len(jobs) if jobs else 1

        for idx, job in enumerate(jobs):
            loc_original = str(job.get("location_code", "EU")).strip()
            if demo and len(loc_original) <= 2:
                country_prefix = loc_original[:2].upper() if len(loc_original) >= 2 else "EU"
                l1, l2, l3 = (idx % 3) + 1, (idx % 4) + 1, (idx % 5)
                loc_projected = f"{country_prefix}{l1}{l2}{l3}"
            else:
                loc_projected = loc_original

            nuts_levels = {
                "NUTS1": loc_projected[:3],
                "NUTS2": loc_projected[:4] if len(loc_projected) >= 4 else None,
                "NUTS3": loc_projected if len(loc_projected) >= 5 else None,
            }

            raw_map.setdefault(loc_original, {"count": 0, "skills": {}})
            raw_map[loc_original]["count"] += 1

            for level, code in nuts_levels.items():
                if code:
                    nuts_map[level].setdefault(code, {"count": 0, "skills": {}})
                    nuts_map[level][code]["count"] += 1

            for s_uri in job.get("skills", []):
                label = self.skill_map.get(s_uri, {}).get("label", s_uri)
                global_counts[label] = global_counts.get(label, 0) + 1
                raw_map[loc_original]["skills"][label] = raw_map[loc_original]["skills"].get(label, 0) + 1
                for level, code in nuts_levels.items():
                    if code:
                        node_skills = nuts_map[level][code]["skills"]
                        node_skills[label] = node_skills.get(label, 0) + 1

        def format_output(source_map):
            formatted = []
            for code, data in source_map.items():
                skills_list = []
                for s_name, count in data["skills"].items():
                    lq = (count / data["count"]) / (global_counts[s_name] / total_jobs)
                    skills_list.append({"skill": s_name, "count": count, "specialization": round(lq, 2)})
                formatted.append({
                    "code": code,
                    "total_jobs": data["count"],
                    "market_share": round((data["count"] / total_jobs) * 100, 2),
                    "top_skills": sorted(skills_list, key=lambda x: x["count"], reverse=True)[:10],
                })
            return sorted(formatted, key=lambda x: x["total_jobs"], reverse=True)

        return {
            "raw": format_output(raw_map),
            "nuts1": format_output(nuts_map["NUTS1"]),
            "nuts2": format_output(nuts_map["NUTS2"]),
            "nuts3": format_output(nuts_map["NUTS3"]),
        }

    def _empty_res(self):
        return {
            "total_jobs": 0,
            "rankings": {"skills": [], "employers": [], "job_titles": [], "sectors": []},
            "geo": [],
        }

    def _empty_insights(self):
        return {
            "ranking": [],
            "sectors": [],
            "job_titles": [],
            "employers": [],
            "trends": {"market_health": {"status": "no_data", "volume_growth_percentage": 0}, "trends": []},
            "regional": {"raw": [], "nuts1": [], "nuts2": [], "nuts3": []},
            "sectoral": {"occupation_level": 1, "skill_group_level": 1, "sectors": []},
        }

    def _compare_periods(self, res_a, res_b):
        dict_a = {s["skill_id"]: s for s in res_a["rankings"]["skills"]}
        dict_b = {s["skill_id"]: s for s in res_b["rankings"]["skills"]}
        trends = []
        for s_id in set(dict_a) | set(dict_b):
            v_a = dict_a.get(s_id, {}).get("count", 0)
            info_b = dict_b.get(s_id, {})
            v_b = info_b.get("count", 0)
            name = info_b.get("name") or dict_a.get(s_id, {}).get("name")
            primary_sector = info_b.get("primary_sector", "N/D")
            if v_a == 0 and v_b > 0:
                growth, t_type = "new_entry", "emerging"
            elif v_b == 0 and v_a > 0:
                growth, t_type = -100.0, "declining"
            elif v_a == 0:
                growth, t_type = 0.0, "stable"
            else:
                growth = round(((v_b - v_a) / v_a) * 100, 2)
                t_type = "emerging" if growth > 0 else "declining" if growth < 0 else "stable"
            trends.append({
                "name": name,
                "growth": growth,
                "trend_type": t_type,
                "primary_sector": primary_sector,
                "is_green": info_b.get("is_green", False),
                "is_digital": info_b.get("is_digital", False),
            })
        trends.sort(key=lambda x: float("inf") if x["growth"] == "new_entry" else x["growth"], reverse=True)
        vol_growth = round(((res_b["total_jobs"] - res_a["total_jobs"]) / res_a["total_jobs"] * 100), 2) if res_a["total_jobs"] > 0 else 0
        return {"market_health": {"status": "expanding" if vol_growth > 0 else "shrinking", "volume_growth_percentage": vol_growth}, "trends": trends}

    async def calculate_trends_from_data(self, all_jobs: List[dict], min_date: str, max_date: str):
        mid = self._get_midpoint(min_date, max_date)
        jobs_a = [j for j in all_jobs if j.get("upload_date", "") <= mid]
        jobs_b = [j for j in all_jobs if j.get("upload_date", "") > mid]
        res_a = await self.analyze_market_data(jobs_a)
        res_b = await self.analyze_market_data(jobs_b)
        return self._compare_periods(res_a, res_b)

    async def calculate_smart_trends(self, base_filters: dict, min_date: str, max_date: str):
        mid = self._get_midpoint(min_date, max_date)
        f_a = {**base_filters, "min_upload_date": min_date, "max_upload_date": mid}
        f_b = {**base_filters, "min_upload_date": mid, "max_upload_date": max_date}
        res_a = await self.analyze_market_data(await self.fetch_all_jobs(f_a))
        if self.stop_requested:
            return {"market_health": {"status": "stopped", "volume_growth_percentage": 0}, "trends": []}
        res_b = await self.analyze_market_data(await self.fetch_all_jobs(f_b))
        return self._compare_periods(res_a, res_b)

    @staticmethod
    def _get_midpoint(d1, d2):
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
    demo: bool = Form(False),
    occupation_level: int = Form(1),
    skill_group_level: int = Form(1),
    include_sectoral: bool = Form(True),
):
    engine.stop_requested = False
    payload = {
        "keywords": keywords,
        "location_code": locations,
        "min_upload_date": min_date,
        "max_upload_date": max_date,
    }
    clean_payload = {k: v for k, v in payload.items() if v is not None}
    raw = await engine.fetch_all_jobs(clean_payload)

    if not raw:
        return {"status": "completed", "dimension_summary": {"jobs_analyzed": 0, "geo_breakdown": []}, "insights": engine._empty_insights()}

    all_occs = []
    all_skills = []
    for j in raw:
        all_occs.extend(engine._get_job_occupations(j))
        all_skills.extend([str(s).strip() for s in j.get("skills", []) if str(s).strip()])

    await engine.fetch_occupation_details(list(set(all_occs)))
    await engine.fetch_skill_names(list(set(all_skills)))

    analysis = await engine.analyze_market_data(raw)
    trends = await engine.calculate_trends_from_data(raw, min_date, max_date)
    regional = engine.get_regional_projections(raw, demo=demo)
    sectoral = engine.get_sectoral_projections(raw, occupation_level=occupation_level, skill_group_level=skill_group_level) if include_sectoral else {"occupation_level": occupation_level, "skill_group_level": skill_group_level, "sectors": []}

    start = (page - 1) * page_size
    return {
        "status": "completed" if not engine.stop_requested else "stopped",
        "dimension_summary": {"jobs_analyzed": analysis["total_jobs"], "geo_breakdown": analysis["geo"]},
        "insights": {
            "ranking": analysis["rankings"]["skills"][start:start + page_size],
            "sectors": analysis["rankings"]["sectors"],
            "job_titles": analysis["rankings"]["job_titles"],
            "employers": analysis["rankings"]["employers"],
            "trends": trends,
            "regional": regional,
            "sectoral": sectoral,
        },
    }


@app.post("/projector/sectoral-intelligence")
async def sectoral_intelligence(
    keywords: Optional[List[str]] = Form(None),
    locations: Optional[List[str]] = Form(None),
    min_date: str = Form(...),
    max_date: str = Form(...),
    occupation_level: int = Form(1),
    skill_group_level: int = Form(1),
):
    engine.stop_requested = False
    payload = {
        "keywords": keywords,
        "location_code": locations,
        "min_upload_date": min_date,
        "max_upload_date": max_date,
    }
    clean_payload = {k: v for k, v in payload.items() if v is not None}
    raw = await engine.fetch_all_jobs(clean_payload)
    all_occs = []
    all_skills = []
    for j in raw:
        all_occs.extend(engine._get_job_occupations(j))
        all_skills.extend([str(s).strip() for s in j.get("skills", []) if str(s).strip()])
    await engine.fetch_occupation_details(list(set(all_occs)))
    await engine.fetch_skill_names(list(set(all_skills)))
    return {
        "status": "completed" if not engine.stop_requested else "stopped",
        "jobs_analyzed": len(raw),
        "sectoral": engine.get_sectoral_projections(raw, occupation_level=occupation_level, skill_group_level=skill_group_level),
    }


@app.post("/projector/emerging-skills")
async def emerging_skills(min_date: str = Form(...), max_date: str = Form(...), keywords: Optional[List[str]] = Form(None)):
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
