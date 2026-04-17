-- Migration 003: Create hotspots table
-- Stores risk-ranked file entries by correlating git commit frequency
-- with cyclomatic complexity. Files that change often AND are complex
-- are the highest-priority refactoring targets.

CREATE TABLE IF NOT EXISTS hotspots (
    id                          SERIAL          PRIMARY KEY,
    repository_id               INTEGER         NOT NULL,   -- FK → projects.id
    file_path                   VARCHAR(500)    NOT NULL,

    -- Git churn metrics
    commit_frequency            INTEGER         NOT NULL    DEFAULT 0,

    -- Complexity metrics (from the latest analysis of this file)
    avg_cyclomatic_complexity   NUMERIC(6,2)    NOT NULL    DEFAULT 0,
    max_cyclomatic_complexity   INTEGER         NOT NULL    DEFAULT 0,

    -- Composite hotspot score: commit_frequency × avg_cyclomatic_complexity
    -- Higher scores indicate higher refactoring priority.
    hotspot_score               NUMERIC(8,2)    NOT NULL    DEFAULT 0,

    -- Timestamps
    last_analyzed_at            TIMESTAMPTZ     NOT NULL    DEFAULT NOW(),

    -- Extended data (top functions, change authors, related files, etc.)
    metadata                    JSONB                       DEFAULT '{}'::jsonb,

    -- Ensure one hotspot entry per file per repository
    CONSTRAINT uq_hotspots_repo_file UNIQUE (repository_id, file_path)
);

-- Primary lookup pattern: "show me the top hotspots for repo X"
CREATE INDEX IF NOT EXISTS idx_hotspots_repo_score
    ON hotspots (repository_id, hotspot_score DESC);

-- Secondary index for file-specific lookups
CREATE INDEX IF NOT EXISTS idx_hotspots_repo_file
    ON hotspots (repository_id, file_path);
