ALTER TABLE sector_yearly_snapshots
    ADD COLUMN IF NOT EXISTS all_skills JSONB NOT NULL DEFAULT '[]'::jsonb;

WITH extra_skills AS (
    SELECT jsonb_build_array(
        jsonb_build_object('skill_id', 'skill-communication', 'label', 'communication', 'count', 36, 'frequency', 0.058, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-teamwork', 'label', 'teamwork', 'count', 34, 'frequency', 0.055, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-excel', 'label', 'Microsoft Excel', 'count', 32, 'frequency', 0.052, 'is_green', false, 'is_digital', true),
        jsonb_build_object('skill_id', 'skill-english', 'label', 'English', 'count', 30, 'frequency', 0.049, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-problem-solving', 'label', 'problem solving', 'count', 28, 'frequency', 0.045, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-planning', 'label', 'planning', 'count', 26, 'frequency', 0.042, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-data-analysis', 'label', 'data analysis', 'count', 24, 'frequency', 0.039, 'is_green', false, 'is_digital', true),
        jsonb_build_object('skill_id', 'skill-documentation', 'label', 'documentation', 'count', 22, 'frequency', 0.036, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-compliance', 'label', 'compliance', 'count', 20, 'frequency', 0.032, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-budgeting', 'label', 'budgeting', 'count', 18, 'frequency', 0.029, 'is_green', false, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-sustainability', 'label', 'sustainability', 'count', 16, 'frequency', 0.026, 'is_green', true, 'is_digital', false),
        jsonb_build_object('skill_id', 'skill-reporting-dashboard', 'label', 'dashboard reporting', 'count', 14, 'frequency', 0.023, 'is_green', false, 'is_digital', true)
    ) AS skills
)
UPDATE sector_yearly_snapshots
SET all_skills = top_skills || extra_skills.skills
FROM extra_skills
WHERE all_skills = '[]'::jsonb;

WITH region_scales(location_code, scale_factor) AS (
    VALUES
        ('IT', 0.55::numeric),
        ('DE', 0.75::numeric),
        ('FR', 0.65::numeric)
),
global_runs AS (
    SELECT *
    FROM sector_snapshot_runs
    WHERE location_code IS NULL
      AND status = 'completed'
      AND year BETWEEN 2020 AND 2024
),
run_values AS (
    SELECT
        global_runs.year,
        region_scales.location_code,
        global_runs.version,
        global_runs.period_start,
        global_runs.period_end,
        GREATEST(round(global_runs.total_jobs * region_scales.scale_factor)::int, 1) AS total_jobs
    FROM global_runs
    CROSS JOIN region_scales
),
inserted_runs AS (
    INSERT INTO sector_snapshot_runs (
        year, location_code, version, status, period_start, period_end, total_jobs, completed_at, message
    )
    SELECT
        year,
        location_code,
        version,
        'completed',
        period_start,
        period_end,
        total_jobs,
        now(),
        'Demo regional sector snapshot'
    FROM run_values
    ON CONFLICT DO NOTHING
    RETURNING id, year, location_code
),
runs AS (
    SELECT id, year, location_code
    FROM inserted_runs
    UNION
    SELECT r.id, r.year, r.location_code
    FROM sector_snapshot_runs r
    JOIN run_values v
        ON r.year = v.year
        AND r.location_code = v.location_code
        AND r.version = v.version
),
global_rows AS (
    SELECT
        snapshots.run_id,
        snapshots.year,
        snapshots.sector,
        snapshots.sector_label,
        snapshots.job_count,
        snapshots.job_share,
        snapshots.total_skill_mentions,
        snapshots.unique_skills,
        snapshots.top_skills,
        snapshots.top_job_titles,
        snapshots.all_skills,
        region_scales.location_code AS target_location_code,
        region_scales.scale_factor
    FROM sector_yearly_snapshots snapshots
    JOIN sector_snapshot_runs global_runs ON snapshots.run_id = global_runs.id
    CROSS JOIN region_scales
    WHERE global_runs.location_code IS NULL
      AND global_runs.status = 'completed'
      AND snapshots.year BETWEEN 2020 AND 2024
)
INSERT INTO sector_yearly_snapshots (
    run_id, year, location_code, sector, sector_label, job_count, job_share,
    total_skill_mentions, unique_skills, top_skills, top_job_titles, all_skills
)
SELECT
    runs.id,
    global_rows.year,
    runs.location_code,
    global_rows.sector,
    global_rows.sector_label,
    GREATEST(round(global_rows.job_count * global_rows.scale_factor)::int, 1),
    global_rows.job_share,
    GREATEST(round(global_rows.total_skill_mentions * global_rows.scale_factor)::int, 1),
    global_rows.unique_skills,
    global_rows.top_skills,
    global_rows.top_job_titles,
    global_rows.all_skills
FROM global_rows
JOIN runs
    ON runs.year = global_rows.year
    AND runs.location_code = global_rows.target_location_code
ON CONFLICT DO NOTHING;
