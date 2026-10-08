-- ============================================================
-- Distributed File Sharing System – Database Schema v2
-- Intelligent Self-Healing Distributed Storage Platform
-- ============================================================

-- Drop tables in correct dependency order
DROP TABLE IF EXISTS security_events      CASCADE;
DROP TABLE IF EXISTS simulation_state     CASCADE;
DROP TABLE IF EXISTS replication_events   CASCADE;
DROP TABLE IF EXISTS node_metrics         CASCADE;
DROP TABLE IF EXISTS system_events        CASCADE;
DROP TABLE IF EXISTS file_versions        CASCADE;
DROP TABLE IF EXISTS audit_logs           CASCADE;
DROP TABLE IF EXISTS file_permissions     CASCADE;
DROP TABLE IF EXISTS file_locations       CASCADE;
DROP TABLE IF EXISTS files                CASCADE;
DROP TABLE IF EXISTS storage_nodes        CASCADE;
DROP TABLE IF EXISTS users                CASCADE;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(255)        NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255)        NOT NULL,
    role          VARCHAR(50)         NOT NULL DEFAULT 'USER',  -- USER | ADMIN
    is_active     BOOLEAN             NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- STORAGE NODES
-- ============================================================
CREATE TABLE storage_nodes (
    id                SERIAL PRIMARY KEY,
    node_id           VARCHAR(100) UNIQUE NOT NULL,
    name              VARCHAR(255)        NOT NULL,
    host              VARCHAR(255)        NOT NULL,
    port              INTEGER             NOT NULL,
    status            VARCHAR(50)         NOT NULL DEFAULT 'UNKNOWN',
    total_storage     BIGINT              NOT NULL DEFAULT 0,
    available_storage BIGINT              NOT NULL DEFAULT 0,
    file_count        INTEGER             NOT NULL DEFAULT 0,
    last_heartbeat    TIMESTAMPTZ,
    created_at        TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    -- Advanced feature columns
    avg_latency_ms    FLOAT               NOT NULL DEFAULT 0,
    failure_count     INTEGER             NOT NULL DEFAULT 0,
    request_count     INTEGER             NOT NULL DEFAULT 0,
    last_latency_ms   FLOAT               NOT NULL DEFAULT 0
);

CREATE INDEX idx_storage_nodes_node_id ON storage_nodes(node_id);
CREATE INDEX idx_storage_nodes_status  ON storage_nodes(status);

