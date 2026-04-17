// Package aggregator implements the core business logic for computing
// longitudinal code quality metrics from raw IntelliReview analysis data.
//
// It reads completed analyses from the `analyses` table, computes:
//   - Code Health Score (1.0–10.0)
//   - Technical Debt in hours (SonarQube 8-hour day convention)
//   - Dimension Grades (A/B/C/D) for Reliability, Security, Maintainability, Coverage
//
// and writes the results to the `metrics_history` TimescaleDB hypertable.
package aggregator

import (
	"context"
	"encoding/json"
	"math"
	"strings"
	"time"

	"go.uber.org/zap"

	"github.com/aminul01-g/intellireview/services/analysis-history/internal/store"
)

// Engine orchestrates the aggregation pipeline.
type Engine struct {
	store  *store.Store
	logger *zap.Logger
}

// NewEngine creates a new aggregation engine.
func NewEngine(s *store.Store, logger *zap.Logger) *Engine {
	return &Engine{store: s, logger: logger}
}

// Run executes a single aggregation pass:
// 1. Fetch unprocessed analyses
// 2. For each analysis, parse issues/metrics JSON
// 3. Compute Code Health, Technical Debt, and Dimension Grades
// 4. Write MetricsSnapshot to the hypertable
// 5. Compute and upsert Hotspot entries
func (e *Engine) Run(ctx context.Context) error {
	analyses, err := e.store.GetUnprocessedAnalyses(ctx)
	if err != nil {
		return err
	}

	if len(analyses) == 0 {
		e.logger.Debug("no unprocessed analyses found")
		return nil
	}

	e.logger.Info("aggregating analyses", zap.Int("count", len(analyses)))

	var snapshots []store.MetricsSnapshot

	for _, raw := range analyses {
		snap, err := e.aggregate(raw)
		if err != nil {
			e.logger.Warn("skipping analysis",
				zap.Int("id", raw.ID),
				zap.Error(err),
			)
			continue
		}
		snapshots = append(snapshots, snap)

		// Compute hotspot for this file
		if err := e.computeHotspot(ctx, raw, snap); err != nil {
			e.logger.Warn("hotspot computation failed",
				zap.Int("analysis_id", raw.ID),
				zap.String("file", raw.FilePath),
				zap.Error(err),
			)
		}
	}

	// Batch insert all snapshots
	if err := e.store.BatchInsertSnapshots(ctx, snapshots); err != nil {
		return err
	}

	e.logger.Info("aggregation complete",
		zap.Int("processed", len(snapshots)),
		zap.Int("skipped", len(analyses)-len(snapshots)),
	)
	return nil
}

// aggregate computes a MetricsSnapshot from a single raw analysis.
func (e *Engine) aggregate(raw store.RawAnalysis) (store.MetricsSnapshot, error) {
	// Parse issues from JSON
	issues, err := parseIssues(raw.Issues)
	if err != nil {
		return store.MetricsSnapshot{}, err
	}

	// Parse metrics from JSON
	metrics, err := parseMetrics(raw.Metrics)
	if err != nil {
		return store.MetricsSnapshot{}, err
	}

	// Count issues by severity
	counts := countBySeverity(issues)

	// Compute composite scores
	healthScore := computeCodeHealth(counts, metrics)
	debtHours := computeTechnicalDebt(counts)
	grades := computeDimensionGrades(issues, metrics, counts)

	// Determine the recorded_at timestamp
	recordedAt := raw.CreatedAt
	if raw.CompletedAt != nil {
		recordedAt = *raw.CompletedAt
	}

	// Repository ID (project_id in the analyses table)
	repoID := 0
	if raw.ProjectID != nil {
		repoID = *raw.ProjectID
	}

	// Build metadata
	metadata := map[string]interface{}{
		"language":        raw.Language,
		"file_path":       raw.FilePath,
		"processing_time": raw.ProcessingTime,
		"debt_days":       debtHours / 8.0, // SonarQube 8-hour day convention
	}
	metadataJSON, _ := json.Marshal(metadata)

	return store.MetricsSnapshot{
		RecordedAt:           recordedAt,
		RepositoryID:         repoID,
		AnalysisRunID:        raw.ID,
		CodeHealthScore:      healthScore,
		TechnicalDebtHours:   debtHours,
		TotalIssues:          counts.Total,
		CriticalCount:        counts.Critical,
		HighCount:            counts.High,
		MediumCount:          counts.Medium,
		LowCount:             counts.Low,
		LinesOfCode:          metrics.LinesOfCode,
		AvgComplexity:        derefFloat(metrics.Complexity, 0),
		MaxComplexity:        int(derefFloat(metrics.Complexity, 0) * 1.5), // Estimate max from avg
		MaintainabilityIndex: derefFloat(metrics.MaintainabilityIndex, 50),
		DuplicationPct:       derefFloat(metrics.DuplicationPct, 0),
		ReliabilityGrade:     grades.Reliability,
		SecurityGrade:        grades.Security,
		MaintainabilityGrade: grades.Maintainability,
		CoverageGrade:        grades.Coverage,
		Metadata:             metadataJSON,
	}, nil
}

