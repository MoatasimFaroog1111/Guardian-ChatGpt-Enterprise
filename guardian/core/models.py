from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStatus(str, Enum):
    RECEIVED = "received"
    PLANNED = "planned"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class ActorIdentity:
    actor_id: str
    channel: str
    roles: tuple[str, ...] = ()


@dataclass
class EvidenceItem:
    source: str
    payload: dict[str, Any]
    captured_at: datetime = field(default_factory=utcnow)

    @property
    def digest(self) -> str:
        raw = repr(
            (
                self.source,
                sorted(self.payload.items()),
                self.captured_at.isoformat(),
            )
        )
        return sha256(raw.encode()).hexdigest()


@dataclass
class CommandEnvelope:
    intent: str
    payload: dict[str, Any]
    actor: ActorIdentity
    idempotency_key: str
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ApprovalRequest:
    workflow_id: str
    risk: RiskLevel
    reason: str
    requested_by: str
    approved_by: str | None = None
    approved_at: datetime | None = None


@dataclass
class AuditRecord:
    workflow_id: str
    event_type: str
    payload: dict[str, Any]
    actor_id: str
    created_at: datetime = field(default_factory=utcnow)
    previous_hash: str = ""
    record_hash: str = ""

    def seal(self) -> AuditRecord:
        raw = (
            f"{self.workflow_id}|{self.event_type}|{self.actor_id}|"
            f"{self.created_at.isoformat()}|{self.previous_hash}|"
            f"{sorted(self.payload.items())!r}"
        )
        self.record_hash = sha256(raw.encode()).hexdigest()
        return self
