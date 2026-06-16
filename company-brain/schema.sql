-- Company Brain – PostgreSQL Schema
-- Run: psql -f schema.sql  OR  mounted into docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────
--  CRM TABLES
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contacts (
    id          TEXT PRIMARY KEY,
    email       TEXT,
    name        TEXT,
    company     TEXT,
    clv_score   DECIMAL DEFAULT 0,
    clv_tier    TEXT DEFAULT 'STANDARD',   -- STANDARD | SILVER | GOLD | PLATINUM
    industry    TEXT,
    phone       TEXT,
    crm_source  TEXT DEFAULT 'mock',
    raw_data    JSONB,
    synced_at   TIMESTAMP DEFAULT NOW(),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deals (
    id                  TEXT PRIMARY KEY,
    name                TEXT,
    company             TEXT,
    contact_id          TEXT REFERENCES contacts(id) ON DELETE SET NULL,
    owner_id            TEXT,
    owner_name          TEXT,
    amount              DECIMAL DEFAULT 0,
    stage               TEXT,              -- e.g. 'negotiation', 'closed_won', 'closed_lost'
    close_date          DATE,
    renewal_date        DATE,
    contract_length_mo  INTEGER DEFAULT 12,
    last_activity_at    TIMESTAMP,
    days_since_activity INTEGER GENERATED ALWAYS AS (
                            EXTRACT(DAY FROM NOW() - last_activity_at)::INTEGER
                        ) STORED,
    crm_source          TEXT DEFAULT 'mock',
    raw_data            JSONB,
    synced_at           TIMESTAMP DEFAULT NOW(),
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deals_renewal_date ON deals(renewal_date);
CREATE INDEX IF NOT EXISTS idx_deals_stage        ON deals(stage);
CREATE INDEX IF NOT EXISTS idx_deals_contact      ON deals(contact_id);

CREATE TABLE IF NOT EXISTS reps (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT,
    role        TEXT DEFAULT 'sales_rep',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
--  KNOWLEDGE BASE (RAG)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,  -- e.g. 'Sales Playbook v3', 'Refund Policy'
    source_type TEXT DEFAULT 'document',  -- 'document' | 'sop' | 'email_template'
    content     TEXT NOT NULL,
    embedding   vector(1536),
    metadata    JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ─────────────────────────────────────────
--  ACTION QUEUE (Human Approval Gate)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS action_queue (
    id              SERIAL PRIMARY KEY,
    action_type     TEXT NOT NULL,   -- 'renewal_email' | 'assign_task' | 'slack_reminder' | 'escalate'
    deal_id         TEXT REFERENCES deals(id) ON DELETE CASCADE,
    contact_id      TEXT,
    payload         JSONB NOT NULL,  -- drafted email / task / etc.
    urgency         TEXT DEFAULT 'MEDIUM',   -- HIGH | MEDIUM | LOW
    reason          TEXT,            -- why the action was suggested
    status          TEXT DEFAULT 'PENDING_APPROVAL',
    --              PENDING_APPROVAL | APPROVED | REJECTED | EXECUTED | FAILED
    created_at      TIMESTAMP DEFAULT NOW(),
    approved_by     TEXT,
    approved_at     TIMESTAMP,
    executed_at     TIMESTAMP,
    rejected_by     TEXT,
    reject_reason   TEXT,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_action_queue_status ON action_queue(status);
CREATE INDEX IF NOT EXISTS idx_action_queue_deal   ON action_queue(deal_id);

-- ─────────────────────────────────────────
--  AUDIT LOG
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    action_type TEXT NOT NULL,
    deal_id     TEXT,
    actor       TEXT,   -- user_id or 'system'
    details     JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_deal    ON audit_log(deal_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);

-- ─────────────────────────────────────────
--  REP PERFORMANCE SNAPSHOTS
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rep_metrics (
    id                    SERIAL PRIMARY KEY,
    rep_id                TEXT REFERENCES reps(id),
    win_rate              DECIMAL,
    avg_response_time_hrs DECIMAL,
    avg_deal_size         DECIMAL,
    deals_stalled         INTEGER DEFAULT 0,
    snapshot_date         DATE DEFAULT CURRENT_DATE,
    created_at            TIMESTAMP DEFAULT NOW()
);
