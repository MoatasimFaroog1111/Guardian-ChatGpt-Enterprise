from __future__ import annotations

import os

from guardian.adapters.local import (
    InMemoryERP,
    InMemoryEvidenceStore,
    InMemoryIdempotencyStore,
    InMemoryWorkflowStateStore,
)
from guardian.adapters.postgres import (
    PostgresStorage,
    PostgresWorkflowStateStore,
)
from guardian.adapters.upstash import UpstashIdempotencyStore
from guardian.core.audit import SQLiteAuditLedger
from guardian.core.workflow import WorkflowCoordinator


def build_coordinator() -> WorkflowCoordinator:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        postgres = PostgresStorage(database_url)
        audit = postgres
        evidence = postgres
        state_store = PostgresWorkflowStateStore(postgres)
    else:
        audit = SQLiteAuditLedger(
            os.getenv("GUARDIAN_DB", "/tmp/guardian.db")
        )
        evidence = InMemoryEvidenceStore()
        state_store = InMemoryWorkflowStateStore()

    upstash_url = os.getenv("UPSTASH_REDIS_REST_URL")
    upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if upstash_url and upstash_token:
        idempotency = UpstashIdempotencyStore(
            upstash_url,
            upstash_token,
        )
    else:
        idempotency = InMemoryIdempotencyStore()

    return WorkflowCoordinator(
        audit=audit,
        erp=InMemoryERP(),
        evidence=evidence,
        state_store=state_store,
        idempotency=idempotency,
    )