-- ============================================================
-- FILES
-- ============================================================
CREATE TABLE files (
    id                    SERIAL PRIMARY KEY,
    filename              VARCHAR(500)  NOT NULL,
    original_filename     VARCHAR(500)  NOT NULL,
    size                  BIGINT        NOT NULL DEFAULT 0,
    mime_type             VARCHAR(255),
    owner_id              INTEGER       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checksum              VARCHAR(64)   NOT NULL,
    primary_node_id       VARCHAR(100)  REFERENCES storage_nodes(node_id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- Versioning
    version_number        INTEGER       NOT NULL DEFAULT 1,
    parent_file_id        INTEGER       REFERENCES files(id) ON DELETE SET NULL,
    is_current_version    BOOLEAN       NOT NULL DEFAULT TRUE,
    -- Deduplication
    is_deduplicated       BOOLEAN       NOT NULL DEFAULT FALSE,
    dedup_source_file_id  INTEGER       REFERENCES files(id) ON DELETE SET NULL,
    -- Access tracking
    access_count          INTEGER       NOT NULL DEFAULT 0,
    last_accessed_at      TIMESTAMPTZ
);

CREATE INDEX idx_files_owner_id       ON files(owner_id);
CREATE INDEX idx_files_primary_node   ON files(primary_node_id);
CREATE INDEX idx_files_original_name  ON files(original_filename);
CREATE INDEX idx_files_created_at     ON files(created_at DESC);
CREATE INDEX idx_files_parent_file_id ON files(parent_file_id);
CREATE INDEX idx_files_checksum       ON files(checksum);

-- ============================================================
-- FILE LOCATIONS (tracks which node holds which copy)
-- ============================================================
CREATE TABLE file_locations (
    id            SERIAL PRIMARY KEY,
    file_id       INTEGER      NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    node_id       VARCHAR(100) NOT NULL REFERENCES storage_nodes(node_id) ON DELETE CASCADE,
    location_type VARCHAR(50)  NOT NULL,  -- PRIMARY | REPLICA
    status        VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE | FAILED | PENDING_CLEANUP
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_file_locations_file_id ON file_locations(file_id);
CREATE INDEX idx_file_locations_node_id ON file_locations(node_id);
CREATE UNIQUE INDEX idx_file_locations_unique ON file_locations(file_id, node_id);

-- ============================================================
-- FILE PERMISSIONS
-- ============================================================
CREATE TABLE file_permissions (
    id         SERIAL PRIMARY KEY,
    file_id    INTEGER      NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    user_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(50)  NOT NULL DEFAULT 'VIEW',  -- OWNER | VIEW | DOWNLOAD | MANAGE
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(file_id, user_id)
);

CREATE INDEX idx_file_permissions_file_id ON file_permissions(file_id);
CREATE INDEX idx_file_permissions_user_id ON file_permissions(user_id);

-- ============================================================
-- AUDIT LOGS
-- ============================================================
CREATE TABLE audit_logs (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    action    VARCHAR(100) NOT NULL,
    file_id   INTEGER      REFERENCES files(id) ON DELETE SET NULL,
    node_id   VARCHAR(100),
    details   TEXT,
    timestamp TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id   ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_file_id   ON audit_logs(file_id);
CREATE INDEX idx_audit_logs_action    ON audit_logs(action);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- ============================================================
-- FILE VERSIONS (history ledger per file lineage)
-- ============================================================
CREATE TABLE file_versions (
    id              SERIAL PRIMARY KEY,
    file_id         INTEGER      NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    version_number  INTEGER      NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by_id   INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(file_id, version_number)
);

CREATE INDEX idx_file_versions_file_id ON file_versions(file_id);

-- ============================================================
-- SYSTEM EVENTS (real-time event log for SSE + dashboards)
-- ============================================================
CREATE TABLE system_events (
    id          SERIAL PRIMARY KEY,
    event_type  VARCHAR(100) NOT NULL,
    severity    VARCHAR(20)  NOT NULL DEFAULT 'INFO',  -- INFO | WARNING | ERROR | CRITICAL
    node_id     VARCHAR(100),
    file_id     INTEGER      REFERENCES files(id) ON DELETE SET NULL,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    payload     TEXT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_system_events_type      ON system_events(event_type);
CREATE INDEX idx_system_events_timestamp ON system_events(timestamp DESC);
CREATE INDEX idx_system_events_node      ON system_events(node_id);

-- ============================================================
-- NODE METRICS (time-series snapshots for analytics)
-- ============================================================
CREATE TABLE node_metrics (
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

CREATE INDEX idx_node_metrics_node_id    ON node_metrics(node_id);
CREATE INDEX idx_node_metrics_sampled_at ON node_metrics(sampled_at DESC);

-- ============================================================
-- REPLICATION EVENTS (self-healing recovery log)
-- ============================================================
CREATE TABLE replication_events (
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

CREATE INDEX idx_replication_events_file_id   ON replication_events(file_id);
CREATE INDEX idx_replication_events_status    ON replication_events(status);
CREATE INDEX idx_replication_events_started   ON replication_events(started_at DESC);

-- ============================================================
-- SIMULATION STATE (admin chaos simulation flags)
-- ============================================================
CREATE TABLE simulation_state (
    id                        SERIAL PRIMARY KEY,
    node_id                   VARCHAR(100) UNIQUE NOT NULL,
    is_simulated              BOOLEAN      NOT NULL DEFAULT FALSE,
    simulated_status          VARCHAR(50),   -- OFFLINE | DEGRADED | HIGH_LOAD
    simulated_latency_ms      INTEGER      NOT NULL DEFAULT 0,
    simulated_load_pct        INTEGER      NOT NULL DEFAULT 0,
    simulated_storage_warning BOOLEAN      NOT NULL DEFAULT FALSE,
    activated_at              TIMESTAMPTZ,
    activated_by_id           INTEGER      REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- SECURITY EVENTS (behavioral anomaly log)
-- ============================================================
CREATE TABLE security_events (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    event_type  VARCHAR(100) NOT NULL,
    risk_level  VARCHAR(20)  NOT NULL DEFAULT 'LOW',  -- LOW | MEDIUM | HIGH
    details     TEXT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_security_events_user_id   ON security_events(user_id);
CREATE INDEX idx_security_events_risk      ON security_events(risk_level);
CREATE INDEX idx_security_events_timestamp ON security_events(timestamp DESC);

-- ============================================================
-- SEED: Default admin user  (password: Admin@123)
-- ============================================================
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'System Admin',
    'admin@dfs.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBaaHr7dBZzUoW',
    'ADMIN'
);

-- ============================================================
-- SEED: Storage Nodes
-- ============================================================
INSERT INTO storage_nodes (node_id, name, host, port, status)
VALUES
    ('node1', 'Storage Node 1', 'node1', 8001, 'UNKNOWN'),
    ('node2', 'Storage Node 2', 'node2', 8002, 'UNKNOWN'),
    ('node3', 'Storage Node 3', 'node3', 8003, 'UNKNOWN')
ON CONFLICT (node_id) DO NOTHING;

-- ============================================================
-- SEED: Simulation state (one row per node)
-- ============================================================
INSERT INTO simulation_state (node_id, is_simulated)
VALUES ('node1', FALSE), ('node2', FALSE), ('node3', FALSE)
ON CONFLICT (node_id) DO NOTHING;
