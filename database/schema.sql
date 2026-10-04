-- ============================================================
-- Distributed File Sharing System – Database Schema
-- ============================================================

-- Drop tables in correct dependency order
DROP TABLE IF EXISTS audit_logs       CASCADE;
DROP TABLE IF EXISTS file_permissions CASCADE;
DROP TABLE IF EXISTS file_locations   CASCADE;
DROP TABLE IF EXISTS files            CASCADE;
DROP TABLE IF EXISTS storage_nodes    CASCADE;
DROP TABLE IF EXISTS users            CASCADE;

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
    status            VARCHAR(50)         NOT NULL DEFAULT 'UNKNOWN', -- ONLINE | OFFLINE | UNKNOWN | DISABLED
    total_storage     BIGINT              NOT NULL DEFAULT 0,
    available_storage BIGINT              NOT NULL DEFAULT 0,
    file_count        INTEGER             NOT NULL DEFAULT 0,
    last_heartbeat    TIMESTAMPTZ,
    created_at        TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_storage_nodes_node_id ON storage_nodes(node_id);
CREATE INDEX idx_storage_nodes_status  ON storage_nodes(status);

-- ============================================================
-- FILES
-- ============================================================
CREATE TABLE files (
    id                SERIAL PRIMARY KEY,
    filename          VARCHAR(500)  NOT NULL,  -- stored/safe filename
    original_filename VARCHAR(500)  NOT NULL,  -- user-supplied name
    size              BIGINT        NOT NULL DEFAULT 0,
    mime_type         VARCHAR(255),
    owner_id          INTEGER       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checksum          VARCHAR(64)   NOT NULL,  -- SHA-256 hex
    primary_node_id   VARCHAR(100)  REFERENCES storage_nodes(node_id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_files_owner_id       ON files(owner_id);
CREATE INDEX idx_files_primary_node   ON files(primary_node_id);
CREATE INDEX idx_files_original_name  ON files(original_filename);
CREATE INDEX idx_files_created_at     ON files(created_at DESC);

-- ============================================================
-- FILE LOCATIONS  (tracks which node holds which copy)
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
    action    VARCHAR(100) NOT NULL,  -- REGISTER|LOGIN|UPLOAD|DOWNLOAD|DELETE|SHARE|etc.
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
-- SEED: Default admin user  (password: Admin@123)
-- ============================================================
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'System Admin',
    'admin@dfs.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBaaHr7dBZzUoW', -- Admin@123
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

