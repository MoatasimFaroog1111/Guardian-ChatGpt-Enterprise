from __future__ import annotations

import json
from datetime import datetime

import psycopg

from guardian.core.models import AuditRecord, EvidenceItem


class PostgresStorage:
    """Neon/PostgreSQL-backed durable audit, evidence and workflow state."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._ensure_schema()

    def _connect(self):
        return psycopg.connect(self.database_url)

    def _ensure_schema(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS guardian_audit (
                    seq BIGSERIAL PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    actor_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_guardian_audit_workflow
                ON guardian_audit(workflow_id, seq)
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS guardian_evidence (
                    workflow_id TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS guardian_workflow_state (
                    workflow_id TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

    def append(self, record: AuditRecord) -> AuditRecord:
        with self._connect() as db:
            db.execute(
                "SELECT pg_advisory_xact_lock(hashtext('guardian_audit_chain'))"
            )
            row = db.execute(
                """
                SELECT record_hash
                FROM guardian_audit
                ORDER BY seq DESC
                LIMIT 1
                """
            ).fetchone()
            record.previous_hash = row[0] if row else "GENESIS"
            record.seal()
            db.execute(
                """
                INSERT INTO guardian_audit(
                    workflow_id,
                    event_type,
                    payload,
                    actor_id,
                    created_at,
                    previous_hash,
                    record_hash
                )
                VALUES(%s, %s, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    record.workflow_id,
                    record.event_type,
                    json.dumps(record.payload, default=str, sort_keys=True),
                    record.actor_id,
                    record.created_at,
                    record.previous_hash,
                    record.record_hash,
                ),
            )
        return record

    def list_for_workflow(self, workflow_id: str) -> list[AuditRecord]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT
                    workflow_id,
                    event_type,
                    payload,
                    actor_id,
                    created_at,
                    previous_hash,
                    record_hash
                FROM guardian_audit
                WHERE workflow_id = %s
                ORDER BY seq
                """,
                (workflow_id,),
            ).fetchall()

        return [
            AuditRecord(
                workflow_id=row[0],
                event_type=row[1],
                payload=row[2],
                actor_id=row[3],
                created_at=row[4],
                previous_hash=row[5],
                record_hash=row[6],
            )
            for row in rows
        ]

    def store(
        self,
        workflow_id: str,
        evidence: list[EvidenceItem],
    ) -> None:
        payload = [
            {
                "source": item.source,
                "payload": item.payload,
                "captured_at": item.captured_at.isoformat(),
            }
            for item in evidence
        ]
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO guardian_evidence(workflow_id, payload)
                VALUES(%s, %s::jsonb)
                ON CONFLICT(workflow_id)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (workflow_id, json.dumps(payload, default=str)),
            )

    def load(self, workflow_id: str) -> list[EvidenceItem]:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT payload
                FROM guardian_evidence
                WHERE workflow_id = %s
                """,
                (workflow_id,),
            ).fetchone()

        if not row:
            return []

        return [
            EvidenceItem(
                source=item["source"],
                payload=item["payload"],
                captured_at=datetime.fromisoformat(item["captured_at"]),
            )
            for item in row[0]
        ]

    def save(self, workflow_id: str, payload: dict) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO guardian_workflow_state(workflow_id, payload)
                VALUES(%s, %s::jsonb)
                ON CONFLICT(workflow_id)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (workflow_id, json.dumps(payload, default=str)),
            )

    def load_workflow(self, workflow_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT payload
                FROM guardian_workflow_state
                WHERE workflow_id = %s
                """,
                (workflow_id,),
            ).fetchone()
        return row[0] if row else None


class PostgresWorkflowStateStore:
    def __init__(self, storage: PostgresStorage) -> None:
        self.storage = storage

    def save(self, workflow_id: str, payload: dict) -> None:
        self.storage.save(workflow_id, payload)

    def load(self, workflow_id: str) -> dict | None:
        return self.storage.load_workflow(workflow_id)
