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
    top_job_titles JSONB NOT NULL,
    PRIMARY KEY (run_id, sector)
);

CREATE INDEX IF NOT EXISTS ix_sector_yearly_snapshots_lookup
    ON sector_yearly_snapshots (year, COALESCE(location_code, ''), job_count DESC);
