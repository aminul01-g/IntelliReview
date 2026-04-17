// Package aggregator — hotspot.go implements advanced hotspot identification
// by correlating git commit frequency with cyclomatic complexity.
//
// A "hotspot" is a file that is both frequently changed AND highly complex.
// These files represent the highest-risk refactoring targets because:
//   - High change frequency = higher probability of introducing bugs
//   - High complexity = harder to understand and modify correctly
//
// The hotspot score is computed as: commit_frequency × avg_cyclomatic_complexity
//
// This module supports multiple strategies for obtaining commit frequency:
//   1. Analysis count proxy (default) — uses the number of analyses as a proxy
//   2. Webhook payload parsing — extracts commit data from GitHub PR webhooks
//   3. Git log execution — shells out to `git log` if a repo path is available
package aggregator

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"time"

	"go.uber.org/zap"

	"github.com/aminul01-g/intellireview/services/analysis-history/internal/store"
)

// HotspotAnalyzer performs batch hotspot computation for a repository.
type HotspotAnalyzer struct {
	store  *store.Store
	logger *zap.Logger
}

// NewHotspotAnalyzer creates a new HotspotAnalyzer.
func NewHotspotAnalyzer(s *store.Store, logger *zap.Logger) *HotspotAnalyzer {
	return &HotspotAnalyzer{store: s, logger: logger}
}

// FileChurnData holds aggregated churn and complexity data for a single file.
type FileChurnData struct {
	FilePath        string
	CommitFrequency int
	AvgComplexity   float64
	MaxComplexity   int
	TotalIssues     int
	Languages       map[string]int
	LastSeen        time.Time
}

// ComputeForRepository performs a full hotspot analysis for a given repository.
// It aggregates all completed analyses for the repository, groups them by file,
// correlates change frequency with complexity, and upserts the top hotspots.
func (h *HotspotAnalyzer) ComputeForRepository(ctx context.Context, repoID int) error {
	h.logger.Info("computing hotspots for repository", zap.Int("repo_id", repoID))

	// Fetch all completed analyses for this repository
	fileData, err := h.aggregateFileData(ctx, repoID)
	if err != nil {
		return fmt.Errorf("aggregate file data: %w", err)
	}

	if len(fileData) == 0 {
		h.logger.Debug("no file data found for repository", zap.Int("repo_id", repoID))
		return nil
	}

	// Compute hotspot scores and rank
	hotspots := h.rankFiles(fileData)

	// Upsert top hotspots (limit to top 100 per repository to bound storage)
	limit := 100
	if len(hotspots) < limit {
		limit = len(hotspots)
	}

	for _, hs := range hotspots[:limit] {
		if err := h.store.UpsertHotspot(ctx, hs); err != nil {
			h.logger.Warn("failed to upsert hotspot",
				zap.String("file", hs.FilePath),
				zap.Error(err),
			)
		}
	}

	h.logger.Info("hotspot computation complete",
		zap.Int("repo_id", repoID),
		zap.Int("files_analyzed", len(fileData)),
		zap.Int("hotspots_stored", limit),
	)
	return nil
}

