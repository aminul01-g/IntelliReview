// Package store provides the data access layer for the analysis-history
// service. It uses pgx/v5 connection pooling to communicate with the
// TimescaleDB-backed PostgreSQL instance.
package store

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"sort"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"
)

// Store wraps a pgx connection pool and exposes typed data access methods.
type Store struct {
	pool   *pgxpool.Pool
	logger *zap.Logger
}

// New creates a new Store with the given connection pool.
func New(pool *pgxpool.Pool, logger *zap.Logger) *Store {
	return &Store{pool: pool, logger: logger}
}

// Pool returns the underlying pgx connection pool for advanced queries.
func (s *Store) Pool() *pgxpool.Pool {
	return s.pool
}

// ─── Domain Types ───────────────────────────────────────────────────

// RawAnalysis represents a row from the existing `analyses` table that
// has not yet been aggregated into metrics_history.
type RawAnalysis struct {
	ID            int
	ProjectID     *int
	FilePath      string
	Language      string
	Status        string
	Issues        json.RawMessage
	Metrics       json.RawMessage
	ProcessingTime *float64
	CreatedAt     time.Time
	CompletedAt   *time.Time
}

// AnalysisIssue is the structure of a single issue within the analyses.issues JSON array.
type AnalysisIssue struct {
	Type       string  `json:"type"`
	Severity   string  `json:"severity"`
	Line       int     `json:"line"`
	Message    string  `json:"message"`
	Confidence float64 `json:"confidence,omitempty"`
	CWE        string  `json:"cwe,omitempty"`
}

// AnalysisMetrics is the structure of the analyses.metrics JSON object.
type AnalysisMetrics struct {
	LinesOfCode          int      `json:"lines_of_code"`
	Complexity           *float64 `json:"complexity"`
	MaintainabilityIndex *float64 `json:"maintainability_index"`
	DuplicationPct       *float64 `json:"duplication_percentage"`
}

// MetricsSnapshot represents a single row in the metrics_history hypertable.
type MetricsSnapshot struct {
	RecordedAt           time.Time
	RepositoryID         int
	AnalysisRunID        int
	CodeHealthScore      float64
	TechnicalDebtHours   float64
	TotalIssues          int
	CriticalCount        int
	HighCount            int
	MediumCount          int
	LowCount             int
	LinesOfCode          int
	AvgComplexity        float64
	MaxComplexity        int
	MaintainabilityIndex float64
	DuplicationPct       float64
	ReliabilityGrade     string
	SecurityGrade        string
	MaintainabilityGrade string
	CoverageGrade        string
	Metadata             json.RawMessage
}

// Hotspot represents a file-level risk entry in the hotspots table.
type Hotspot struct {
	ID                       int
	RepositoryID             int
	FilePath                 string
	CommitFrequency          int
	AvgCyclomaticComplexity  float64
	MaxCyclomaticComplexity  int
	HotspotScore             float64
	LastAnalyzedAt           time.Time
	Metadata                 json.RawMessage
}

// WeeklySnapshot represents a row from the weekly_code_health continuous aggregate.
type WeeklySnapshot struct {
	Week                   time.Time
	RepositoryID           int
	AvgHealth              float64
	TotalDebtHours         float64
	PeakIssues             int
	AvgIssues              float64
	RunCount               int
	LatestReliability      string
	LatestSecurity         string
	LatestMaintainability  string
	LatestCoverage         string
}

// ─── Migrations ─────────────────────────────────────────────────────

// RunMigrations reads SQL migration files from the provided filesystem
// and executes them sequentially against the database. Each migration is
// idempotent. The migrations FS and root directory are passed in from
// the caller (typically cmd/server/main.go which embeds them).
func (s *Store) RunMigrations(ctx context.Context, migrationsFS fs.FS, root string) error {
	entries, err := fs.ReadDir(migrationsFS, root)
	if err != nil {
		s.logger.Warn("could not read migrations directory", zap.String("root", root), zap.Error(err))
		return nil
	}

	// Sort entries to ensure execution order
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Name() < entries[j].Name()
	})

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".sql") {
			continue
		}

		path := root + "/" + entry.Name()
		data, err := fs.ReadFile(migrationsFS, path)
		if err != nil {
			return fmt.Errorf("read migration %s: %w", entry.Name(), err)
		}

		s.logger.Info("applying migration", zap.String("file", entry.Name()))
		if _, err := s.pool.Exec(ctx, string(data)); err != nil {
			return fmt.Errorf("execute migration %s: %w", entry.Name(), err)
		}
	}
	return nil
}

