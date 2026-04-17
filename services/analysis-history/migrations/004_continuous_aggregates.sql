-- Migration 004: Continuous Aggregates for Weekly Rollups
-- TimescaleDB continuous aggregates automatically maintain materialized
-- views that incrementally update as new data arrives. This eliminates
-- the need for manual batch rollup jobs for dashboard trend queries.

-- Weekly code health rollup per repository
CREATE MATERIALIZED VIEW IF NOT EXISTS weekly_code_health
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('7 days', recorded_at)                  AS week,
    repository_id,
    AVG(code_health_score)                              AS avg_health,
    MIN(code_health_score)                              AS min_health,
    MAX(code_health_score)                              AS max_health,
    SUM(technical_debt_hours)                           AS total_debt_hours,
    AVG(technical_debt_hours)                           AS avg_debt_hours,
    MAX(total_issues)                                   AS peak_issues,
    AVG(total_issues)                                   AS avg_issues,
    AVG(avg_complexity)                                 AS avg_complexity,
    AVG(maintainability_index)                          AS avg_maintainability,
    MAX(lines_of_code)                                  AS max_loc,
    COUNT(*)                                            AS run_count,
    LAST(reliability_grade, recorded_at)                AS latest_reliability,
    LAST(security_grade, recorded_at)                   AS latest_security,
    LAST(maintainability_grade, recorded_at)            AS latest_maintainability,
    LAST(coverage_grade, recorded_at)                   AS latest_coverage
FROM metrics_history
GROUP BY week, repository_id
WITH NO DATA;

-- Refresh policy: automatically refresh the continuous aggregate
-- for the last 2 weeks of data, every hour.
SELECT add_continuous_aggregate_policy('weekly_code_health',
    start_offset    => INTERVAL '14 days',
    end_offset      => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists   => TRUE
);

-- Data retention policy: automatically drop raw metrics_history chunks
-- older than 1 year. The weekly_code_health aggregate retains the rolled-up
-- summaries indefinitely.
SELECT add_retention_policy('metrics_history',
    drop_after => INTERVAL '365 days',
    if_not_exists => TRUE
);
