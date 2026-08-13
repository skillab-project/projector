import json
from contextlib import contextmanager
from collections import Counter
from typing import Optional, List


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sector_snapshot_runs (
    id BIGSERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    location_code TEXT,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_jobs INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    message TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_sector_snapshot_runs_version
    ON sector_snapshot_runs (year, COALESCE(location_code, ''), version);

CREATE INDEX IF NOT EXISTS ix_sector_snapshot_runs_latest
    ON sector_snapshot_runs (year, COALESCE(location_code, ''), status, completed_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS sector_yearly_snapshots (
    run_id BIGINT NOT NULL REFERENCES sector_snapshot_runs(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    location_code TEXT,
    sector TEXT NOT NULL,
    sector_label TEXT NOT NULL,
    job_count INTEGER NOT NULL,
    job_share DOUBLE PRECISION NOT NULL,
    total_skill_mentions INTEGER NOT NULL,
    unique_skills INTEGER NOT NULL,
    top_skills JSONB NOT NULL,
    all_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_job_titles JSONB NOT NULL,
    PRIMARY KEY (run_id, sector)
);

CREATE INDEX IF NOT EXISTS ix_sector_yearly_snapshots_lookup
    ON sector_yearly_snapshots (year, COALESCE(location_code, ''), job_count DESC);

CREATE TABLE IF NOT EXISTS sector_snapshot_refresh_status (
    year INTEGER NOT NULL,
    location_code TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    last_success_at TIMESTAMPTZ,
    last_failed_at TIMESTAMPTZ,
    last_error TEXT,
    last_checkpoint_page INTEGER,
    fetched_jobs INTEGER NOT NULL DEFAULT 0,
    expected_jobs INTEGER NOT NULL DEFAULT 0,
    source TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (year, location_code)
);
"""


class SectorSnapshotStore:
    def __init__(self, database_url: Optional[str]):
        self.database_url = database_url

    @property
    def enabled(self):
        return bool(self.database_url)

    @contextmanager
    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL not configured")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg is required for PostgreSQL snapshot storage") from exc

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def ensure_schema(self):
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)
            conn.commit()

    def read_latest(self, year: int, location_code: Optional[str] = None):
        if not self.enabled:
            return None

        location_key = location_code or ""
        with self._connect() as conn:
            run = conn.execute(
                """
                SELECT *
                FROM sector_snapshot_runs
                WHERE year = %s
                  AND COALESCE(location_code, '') = %s
                  AND status = 'completed'
                ORDER BY completed_at DESC NULLS LAST, id DESC
                LIMIT 1
                """,
                (year, location_key),
            ).fetchone()
            if not run:
                return None

            rows = conn.execute(
                """
                SELECT sector, sector_label, job_count, job_share, total_skill_mentions,
                       unique_skills, top_skills, all_skills, top_job_titles
                FROM sector_yearly_snapshots
                WHERE run_id = %s
                ORDER BY job_count DESC, total_skill_mentions DESC, sector_label ASC
                """,
                (run["id"],),
            ).fetchall()

        return {
            "status": "completed",
            "year": run["year"],
            "data_source": "postgres",
            "window": {
                "label": f"{run['year']} snapshot",
                "min_date": str(run["period_start"]),
                "max_date": str(run["period_end"]),
            },
            "total_jobs": run["total_jobs"],
            "sector_filter": [],
            "refresh_status": self.read_refresh_status(year, location_code),
            "sectors": [
                {
                    **dict(row),
                    "top_skills": row["top_skills"],
                    "all_skills": row["all_skills"] or row["top_skills"],
                    "top_job_titles": row["top_job_titles"],
                }
                for row in rows
            ],
        }

    def read_regional_sectoral(self, year: int, location_code: Optional[str] = None, top_k: int = 10):
        if not self.enabled:
            return None

        top_k = max(int(top_k or 10), 1)
        location_filter = str(location_code or "").strip()
        with self._connect() as conn:
            rows = conn.execute(
                """
                WITH latest_runs AS (
                    SELECT DISTINCT ON (COALESCE(location_code, ''))
                        id, year, location_code, total_jobs, period_start, period_end, completed_at
                    FROM sector_snapshot_runs
                    WHERE year = %s
                      AND status = 'completed'
                      AND location_code IS NOT NULL
                      AND (%s = '' OR location_code = %s)
                      AND (%s <> '' OR UPPER(location_code) <> 'DEMO')
                    ORDER BY COALESCE(location_code, ''), completed_at DESC NULLS LAST, id DESC
                )
                SELECT
                    latest_runs.id AS run_id,
                    latest_runs.location_code,
                    latest_runs.total_jobs,
                    latest_runs.period_start,
                    latest_runs.period_end,
                    snapshots.sector,
                    snapshots.sector_label,
                    snapshots.job_count
                FROM latest_runs
                JOIN sector_yearly_snapshots snapshots
                    ON snapshots.run_id = latest_runs.id
                ORDER BY latest_runs.location_code, snapshots.job_count DESC, snapshots.sector_label ASC
                """,
                (year, location_filter, location_filter, location_filter),
            ).fetchall()

            global_rows = conn.execute(
                """
                WITH latest_global AS (
                    SELECT id, total_jobs
                    FROM sector_snapshot_runs
                    WHERE year = %s
                      AND status = 'completed'
                      AND location_code IS NULL
                    ORDER BY completed_at DESC NULLS LAST, id DESC
                    LIMIT 1
                )
                SELECT latest_global.total_jobs, snapshots.sector, snapshots.job_count
                FROM latest_global
                JOIN sector_yearly_snapshots snapshots
                    ON snapshots.run_id = latest_global.id
                """,
                (year,),
            ).fetchall()

        if not rows:
            return None

        window = {
            "label": f"{int(year)} snapshot",
            "min_date": str(rows[0]["period_start"]),
            "max_date": str(rows[0]["period_end"]),
        }
        global_total_jobs = sum({row["run_id"]: int(row["total_jobs"] or 0) for row in rows}.values())
        global_sector_counts = Counter()
        if global_rows:
            global_total_jobs = int(global_rows[0]["total_jobs"] or global_total_jobs or 0)
            for row in global_rows:
                global_sector_counts[row["sector"]] += int(row["job_count"] or 0)
        else:
            for row in rows:
                global_sector_counts[row["sector"]] += int(row["job_count"] or 0)

        levels = {"raw": {}, "nuts1": {}, "nuts2": {}, "nuts3": {}}
        seen_run_by_level = {level: set() for level in levels}
        for row in rows:
            raw_code = str(row["location_code"] or "").strip()
            codes = {
                "raw": raw_code,
                "nuts1": raw_code[:3],
                "nuts2": raw_code[:4] if len(raw_code) >= 4 else None,
                "nuts3": raw_code if len(raw_code) >= 5 else None,
            }
            for level, code in codes.items():
                if not code:
                    continue
                bucket = levels[level].setdefault(
                    code,
                    {"total_jobs": 0, "sectors": Counter(), "labels": {}},
                )
                run_key = (level, code, row["run_id"])
                if run_key not in seen_run_by_level[level]:
                    bucket["total_jobs"] += int(row["total_jobs"] or 0)
                    seen_run_by_level[level].add(run_key)
                bucket["sectors"][row["sector"]] += int(row["job_count"] or 0)
                bucket["labels"][row["sector"]] = row["sector_label"] or row["sector"]

        def format_level(source):
            output = []
            for code, data in source.items():
                sector_items = []
                total_jobs = int(data["total_jobs"] or 0)
                for sector_code, count in data["sectors"].most_common(top_k):
                    region_share = count / total_jobs if total_jobs else 0
                    global_count = global_sector_counts.get(sector_code, 0)
                    global_share = global_count / global_total_jobs if global_total_jobs else 0
                    specialization = region_share / global_share if global_share else 0
                    sector_items.append({
                        "sector": data["labels"].get(sector_code, sector_code),
                        "sector_code": sector_code,
                        "count": count,
                        "share_in_region": round(region_share * 100, 2),
                        "specialization": round(specialization, 2),
                    })
                output.append({
                    "code": code,
                    "total_jobs": total_jobs,
                    "top_sectors": sector_items,
                })
            return sorted(output, key=lambda item: item["total_jobs"], reverse=True)

        return {
            "status": "completed",
            "year": int(year),
            "data_source": "postgres",
            "window": window,
            "refresh_status": self.read_refresh_status(year, location_code),
            "regional_sectoral": {
                "raw": format_level(levels["raw"]),
                "nuts1": format_level(levels["nuts1"]),
                "nuts2": format_level(levels["nuts2"]),
                "nuts3": format_level(levels["nuts3"]),
            },
        }

    def latest_completed_at(self, year: int, location_code: Optional[str] = None):
        if not self.enabled:
            return None

        location_key = location_code or ""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT completed_at
                FROM sector_snapshot_runs
                WHERE year = %s
                  AND COALESCE(location_code, '') = %s
                  AND status = 'completed'
                ORDER BY completed_at DESC NULLS LAST, id DESC
                LIMIT 1
                """,
                (year, location_key),
            ).fetchone()

        return row["completed_at"] if row else None

    def read_refresh_status(self, year: int, location_code: Optional[str] = None):
        if not self.enabled:
            return None

        rows = []
        with self._connect() as conn:
            for key in [location_code, ""] if location_code else [""]:
                row = conn.execute(
                    """
                    SELECT status, last_success_at, last_failed_at, last_error,
                           last_checkpoint_page, fetched_jobs, expected_jobs, source, updated_at
                    FROM sector_snapshot_refresh_status
                    WHERE year = %s AND location_code = %s
                    LIMIT 1
                    """,
                    (year, key),
                ).fetchone()
                if row:
                    rows.append(row)
                    break

        if not rows:
            return None
        row = rows[0]
        return {
            "status": row["status"],
            "last_success_at": row["last_success_at"].isoformat() if row["last_success_at"] else None,
            "last_failed_at": row["last_failed_at"].isoformat() if row["last_failed_at"] else None,
            "last_error": row["last_error"],
            "last_checkpoint_page": row["last_checkpoint_page"],
            "fetched_jobs": row["fetched_jobs"],
            "expected_jobs": row["expected_jobs"],
            "source": row["source"],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    def write_refresh_status(
            self,
            year: int,
            location_code: Optional[str],
            status: str,
            last_error: Optional[str] = None,
            last_checkpoint_page: Optional[int] = None,
            fetched_jobs: Optional[int] = None,
            expected_jobs: Optional[int] = None,
            source: Optional[str] = None,
    ):
        fetched_jobs = 0 if fetched_jobs is None else fetched_jobs
        expected_jobs = 0 if expected_jobs is None else expected_jobs
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sector_snapshot_refresh_status (
                    year, location_code, status, last_success_at, last_failed_at,
                    last_error, last_checkpoint_page, fetched_jobs, expected_jobs, source, updated_at
                )
                VALUES (
                    %s, %s, %s,
                    CASE WHEN %s = 'completed' THEN now() ELSE NULL END,
                    CASE WHEN %s = 'failed' THEN now() ELSE NULL END,
                    %s, %s, %s, %s, %s, now()
                )
                ON CONFLICT (year, location_code)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    last_success_at = CASE
                        WHEN EXCLUDED.status = 'completed' THEN EXCLUDED.last_success_at
                        ELSE sector_snapshot_refresh_status.last_success_at
                    END,
                    last_failed_at = CASE
                        WHEN EXCLUDED.status = 'failed' THEN EXCLUDED.last_failed_at
                        ELSE sector_snapshot_refresh_status.last_failed_at
                    END,
                    last_error = EXCLUDED.last_error,
                    last_checkpoint_page = EXCLUDED.last_checkpoint_page,
                    fetched_jobs = EXCLUDED.fetched_jobs,
                    expected_jobs = EXCLUDED.expected_jobs,
                    source = EXCLUDED.source,
                    updated_at = now()
                """,
                (
                    year,
                    location_code or "",
                    status,
                    status,
                    status,
                    last_error,
                    last_checkpoint_page,
                    fetched_jobs,
                    expected_jobs,
                    source,
                ),
            )
            conn.commit()

    def write_snapshot(
            self,
            year: int,
            location_code: Optional[str],
            period_start: str,
            period_end: str,
            total_jobs: int,
            sectors: List[dict],
    ):
        self.ensure_schema()
        location_key = location_code or None
        with self._connect() as conn:
            with conn.transaction():
                version = conn.execute(
                    """
                    SELECT COALESCE(MAX(version), 0) + 1 AS next_version
                    FROM sector_snapshot_runs
                    WHERE year = %s AND COALESCE(location_code, '') = %s
                    """,
                    (year, location_code or ""),
                ).fetchone()["next_version"]

                run = conn.execute(
                    """
                    INSERT INTO sector_snapshot_runs (
                        year, location_code, version, status, period_start, period_end, total_jobs
                    )
                    VALUES (%s, %s, %s, 'running', %s, %s, %s)
                    RETURNING id
                    """,
                    (year, location_key, version, period_start, period_end, total_jobs),
                ).fetchone()
                run_id = run["id"]

                for row in sectors:
                    conn.execute(
                        """
                        INSERT INTO sector_yearly_snapshots (
                            run_id, year, location_code, sector, sector_label, job_count,
                            job_share, total_skill_mentions, unique_skills, top_skills, all_skills, top_job_titles
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                        """,
                        (
                            run_id,
                            year,
                            location_key,
                            row["sector"],
                            row["sector_label"],
                            row["job_count"],
                            row["job_share"],
                            row["total_skill_mentions"],
                            row["unique_skills"],
                            json.dumps(row["top_skills"]),
                            json.dumps(row.get("all_skills") or row["top_skills"]),
                            json.dumps(row["top_job_titles"]),
                        ),
                    )

                conn.execute(
                    """
                    UPDATE sector_snapshot_runs
                    SET status = 'completed', completed_at = now()
                    WHERE id = %s
                    """,
                    (run_id,),
                )

        self.write_refresh_status(
            year=year,
            location_code=location_code,
            status="completed",
            fetched_jobs=total_jobs,
            expected_jobs=total_jobs,
            source="tracker",
        )
        return run_id
