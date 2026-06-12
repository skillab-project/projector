WITH years(year, total_jobs, ict, education, manufacturing, professional, admin_support) AS (
    VALUES
        (2020, 870, 230, 190, 210, 140, 100),
        (2021, 960, 280, 205, 215, 155, 105),
        (2022, 1060, 330, 225, 225, 170, 110),
        (2023, 1160, 375, 240, 235, 190, 120)
),
run_values AS (
    SELECT year, NULL::text AS location_code, total_jobs
    FROM years
    UNION ALL
    SELECT year, 'DEMO'::text AS location_code, total_jobs
    FROM years
),
inserted_runs AS (
    INSERT INTO sector_snapshot_runs (
        year, location_code, version, status, period_start, period_end, total_jobs, completed_at, message
    )
    SELECT
        year,
        location_code,
        1,
        'completed',
        make_date(year, 1, 1),
        make_date(year, 12, 31),
        total_jobs,
        now(),
        'Demo historical sector snapshot'
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
        AND COALESCE(r.location_code, '') = COALESCE(v.location_code, '')
        AND r.version = 1
),
sector_rows AS (
    SELECT
        year,
        total_jobs,
        'Information and communication' AS sector,
        'Information and communication' AS sector_label,
        ict AS job_count,
        (ict * 3) AS total_skill_mentions,
        30 + (year - 2020) * 2 AS unique_skills,
        jsonb_build_array(
            jsonb_build_object('skill_id', 'skill-python', 'label', 'Python', 'count', 72 + (year - 2020) * 28, 'frequency', 0.16, 'is_green', false, 'is_digital', true),
            jsonb_build_object('skill_id', 'skill-sql', 'label', 'SQL', 'count', 58 + (year - 2020) * 21, 'frequency', 0.13, 'is_green', false, 'is_digital', true),
            jsonb_build_object('skill_id', 'skill-cloud', 'label', 'cloud computing', 'count', 36 + (year - 2020) * 15, 'frequency', 0.09, 'is_green', false, 'is_digital', true)
        ) AS top_skills,
        jsonb_build_array(
            jsonb_build_object('name', 'Software Engineer', 'count', 44 + (year - 2020) * 10),
            jsonb_build_object('name', 'Data Analyst', 'count', 26 + (year - 2020) * 7),
            jsonb_build_object('name', 'DevOps Engineer', 'count', 18 + (year - 2020) * 5)
        ) AS top_job_titles
    FROM years
    UNION ALL
    SELECT
        year,
        total_jobs,
        'Education',
        'Education',
        education,
        (education * 3),
        26 + (year - 2020),
        jsonb_build_array(
            jsonb_build_object('skill_id', 'skill-training', 'label', 'deliver training', 'count', 62 + (year - 2020) * 9, 'frequency', 0.14, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-curriculum', 'label', 'develop curriculum', 'count', 48 + (year - 2020) * 7, 'frequency', 0.11, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-digital-learning', 'label', 'digital learning platforms', 'count', 31 + (year - 2020) * 8, 'frequency', 0.08, 'is_green', false, 'is_digital', true)
        ),
        jsonb_build_array(
            jsonb_build_object('name', 'Teacher', 'count', 46 + (year - 2020) * 6),
            jsonb_build_object('name', 'Training Specialist', 'count', 22 + (year - 2020) * 4),
            jsonb_build_object('name', 'Education Coordinator', 'count', 14 + (year - 2020) * 3)
        )
    FROM years
    UNION ALL
    SELECT
        year,
        total_jobs,
        'Manufacturing',
        'Manufacturing',
        manufacturing,
        (manufacturing * 3),
        25 + (year - 2020),
        jsonb_build_array(
            jsonb_build_object('skill_id', 'skill-quality', 'label', 'quality control', 'count', 88 + (year - 2020) * 6, 'frequency', 0.18, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-lean', 'label', 'lean manufacturing', 'count', 56 + (year - 2020) * 5, 'frequency', 0.12, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-maintenance', 'label', 'equipment maintenance', 'count', 43 + (year - 2020) * 4, 'frequency', 0.10, 'is_green', false, 'is_digital', false)
        ),
        jsonb_build_array(
            jsonb_build_object('name', 'Production Operator', 'count', 54 + (year - 2020) * 3),
            jsonb_build_object('name', 'Quality Specialist', 'count', 31 + (year - 2020) * 3),
            jsonb_build_object('name', 'Maintenance Technician', 'count', 24 + (year - 2020) * 2)
        )
    FROM years
    UNION ALL
    SELECT
        year,
        total_jobs,
        'Professional, scientific and technical activities',
        'Professional, scientific and technical activities',
        professional,
        (professional * 3),
        28 + (year - 2020) * 2,
        jsonb_build_array(
            jsonb_build_object('skill_id', 'skill-project-management', 'label', 'project management', 'count', 53 + (year - 2020) * 9, 'frequency', 0.16, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-research', 'label', 'conduct research', 'count', 41 + (year - 2020) * 7, 'frequency', 0.13, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-reporting', 'label', 'technical reporting', 'count', 37 + (year - 2020) * 7, 'frequency', 0.12, 'is_green', false, 'is_digital', true)
        ),
        jsonb_build_array(
            jsonb_build_object('name', 'Project Manager', 'count', 24 + (year - 2020) * 5),
            jsonb_build_object('name', 'Research Analyst', 'count', 18 + (year - 2020) * 4),
            jsonb_build_object('name', 'Consultant', 'count', 16 + (year - 2020) * 3)
        )
    FROM years
    UNION ALL
    SELECT
        year,
        total_jobs,
        'Administrative and support service activities',
        'Administrative and support service activities',
        admin_support,
        (admin_support * 3),
        19 + (year - 2020),
        jsonb_build_array(
            jsonb_build_object('skill_id', 'skill-customer-service', 'label', 'customer service', 'count', 48 + (year - 2020) * 8, 'frequency', 0.23, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-scheduling', 'label', 'scheduling', 'count', 30 + (year - 2020) * 5, 'frequency', 0.14, 'is_green', false, 'is_digital', false),
            jsonb_build_object('skill_id', 'skill-crm', 'label', 'CRM software', 'count', 24 + (year - 2020) * 5, 'frequency', 0.12, 'is_green', false, 'is_digital', true)
        ),
        jsonb_build_array(
            jsonb_build_object('name', 'Administrative Assistant', 'count', 30 + (year - 2020) * 4),
            jsonb_build_object('name', 'Customer Support Specialist', 'count', 22 + (year - 2020) * 4),
            jsonb_build_object('name', 'Office Coordinator', 'count', 13 + (year - 2020) * 2)
        )
    FROM years
)
INSERT INTO sector_yearly_snapshots (
    run_id, year, location_code, sector, sector_label, job_count, job_share,
    total_skill_mentions, unique_skills, top_skills, top_job_titles
)
SELECT
    runs.id,
    sector_rows.year,
    runs.location_code,
    sector_rows.sector,
    sector_rows.sector_label,
    sector_rows.job_count,
    round((sector_rows.job_count::numeric / sector_rows.total_jobs), 4)::double precision,
    sector_rows.total_skill_mentions,
    sector_rows.unique_skills,
    sector_rows.top_skills,
    sector_rows.top_job_titles
FROM runs
JOIN sector_rows ON runs.year = sector_rows.year
ON CONFLICT DO NOTHING;
