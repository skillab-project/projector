from collections import defaultdict, Counter
from typing import List


class SectoralAnalytics:
    def __init__(self, engine, occupations):
        self.engine = engine
        self.occupations = occupations



    def build_observed_occupation_skill_matrix(self, jobs: List[dict], reset: bool = True):
        """
        Build an observed occupation -> skill count matrix from raw Tracker jobs.

        Parameters
        ----------
        jobs : List[dict]
            Raw jobs returned by the Tracker
        reset : bool
            If True, clears the previous matrix before rebuilding it

        Returns
        -------
        defaultdict(Counter)
            occ_id -> Counter(skill_id -> count)
        """
        if reset:
            self.engine.occ_skill_observed = defaultdict(Counter)

        for job in jobs:
            occ_ids = self.occupations.get_occupation_ids(job)
            if not occ_ids:
                continue

            for occ_id in occ_ids:
                for skill_id in job.get("skills", []):
                    skill_id = str(skill_id).strip()
                    if not skill_id:
                        continue
                    self.engine.occ_skill_observed[occ_id][skill_id] += 1

        return self.engine.occ_skill_observed

    def get_canonical_skills_for_occupation(self, occ_id: str, resolve_labels: bool = False, top_k: int = 50):
        """
        Return canonical ESCO skills linked to an occupation through the local
        occupation-skill relations CSV.

        Since the CSV relations are unweighted at this stage, every canonical skill
        gets count=1.
        """
        occ_id = str(occ_id).strip()
        skill_ids = sorted(self.engine.occ_skill_relations.get(occ_id, set()))
        total_skill_mentions = len(skill_ids)

        results = []
        for skill_id in skill_ids[:top_k]:
            entry = {
                "skill_id": skill_id,
                "count": 1,
                "frequency": round(1 / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0,
            }

            if resolve_labels:
                meta = self.engine.skill_map.get(skill_id, {})
                entry["label"] = meta.get("label", skill_id)
                entry["is_green"] = meta.get("is_green", False)
                entry["is_digital"] = meta.get("is_digital", False)

            results.append(entry)

        return results

    def build_canonical_sector_skill_matrix(self, jobs: List[dict], sector_level: str = "isco_group",
                                            reset: bool = True):
        """
        Build a sector -> canonical skill matrix.

        For each job:
        - extract the primary occupation
        - resolve the sector from that occupation
        - take all canonical ESCO skills linked to that occupation
        - accumulate them at sector level

        Each canonical skill contributes +1 per job occurrence of that occupation.
        """
        if reset:
            self.engine.sector_skill_canonical = defaultdict(Counter)

        for job in jobs:
            occ_ids = self.occupations.get_occupation_ids(job)
            if not occ_ids:
                continue

            for occ_id in occ_ids:
                sector_names = self.occupations.get_sector_keys_from_occupation(occ_id, level=sector_level)
                canonical_skills = self.engine.occ_skill_relations.get(occ_id, set())
                for sector_name in sector_names:
                    for skill_id in canonical_skills:
                        skill_id = str(skill_id).strip()
                        if not skill_id:
                            continue
                        self.engine.sector_skill_canonical[sector_name][skill_id] += 1

        return self.engine.sector_skill_canonical

    def get_canonical_skills_for_sector(self, sector_name: str, resolve_labels: bool = False, top_k: int = 20):
        """
        Return canonical skills for a sector, sorted by count.
        """
        sector_name = str(sector_name).strip()
        counter = self.engine.sector_skill_canonical.get(sector_name, Counter())
        total_skill_mentions = sum(counter.values())

        results = []
        for skill_id, count in counter.most_common(top_k):
            entry = {
                "skill_id": skill_id,
                "count": count,
                "frequency": round(count / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0,
            }
            if resolve_labels:
                meta = self.engine.skill_map.get(skill_id, {})
                entry["label"] = meta.get("label", skill_id)
                entry["is_green"] = meta.get("is_green", False)
                entry["is_digital"] = meta.get("is_digital", False)
            results.append(entry)

        return results

    def summarize_canonical_sector_skills(
            self,
            resolve_labels: bool = False,
            top_k: int = 20
    ):
        """
        Build a readable summary of canonical ESCO skills per sector, starting from
        sself.engine.sector_skill_canonical.
        """
        results = []

        for sector_name, counter in self.engine.sector_skill_canonical.items():
            total_skill_mentions = sum(counter.values())

            top_skills = []
            for skill_id, count in counter.most_common(top_k):
                entry = {
                    "skill_id": skill_id,
                    "count": count,
                    "frequency": round(count / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0
                }

                if resolve_labels:
                    meta = self.engine.skill_map.get(skill_id, {})
                    entry["label"] = meta.get("label", skill_id)
                    entry["is_green"] = meta.get("is_green", False)
                    entry["is_digital"] = meta.get("is_digital", False)

                top_skills.append(entry)

            results.append({
                "sector": sector_name,
                "total_skill_mentions": total_skill_mentions,
                "unique_skills": len(counter),
                "top_skills": top_skills
            })

        return sorted(results, key=lambda x: x["total_skill_mentions"], reverse=True)

    def compare_observed_and_canonical_for_sector(
            self,
            sector_name: str,
            resolve_labels: bool = False,
            top_k: int = 20
    ):
        """
        Return both observed and canonical summaries for a sector.
        """
        return {
            "sector": sector_name,
            "observed": self.summarize_single_sector(
                sector_name=sector_name,
                resolve_labels=resolve_labels,
                top_k=top_k
            ),
            "canonical": {
                "sector": sector_name,
                "top_skills": self.get_canonical_skills_for_sector(
                    sector_name=sector_name,
                    resolve_labels=resolve_labels,
                    top_k=top_k
                ),
                "total_skill_mentions": sum(self.engine.sector_skill_canonical.get(sector_name, Counter()).values()),
                "unique_skills": len(self.engine.sector_skill_canonical.get(sector_name, Counter()))
            }
        }

    def get_observed_skills_for_sector(self, sector_name: str, resolve_labels: bool = False, top_k: int = 20):
        """
        Return the observed skills for a sector, sorted by count.
        """
        sector_name = str(sector_name).strip()
        counter = self.engine.sector_skill_observed.get(sector_name, Counter())
        total_skill_mentions = sum(counter.values())

        results = []
        for skill_id, count in counter.most_common(top_k):
            entry = {
                "skill_id": skill_id,
                "count": count,
                "frequency": round(count / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0,
            }
            if resolve_labels:
                meta = self.engine.skill_map.get(skill_id, {})
                entry["label"] = meta.get("label", skill_id)
                entry["is_green"] = meta.get("is_green", False)
                entry["is_digital"] = meta.get("is_digital", False)
            results.append(entry)

        return results

    def build_observed_sector_skill_matrix(self, jobs: List[dict], sector_level: str = "isco_group",
                                           reset: bool = True):
        """
        Aggregate observed skills at sector level starting from raw jobs.

        Parameters
        ----------
        jobs : List[dict]
            Raw Tracker jobs
        sector_level : str
            Passed to get_sector_from_occupation()
        reset : bool
            If True, clears the previous sector matrix before rebuilding it

        Returns
        -------
        defaultdict(Counter)
            sector_name -> Counter(skill_id -> count)
        """
        if reset:
            self.engine.sector_skill_observed = defaultdict(Counter)

        for job in jobs:
            occ_ids = self.occupations.get_occupation_ids(job)
            if not occ_ids:
                continue

            for occ_id in occ_ids:
                sector_names = self.occupations.get_sector_keys_from_occupation(occ_id, level=sector_level)
                for sector_name in sector_names:
                    for skill_id in job.get("skills", []):
                        skill_id = str(skill_id).strip()
                        if not skill_id:
                            continue
                        self.engine.sector_skill_observed[sector_name][skill_id] += 1

        return self.engine.sector_skill_observed

    def get_observed_skills_for_occupation(self, occ_id: str, resolve_labels: bool = False, top_k: int = 20):
        """
                Return the observed skills for a single occupation, sorted by count.

                Parameters
                ----------
                occ_id : str
                    Occupation id
                resolve_labels : bool
                    If True, tries to resolve skill labels using self.engine.skill_map
                top_k : int
                    Maximum number of returned skills

                Returns
                -------
                List[dict]
                """
        occ_id = str(occ_id).strip()
        counter = self.engine.occ_skill_observed.get(occ_id, Counter())
        total_skill_mentions = sum(counter.values())

        results = []
        for skill_id, count in counter.most_common(top_k):
            entry = {
                "skill_id": skill_id,
                "count": count,
                "frequency": round(count / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0,
            }
            if resolve_labels:
                meta = self.engine.skill_map.get(skill_id, {})
                entry["label"] = meta.get("label", skill_id)
                entry["is_green"] = meta.get("is_green", False)
                entry["is_digital"] = meta.get("is_digital", False)
            results.append(entry)

        return results

    def summarize_observed_sector_skills(
            self,
            sector_level: str = "isco_group",
            resolve_labels: bool = False,
            top_k: int = 20
    ):
        """
        Build a readable summary of observed skills per sector, starting from
        self.engine.sector_skill_observed.

        Parameters
        ----------
        sector_level : str
            Informational only for now; kept for consistency with previous steps
        resolve_labels : bool
            If True, resolves skill labels through self.engine.skill_map
        top_k : int
            Max number of top skills to return per sector

        Returns
        -------
        List[dict]
            One entry per sector
        """
        results = []

        for sector_name, counter in self.engine.sector_skill_observed.items():
            total_skill_mentions = sum(counter.values())

            top_skills = []
            for skill_id, count in counter.most_common(top_k):
                entry = {
                    "skill_id": skill_id,
                    "count": count,
                    "frequency": round(count / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0
                }

                if resolve_labels:
                    meta = self.engine.skill_map.get(skill_id, {})
                    entry["label"] = meta.get("label", skill_id)
                    entry["is_green"] = meta.get("is_green", False)
                    entry["is_digital"] = meta.get("is_digital", False)

                top_skills.append(entry)

            results.append({
                "sector": sector_name,
                "total_skill_mentions": total_skill_mentions,
                "unique_skills": len(counter),
                "top_skills": top_skills
            })

        return sorted(results, key=lambda x: x["total_skill_mentions"], reverse=True)

    # def build_and_summarize_observed_sector_skills(
    #     self,
    #     jobs: List[dict],
    #     sector_level: str = "isco_group",
    #     resolve_labels: bool = False,
    #     top_k: int = 20,
    #     reset: bool = True
    # ):
    #     """
    #     Convenience method:
    #     1. builds sector -> skill observed matrix
    #     2. returns a readable summary
    #     """
    #     self.build_observed_sector_skill_matrix(
    #         jobs=jobs,
    #         sector_level=sector_level,
    #         reset=reset
    #     )
    #
    #     return self.summarize_observed_sector_skills(
    #         sector_level=sector_level,
    #         resolve_labels=resolve_labels,
    #         top_k=top_k
    #     )

    def build_and_summarize_observed_sector_skills(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            resolve_labels: bool = False,
            top_k: int = 20,
            reset: bool = True
    ):
        """
        Convenience method:
        1. builds sector -> skill observed matrix
        2. returns a readable summary
        """
        self.build_observed_sector_skill_matrix(
            jobs=jobs,
            sector_level=sector_level,
            reset=reset
        )

        return self.summarize_observed_sector_skills(
            sector_level=sector_level,
            resolve_labels=resolve_labels,
            top_k=top_k
        )

    def build_and_summarize_canonical_sector_skills(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            resolve_labels: bool = False,
            top_k: int = 20,
            reset: bool = True
    ):
        """
        Convenience method:
        1. builds sector -> canonical skill matrix
        2. returns a readable summary
        """
        self.build_canonical_sector_skill_matrix(
            jobs=jobs,
            sector_level=sector_level,
            reset=reset
        )

        return self.summarize_canonical_sector_skills(
            resolve_labels=resolve_labels,
            top_k=top_k
        )

    def summarize_single_sector(
            self,
            sector_name: str,
            resolve_labels: bool = False,
            top_k: int = 20
    ):
        """
        Return a readable summary for one specific sector only.
        """
        from collections import Counter  # sicurezza se non già importato

        sector_name = str(sector_name).strip()
        counter = self.engine.sector_skill_observed.get(sector_name, Counter())
        total_skill_mentions = sum(counter.values())

        top_skills = []
        for skill_id, count in counter.most_common(top_k):
            entry = {
                "skill_id": skill_id,
                "count": count,
                "frequency": round(count / total_skill_mentions, 6) if total_skill_mentions > 0 else 0.0
            }

            if resolve_labels:
                meta = self.engine.skill_map.get(skill_id, {})
                entry["label"] = meta.get("label", skill_id)
                entry["is_green"] = meta.get("is_green", False)
                entry["is_digital"] = meta.get("is_digital", False)

            top_skills.append(entry)

        return {
            "sector": sector_name,
            "total_skill_mentions": total_skill_mentions,
            "unique_skills": len(counter),
            "top_skills": top_skills
        }

    def _read_group_counter(self, counter: Counter, top_k: int = 20):
        """
        Internal helper: convert a Counter into a sorted list with frequencies.
        """
        total = sum(counter.values())
        results = []

        for group_id, count in counter.most_common(top_k):
            results.append({
                "group_id": group_id,
                "group_label": self.get_skill_group_label(group_id),
                "count": count,
                "frequency": round(count / total, 6) if total > 0 else 0.0
            })

        return {
            "total_mentions": total,
            "unique_groups": len(counter),
            "top_groups": results
        }

    def get_skill_group_label(self, group_id: str) -> str:
        """
        Resolve a human-readable label for a skill group id.
        Supports both full ESCO URI and short code.
        """
        group_id = str(group_id).strip()
        if not group_id:
            return "Skill group not specified"

        if group_id in self.engine.skill_group_labels:
            return self.engine.skill_group_labels[group_id]

        if group_id.startswith("http"):
            short_gid = group_id.rstrip("/").split("/")[-1]
            if short_gid in self.engine.skill_group_labels:
                return self.engine.skill_group_labels[short_gid]

        return group_id

    def summarize_observed_sector_skillgroups(self, top_k: int = 20):
        """
        Build a readable summary of observed ESCO skill groups per sector.
        """
        results = []

        for sector_name, counter in self.engine.sector_skillgroup_observed.items():
            base = self._read_group_counter(counter, top_k=top_k)
            results.append({
                "sector": sector_name,
                "total_group_mentions": base["total_mentions"],
                "unique_groups": base["unique_groups"],
                "top_groups": base["top_groups"]
            })

        return sorted(results, key=lambda x: x["total_group_mentions"], reverse=True)

    def summarize_canonical_sector_skillgroups(self, top_k: int = 20):
        """
        Build a readable summary of canonical ESCO skill groups per sector.
        """
        results = []

        for sector_name, counter in self.engine.sector_skillgroup_canonical.items():
            base = self._read_group_counter(counter, top_k=top_k)
            results.append({
                "sector": sector_name,
                "total_group_mentions": base["total_mentions"],
                "unique_groups": base["unique_groups"],
                "top_groups": base["top_groups"]
            })

        return sorted(results, key=lambda x: x["total_group_mentions"], reverse=True)

    def compare_observed_and_canonical_groups_for_sector(
            self,
            sector_name: str,
            top_k: int = 20
    ):
        """
        Compare observed vs canonical skill-group distributions for one sector.
        """
        sector_name = str(sector_name).strip()

        observed_counter = self.engine.sector_skillgroup_observed.get(sector_name, Counter())
        canonical_counter = self.engine.sector_skillgroup_canonical.get(sector_name, Counter())

        observed = self._read_group_counter(observed_counter, top_k=top_k)
        canonical = self._read_group_counter(canonical_counter, top_k=top_k)

        return {
            "sector": sector_name,
            "observed_groups": {
                "total_group_mentions": observed["total_mentions"],
                "unique_groups": observed["unique_groups"],
                "top_groups": observed["top_groups"]
            },
            "canonical_groups": {
                "total_group_mentions": canonical["total_mentions"],
                "unique_groups": canonical["unique_groups"],
                "top_groups": canonical["top_groups"]
            }
        }

    def build_and_summarize_observed_sector_skillgroups(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 2,
            top_k: int = 20,
            reset: bool = True
    ):
        self.build_observed_sector_skillgroup_matrix(
            jobs=jobs,
            sector_level=sector_level,
            skill_group_level=skill_group_level,
            reset=reset
        )
        return self.summarize_observed_sector_skillgroups(top_k=top_k)

    def build_and_summarize_canonical_sector_skillgroups(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 2,
            top_k: int = 20,
            reset: bool = True
    ):
        self.build_canonical_sector_skillgroup_matrix(
            jobs=jobs,
            sector_level=sector_level,
            skill_group_level=skill_group_level,
            reset=reset
        )
        return self.summarize_canonical_sector_skillgroups(top_k=top_k)

    def get_skill_group(self, skill_id: str, level: int = 2) -> str:
        """
        Resolve the ESCO skill group for a skill using the local skill hierarchy.
        Returns a normalized short group id when possible (e.g. S4.8 instead of full URI).
        """
        skill_id = str(skill_id).strip()
        if not skill_id:
            return "Skill group not specified"

        meta = self.engine.skill_hierarchy.get(skill_id)
        if meta:
            if level == 1:
                group_id = (meta.get("level_1") or "").strip()
            elif level == 3:
                group_id = (meta.get("level_3") or "").strip()
            else:
                group_id = (meta.get("level_2") or "").strip()

            if group_id:
                # normalize URI -> short code
                if group_id.startswith("http"):
                    return group_id.rstrip("/").split("/")[-1]
                return group_id

        skill_meta = self.engine.skill_map.get(skill_id, {})
        label = skill_meta.get("label", "").strip()
        if label:
            return label

        return "Skill group not specified"

    def build_and_summarize_official_matrix_sector_skillgroups(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 1,
            occupation_level: int = 1,
            top_k: int = 20,
            reset: bool = True
    ):
        self.build_official_matrix_sector_skillgroup_profile(
            jobs=jobs,
            sector_level=sector_level,
            skill_group_level=skill_group_level,
            occupation_level=occupation_level,
            reset=reset
        )
        return self.summarize_official_matrix_sector_skillgroups(top_k=top_k)

    def summarize_official_matrix_single_sector(
            self,
            sector_name: str,
            top_k: int = 20
    ):
        """
        Return a readable summary for one sector using the official ESCO matrix profile.
        """
        return self.get_official_matrix_groups_for_sector(
            sector_name=sector_name,
            top_k=top_k
        )

    def get_official_matrix_groups_for_sector(self, sector_name: str, top_k: int = 20):
        """
        Return the official ESCO matrix skill-group profile for a sector.
        """
        sector_name = str(sector_name).strip()
        counter = self.engine.matrix_profiles.get(sector_name, Counter())
        total_group_mentions = sum(counter.values())

        top_groups = []
        for group_id, count in counter.most_common(top_k):
            top_groups.append({
                "group_id": group_id,
                "group_label": self.get_skill_group_label(group_id),
                "count": count,
                "frequency": round(count / total_group_mentions, 6) if total_group_mentions > 0 else 0.0
            })

        return {
            "sector": sector_name,
            "total_group_mentions": total_group_mentions,
            "unique_groups": len(counter),
            "top_groups": top_groups
        }

    def build_official_matrix_sector_skillgroup_profile(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 1,
            occupation_level: int = 1,
            reset: bool = True
    ):
        """
        Build a sector -> official ESCO skill-group profile using the workbook.

        For each job:
        - resolve occupation
        - resolve sector
        - get official matrix profile for that occupation group
        - accumulate profile values into the sector
        """
        if reset:
            self.engine.matrix_profiles = defaultdict(Counter)

        for job in jobs:
            occ_ids = self.occupations.get_occupation_ids(job)
            if not occ_ids:
                continue

            for occ_id in occ_ids:
                group_code = self.occupations.get_occupation_group_id_for_matrix(
                    occ_id=occ_id,
                    occupation_level=occupation_level
                )

                if not group_code:
                    continue

                sector_names = self.occupations.get_sector_keys_from_occupation(occ_id, level=sector_level)

                official = self.occupations.get_official_esco_profile_for_occupation(
                    occ_id=occ_id,
                    skill_group_level=skill_group_level,
                    occupation_level=occupation_level
                )
                if not official:
                    continue

                for sector_name in sector_names:
                    for skill_group_id, share in official["profile"].items():
                        self.engine.matrix_profiles[sector_name][skill_group_id] += float(share)

        return self.engine.matrix_profiles

    def summarize_official_matrix_sector_skillgroups(self, top_k: int = 20):
        """
        Build a readable summary of official ESCO matrix skill-group profiles per sector.
        """
        results = []

        for sector_name, counter in self.engine.matrix_profiles.items():
            base = self._read_group_counter(counter, top_k=top_k)
            results.append({
                "sector": sector_name,
                "total_group_mentions": base["total_mentions"],
                "unique_groups": base["unique_groups"],
                "top_groups": base["top_groups"]
            })

        return sorted(results, key=lambda x: x["total_group_mentions"], reverse=True)

    def compare_all_group_profiles_for_sector(
            self,
            sector_name: str,
            top_k: int = 20
    ):
        """
        Compare observed vs canonical vs official matrix group profiles for one sector.
        """
        sector_name = str(sector_name).strip()

        observed_counter = self.engine.sector_skillgroup_observed.get(sector_name, Counter())
        canonical_counter = self.engine.sector_skillgroup_canonical.get(sector_name, Counter())
        official_counter = self.engine.matrix_profiles.get(sector_name, Counter())

        observed = self._read_group_counter(observed_counter, top_k=top_k)
        canonical = self._read_group_counter(canonical_counter, top_k=top_k)
        official = self._read_group_counter(official_counter, top_k=top_k)

        return {
            "sector": sector_name,
            "observed_groups": {
                "total_group_mentions": observed["total_mentions"],
                "unique_groups": observed["unique_groups"],
                "top_groups": observed["top_groups"]
            },
            "canonical_groups": {
                "total_group_mentions": canonical["total_mentions"],
                "unique_groups": canonical["unique_groups"],
                "top_groups": canonical["top_groups"]
            },
            "official_matrix_groups": {
                "total_group_mentions": official["total_mentions"],
                "unique_groups": official["unique_groups"],
                "top_groups": official["top_groups"]
            }
        }

    def build_sectoral_intelligence(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 1,
            occupation_level: int = 1,
            resolve_labels: bool = False,
            top_k_skills: int = 10,
            top_k_groups: int = 10,
            reset: bool = True
    ):
        """
        Build a unified sectoral intelligence payload combining:
        - observed skills
        - canonical skills
        - observed skill groups
        - canonical skill groups
        - official matrix skill groups
        """
        # 1. Build all required layers
        self.build_observed_sector_skill_matrix(
            jobs=jobs,
            sector_level=sector_level,
            reset=reset
        )

        self.build_canonical_sector_skill_matrix(
            jobs=jobs,
            sector_level=sector_level,
            reset=reset
        )

        self.build_observed_sector_skillgroup_matrix(
            jobs=jobs,
            sector_level=sector_level,
            skill_group_level=skill_group_level,
            reset=reset
        )

        self.build_canonical_sector_skillgroup_matrix(
            jobs=jobs,
            sector_level=sector_level,
            skill_group_level=skill_group_level,
            reset=reset
        )

        self.build_official_matrix_sector_skillgroup_profile(
            jobs=jobs,
            sector_level=sector_level,
            skill_group_level=skill_group_level,
            occupation_level=occupation_level,
            reset=reset
        )

        # 2. Collect all sector names seen in any layer
        sectors = set()
        sectors.update(self.engine.sector_skill_observed.keys())
        sectors.update(self.engine.sector_skill_canonical.keys())
        sectors.update(self.engine.sector_skillgroup_observed.keys())
        sectors.update(self.engine.sector_skillgroup_canonical.keys())
        sectors.update(self.engine.matrix_profiles.keys())

        results = []
        sector_system = "nace" if str(sector_level).startswith("nace") else "isco"
        skill_metrics = self.compute_skill_breadth_and_concentration(
            resolve_labels=resolve_labels,
            top_k_sectors=5,
            sector_system=sector_system
        )

        for sector_name in sorted(sectors):
            observed_skills = self.summarize_single_sector(
                sector_name=sector_name,
                resolve_labels=resolve_labels,
                top_k=top_k_skills
            )

            canonical_skills = {
                "sector": sector_name,
                "top_skills": self.get_canonical_skills_for_sector(
                    sector_name=sector_name,
                    resolve_labels=resolve_labels,
                    top_k=top_k_skills
                ),
                "total_skill_mentions": sum(self.engine.sector_skill_canonical.get(sector_name, Counter()).values()),
                "unique_skills": len(self.engine.sector_skill_canonical.get(sector_name, Counter()))
            }

            group_profiles = self.compare_all_group_profiles_for_sector(
                sector_name=sector_name,
                top_k=top_k_groups
            )

            sector_total_mentions = observed_skills.get("total_skill_mentions", 0)
            sector_metrics = {
                "coverage_unique_skills": observed_skills.get("unique_skills", 0),
                "dominance_top10_share": self.compute_sector_skill_dominance(sector_name, top_k=10)
            }

            skill_transversal_insights = []
            observed_top_skills = observed_skills.get("top_skills", [])
            for skill in observed_top_skills:
                skill_id = skill.get("skill_id")
                if not skill_id:
                    continue
                base = skill_metrics.get(skill_id, {})
                if not base:
                    continue
                insight = {
                    "skill_id": skill_id,
                    "label": skill.get("label", base.get("label", skill_id)),
                    "count": skill.get("count", 0),
                    "importance_in_sector": round((skill.get("count", 0) / sector_total_mentions), 6) if sector_total_mentions > 0 else 0.0,
                    "sector_breadth": base.get("sector_breadth", 0),
                    "dominant_sector": base.get("dominant_sector", ""),
                    "dominant_sector_label": base.get("dominant_sector_label", ""),
                    "dominant_share": base.get("dominant_share", 0.0),
                    "top_sectors": base.get("top_sectors", []),
                }
                skill_transversal_insights.append(insight)

            isco_interpretation = None
            if sector_system == "isco":
                isco_interpretation = self.compute_isco_skill_gap_and_stability(sector_name)

            results.append({
                "sector": sector_name,
                "sector_label": self.occupations.get_sector_label(sector_name, system=sector_system),

                "observed_skills": observed_skills,
                "canonical_skills": canonical_skills,

                "observed_groups": group_profiles["observed_groups"],
                "canonical_groups": group_profiles["canonical_groups"],

                "matrix_groups": group_profiles["official_matrix_groups"],
                "sector_metrics": sector_metrics,
                "skill_transversal_insights": skill_transversal_insights,
                "isco_interpretation": isco_interpretation
            })

        return results

    def build_single_sector_intelligence(
            self,
            sector_name: str,
            sector_level: str = "isco_group",
            resolve_labels: bool = False,
            top_k_skills: int = 10,
            top_k_groups: int = 10
    ):
        """
        Return the unified sectoral intelligence block for a single already-built sector.
        Assumes the matrices have already been populated.
        """
        sector_name = str(sector_name).strip()

        observed_skills = self.summarize_single_sector(
            sector_name=sector_name,
            resolve_labels=resolve_labels,
            top_k=top_k_skills
        )

        canonical_skills = {
            "sector": sector_name,
            "top_skills": self.get_canonical_skills_for_sector(
                sector_name=sector_name,
                resolve_labels=resolve_labels,
                top_k=top_k_skills
            ),
            "total_skill_mentions": sum(self.engine.sector_skill_canonical.get(sector_name, Counter()).values()),
            "unique_skills": len(self.engine.sector_skill_canonical.get(sector_name, Counter()))
        }

        group_profiles = self.compare_all_group_profiles_for_sector(
            sector_name=sector_name,
            top_k=top_k_groups
        )

        sector_system = "nace" if str(sector_level).startswith("nace") else "isco"
        skill_metrics = self.compute_skill_breadth_and_concentration(
            resolve_labels=resolve_labels,
            top_k_sectors=5,
            sector_system=sector_system
        )
        sector_total_mentions = observed_skills.get("total_skill_mentions", 0)
        skill_transversal_insights = []
        for skill in observed_skills.get("top_skills", []):
            skill_id = skill.get("skill_id")
            if not skill_id:
                continue
            base = skill_metrics.get(skill_id, {})
            skill_transversal_insights.append({
                "skill_id": skill_id,
                "label": skill.get("label", base.get("label", skill_id)),
                "count": skill.get("count", 0),
                "importance_in_sector": round((skill.get("count", 0) / sector_total_mentions), 6) if sector_total_mentions > 0 else 0.0,
                "sector_breadth": base.get("sector_breadth", 0),
                "dominant_sector": base.get("dominant_sector", ""),
                "dominant_sector_label": base.get("dominant_sector_label", ""),
                "dominant_share": base.get("dominant_share", 0.0),
                "top_sectors": base.get("top_sectors", []),
            })

        isco_interpretation = self.compute_isco_skill_gap_and_stability(sector_name) if sector_system == "isco" else None
        return {
            "sector": sector_name,
            "sector_label": self.occupations.get_sector_label(sector_name, system=sector_system),

            "observed_skills": observed_skills,
            "canonical_skills": canonical_skills,

            "observed_groups": group_profiles["observed_groups"],
            "canonical_groups": group_profiles["canonical_groups"],

            "matrix_groups": group_profiles["official_matrix_groups"],
            "sector_metrics": {
                "coverage_unique_skills": observed_skills.get("unique_skills", 0),
                "dominance_top10_share": self.compute_sector_skill_dominance(sector_name, top_k=10)
            },
            "skill_transversal_insights": skill_transversal_insights,
            "isco_interpretation": isco_interpretation
        }

    def build_canonical_sector_skillgroup_matrix(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 2,
            reset: bool = True
    ):
        if reset:
            self.engine.sector_skillgroup_canonical = defaultdict(Counter)

        for job in jobs:
            occ_ids = self.occupations.get_occupation_ids(job)
            if not occ_ids:
                continue

            for occ_id in occ_ids:
                sector_names = self.occupations.get_sector_keys_from_occupation(occ_id, level=sector_level)
                canonical_skills = self.engine.occ_skill_relations.get(occ_id, set())
                for sector_name in sector_names:
                    for skill_id in canonical_skills:
                        skill_group = self.get_skill_group(skill_id, level=skill_group_level)
                        self.engine.sector_skillgroup_canonical[sector_name][skill_group] += 1

        return self.engine.sector_skillgroup_canonical

    def build_observed_sector_skillgroup_matrix(
            self,
            jobs: List[dict],
            sector_level: str = "isco_group",
            skill_group_level: int = 2,
            reset: bool = True
    ):
        """
        Build a sector -> observed skill-group count matrix from raw jobs.
        """
        if reset:
            self.engine.sector_skillgroup_observed = defaultdict(Counter)

        for job in jobs:
            occ_ids = self.occupations.get_occupation_ids(job)
            if not occ_ids:
                continue

            for occ_id in occ_ids:
                sector_names = self.occupations.get_sector_keys_from_occupation(occ_id, level=sector_level)
                for sector_name in sector_names:
                    for skill_id in job.get("skills", []):
                        skill_id = str(skill_id).strip()
                        if not skill_id:
                            continue

                        skill_group = self.get_skill_group(skill_id, level=skill_group_level)
                        self.engine.sector_skillgroup_observed[sector_name][skill_group] += 1

        return self.engine.sector_skillgroup_observed

    def compute_skill_breadth_and_concentration(
            self,
            resolve_labels: bool = False,
            top_k_sectors: int = 5,
            sector_system: str = "nace"
    ):
        """
        NACE/ISCO-agnostic metric helper built on observed sector-skill matrix.

        Returns:
            skill_id -> metrics dict (breadth, concentration, top sectors).
        """
        by_skill = defaultdict(Counter)
        for sector_name, counter in self.engine.sector_skill_observed.items():
            for skill_id, count in counter.items():
                by_skill[skill_id][sector_name] += count

        out = {}
        for skill_id, sector_counts in by_skill.items():
            total = sum(sector_counts.values())
            dominant_sector, dominant_count = ("", 0)
            if sector_counts:
                dominant_sector, dominant_count = sector_counts.most_common(1)[0]
            top_sectors = []
            for sector_name, count in sector_counts.most_common(top_k_sectors):
                top_sectors.append({
                    "sector": sector_name,
                    "sector_label": self.occupations.get_sector_label(sector_name, system=sector_system),
                    "count": count,
                    "share": round(count / total, 6) if total > 0 else 0.0
                })

            skill_entry = {
                "skill_id": skill_id,
                "sector_breadth": len(sector_counts),
                "total_mentions": total,
                "dominant_sector": dominant_sector,
                "dominant_sector_label": self.occupations.get_sector_label(dominant_sector, system=sector_system) if dominant_sector else "",
                "dominant_share": round(dominant_count / total, 6) if total > 0 else 0.0
                ,
                "top_sectors": top_sectors
            }
            if resolve_labels:
                meta = self.engine.skill_map.get(skill_id, {})
                skill_entry["label"] = meta.get("label", skill_id)
                skill_entry["is_green"] = meta.get("is_green", False)
                skill_entry["is_digital"] = meta.get("is_digital", False)
            out[skill_id] = skill_entry
        return out

    def compute_sector_skill_dominance(self, sector_name: str, top_k: int = 10):
        sector_name = str(sector_name).strip()
        counter = self.engine.sector_skill_observed.get(sector_name, Counter())
        total_mentions = sum(counter.values())
        if total_mentions <= 0:
            return 0.0
        top_mentions = sum(count for _skill_id, count in counter.most_common(top_k))
        return round(top_mentions / total_mentions, 6)

    def compute_isco_skill_gap_and_stability(self, sector_name: str):
        """
        ISCO interpretation helper:
        - emerging_skills: observed - canonical
        - missing_skills: canonical - observed
        - stability_overlap: Jaccard overlap
        """
        sector_name = str(sector_name).strip()
        observed = set(self.engine.sector_skill_observed.get(sector_name, Counter()).keys())
        canonical = set(self.engine.sector_skill_canonical.get(sector_name, Counter()).keys())

        union = observed.union(canonical)
        intersection = observed.intersection(canonical)
        overlap = round(len(intersection) / len(union), 6) if union else 0.0

        return {
            "sector": sector_name,
            "emerging_skills": sorted(observed - canonical),
            "missing_skills": sorted(canonical - observed),
            "stability_overlap": overlap,
            "observed_skill_count": len(observed),
            "canonical_skill_count": len(canonical),
            "overlap_skill_count": len(intersection)
        }