// runMigrationsFromDir is a fallback for when embed doesn't work (e.g., tests).
func (s *Store) runMigrationsFromDir(ctx context.Context) error {
	s.logger.Info("skipping embedded migrations (fallback path)")
	return nil
}

// ─── Raw Analysis Reads ─────────────────────────────────────────────

// GetUnprocessedAnalyses returns completed analyses that have not yet
// been aggregated into metrics_history. It checks for analyses with
// a project_id (repository association) that don't have a corresponding
// entry in metrics_history.
func (s *Store) GetUnprocessedAnalyses(ctx context.Context) ([]RawAnalysis, error) {
	query := `
		SELECT
			a.id, a.project_id, a.file_path, a.language, a.status,
			a.issues, a.metrics, a.processing_time,
			a.created_at, a.completed_at
		FROM analyses a
		WHERE a.status = 'completed'
		  AND a.project_id IS NOT NULL
		  AND NOT EXISTS (
			SELECT 1 FROM metrics_history mh
			WHERE mh.analysis_run_id = a.id
		  )
		ORDER BY a.created_at ASC
		LIMIT 500
	`

	rows, err := s.pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("query unprocessed analyses: %w", err)
	}
	defer rows.Close()

	var results []RawAnalysis
	for rows.Next() {
		var ra RawAnalysis
		if err := rows.Scan(
			&ra.ID, &ra.ProjectID, &ra.FilePath, &ra.Language, &ra.Status,
			&ra.Issues, &ra.Metrics, &ra.ProcessingTime,
			&ra.CreatedAt, &ra.CompletedAt,
		); err != nil {
			return nil, fmt.Errorf("scan analysis row: %w", err)
		}
		results = append(results, ra)
	}

	return results, rows.Err()
}

// ─── Metrics History Writes ─────────────────────────────────────────

// InsertMetricsSnapshot writes an aggregated snapshot to the metrics_history
// hypertable. This is idempotent due to the ON CONFLICT clause.
func (s *Store) InsertMetricsSnapshot(ctx context.Context, snap MetricsSnapshot) error {
	query := `
		INSERT INTO metrics_history (
			recorded_at, repository_id, analysis_run_id,
			code_health_score, technical_debt_hours,
			total_issues, critical_count, high_count, medium_count, low_count,
			lines_of_code, avg_complexity, max_complexity,
			maintainability_index, duplication_pct,
			reliability_grade, security_grade, maintainability_grade, coverage_grade,
			metadata
		) VALUES (
			$1, $2, $3, $4, $5,
			$6, $7, $8, $9, $10,
			$11, $12, $13, $14, $15,
			$16, $17, $18, $19, $20
		)
		ON CONFLICT (analysis_run_id, recorded_at) DO NOTHING
	`

	_, err := s.pool.Exec(ctx, query,
		snap.RecordedAt, snap.RepositoryID, snap.AnalysisRunID,
		snap.CodeHealthScore, snap.TechnicalDebtHours,
		snap.TotalIssues, snap.CriticalCount, snap.HighCount, snap.MediumCount, snap.LowCount,
		snap.LinesOfCode, snap.AvgComplexity, snap.MaxComplexity,
		snap.MaintainabilityIndex, snap.DuplicationPct,
		snap.ReliabilityGrade, snap.SecurityGrade, snap.MaintainabilityGrade, snap.CoverageGrade,
		snap.Metadata,
	)
	if err != nil {
		return fmt.Errorf("insert metrics snapshot: %w", err)
	}
	return nil
}

// ─── Hotspot Writes ─────────────────────────────────────────────────

// UpsertHotspot inserts or updates a hotspot entry for a given file.
func (s *Store) UpsertHotspot(ctx context.Context, h Hotspot) error {
	query := `
		INSERT INTO hotspots (
			repository_id, file_path,
			commit_frequency, avg_cyclomatic_complexity, max_cyclomatic_complexity,
			hotspot_score, last_analyzed_at, metadata
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		ON CONFLICT (repository_id, file_path) DO UPDATE SET
			commit_frequency          = EXCLUDED.commit_frequency,
			avg_cyclomatic_complexity  = EXCLUDED.avg_cyclomatic_complexity,
			max_cyclomatic_complexity  = EXCLUDED.max_cyclomatic_complexity,
			hotspot_score             = EXCLUDED.hotspot_score,
			last_analyzed_at          = EXCLUDED.last_analyzed_at,
			metadata                  = EXCLUDED.metadata
	`

	_, err := s.pool.Exec(ctx, query,
		h.RepositoryID, h.FilePath,
		h.CommitFrequency, h.AvgCyclomaticComplexity, h.MaxCyclomaticComplexity,
		h.HotspotScore, h.LastAnalyzedAt, h.Metadata,
	)
	if err != nil {
		return fmt.Errorf("upsert hotspot: %w", err)
	}
	return nil
}

