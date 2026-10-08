-- ============================================================
-- Migration 001: Add Advanced Features
-- Intelligent Self-Healing Distributed File Storage Platform
-- ============================================================
-- This migration is ADDITIVE only. No existing data is dropped.

-- ============================================================
-- EXTEND: files table
-- ============================================================
ALTER TABLE files
    ADD COLUMN IF NOT EXISTS version_number       INTEGER     NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS parent_file_id       INTEGER     REFERENCES files(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS is_current_version   BOOLEAN     NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS is_deduplicated      BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS dedup_source_file_id INTEGER     REFERENCES files(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS access_count         INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_accessed_at     TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_files_parent_file_id ON files(parent_file_id);
CREATE INDEX IF NOT EXISTS idx_files_checksum ON files(checksum);

-- ============================================================
-- EXTEND: storage_nodes table
-- ============================================================
ALTER TABLE storage_nodes
    ADD COLUMN IF NOT EXISTS avg_latency_ms   FLOAT       NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS failure_count    INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS request_count    INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_latency_ms  FLOAT       NOT NULL DEFAULT 0;

-- ============================================================
-- FILE VERSIONS  (history ledger per file lineage)
-- ============================================================
CREATE TABLE IF NOT EXISTS file_versions (
    id              SERIAL PRIMARY KEY,
    file_id         INTEGER      NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    version_number  INTEGER      NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by_id   INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(file_id, version_number)
);
CREATE INDEX IF NOT EXISTS idx_file_versions_file_id ON file_versions(file_id);

-- ============================================================
-- SYSTEM EVENTS  (real-time event log for SSE + dashboards)
-- ============================================================
CREATE TABLE IF NOT EXISTS system_events (
    id          SERIAL PRIMARY KEY,
    event_type  VARCHAR(100) NOT NULL,
    severity    VARCHAR(20)  NOT NULL DEFAULT 'INFO',  -- INFO | WARNING | ERROR | CRITICAL
    node_id     VARCHAR(100),
    file_id     INTEGER      REFERENCES files(id) ON DELETE SET NULL,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    payload     TEXT,        -- JSON payload
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_system_events_type      ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_node      ON system_events(node_id);

-- ============================================================
-- NODE METRICS  (time-series snapshots for analytics)
-- ============================================================
CREATE TABLE IF NOT EXISTS node_metrics (
    id                SERIAL PRIMARY KEY,
    node_id           VARCHAR(100) NOT NULL REFERENCES storage_nodes(node_id) ON DELETE CASCADE,
    sampled_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    latency_ms        FLOAT        NOT NULL DEFAULT 0,
    available_storage BIGINT       NOT NULL DEFAULT 0,
    used_storage      BIGINT       NOT NULL DEFAULT 0,
    file_count        INTEGER      NOT NULL DEFAULT 0,
    request_count     INTEGER      NOT NULL DEFAULT 0,
    is_online         BOOLEAN      NOT NULL DEFAULT TRUE,
    placement_score   FLOAT        NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_node_metrics_node_id    ON node_metrics(node_id);
CREATE INDEX IF NOT EXISTS idx_node_metrics_sampled_at ON node_metrics(sampled_at DESC);

-- ============================================================
-- REPLICATION EVENTS  (self-healing recovery log)
-- ============================================================
CREATE TABLE IF NOT EXISTS replication_events (
    id            SERIAL PRIMARY KEY,
    file_id       INTEGER      REFERENCES files(id) ON DELETE SET NULL,
    source_node   VARCHAR(100),
    target_node   VARCHAR(100),
    trigger       VARCHAR(100) NOT NULL DEFAULT 'AUTO_HEAL',  -- AUTO_HEAL | MANUAL | INITIAL
    status        VARCHAR(50)  NOT NULL DEFAULT 'PENDING',    -- PENDING | IN_PROGRESS | COMPLETE | FAILED
    started_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ,
    duration_ms   INTEGER,
    error_detail  TEXT
);
CREATE INDEX IF NOT EXISTS idx_replication_events_file_id   ON replication_events(file_id);
CREATE INDEX IF NOT EXISTS idx_replication_events_status    ON replication_events(status);
CREATE INDEX IF NOT EXISTS idx_replication_events_started   ON replication_events(started_at DESC);

-- ============================================================
-- SIMULATION STATE  (admin chaos simulation flags)
-- ============================================================
CREATE TABLE IF NOT EXISTS simulation_state (
    id                  SERIAL PRIMARY KEY,
    node_id             VARCHAR(100) UNIQUE NOT NULL,
    is_simulated        BOOLEAN      NOT NULL DEFAULT FALSE,
    simulated_status    VARCHAR(50),   -- OFFLINE | DEGRADED | HIGH_LOAD
    simulated_latency_ms INTEGER      NOT NULL DEFAULT 0,
    simulated_load_pct  INTEGER      NOT NULL DEFAULT 0,
    simulated_storage_warning BOOLEAN NOT NULL DEFAULT FALSE,
    activated_at        TIMESTAMPTZ,
    activated_by_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- SECURITY EVENTS  (behavioral anomaly log)
-- ============================================================
CREATE TABLE IF NOT EXISTS security_events (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    event_type  VARCHAR(100) NOT NULL,
    risk_level  VARCHAR(20)  NOT NULL DEFAULT 'LOW',  -- LOW | MEDIUM | HIGH
    details     TEXT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_security_events_user_id   ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_risk      ON security_events(risk_level);
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp DESC);

-- ============================================================
-- SEED: Simulation state rows (one per node)
-- ============================================================
INSERT INTO simulation_state (node_id, is_simulated)
VALUES ('node1', FALSE), ('node2', FALSE), ('node3', FALSE)
ON CONFLICT (node_id) DO NOTHING;
