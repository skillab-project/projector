import os
from collections import defaultdict, Counter

import httpx
import logging
logger = logging.getLogger("SKILLAB-Projector")

class ProjectorEngine:
    def __init__(self):
        self.api_url = os.getenv("TRACKER_API")
        self.username = os.getenv("TRACKER_USERNAME")
        self.password = os.getenv("TRACKER_PASSWORD")
        self.token = None
        self.skill_map = {}
        self.sector_map = {}  # Cache specifica per le occupazioni/settori
        # --- Local ESCO support maps ---
        self.occupation_meta = {}  # occ_id -> meta info from local CSV
        self.skill_hierarchy = {}  # skill_id -> hierarchy/group info
        self.occ_skill_relations = defaultdict(set)  # occ_id -> set(skill_id)
        self.occupation_group_labels = {}  # optional: group id -> readable label
        self.matrix_profiles = {}  # optional, for later step
        self.occ_skill_observed = defaultdict(Counter)  # occ_id -> Counter(skill_id -> count)
        self.sector_skill_observed = defaultdict(Counter)  # sector -> Counter(skill_id -> count)
        self.sector_skill_canonical = defaultdict(Counter)  # sector -> Counter(skill_id -> count)
        self.sector_skillgroup_observed = defaultdict(Counter)  # sector -> Counter(skill_group -> count)
        self.sector_skillgroup_canonical = defaultdict(Counter)  # sector -> Counter(skill_group -> count)
        self.esco_matrix_overview = {}  # sheet_name -> metadata
        self.esco_matrix_profiles = {}  # (sheet_name, occupation_group_id) -> profile dict
        self.esco_matrix_loaded = False
        self.stop_requested = False
        # Timeout impostato a None per evitare ReadTimeout su query pesanti
        self.client = httpx.AsyncClient(timeout=None)
        self.skill_group_labels = {}  # group_id -> readable label
        #
        # self.green_skill_uris = self._load_skill_uris_from_csv("complementary_data/greenSkillsCollection_lt.csv")
        # self.digital_skill_uris = self._load_skill_uris_from_csv("complementary_data/digitalSkillsCollection_lt.csv")

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