from __future__ import annotations

import json
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


def load_guardian_config() -> dict[str, str]:
    raw = os.getenv("GUARDIAN_CONFIG", "").strip()
    if not raw:
        return {}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GUARDIAN_CONFIG must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise TypeError("GUARDIAN_CONFIG must be a JSON object")

    return {
        str(key): str(value)
        for key, value in payload.items()
        if value is not None
    }


def config_value(name: str, default: str | None = None) -> str | None:
    config = load_guardian_config()
    return config.get(name) or os.getenv(name) or default


def build_coordinator() -> WorkflowCoordinator:
    database_url = config_value("DATABASE_URL")

    if database_url:
        postgres = PostgresStorage(database_url)
        audit = postgres
        evidence = postgres
        state_store = PostgresWorkflowStateStore(postgres)
    else:
        audit = SQLiteAuditLedger(
            config_value("GUARDIAN_DB", "/tmp/guardian.db")
            or "/tmp/guardian.db"
        )
        evidence = InMemoryEvidenceStore()
        state_store = InMemoryWorkflowStateStore()

    upstash_url = config_value("UPSTASH_REDIS_REST_URL")
    upstash_token = config_value("UPSTASH_REDIS_REST_TOKEN")
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
