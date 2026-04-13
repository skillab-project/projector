from typing import List


class RegionalAnalytics:
    def __init__(self, engine):
        self.engine = engine

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
                label = self.engine.skill_map.get(s_uri, {}).get("label", s_uri)

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