// ─── Metrics History Reads (GraphQL) ────────────────────────────────

// GetHistory returns paginated metrics snapshots for a repository,
// using cursor-based pagination on recorded_at.
func (s *Store) GetHistory(
	ctx context.Context,
	repoID int,
	cursor *time.Time,
	limit int,
	startDate, endDate *time.Time,
) ([]MetricsSnapshot, bool, error) {
	// Fetch limit+1 to determine hasNextPage
	fetchLimit := limit + 1

	var args []interface{}
	argIdx := 1

	query := `SELECT
		recorded_at, repository_id, analysis_run_id,
		code_health_score, technical_debt_hours,
		total_issues, critical_count, high_count, medium_count, low_count,
		lines_of_code, avg_complexity, max_complexity,
		maintainability_index, duplication_pct,
		reliability_grade, security_grade, maintainability_grade, coverage_grade,
		metadata
	FROM metrics_history
	WHERE repository_id = $1`
	args = append(args, repoID)
	argIdx++

	if cursor != nil {
		query += fmt.Sprintf(" AND recorded_at < $%d", argIdx)
		args = append(args, *cursor)
		argIdx++
	}
	if startDate != nil {
		query += fmt.Sprintf(" AND recorded_at >= $%d", argIdx)
		args = append(args, *startDate)
		argIdx++
	}
	if endDate != nil {
		query += fmt.Sprintf(" AND recorded_at <= $%d", argIdx)
		args = append(args, *endDate)
		argIdx++
	}

	query += fmt.Sprintf(" ORDER BY recorded_at DESC LIMIT $%d", argIdx)
	args = append(args, fetchLimit)

	rows, err := s.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, false, fmt.Errorf("query history: %w", err)
	}
	defer rows.Close()

	var results []MetricsSnapshot
	for rows.Next() {
		var snap MetricsSnapshot
		if err := rows.Scan(
			&snap.RecordedAt, &snap.RepositoryID, &snap.AnalysisRunID,
			&snap.CodeHealthScore, &snap.TechnicalDebtHours,
			&snap.TotalIssues, &snap.CriticalCount, &snap.HighCount, &snap.MediumCount, &snap.LowCount,
			&snap.LinesOfCode, &snap.AvgComplexity, &snap.MaxComplexity,
			&snap.MaintainabilityIndex, &snap.DuplicationPct,
			&snap.ReliabilityGrade, &snap.SecurityGrade, &snap.MaintainabilityGrade, &snap.CoverageGrade,
			&snap.Metadata,
		); err != nil {
			return nil, false, fmt.Errorf("scan history row: %w", err)
		}
		results = append(results, snap)
	}

	hasNextPage := len(results) > limit
	if hasNextPage {
		results = results[:limit]
	}

	return results, hasNextPage, rows.Err()
}

// GetHistoryCount returns the total number of metrics snapshots for a repository.
func (s *Store) GetHistoryCount(ctx context.Context, repoID int) (int, error) {
	var count int
	err := s.pool.QueryRow(ctx,
		"SELECT COUNT(*) FROM metrics_history WHERE repository_id = $1", repoID,
	).Scan(&count)
	return count, err
}

// ─── Hotspot Reads (GraphQL) ────────────────────────────────────────

// GetHotspots returns the top hotspots for a repository, ordered by score.
func (s *Store) GetHotspots(ctx context.Context, repoID, limit int) ([]Hotspot, error) {
	query := `
		SELECT
			id, repository_id, file_path,
			commit_frequency, avg_cyclomatic_complexity, max_cyclomatic_complexity,
			hotspot_score, last_analyzed_at, metadata
		FROM hotspots
		WHERE repository_id = $1
		ORDER BY hotspot_score DESC
		LIMIT $2
	`

	rows, err := s.pool.Query(ctx, query, repoID, limit)
	if err != nil {
		return nil, fmt.Errorf("query hotspots: %w", err)
	}
	defer rows.Close()

	var results []Hotspot
	for rows.Next() {
		var h Hotspot
		if err := rows.Scan(
			&h.ID, &h.RepositoryID, &h.FilePath,
			&h.CommitFrequency, &h.AvgCyclomaticComplexity, &h.MaxCyclomaticComplexity,
			&h.HotspotScore, &h.LastAnalyzedAt, &h.Metadata,
		); err != nil {
			return nil, fmt.Errorf("scan hotspot row: %w", err)
		}
		results = append(results, h)
	}
	return results, rows.Err()
}