// ─── Severity Counting ──────────────────────────────────────────────

// SeverityCounts holds issue counts by severity level.
type SeverityCounts struct {
	Critical int
	High     int
	Medium   int
	Low      int
	Total    int
}

func countBySeverity(issues []store.AnalysisIssue) SeverityCounts {
	var c SeverityCounts
	for _, issue := range issues {
		switch strings.ToLower(issue.Severity) {
		case "critical":
			c.Critical++
		case "high":
			c.High++
		case "medium":
			c.Medium++
		case "low":
			c.Low++
		}
		c.Total++
	}
	return c
}

// ─── Code Health Score (1.0 – 10.0) ─────────────────────────────────
//
// Scoring model:
//   health = 10.0
//   health -= critical_count × 2.0     (each critical penalizes 2 points)
//   health -= high_count × 1.0         (each high penalizes 1 point)
//   health -= medium_count × 0.3
//   health -= low_count × 0.1
//   health -= (duplication_pct / 20.0)  (every 20% duplication = -1 point)
//   health -= max(0, (avg_complexity - 10) × 0.5)  (penalize complexity above 10)
//   Clamped to [1.0, 10.0]

func computeCodeHealth(counts SeverityCounts, metrics store.AnalysisMetrics) float64 {
	health := 10.0

	// Severity-based penalties
	health -= float64(counts.Critical) * 2.0
	health -= float64(counts.High) * 1.0
	health -= float64(counts.Medium) * 0.3
	health -= float64(counts.Low) * 0.1

	// Duplication penalty: every 20% duplication costs 1 point
	dupPct := derefFloat(metrics.DuplicationPct, 0)
	health -= dupPct / 20.0

	// Complexity penalty: penalize average complexity above 10
	avgCC := derefFloat(metrics.Complexity, 0)
	if avgCC > 10 {
		health -= (avgCC - 10) * 0.5
	}

	// Maintainability bonus/penalty: MI below 40 = penalty, above 80 = small bonus
	mi := derefFloat(metrics.MaintainabilityIndex, 50)
	if mi < 40 {
		health -= (40 - mi) / 40.0 // Max -1.0 penalty
	} else if mi > 80 {
		health += 0.5 // Small bonus for highly maintainable code
	}

	// Clamp to [1.0, 10.0]
	return math.Max(1.0, math.Min(10.0, health))
}

// ─── Technical Debt (hours) ─────────────────────────────────────────
//
// Based on SonarQube's remediation model with 8-hour day convention:
//   critical:  90 minutes per issue  (substantial remediation)
//   high:      60 minutes per issue
//   medium:    30 minutes per issue
//   low:       10 minutes per issue
//
// Result is in hours. To get days, divide by 8 (available in metadata).

func computeTechnicalDebt(counts SeverityCounts) float64 {
	debtMinutes := 0.0
	debtMinutes += float64(counts.Critical) * 90.0
	debtMinutes += float64(counts.High) * 60.0
	debtMinutes += float64(counts.Medium) * 30.0
	debtMinutes += float64(counts.Low) * 10.0

	return math.Round(debtMinutes/60.0*100) / 100 // Round to 2 decimal places
}

// ─── Dimension Grades (A / B / C / D) ───────────────────────────────
//
// Grading criteria:
//
// Reliability:
//   A: 0 critical/high bugs
//   B: 1 high bug
//   C: 2–5 bugs (critical + high)
//   D: >5 bugs
//
// Security:
//   A: 0 security vulnerabilities
//   B: 1 vulnerability
//   C: 2–5 vulnerabilities
//   D: >5 vulnerabilities
//
// Maintainability:
//   A: MI ≥ 80 AND avg_complexity ≤ 5
//   B: MI ≥ 60 AND avg_complexity ≤ 10
//   C: MI ≥ 40 AND avg_complexity ≤ 20
//   D: MI < 40 OR avg_complexity > 20
//
// Coverage:
//   Defaults to 'D' until test coverage integration is available.

// DimensionGrades holds the A/B/C/D grades for each quality dimension.
type DimensionGrades struct {
	Reliability     string
	Security        string
	Maintainability string
	Coverage        string
}

func computeDimensionGrades(issues []store.AnalysisIssue, metrics store.AnalysisMetrics, counts SeverityCounts) DimensionGrades {
	return DimensionGrades{
		Reliability:     gradeReliability(counts),
		Security:        gradeSecurity(issues),
		Maintainability: gradeMaintainability(metrics),
		Coverage:        "D", // Default until test coverage integration
	}
}

