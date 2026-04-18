# ─── Build Stage ─────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build

# Cache dependency downloads
COPY go.mod go.sum* ./
RUN go mod download 2>/dev/null || true




# Explicitly copy migrations directory into cmd/server/migrations before build step
RUN mkdir -p cmd/server/migrations
COPY migrations/*.sql cmd/server/migrations/

# Copy source code
COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-w -s" -o /analysis-history ./cmd/server

# ─── Runtime Stage ───────────────────────────────────────────────────
FROM alpine:3.19

RUN apk add --no-cache ca-certificates tzdata

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app

# Copy binary and migrations
COPY --from=builder /analysis-history .
COPY --from=builder /build/migrations ./migrations

# Own the workdir
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 4000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:4000/health || exit 1

ENTRYPOINT ["./analysis-history"]
