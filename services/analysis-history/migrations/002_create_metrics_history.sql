-- Migration 002: Create metrics_history hypertable
-- Stores aggregated code quality snapshots per repository per analysis run.
-- Partitioned by recorded_at using TimescaleDB's hypertable pattern for
-- efficient time-range queries and automatic chunk management.

CREATE TABLE IF NOT EXISTS metrics_history (
    -- Time dimension (hypertable partition key)
    recorded_at         TIMESTAMPTZ     NOT NULL,

    -- Entity references
    repository_id       INTEGER         NOT NULL,   -- FK → projects.id
    analysis_run_id     INTEGER         NOT NULL,   -- FK → analyses.id

    -- Composite scores
    code_health_score   NUMERIC(3,1)    NOT NULL    CHECK (code_health_score BETWEEN 1.0 AND 10.0),
    technical_debt_hours NUMERIC(10,2)  NOT NULL    DEFAULT 0,

    -- Issue counts by severity
    total_issues        INTEGER         NOT NULL    DEFAULT 0,
    critical_count      INTEGER         NOT NULL    DEFAULT 0,
    high_count          INTEGER         NOT NULL    DEFAULT 0,
    medium_count        INTEGER         NOT NULL    DEFAULT 0,
    low_count           INTEGER         NOT NULL    DEFAULT 0,

    -- Code metrics
    lines_of_code       INTEGER         NOT NULL    DEFAULT 0,
    avg_complexity      NUMERIC(6,2)               DEFAULT 0,
    max_complexity      INTEGER                    DEFAULT 0,
    maintainability_index NUMERIC(6,2)             DEFAULT 0,
    duplication_pct     NUMERIC(5,2)               DEFAULT 0,

    -- Dimension grades (A, B, C, D)
    reliability_grade       CHAR(1)     NOT NULL    DEFAULT 'D'  CHECK (reliability_grade IN ('A','B','C','D')),
    security_grade          CHAR(1)     NOT NULL    DEFAULT 'D'  CHECK (security_grade IN ('A','B','C','D')),
    maintainability_grade   CHAR(1)     NOT NULL    DEFAULT 'D'  CHECK (maintainability_grade IN ('A','B','C','D')),
    coverage_grade          CHAR(1)     NOT NULL    DEFAULT 'D'  CHECK (coverage_grade IN ('A','B','C','D')),

    -- Extensible metadata (language breakdown, per-file details, etc.)
    metadata            JSONB                      DEFAULT '{}'::jsonb
);

-- Convert to TimescaleDB hypertable partitioned on recorded_at
-- chunk_time_interval of 7 days is optimized for weekly dashboard queries.
-- if_not_exists prevents errors on re-runs.
SELECT create_hypertable(
    'metrics_history',
    'recorded_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Primary composite index for repository-scoped time-series lookups.
-- This is the most common query pattern: "show me history for repo X ordered by time".
CREATE INDEX IF NOT EXISTS idx_metrics_history_repo_time
    ON metrics_history (repository_id, recorded_at DESC);

-- Index for joining back to specific analysis runs
CREATE INDEX IF NOT EXISTS idx_metrics_history_run_id
    ON metrics_history (analysis_run_id);

-- Unique constraint to prevent duplicate aggregations for the same run
CREATE UNIQUE INDEX IF NOT EXISTS idx_metrics_history_unique_run
    ON metrics_history (analysis_run_id, recorded_at);