// ─── Weekly Trend Reads (GraphQL) ───────────────────────────────────

// GetWeeklyTrend returns aggregated weekly snapshots from the continuous aggregate.
func (s *Store) GetWeeklyTrend(ctx context.Context, repoID, weeks int) ([]WeeklySnapshot, error) {
	query := `
		SELECT
			week, repository_id,
			avg_health, total_debt_hours, peak_issues, avg_issues, run_count,
			latest_reliability, latest_security, latest_maintainability, latest_coverage
		FROM weekly_code_health
		WHERE repository_id = $1
		ORDER BY week DESC
		LIMIT $2
	`

	rows, err := s.pool.Query(ctx, query, repoID, weeks)
	if err != nil {
		// If the continuous aggregate doesn't exist yet, return empty
		if strings.Contains(err.Error(), "does not exist") {
			return nil, nil
		}
		return nil, fmt.Errorf("query weekly trend: %w", err)
	}
	defer rows.Close()

	var results []WeeklySnapshot
	for rows.Next() {
		var ws WeeklySnapshot
		if err := rows.Scan(
			&ws.Week, &ws.RepositoryID,
			&ws.AvgHealth, &ws.TotalDebtHours, &ws.PeakIssues, &ws.AvgIssues, &ws.RunCount,
			&ws.LatestReliability, &ws.LatestSecurity, &ws.LatestMaintainability, &ws.LatestCoverage,
		); err != nil {
			return nil, fmt.Errorf("scan weekly row: %w", err)
		}
		results = append(results, ws)
	}
	return results, rows.Err()
}

// ─── Utility: Check table existence ─────────────────────────────────

// TableExists checks if a table exists in the public schema.
func (s *Store) TableExists(ctx context.Context, tableName string) (bool, error) {
	var exists bool
	err := s.pool.QueryRow(ctx, `
		SELECT EXISTS (
			SELECT FROM information_schema.tables
			WHERE table_schema = 'public'
			  AND table_name = $1
		)
	`, tableName).Scan(&exists)
	return exists, err
}

// Ping checks database connectivity.
func (s *Store) Ping(ctx context.Context) error {
	return s.pool.Ping(ctx)
}

// BatchInsertSnapshots writes multiple snapshots in a single transaction
// for efficiency during bulk aggregation.
func (s *Store) BatchInsertSnapshots(ctx context.Context, snapshots []MetricsSnapshot) error {
	if len(snapshots) == 0 {
		return nil
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer tx.Rollback(ctx)

	batch := &pgx.Batch{}
	for _, snap := range snapshots {
		batch.Queue(`
			INSERT INTO metrics_history (
				recorded_at, repository_id, analysis_run_id,
				code_health_score, technical_debt_hours,
				total_issues, critical_count, high_count, medium_count, low_count,
				lines_of_code, avg_complexity, max_complexity,
				maintainability_index, duplication_pct,
				reliability_grade, security_grade, maintainability_grade, coverage_grade,
				metadata
			) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
			ON CONFLICT (analysis_run_id, recorded_at) DO NOTHING`,
			snap.RecordedAt, snap.RepositoryID, snap.AnalysisRunID,
			snap.CodeHealthScore, snap.TechnicalDebtHours,
			snap.TotalIssues, snap.CriticalCount, snap.HighCount, snap.MediumCount, snap.LowCount,
			snap.LinesOfCode, snap.AvgComplexity, snap.MaxComplexity,
			snap.MaintainabilityIndex, snap.DuplicationPct,
			snap.ReliabilityGrade, snap.SecurityGrade, snap.MaintainabilityGrade, snap.CoverageGrade,
			snap.Metadata,
		)
	}

	br := tx.SendBatch(ctx, batch)
	defer br.Close()

	for i := 0; i < len(snapshots); i++ {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("batch insert snapshot %d: %w", i, err)
		}
	}

	return tx.Commit(ctx)
}
