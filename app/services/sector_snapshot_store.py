import json
from contextlib import contextmanager
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

        return run_id
