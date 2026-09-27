from __future__ import annotations

from typing import Any, Protocol

from guardian.core.models import AuditRecord, EvidenceItem


class AuditPort(Protocol):
    def append(self, record: AuditRecord) -> AuditRecord: ...
    def list_for_workflow(self, workflow_id: str) -> list[AuditRecord]: ...


class ErpPort(Protocol):
    def create_draft_journal(
        self,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def read_journal(self, external_id: str) -> dict[str, Any]: ...


class NotificationPort(Protocol):
    async def send(self, actor_id: str, message: str) -> None: ...


class EvidencePort(Protocol):
    def store(
        self,
        workflow_id: str,
        evidence: list[EvidenceItem],
    ) -> None: ...

    def load(self, workflow_id: str) -> list[EvidenceItem]: ...


class WorkflowStatePort(Protocol):
    def save(self, workflow_id: str, payload: dict[str, Any]) -> None: ...
    def load(self, workflow_id: str) -> dict[str, Any] | None: ...


class IdempotencyPort(Protocol):
    def get(self, key: str) -> str | None: ...
    def put(self, key: str, workflow_id: str, ttl_seconds: int = 86400) -> None: ...


class ObjectStorePort(Protocol):
    def put_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str: ...

    def get_bytes(self, key: str) -> bytes: ...
