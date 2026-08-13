WITH run_global AS (
    INSERT INTO sector_snapshot_runs (
        year, location_code, version, status, period_start, period_end, total_jobs, completed_at, message
    )
    VALUES (
        2024, NULL, 1, 'completed', '2024-01-01', '2024-12-31', 1280, now(), 'Demo global sector snapshot'
    )
    RETURNING id
),
run_demo AS (
    INSERT INTO sector_snapshot_runs (
        year, location_code, version, status, period_start, period_end, total_jobs, completed_at, message
    )
    VALUES (
        2024, 'DEMO', 1, 'completed', '2024-01-01', '2024-12-31', 1280, now(), 'Demo location sector snapshot'
    )
    RETURNING id
),
demo_rows AS (
    SELECT *
    FROM (
        VALUES
        (
            'Information and communication',
            'Information and communication',
            420,
            0.3281,
            1260,
            38,
            '[{"skill_id":"skill-python","label":"Python","count":188,"frequency":0.1492,"is_green":false,"is_digital":true},{"skill_id":"skill-sql","label":"SQL","count":142,"frequency":0.1127,"is_green":false,"is_digital":true},{"skill_id":"skill-cloud","label":"cloud computing","count":96,"frequency":0.0762,"is_green":false,"is_digital":true}]'::jsonb,
            '[{"name":"Software Engineer","count":86},{"name":"Data Analyst","count":54},{"name":"DevOps Engineer","count":41}]'::jsonb
        ),
        (
            'Education',
            'Education',
            260,
            0.2031,
            690,
            31,
            '[{"skill_id":"skill-training","label":"deliver training","count":98,"frequency":0.142,"is_green":false,"is_digital":false},{"skill_id":"skill-curriculum","label":"develop curriculum","count":74,"frequency":0.1072,"is_green":false,"is_digital":false},{"skill_id":"skill-digital-learning","label":"digital learning platforms","count":58,"frequency":0.0841,"is_green":false,"is_digital":true}]'::jsonb,
            '[{"name":"Teacher","count":72},{"name":"Training Specialist","count":39},{"name":"Education Coordinator","count":26}]'::jsonb
        ),
        (
            'Manufacturing',
            'Manufacturing',
            240,
            0.1875,
            610,
            29,
            '[{"skill_id":"skill-quality","label":"quality control","count":112,"frequency":0.1836,"is_green":false,"is_digital":false},{"skill_id":"skill-lean","label":"lean manufacturing","count":76,"frequency":0.1246,"is_green":false,"is_digital":false},{"skill_id":"skill-maintenance","label":"equipment maintenance","count":63,"frequency":0.1033,"is_green":false,"is_digital":false}]'::jsonb,
            '[{"name":"Production Operator","count":64},{"name":"Quality Specialist","count":42},{"name":"Maintenance Technician","count":31}]'::jsonb
        ),
        (
            'Professional, scientific and technical activities',
            'Professional, scientific and technical activities',
            210,
            0.1641,
            540,
            34,
            '[{"skill_id":"skill-project-management","label":"project management","count":89,"frequency":0.1648,"is_green":false,"is_digital":false},{"skill_id":"skill-research","label":"conduct research","count":70,"frequency":0.1296,"is_green":false,"is_digital":false},{"skill_id":"skill-reporting","label":"technical reporting","count":66,"frequency":0.1222,"is_green":false,"is_digital":true}]'::jsonb,
            '[{"name":"Project Manager","count":44},{"name":"Research Analyst","count":35},{"name":"Consultant","count":29}]'::jsonb
        ),
        (
            'Administrative and support service activities',
            'Administrative and support service activities',
            150,
            0.1172,
            360,
            22,
            '[{"skill_id":"skill-customer-service","label":"customer service","count":84,"frequency":0.2333,"is_green":false,"is_digital":false},{"skill_id":"skill-scheduling","label":"scheduling","count":52,"frequency":0.1444,"is_green":false,"is_digital":false},{"skill_id":"skill-crm","label":"CRM software","count":44,"frequency":0.1222,"is_green":false,"is_digital":true}]'::jsonb,
            '[{"name":"Administrative Assistant","count":48},{"name":"Customer Support Specialist","count":37},{"name":"Office Coordinator","count":22}]'::jsonb
        )
    ) AS rows (
        sector, sector_label, job_count, job_share, total_skill_mentions,
        unique_skills, top_skills, top_job_titles
    )
)
INSERT INTO sector_yearly_snapshots (
    run_id, year, location_code, sector, sector_label, job_count, job_share,
    total_skill_mentions, unique_skills, top_skills, top_job_titles
)
SELECT run_global.id, 2024, NULL, demo_rows.*
FROM run_global, demo_rows
UNION ALL
SELECT run_demo.id, 2024, 'DEMO', demo_rows.*
FROM run_demo, demo_rows;
