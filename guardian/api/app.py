from __future__ import annotations

import os
import secrets

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from guardian.core.models import ActorIdentity, CommandEnvelope
from guardian.runtime import build_coordinator

coordinator = build_coordinator()
app = FastAPI(title="Guardian Autonomous Enterprise", version="0.2.0")


@app.middleware("http")
async def require_edge_secret(request: Request, call_next):
    expected = os.getenv("GUARDIAN_EDGE_SECRET")
    if expected and request.url.path != "/health":
        supplied = request.headers.get("X-Guardian-Edge-Secret", "")
        if not secrets.compare_digest(supplied, expected):
            raise HTTPException(403, "edge authorization required")
    return await call_next(request)


class ReconcileRequest(BaseModel):
    bank: dict
    gl_rows: list[dict] = Field(default_factory=list)
    idempotency_key: str


class ApproveRequest(BaseModel):
    approver_id: str


class ExecuteRequest(BaseModel):
    actor_id: str


def actor(actor_id: str | None, roles: str | None = "") -> ActorIdentity:
    if not actor_id:
        raise HTTPException(401, "X-Actor-Id required")

    resolved_roles = tuple(
        value.strip()
        for value in (roles or "").split(",")
        if value.strip()
    )
    return ActorIdentity(actor_id, "api", resolved_roles)


def serialize(state) -> dict:
    return {
        "workflow_id": state.workflow_id,
        "status": state.status.value,
        "risk": state.risk.value,
        "proposal": state.proposal,
        "approval": vars(state.approval) if state.approval else None,
        "execution": state.execution,
        "verification": state.verification,
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "guardian-command-center",
        "persistence": (
            "postgres"
            if os.getenv("DATABASE_URL")
            else "local"
        ),
        "idempotency": (
            "upstash"
            if os.getenv("UPSTASH_REDIS_REST_URL")
            else "memory"
        ),
    }


@app.post("/v1/finance/bank-reconciliation")
def reconcile(
    req: ReconcileRequest,
    x_actor_id: str | None = Header(default=None),
    x_actor_roles: str | None = Header(default=""),
) -> dict:
    request_actor = actor(x_actor_id, x_actor_roles)
    command = CommandEnvelope(
        "finance.bank_reconcile",
        req.model_dump(exclude={"idempotency_key"}),
        request_actor,
        req.idempotency_key,
    )
    try:
        return serialize(coordinator.submit_bank_reconciliation(command))
    except (PermissionError, ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/v1/workflows/{workflow_id}/approve")
def approve(workflow_id: str, req: ApproveRequest) -> dict:
    try:
        approver = ActorIdentity(req.approver_id, "api", ("approver",))
        return serialize(coordinator.approve(workflow_id, approver))
    except KeyError as exc:
        raise HTTPException(404, "workflow not found") from exc
    except (PermissionError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/v1/workflows/{workflow_id}/execute")
def execute(workflow_id: str, req: ExecuteRequest) -> dict:
    try:
        executor = ActorIdentity(req.actor_id, "api", ("executor",))
        return serialize(coordinator.execute(workflow_id, executor))
    except KeyError as exc:
        raise HTTPException(404, "workflow not found") from exc
    except (PermissionError, ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/v1/workflows/{workflow_id}/audit")
def audit(workflow_id: str) -> list[dict]:
    return [
        {
            "event_type": item.event_type,
            "actor_id": item.actor_id,
            "created_at": item.created_at,
            "previous_hash": item.previous_hash,
            "record_hash": item.record_hash,
            "payload": item.payload,
        }
        for item in coordinator.audit.list_for_workflow(workflow_id)
    ]
