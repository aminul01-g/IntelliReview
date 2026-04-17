// Package graphql — resolvers.go implements the query resolvers for
// the analysis-history GraphQL API.
//
// Each resolver method reads from the TimescaleDB-backed store and
// converts the results to GraphQL model types with cursor-based
// pagination support.
package graphql

import (
	"context"
	"time"

	"go.uber.org/zap"

	"github.com/aminul01-g/intellireview/services/analysis-history/internal/store"
)

// Resolver is the root resolver that holds references to dependencies.
type Resolver struct {
	Store  *store.Store
	Logger *zap.Logger
}

// ─── Query Resolvers ────────────────────────────────────────────────

// AnalysisHistory returns a paginated connection of metrics snapshots
// for a given repository. Implements Relay-style cursor-based pagination
// using the recorded_at timestamp as the cursor.
func (r *Resolver) AnalysisHistory(
	ctx context.Context,
	repositoryID int,
	first int,
	after *string,
	startDate, endDate *time.Time,
) (*AnalysisHistoryConnection, error) {
	log := r.Logger.Sugar()

	// Clamp page size to reasonable bounds
	if first <= 0 {
		first = 20
	}
	if first > 100 {
		first = 100
	}

	// Decode cursor if provided
	var cursorTime *time.Time
	if after != nil && *after != "" {
		t, err := DecodeCursor(*after)
		if err != nil {
			log.Warnw("invalid cursor", "cursor", *after, "error", err)
			// Continue without cursor — start from the beginning
		} else {
			cursorTime = &t
		}
	}

	// Query the store
	snapshots, hasNextPage, err := r.Store.GetHistory(ctx, repositoryID, cursorTime, first, startDate, endDate)
	if err != nil {
		log.Errorw("failed to get history", "repo_id", repositoryID, "error", err)
		return nil, err
	}

	// Get total count for the connection
	totalCount, err := r.Store.GetHistoryCount(ctx, repositoryID)
	if err != nil {
		log.Warnw("failed to get history count", "repo_id", repositoryID, "error", err)
		totalCount = len(snapshots) // Fallback
	}

	// Build edges
	edges := make([]AnalysisHistoryEdge, 0, len(snapshots))
	for _, snap := range snapshots {
		edges = append(edges, AnalysisHistoryEdge{
			Cursor: EncodeCursor(snap.RecordedAt),
			Node:   ToGraphQLSnapshot(snap),
		})
	}

	// Build page info
	var startCursor, endCursor *string
	hasPreviousPage := after != nil && *after != ""

	if len(edges) > 0 {
		sc := edges[0].Cursor
		ec := edges[len(edges)-1].Cursor
		startCursor = &sc
		endCursor = &ec
	}

	return &AnalysisHistoryConnection{
		Edges: edges,
		PageInfo: PageInfo{
			HasNextPage:     hasNextPage,
			HasPreviousPage: hasPreviousPage,
			StartCursor:     startCursor,
			EndCursor:       endCursor,
		},
		TotalCount: totalCount,
	}, nil
}

// Hotspots returns the top N hotspot files for a repository, ranked by
// the composite score of commit_frequency × avg_cyclomatic_complexity.
func (r *Resolver) Hotspots(
	ctx context.Context,
	repositoryID int,
	limit int,
) ([]Hotspot, error) {
	log := r.Logger.Sugar()

	if limit <= 0 {
		limit = 10
	}
	if limit > 50 {
		limit = 50
	}

	storeHotspots, err := r.Store.GetHotspots(ctx, repositoryID, limit)
	if err != nil {
		log.Errorw("failed to get hotspots", "repo_id", repositoryID, "error", err)
		return nil, err
	}

	result := make([]Hotspot, 0, len(storeHotspots))
	for _, h := range storeHotspots {
		result = append(result, ToGraphQLHotspot(h))
	}

	return result, nil
}

// WeeklyTrend returns aggregated weekly snapshots from the TimescaleDB
// continuous aggregate. This provides pre-computed trend data for
// dashboard visualizations.
func (r *Resolver) WeeklyTrend(
	ctx context.Context,
	repositoryID int,
	weeks int,
) ([]WeeklySnapshot, error) {
	log := r.Logger.Sugar()

	if weeks <= 0 {
		weeks = 12
	}
	if weeks > 52 {
		weeks = 52
	}

	storeWeeklies, err := r.Store.GetWeeklyTrend(ctx, repositoryID, weeks)
	if err != nil {
		log.Errorw("failed to get weekly trend", "repo_id", repositoryID, "error", err)
		return nil, err
	}

	result := make([]WeeklySnapshot, 0, len(storeWeeklies))
	for _, ws := range storeWeeklies {
		result = append(result, ToGraphQLWeekly(ws))
	}

	return result, nil
}
