from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from guardian.core.models import EvidenceItem


class InMemoryERP:
    """Safe default adapter: draft-only. It can never post entries."""

    def __init__(self) -> None:
        self._drafts: dict[str, dict] = {}
        self._idem: dict[str, str] = {}

    def create_draft_journal(self, payload: dict, idempotency_key: str) -> dict:
        if idempotency_key in self._idem:
            return deepcopy(self._drafts[self._idem[idempotency_key]])

        external_id = f"DRAFT-{uuid4().hex[:12]}"
        document = {
            "external_id": external_id,
            "state": "draft",
            **deepcopy(payload),
        }
        self._drafts[external_id] = document
        self._idem[idempotency_key] = external_id
        return deepcopy(document)

    def read_journal(self, external_id: str) -> dict:
        return deepcopy(self._drafts[external_id])


class InMemoryEvidenceStore:
    def __init__(self) -> None:
        self.data: dict[str, list[EvidenceItem]] = {}

    def store(self, workflow_id: str, evidence: list[EvidenceItem]) -> None:
        self.data[workflow_id] = list(evidence)

    def load(self, workflow_id: str) -> list[EvidenceItem]:
        return list(self.data.get(workflow_id, []))


class ConsoleNotifier:
    async def send(self, actor_id: str, message: str) -> None:
        print(f"NOTIFY {actor_id}: {message}")
