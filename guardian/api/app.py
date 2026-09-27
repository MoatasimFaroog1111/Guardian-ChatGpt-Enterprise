from __future__ import annotations

import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from guardian.core.audit import SQLiteAuditLedger
from guardian.core.models import ActorIdentity, CommandEnvelope
from guardian.core.workflow import WorkflowCoordinator
from guardian.adapters.local import InMemoryERP, InMemoryEvidenceStore

DB=os.getenv("GUARDIAN_DB","/tmp/guardian.db")
coordinator=WorkflowCoordinator(SQLiteAuditLedger(DB),InMemoryERP(),InMemoryEvidenceStore())
app=FastAPI(title="Guardian Autonomous Enterprise",version="0.1.0")

class ReconcileRequest(BaseModel):
    bank: dict
    gl_rows: list[dict] = Field(default_factory=list)
    idempotency_key: str

class ApproveRequest(BaseModel): approver_id: str
class ExecuteRequest(BaseModel): actor_id: str

def actor(actor_id: str | None, roles: str | None="") -> ActorIdentity:
    if not actor_id: raise HTTPException(401,"X-Actor-Id required")
    return ActorIdentity(actor_id,"api",tuple(x.strip() for x in (roles or "").split(",") if x.strip()))

def serialize(s):
    return {"workflow_id":s.workflow_id,"status":s.status.value,"risk":s.risk.value,"proposal":s.proposal,"approval":vars(s.approval) if s.approval else None,"execution":s.execution,"verification":s.verification}

@app.get("/health")
def health(): return {"status":"ok","service":"guardian-command-center"}

@app.post("/v1/finance/bank-reconciliation")
def reconcile(req: ReconcileRequest, x_actor_id: str|None=Header(default=None), x_actor_roles: str|None=Header(default="")):
    a=actor(x_actor_id,x_actor_roles)
    cmd=CommandEnvelope("finance.bank_reconcile",req.model_dump(exclude={"idempotency_key"}),a,req.idempotency_key)
    try: return serialize(coordinator.submit_bank_reconciliation(cmd))
    except (PermissionError,ValueError,KeyError) as e: raise HTTPException(400,str(e))

@app.post("/v1/workflows/{workflow_id}/approve")
def approve(workflow_id: str, req: ApproveRequest):
    try: return serialize(coordinator.approve(workflow_id,ActorIdentity(req.approver_id,"api",("approver",))))
    except KeyError: raise HTTPException(404,"workflow not found")
    except (PermissionError,ValueError) as e: raise HTTPException(409,str(e))

@app.post("/v1/workflows/{workflow_id}/execute")
def execute(workflow_id: str, req: ExecuteRequest):
    try: return serialize(coordinator.execute(workflow_id,ActorIdentity(req.actor_id,"api",("executor",))))
    except KeyError: raise HTTPException(404,"workflow not found")
    except (PermissionError,ValueError,RuntimeError) as e: raise HTTPException(409,str(e))

@app.get("/v1/workflows/{workflow_id}/audit")
def audit(workflow_id: str):
    return [{"event_type":x.event_type,"actor_id":x.actor_id,"created_at":x.created_at,"previous_hash":x.previous_hash,"record_hash":x.record_hash,"payload":x.payload} for x in coordinator.audit.list_for_workflow(workflow_id)]