func gradeReliability(counts SeverityCounts) string {
	bugCount := counts.Critical + counts.High
	switch {
	case bugCount == 0:
		return "A"
	case bugCount == 1:
		return "B"
	case bugCount <= 5:
		return "C"
	default:
		return "D"
	}
}

func gradeSecurity(issues []store.AnalysisIssue) string {
	vulnCount := 0
	securityTypes := map[string]bool{
		"security_vulnerability": true,
		"sql_injection":          true,
		"xss":                    true,
		"path_traversal":         true,
		"command_injection":      true,
		"insecure_crypto":        true,
		"hardcoded_secret":       true,
		"ssrf":                   true,
		"xxe":                    true,
	}

	for _, issue := range issues {
		issueType := strings.ToLower(issue.Type)
		if securityTypes[issueType] || strings.Contains(issueType, "security") || issue.CWE != "" {
			vulnCount++
		}
	}

	switch {
	case vulnCount == 0:
		return "A"
	case vulnCount == 1:
		return "B"
	case vulnCount <= 5:
		return "C"
	default:
		return "D"
	}
}

func gradeMaintainability(metrics store.AnalysisMetrics) string {
	mi := derefFloat(metrics.MaintainabilityIndex, 50)
	cc := derefFloat(metrics.Complexity, 0)

	switch {
	case mi >= 80 && cc <= 5:
		return "A"
	case mi >= 60 && cc <= 10:
		return "B"
	case mi >= 40 && cc <= 20:
		return "C"
	default:
		return "D"
	}
}

// ─── JSON Parsing Helpers ───────────────────────────────────────────

func parseIssues(raw json.RawMessage) ([]store.AnalysisIssue, error) {
	if raw == nil || string(raw) == "null" {
		return nil, nil
	}
	var issues []store.AnalysisIssue
	if err := json.Unmarshal(raw, &issues); err != nil {
		return nil, err
	}
	return issues, nil
}

func parseMetrics(raw json.RawMessage) (store.AnalysisMetrics, error) {
	var m store.AnalysisMetrics
	if raw == nil || string(raw) == "null" {
		return m, nil
	}
	if err := json.Unmarshal(raw, &m); err != nil {
		return m, err
	}
	return m, nil
}

func derefFloat(ptr *float64, fallback float64) float64 {
	if ptr != nil {
		return *ptr
	}
	return fallback
}

// ─── Hotspot Computation ────────────────────────────────────────────

// computeHotspot calculates and upserts a hotspot entry for the file
// analyzed in a given raw analysis. Commit frequency is estimated from
// the number of completed analyses for the same file in the same project.
func (e *Engine) computeHotspot(ctx context.Context, raw store.RawAnalysis, snap store.MetricsSnapshot) error {
	if raw.ProjectID == nil {
		return nil // No repository association, skip hotspot
	}

	// Estimate commit frequency from analysis history for this file.
	// In a full implementation, this would parse git log data from webhook
	// payloads or a cloned repo. Here we use the count of analyses for
	// this file as a proxy for change frequency.
	commitFreq, err := e.estimateCommitFrequency(ctx, *raw.ProjectID, raw.FilePath)
	if err != nil {
		commitFreq = 1 // Fallback to 1 if estimation fails
	}

	avgCC := snap.AvgComplexity
	maxCC := snap.MaxComplexity
	hotspotScore := float64(commitFreq) * avgCC

	return e.store.UpsertHotspot(ctx, store.Hotspot{
		RepositoryID:            *raw.ProjectID,
		FilePath:                raw.FilePath,
		CommitFrequency:         commitFreq,
		AvgCyclomaticComplexity: avgCC,
		MaxCyclomaticComplexity: maxCC,
		HotspotScore:            hotspotScore,
		LastAnalyzedAt:          time.Now(),
		Metadata:                buildHotspotMetadata(raw, snap),
	})
}

// estimateCommitFrequency counts the number of completed analyses for a
// given file within a project as a proxy for git commit frequency.
// This correlates well with actual commit frequency since each analysis
// run typically corresponds to a code change event.
func (e *Engine) estimateCommitFrequency(ctx context.Context, projectID int, filePath string) (int, error) {
	var count int
	err := e.store.Pool().QueryRow(ctx, `
		SELECT COUNT(*) FROM analyses
		WHERE project_id = $1
		  AND file_path = $2
		  AND status = 'completed'
	`, projectID, filePath).Scan(&count)
	if err != nil {
		return 0, err
	}
	return count, nil
}

func buildHotspotMetadata(raw store.RawAnalysis, snap store.MetricsSnapshot) json.RawMessage {
	meta := map[string]interface{}{
		"language":            raw.Language,
		"last_health_score":   snap.CodeHealthScore,
		"last_debt_hours":     snap.TechnicalDebtHours,
		"reliability_grade":   snap.ReliabilityGrade,
		"total_issues":        snap.TotalIssues,
	}
	data, _ := json.Marshal(meta)
	return data
}
