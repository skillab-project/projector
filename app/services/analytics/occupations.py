from typing import List


class OccupationAnalytics:
    def __init__(self, engine):
        self.engine = engine
        return

    def get_primary_occupation_id(self, job: dict) -> str:
        """
        Extract the primary occupation id from a job in a backward-compatible way.
        """
        job_occs = job.get("occupations", [])
        legacy_occ = job.get("occupation_id")

        if job_occs and len(job_occs) > 0:
            return str(job_occs[0]).strip()

        if legacy_occ:
            return str(legacy_occ).strip()

        return ""

    def get_occupation_ids(self, job: dict) -> List[str]:
        """
        Extract all occupation ids from a job in a backward-compatible way.
        """
        occ_ids = []

        job_occs = job.get("occupations", [])
        legacy_occ = job.get("occupation_id")

        for occ in job_occs:
            occ = str(occ).strip()
            if occ:
                occ_ids.append(occ)

        if legacy_occ:
            legacy_occ = str(legacy_occ).strip()
            if legacy_occ and legacy_occ not in occ_ids:
                occ_ids.append(legacy_occ)

        return occ_ids

    def get_sector_from_occupation(self, occ_id: str, level: str = "isco_group") -> str:
        """
        Resolve a sector/group label from an occupation id.

        Resolution order:
        1. Local occupation metadata loaded from occupations_lt.csv
        2. Tracker-derived sector_map fallback
        3. Generic fallback

        Parameters
        ----------
        occ_id : str
            ESCO occupation URI or id
        level : str
            Currently supported:
            - "isco_group": uses local isco_group if available
            - "label": returns the occupation label
            - "nace_code": returns the NACE code if available

        Returns
        -------
        str
            A readable sector/group string


        1. CSV locale (migliore qualità)
            ├─ NACE (se richiesto)
            ├─ Label (se richiesto)
            └─ ISCO group (default)

        2. Tracker API fallback
           └─ sector_map

        3. Default
           └─ "Sector not specified"
        """
        occ_id = str(occ_id).strip()
        if not occ_id:
            return "Sector not specified"

        # 1) Local metadata preferred
        meta = self.engine.occupation_meta.get(occ_id)
        if meta:
            if level == "nace_code":
                nace_list = self.get_nace_mappings_for_occupation(occ_id, level="nace_code")
                if nace_list:
                    return nace_list[0]["code"]
                nace = self.normalize_nace_code(meta.get("nace_code", "").strip())
                if nace:
                    return nace
            if level in {"nace_division", "nace_group", "nace_class"}:
                nace_list = self.get_nace_mappings_for_occupation(occ_id, level=level)
                if nace_list:
                    return nace_list[0]["code"]
                nace = meta.get("nace_code", "").strip()
                nace_level_value = self._get_nace_level_code(nace, level)
                if nace_level_value:
                    return nace_level_value

            if level == "label":
                label = meta.get("label", "").strip()
                if label:
                    return label

            # default: ISCO group if available
            isco_group = meta.get("isco_group", "").strip()
            if isco_group:
                # if we have a readable label for the ISCO group, use it
                return self.engine.occupation_group_labels.get(isco_group, isco_group)

            # fallback to occupation label
            label = meta.get("label", "").strip()
            if label:
                return label

        # 2) Tracker-derived fallback
        tracker_label = self.engine.sector_map.get(occ_id, "").strip()
        if tracker_label:
            return tracker_label

        # 3) Last-resort fallback
        return "Sector not specified"

    def get_nace_mappings_for_occupation(self, occ_id: str, level: str = "nace_code") -> List[dict]:
        occ_id = str(occ_id).strip()
        if not occ_id:
            return []

        mappings = self.engine.occupation_nace_map.get(occ_id, [])
        if not mappings:
            return []

        dedup = {}
        for entry in mappings:
            base_code = self.normalize_nace_code(entry.get("code", ""))
            if not base_code:
                continue
            if level == "nace_code":
                final_code = base_code
            else:
                final_code = self._get_nace_level_code(base_code, level)
            if not final_code:
                continue
            label = self.engine.nace_labels.get(final_code, entry.get("label") or final_code)
            if final_code not in dedup:
                dedup[final_code] = {"code": final_code, "label": label}

        return [dedup[k] for k in sorted(dedup.keys())]

    def get_sector_keys_from_occupation(self, occ_id: str, level: str = "isco_group") -> List[str]:
        if str(level).startswith("nace"):
            mapped = [m["code"] for m in self.get_nace_mappings_for_occupation(occ_id, level=level)]
            if mapped:
                return mapped
            fallback = self.get_sector_from_occupation(occ_id, level=level)
            return [fallback] if fallback and fallback != "Sector not specified" else []
        sector = self.get_sector_from_occupation(occ_id, level=level)
        return [sector] if sector else []

    def normalize_nace_code(self, nace_code: str) -> str:
        """
        Normalize NACE codes to standard display format.

        Examples:
        - "http://.../9031" -> "90.31"
        - "242" -> "24.2"
        - "01" -> "01"
        - "A" -> "A"
        """
        raw = str(nace_code or "").strip()
        if not raw:
            return ""

        if "/" in raw:
            raw = raw.rstrip("/").split("/")[-1]

        raw = raw.upper().replace(" ", "")
        if len(raw) == 1 and raw.isalpha():
            return raw

        prefix = ""
        body = raw
        if raw and raw[0].isalpha():
            prefix = raw[0]
            body = raw[1:]

        cleaned = "".join(ch for ch in body if ch.isdigit() or ch == ".")
        if not cleaned:
            return ""

        if "." in cleaned:
            head, tail = cleaned.split(".", 1)
            head = head[:2]
            tail = "".join(ch for ch in tail if ch.isdigit())
            if not head:
                return ""
            if prefix:
                head = f"{prefix}{head}"
            if not tail:
                return head
            if len(tail) == 1:
                return f"{head}.{tail}"
            return f"{head}.{tail[:2]}"

        digits = "".join(ch for ch in cleaned if ch.isdigit())
        if not digits:
            return ""
        if len(digits) <= 2:
            base = digits.zfill(2)
            return f"{prefix}{base}" if prefix else base
        if len(digits) == 3:
            base = digits[:2]
            if prefix:
                base = f"{prefix}{base}"
            return f"{base}.{digits[2]}"
        base = digits[:2]
        if prefix:
            base = f"{prefix}{base}"
        return f"{base}.{digits[2:4]}"

    def _get_nace_level_code(self, nace_code: str, level: str) -> str:
        """
        Extract hierarchical NACE code by level.
        Supported levels:
        - nace_division
        - nace_group
        - nace_class
        """
        normalized = self.normalize_nace_code(nace_code)
        if not normalized:
            return ""

        if len(normalized) == 1 and normalized.isalpha():
            return normalized

        base_division = normalized.split(".", 1)[0]
        tail = normalized.split(".", 1)[1] if "." in normalized else ""

        if level == "nace_division":
            return base_division
        if level == "nace_group":
            if tail:
                return f"{base_division}.{tail[:1]}"
            return base_division
        if level == "nace_class":
            if len(tail) >= 2:
                return f"{base_division}.{tail[:2]}"
            if len(tail) == 1:
                return f"{base_division}.{tail}"
            return base_division

        return ""

    def get_sector_label(self, sector_code: str, system: str = "isco") -> str:
        """
        Resolve a human-readable label for a sector/group code.
        """
        sector_code = str(sector_code).strip()
        if not sector_code:
            return "Sector not specified"

        if str(system or "isco").strip().lower() == "nace":
            nace_code = self.normalize_nace_code(sector_code)
            if not nace_code:
                return "Sector not specified"
            return self.engine.nace_labels.get(nace_code, nace_code)

        # direct lookup
        if sector_code in self.engine.occupation_group_labels:
            return self.engine.occupation_group_labels[sector_code]

        # URI form
        uri_key = f"http://data.europa.eu/esco/isco/{sector_code}"
        if uri_key in self.engine.occupation_group_labels:
            return self.engine.occupation_group_labels[uri_key]

        return sector_code

    def get_esco_matrix_sheet_name(self, skill_group_level: int = 1, occupation_level: int = 1) -> str:
        """
        Resolve the official ESCO matrix sheet name.

        Example:
        skill_group_level=1, occupation_level=1 -> Matrix 1.1
        """
        return f"Matrix {skill_group_level}.{occupation_level}"

    def get_occupation_group_id_for_matrix(self, occ_id: str, occupation_level: int = 1) -> str:
        """
        Resolve the occupation group id used by the official ESCO matrix.

        Current incremental version:
        - read local occupation_meta[occ_id]["isco_group"]
        - try to reduce it to the requested ISCO level if it looks like a C-code

        Examples:
        - occupation_level=1 -> C2
        - occupation_level=2 -> C25
        - occupation_level=3 -> C251
        - occupation_level=4 -> C2512
        """
        occ_id = str(occ_id).strip()
        if not occ_id:
            return ""

        meta = self.engine.occupation_meta.get(occ_id, {})
        group_id = str(meta.get("isco_group", "")).strip()

        if not group_id:
            return ""

        # if already in ESCO/ISCO URI form like http://data.europa.eu/esco/isco/C2512
        if group_id.startswith("http"):
            code = group_id.rstrip("/").split("/")[-1]
        else:
            code = group_id

        code = code.strip()
        if code and not code.startswith("C") and code[0].isdigit():
            code = f"C{code}"
        # normalize to requested level if possible
        if code.startswith("C"):
            if occupation_level == 1:
                return f"C{code[1:2]}" if len(code) >= 2 else code
            elif occupation_level == 2:
                return f"C{code[1:3]}" if len(code) >= 3 else code
            elif occupation_level == 3:
                return f"C{code[1:4]}" if len(code) >= 4 else code
            elif occupation_level == 4:
                return f"C{code[1:5]}" if len(code) >= 5 else code

        return code
    def get_official_esco_profile_for_occupation(
        self,
        occ_id: str,
        skill_group_level: int = 1,
        occupation_level: int = 1
    ):
        """
        Return the official ESCO matrix profile for a given occupation, by:
        1. resolving the occupation group id
        2. selecting the proper matrix sheet
        3. returning the stored profile
        """
        group_code = self.get_occupation_group_id_for_matrix(
            occ_id=occ_id,
            occupation_level=occupation_level
        )
        if not group_code:
            return None

        sheet_name = self.get_esco_matrix_sheet_name(
            skill_group_level=skill_group_level,
            occupation_level=occupation_level
        )

        uri_key = f"http://data.europa.eu/esco/isco/{group_code}"

        profile = self.engine.esco_matrix_profiles.get((sheet_name, uri_key))
        if profile:
            return {
                "sheet_name": sheet_name,
                "occupation_group_id": uri_key,
                "occupation_group_label": profile["occupation_group_label"],
                "profile": profile["profile"]
            }

        # fallback: try raw code if ever needed
        profile = self.engine.esco_matrix_profiles.get((sheet_name, group_code))
        if profile:
            return {
                "sheet_name": sheet_name,
                "occupation_group_id": group_code,
                "occupation_group_label": profile["occupation_group_label"],
                "profile": profile["profile"]
            }

        return None