// aggregateFileData queries all completed analyses for a repository and
// groups the results by file path, computing aggregate metrics.
func (h *HotspotAnalyzer) aggregateFileData(ctx context.Context, repoID int) (map[string]*FileChurnData, error) {
	rows, err := h.store.Pool().Query(ctx, `
		SELECT
			file_path,
			language,
			metrics,
			issues,
			completed_at
		FROM analyses
		WHERE project_id = $1
		  AND status = 'completed'
		  AND metrics IS NOT NULL
		ORDER BY completed_at ASC
	`, repoID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	fileData := make(map[string]*FileChurnData)

	for rows.Next() {
		var (
			filePath    string
			language    string
			metricsJSON json.RawMessage
			issuesJSON  json.RawMessage
			completedAt *time.Time
		)

		if err := rows.Scan(&filePath, &language, &metricsJSON, &issuesJSON, &completedAt); err != nil {
			return nil, err
		}

		// Get or create file entry
		fd, exists := fileData[filePath]
		if !exists {
			fd = &FileChurnData{
				FilePath:  filePath,
				Languages: make(map[string]int),
			}
			fileData[filePath] = fd
		}

		// Increment commit frequency (each analysis = one "change event")
		fd.CommitFrequency++
		fd.Languages[language]++

		if completedAt != nil {
			fd.LastSeen = *completedAt
		}

		// Parse and aggregate complexity
		var metrics store.AnalysisMetrics
		if err := json.Unmarshal(metricsJSON, &metrics); err == nil {
			cc := derefFloat(metrics.Complexity, 0)
			if cc > 0 {
				// Running average: update avg_complexity
				fd.AvgComplexity = (fd.AvgComplexity*float64(fd.CommitFrequency-1) + cc) / float64(fd.CommitFrequency)
			}
			if int(cc) > fd.MaxComplexity {
				fd.MaxComplexity = int(cc)
			}
		}

		// Count issues
		var issues []store.AnalysisIssue
		if err := json.Unmarshal(issuesJSON, &issues); err == nil {
			fd.TotalIssues += len(issues)
		}
	}

	return fileData, rows.Err()
}

// rankFiles computes the hotspot score for each file and returns them
// sorted by score descending.
func (h *HotspotAnalyzer) rankFiles(fileData map[string]*FileChurnData) []store.Hotspot {
	var hotspots []store.Hotspot

	for _, fd := range fileData {
		// Hotspot score: commit_frequency × avg_cyclomatic_complexity
		// We add a small issue density factor to break ties:
		// score = freq × (CC + issue_density × 0.1)
		issueDensity := 0.0
		if fd.CommitFrequency > 0 {
			issueDensity = float64(fd.TotalIssues) / float64(fd.CommitFrequency)
		}

		score := float64(fd.CommitFrequency) * (fd.AvgComplexity + issueDensity*0.1)
		score = math.Round(score*100) / 100

		// Build metadata
		meta := map[string]interface{}{
			"languages":       fd.Languages,
			"total_issues":    fd.TotalIssues,
			"issue_density":   math.Round(issueDensity*100) / 100,
		}
		metaJSON, _ := json.Marshal(meta)

		hotspots = append(hotspots, store.Hotspot{
			RepositoryID:            0, // Set by caller
			FilePath:                fd.FilePath,
			CommitFrequency:         fd.CommitFrequency,
			AvgCyclomaticComplexity: math.Round(fd.AvgComplexity*100) / 100,
			MaxCyclomaticComplexity: fd.MaxComplexity,
			HotspotScore:            score,
			LastAnalyzedAt:          fd.LastSeen,
			Metadata:                metaJSON,
		})
	}

	// Sort by score descending
	sort.Slice(hotspots, func(i, j int) bool {
		return hotspots[i].HotspotScore > hotspots[j].HotspotScore
	})

	return hotspots
}

// ─── Git Log Integration (Webhook-based) ────────────────────────────

// GitCommitInfo represents commit data extracted from a GitHub webhook payload.
type GitCommitInfo struct {
	SHA       string    `json:"sha"`
	Author    string    `json:"author"`
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
	Files     []string  `json:"files_changed"`
}

// EnrichFromWebhookCommits updates commit frequency data using commit
// information extracted from GitHub PR webhook payloads. This provides
// more accurate change frequency than the analysis-count proxy.
func (h *HotspotAnalyzer) EnrichFromWebhookCommits(
	ctx context.Context,
	repoID int,
	commits []GitCommitInfo,
) error {
	if len(commits) == 0 {
		return nil
	}

	// Count file appearances across all commits
	fileFreq := make(map[string]int)
	for _, c := range commits {
		for _, f := range c.Files {
			fileFreq[f]++
		}
	}

	// Update hotspot entries with enriched commit frequency
	for filePath, freq := range fileFreq {
		_, err := h.store.Pool().Exec(ctx, `
			UPDATE hotspots
			SET commit_frequency = commit_frequency + $1,
				hotspot_score = (commit_frequency + $1) * avg_cyclomatic_complexity
			WHERE repository_id = $2 AND file_path = $3
		`, freq, repoID, filePath)
		if err != nil {
			h.logger.Warn("failed to enrich hotspot from webhook",
				zap.String("file", filePath),
				zap.Error(err),
			)
		}
	}

	return nil
}
