// Package main is the entry point for the analysis-history service.
// It initializes the database connection pool, runs SQL migrations,
// starts the periodic aggregation worker, and launches the GraphQL
// HTTP server on port 4000.
package main

import (
	"context"
	"embed"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/robfig/cron/v3"
	"github.com/rs/cors"
	"go.uber.org/zap"

	"github.com/aminul01-g/intellireview/services/analysis-history/internal/aggregator"
	gql "github.com/aminul01-g/intellireview/services/analysis-history/internal/graphql"
	"github.com/aminul01-g/intellireview/services/analysis-history/internal/store"
)

// Embed the SQL migration files from the project root migrations/ directory.
// The embed path is relative to this source file (cmd/server/main.go),
// so ../../migrations reaches services/analysis-history/migrations/.
//
//go:embed migrations/*.sql
var migrationsFS embed.FS

func main() {
	// ── Logger ──────────────────────────────────────────────────────
	logLevel := os.Getenv("LOG_LEVEL")
	var logger *zap.Logger
	var err error
	if logLevel == "debug" {
		logger, err = zap.NewDevelopment()
	} else {
		logger, err = zap.NewProduction()
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to init logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()
	log := logger.Sugar()

	// ── Database ────────────────────────────────────────────────────
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://intellireview:password@localhost:5432/intellireview_db"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	poolCfg, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		log.Fatalf("parse db config: %v", err)
	}
	poolCfg.MaxConns = 10
	poolCfg.MinConns = 2

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		log.Fatalf("connect to database: %v", err)
	}
	defer pool.Close()

	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("ping database: %v", err)
	}
	log.Info("connected to PostgreSQL / TimescaleDB")

	// ── Migrations ──────────────────────────────────────────────────
	pgStore := store.New(pool, logger)
	if err := pgStore.RunMigrations(context.Background(), migrationsFS, "migrations"); err != nil {
		log.Fatalf("run migrations: %v", err)
	}
	log.Info("database migrations applied")

	// ── Aggregation Engine ──────────────────────────────────────────
	engine := aggregator.NewEngine(pgStore, logger)

	// Run initial aggregation on startup
	go func() {
		log.Info("running initial aggregation pass...")
		if err := engine.Run(context.Background()); err != nil {
			log.Errorf("initial aggregation: %v", err)
		}
	}()

	// Schedule periodic aggregation
	interval := os.Getenv("AGGREGATION_INTERVAL")
	if interval == "" {
		interval = "5m"
	}
	cronSpec := fmt.Sprintf("@every %s", interval)
	scheduler := cron.New()
	scheduler.AddFunc(cronSpec, func() {
		log.Debug("scheduled aggregation triggered")
		if err := engine.Run(context.Background()); err != nil {
			log.Errorf("scheduled aggregation: %v", err)
		}
	})
	scheduler.Start()
	defer scheduler.Stop()
	log.Infof("aggregation scheduled: %s", cronSpec)

	// ── GraphQL Server ──────────────────────────────────────────────
	resolver := &gql.Resolver{
		Store:  pgStore,
		Logger: logger,
	}

	// Use our hand-written executable schema (avoids gqlgen codegen dependency)
	srv := gql.NewExecutableSchema(gql.Config{
		Resolvers: resolver,
	})

	mux := http.NewServeMux()
	mux.Handle("/graphql", srv)

	// Simple playground HTML page
	mux.HandleFunc("/playground", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(playgroundHTML))
	})

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"healthy","service":"analysis-history"}`))
	})

	// Trigger endpoint for on-demand aggregation
	mux.HandleFunc("/trigger", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		go func() {
			if err := engine.Run(context.Background()); err != nil {
				log.Errorf("triggered aggregation: %v", err)
			}
		}()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		w.Write([]byte(`{"status":"aggregation_triggered"}`))
	})

	// CORS
	corsHandler := cors.New(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "OPTIONS"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
	}).Handler(mux)

	port := os.Getenv("PORT")
	if port == "" {
		port = "4000"
	}
	httpServer := &http.Server{
		Addr:         ":" + port,
		Handler:      corsHandler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// ── Graceful Shutdown ───────────────────────────────────────────
	errCh := make(chan error, 1)
	go func() {
		log.Infof("GraphQL server listening on :%s", port)
		log.Infof("Playground: http://localhost:%s/playground", port)
		errCh <- httpServer.ListenAndServe()
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-quit:
		log.Infof("received signal %v, shutting down...", sig)
	case err := <-errCh:
		log.Errorf("server error: %v", err)
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		log.Errorf("graceful shutdown failed: %v", err)
	}
	log.Info("analysis-history service stopped")
}

// playgroundHTML is a minimal GraphQL Playground page.
const playgroundHTML = `<!DOCTYPE html>
<html>
<head>
  <title>IntelliReview AnalysisHistory — GraphQL Playground</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
  <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
</head>
<body>
  <div id="root"></div>
  <script>
    window.addEventListener('load', function() {
      GraphQLPlayground.init(document.getElementById('root'), { endpoint: '/graphql' });
    });
  </script>
</body>
</html>`
