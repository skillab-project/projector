import asyncio
import hashlib
import json
import os
from typing import List

import httpx

import logging
from app.core.config import TRACKER_API, TRACKER_USERNAME, TRACKER_PASSWORD

logger = logging.getLogger("SKILLAB-Projector")


class TrackerClient:
    def __init__(self, engine):
        self.api_url = TRACKER_API
        self.username = TRACKER_USERNAME
        self.password = TRACKER_PASSWORD
        self.engine = engine

        self.client = engine.client

    async def fetch_occupation_labels(self, occ_uris: List[str], page_size: int = 500):
        """
           Resolves occupation URIs into human-readable sector labels.

           This method enriches job data by mapping ESCO occupation identifiers
           to their corresponding sector names. The results are cached in `self.engine.sector_map`
           to avoid redundant API calls.

           Args:
               occ_uris (List[str]): List of occupation identifiers (ESCO URIs).
               page_size (int): Pagination size for API requests.

           Behavior:
               - Filters out already known URIs using internal cache.
               - Fetches data in batches (size=40).
               - Updates `self.engine.sector_map` with {occupation_id: label}.

           External Dependencies:
               - POST {TRACKER_API}/occupations

           Side Effects:
               - Modifies `self.engine.sector_map`

           Early Exit:
               - Returns immediately if `stop_requested` is True.
           """

        uris = [str(u).strip() for u in occ_uris if u and str(u).strip() not in self.engine.sector_map]

        if not uris or self.engine.stop_requested: return

        if not self.engine.token: await self._get_token()

        batch_size = 40
        for i in range(0, len(uris), batch_size):
            if self.engine.stop_requested: break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/occupations",
                    headers={"Authorization": f"Bearer {self.engine.token}"},
                    data={"ids": batch}
                )
                if res.status_code == 200:
                    for o in res.json().get("items", []):
                        # Salviamo l'ID e la label (Preferred Label)
                        self.engine.sector_map[str(o.get("id")).strip()] = str(o.get("label", ""))
            except:
                continue

    async def fetch_skill_names(self, skill_uris: List[str], page_size: int = 500):
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
                - Stores results in `self.engine.skill_map`

            External Dependencies:
                - POST {TRACKER_API}/skills

            Side Effects:
                - Modifies `self.engine.skill_map`

            Early Exit:
                - Returns immediately if `stop_requested` is True.
            """
        uris = [u for u in skill_uris if u not in self.engine.skill_map]
        if not uris or self.engine.stop_requested: return

        if not self.engine.token:
            await self._get_token()
        # TODO: Placeholder for Twin Transition tagging (Task 3.5 requirement)
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
            if self.engine.stop_requested: break
            batch = uris[i:i + batch_size]
            try:
                res = await self.client.post(
                    f"{self.api_url}/skills",
                    headers={"Authorization": f"Bearer {self.engine.token}"},
                    data={"ids": batch, "keywords_logic": "or"},
                    params={"page": 1, "page_size": page_size}
                )
                if res.status_code == 200:
                    for s in res.json().get("items", []):
                        s_id = s.get("id")
                        label = s.get("label")

                        # Intelligence: Tagging Twin Transition (Logica euristica basata su metadati o URI)
                        # Nota: In produzione qui interrogheremmo i metadati ESCO
                        # TODO: eliminare is_green, is_digital
                        is_green = False
                        is_digital = False

                        self.engine.skill_map[s_id] = {
                            "label": label,
                            "is_green": is_green,
                            "is_digital": is_digital
                        }
            except:
                continue

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
            self.engine.token = resp.text.replace('"', '')
            return self.engine.token
        except Exception as e:
            logger.error(f"Errore Login: {e}")
            return None

    def _stop_trend_res(self):
        return {
            "market_health": {
                "status": "stopped",
                "volume_growth_percentage": 0.0
            },
            "trends": []
        }

    async def fetch_all_jobs(self, filters: dict, page_size: int = 500):
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

        if not self.engine.token: await self._get_token()

        all_jobs, page = [], 1
        headers = {"Authorization": f"Bearer {self.engine.token}"}

        while True:
            if self.engine.stop_requested:
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

        if not self.engine.stop_requested and all_jobs:
            if not os.path.exists(cache_dir): os.makedirs(cache_dir)
            with open(cache_file, 'w') as f:
                json.dump(all_jobs, f)

        return all_jobs
