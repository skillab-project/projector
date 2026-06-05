import asyncio
import hashlib
import json
import os
import time
from typing import Callable, List, Optional

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

    def _cache_file_for_filters(self, filters: dict):
        query_sig = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()
        return query_sig, "cache_data", f"cache_data/search_{query_sig}.json"

    def _checkpoint_file_for_filters(self, filters: dict):
        query_sig, cache_dir, _cache_file = self._cache_file_for_filters(filters)
        return query_sig, cache_dir, f"{cache_dir}/search_{query_sig}.partial.json"

    def _write_json_atomic(self, path: str, payload):
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(payload, f)
        os.replace(tmp_path, path)

    def load_cached_jobs(self, filters: dict):
        query_sig, _cache_dir, cache_file = self._cache_file_for_filters(filters)
        if not os.path.exists(cache_file):
            logger.info(f"Cache Miss: {query_sig}")
            return None

        logger.info(f"Cache Hit: {query_sig}")
        with open(cache_file, 'r') as f:
            cached_jobs = json.load(f)

        if cached_jobs and not any("sectors" in job for job in cached_jobs):
            logger.info(f"Cache stale without job sectors: {query_sig}")
            return None

        return cached_jobs

    def load_job_fetch_checkpoint(self, filters: dict, page_size: int):
        query_sig, _cache_dir, checkpoint_file = self._checkpoint_file_for_filters(filters)
        if not os.path.exists(checkpoint_file):
            return None

        try:
            with open(checkpoint_file, "r") as f:
                checkpoint = json.load(f)
        except (OSError, json.JSONDecodeError):
            logger.warning(f"Fetch checkpoint unreadable: {query_sig}")
            return None

        if checkpoint.get("filters") != filters or checkpoint.get("page_size") != page_size:
            logger.info(f"Fetch checkpoint stale for query/page size: {query_sig}")
            return None

        jobs = checkpoint.get("jobs", [])
        next_page = int(checkpoint.get("next_page") or 1)
        logger.info(
            "Fetch checkpoint loaded: %s jobs=%s next_page=%s",
            query_sig,
            len(jobs),
            next_page,
        )
        return checkpoint

    def write_job_fetch_checkpoint(
            self,
            filters: dict,
            page_size: int,
            jobs: list,
            next_page: int,
            total: int,
    ):
        query_sig, _cache_dir, checkpoint_file = self._checkpoint_file_for_filters(filters)
        payload = {
            "filters": filters,
            "page_size": page_size,
            "jobs": jobs,
            "next_page": next_page,
            "total": total,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._write_json_atomic(checkpoint_file, payload)
        logger.debug(
            "Fetch checkpoint saved: %s jobs=%s next_page=%s total=%s",
            query_sig,
            len(jobs),
            next_page,
            total,
        )

    def clear_job_fetch_checkpoint(self, filters: dict):
        _query_sig, _cache_dir, checkpoint_file = self._checkpoint_file_for_filters(filters)
        try:
            os.remove(checkpoint_file)
        except FileNotFoundError:
            pass

    async def _fetch_jobs_page(
            self,
            filters: dict,
            page: int,
            page_size: int,
            max_retries: int,
            retry_backoff_seconds: float,
    ):
        res = None
        for attempt in range(1, max_retries + 1):
            try:
                headers = {"Authorization": f"Bearer {self.engine.token}"}
                res = await self.client.post(
                    f"{self.api_url}/jobs",
                    headers=headers,
                    data=filters,
                    params={"page": page, "page_size": page_size}
                )
                if res.status_code == 401 and attempt < max_retries:
                    await self._get_token()
                    logger.warning("Fetch page %s unauthorized. Token refreshed, retry=%s", page, attempt)
                    continue
                if res.status_code == 200:
                    return res.json()
                logger.warning(
                    "Fetch page %s failed: status=%s retry=%s/%s",
                    page,
                    res.status_code,
                    attempt,
                    max_retries,
                )
            except httpx.ReadTimeout:
                logger.warning(
                    "Fetch page %s timeout retry=%s/%s",
                    page,
                    attempt,
                    max_retries,
                )
            except httpx.HTTPError as e:
                logger.warning(
                    "Fetch page %s HTTP error retry=%s/%s error=%s",
                    page,
                    attempt,
                    max_retries,
                    e,
                )
            except Exception as e:
                logger.warning(
                    "Fetch page %s error retry=%s/%s error=%s",
                    page,
                    attempt,
                    max_retries,
                    e,
                )

            if attempt < max_retries:
                await asyncio.sleep(retry_backoff_seconds * attempt)

        status = getattr(res, "status_code", "no-response")
        raise RuntimeError(f"Tracker jobs fetch failed at page {page} after {max_retries} retries. status={status}")

    async def fetch_all_jobs(
            self,
            filters: dict,
            page_size: int = 500,
            progress_callback: Optional[Callable[[dict], None]] = None,
            max_retries: int = 5,
            retry_backoff_seconds: float = 1.0,
            page_concurrency: int = 1,
    ):
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
        query_sig, cache_dir, cache_file = self._cache_file_for_filters(filters)

        cached_jobs = self.load_cached_jobs(filters)
        if cached_jobs is not None:
            if progress_callback:
                progress_callback({
                    "source": "cache",
                    "fetched": len(cached_jobs),
                    "total": len(cached_jobs),
                    "page": 0,
                    "page_size": page_size,
                    "done": True,
                })
            return cached_jobs

        if not self.engine.token: await self._get_token()

        checkpoint = self.load_job_fetch_checkpoint(filters, page_size)
        if checkpoint:
            all_jobs = checkpoint.get("jobs", [])
            page = int(checkpoint.get("next_page") or 1)
            total_from_checkpoint = int(checkpoint.get("total") or 0)
            if progress_callback:
                progress_callback({
                    "source": "checkpoint",
                    "fetched": len(all_jobs),
                    "total": total_from_checkpoint,
                    "page": page,
                    "page_size": page_size,
                    "done": False,
                    "resumed": True,
                })
        else:
            all_jobs, page, total_from_checkpoint = [], 1, 0

        page_concurrency = max(1, int(page_concurrency or 1))

        while True:
            if self.engine.stop_requested:
                logger.warning("Fetch fermato per stop richiesto.")
                break

            batch_pages = list(range(page, page + page_concurrency))
            results = await asyncio.gather(
                *[
                    self._fetch_jobs_page(
                        filters,
                        batch_page,
                        page_size,
                        max_retries,
                        retry_backoff_seconds,
                    )
                    for batch_page in batch_pages
                ],
                return_exceptions=True,
            )

            done = False
            for batch_page, result in zip(batch_pages, results):
                if isinstance(result, Exception):
                    self.write_job_fetch_checkpoint(
                        filters,
                        page_size,
                        all_jobs,
                        batch_page,
                        total_from_checkpoint,
                    )
                    raise RuntimeError(
                        f"{result} Checkpoint saved; rerun resumes from last completed page."
                    ) from result

                data = result
                items = data.get("items", [])
                all_jobs.extend(items)

                total = data.get("count", 0)
                total_from_checkpoint = total
                done = len(all_jobs) >= total or not items
                next_page = batch_page + 1
                self.write_job_fetch_checkpoint(filters, page_size, all_jobs, next_page, total)

                logger.info(f"Fetching: {len(all_jobs)}/{total} (Pagina {batch_page})")
                if progress_callback:
                    progress_callback({
                        "source": "tracker_parallel" if page_concurrency > 1 else "tracker",
                        "fetched": len(all_jobs),
                        "total": total,
                        "page": batch_page,
                        "page_size": page_size,
                        "page_concurrency": page_concurrency,
                        "done": done,
                        "checkpoint_saved": True,
                    })

                if done:
                    break

            if done:
                break

            page = batch_pages[-1] + 1
            await asyncio.sleep(0.01)  # Checkpoint per event loop

        if not self.engine.stop_requested and all_jobs:
            self._write_json_atomic(cache_file, all_jobs)
            self.clear_job_fetch_checkpoint(filters)

        return all_jobs
