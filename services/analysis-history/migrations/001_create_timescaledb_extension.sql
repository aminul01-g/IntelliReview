-- Migration 001: Enable TimescaleDB Extension
-- This is idempotent and safe to run on existing PostgreSQL databases.
-- TimescaleDB is a drop-in superset of PostgreSQL — all existing tables
-- and queries continue to work unchanged.

CREATE EXTENSION IF NOT EXISTS timescaledb;
