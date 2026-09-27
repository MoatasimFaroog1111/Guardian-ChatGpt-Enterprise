from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from guardian.core.models import AuditRecord


class SQLiteAuditLedger:
    def __init__(self, path: str = "guardian.db") -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                record_hash TEXT NOT NULL UNIQUE
            )"""
            )

    def append(self, record: AuditRecord) -> AuditRecord:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT record_hash FROM audit ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            record.previous_hash = row[0] if row else "GENESIS"
            record.seal()
            db.execute(
                """
                INSERT INTO audit(
                    workflow_id,
                    event_type,
                    payload,
                    actor_id,
                    created_at,
                    previous_hash,
                    record_hash
                )
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    record.workflow_id,
                    record.event_type,
                    json.dumps(
                        record.payload,
                        default=str,
                        sort_keys=True,
                    ),
                    record.actor_id,
                    record.created_at.isoformat(),
                    record.previous_hash,
                    record.record_hash,
                ),
            )
        return record

    def list_for_workflow(self, workflow_id: str) -> list[AuditRecord]:
        with sqlite3.connect(self.path) as db:
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
                FROM audit
                WHERE workflow_id=?
                ORDER BY seq
                """,
                (workflow_id,),
            ).fetchall()

        return [
            AuditRecord(
                row[0],
                row[1],
                json.loads(row[2]),
                row[3],
                datetime.fromisoformat(row[4]),
                row[5],
                row[6],
            )
            for row in rows
        ]
