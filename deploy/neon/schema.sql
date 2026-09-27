CREATE TABLE IF NOT EXISTS guardian_audit (
    seq BIGSERIAL PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    actor_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    previous_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_guardian_audit_workflow
ON guardian_audit(workflow_id, seq);

CREATE TABLE IF NOT EXISTS guardian_evidence (
    workflow_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS guardian_workflow_state (
    workflow_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
