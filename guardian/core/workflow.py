from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4
from guardian.core.models import *
from guardian.core.policy import PolicyEngine
from guardian.domains.finance.reconciliation import BankTransaction, GLTransaction, DomainMatcher, proposal_payload


@dataclass
class WorkflowState:
    workflow_id: str
    command: CommandEnvelope
    status: WorkflowStatus
    risk: RiskLevel
    proposal: dict
    approval: ApprovalRequest | None = None
    execution: dict | None = None
    verification: dict | None = None


class WorkflowCoordinator:
    def __init__(self, audit, erp, evidence, policy: PolicyEngine | None = None) -> None:
        self.audit, self.erp, self.evidence = audit, erp, evidence
        self.policy = policy or PolicyEngine()
        self.states: dict[str, WorkflowState] = {}
        self.idempotency: dict[str, str] = {}

    def submit_bank_reconciliation(self, command: CommandEnvelope) -> WorkflowState:
        if command.idempotency_key in self.idempotency:
            return self.states[self.idempotency[command.idempotency_key]]
        decision = self.policy.evaluate(command.intent, command.actor, command.payload)
        if not decision.allowed: raise PermissionError(decision.reason)
        p=command.payload
        bank=BankTransaction(p["bank"]["transaction_id"], date.fromisoformat(p["bank"]["transaction_date"]), Decimal(str(p["bank"]["amount"])), p["bank"].get("reference",""), p["bank"].get("partner",""))
        gl=[GLTransaction(x["external_id"],date.fromisoformat(x["transaction_date"]),Decimal(str(x["amount"])),x.get("reference",""),x.get("partner",""),x.get("account",""),x.get("posted",True)) for x in p.get("gl_rows",[])]
        ranked=DomainMatcher().rank(bank,gl)
        proposal=proposal_payload(bank, ranked[0] if ranked else None)
        wid=str(uuid4())
        approval=ApprovalRequest(wid,decision.risk,decision.reason,command.actor.actor_id) if decision.requires_approval else None
        status=WorkflowStatus.WAITING_APPROVAL if approval else WorkflowStatus.APPROVED
        state=WorkflowState(wid,command,status,decision.risk,proposal,approval)
        self.states[wid]=state; self.idempotency[command.idempotency_key]=wid
        ev=[EvidenceItem("bank_row",p["bank"]),EvidenceItem("gl_candidates",{"count":len(gl),"top":proposal.get("best_match")})]
        self.evidence.store(wid,ev)
        self.audit.append(AuditRecord(wid,"proposal.created",{"proposal":proposal,"risk":decision.risk.value},command.actor.actor_id))
        return state

    def approve(self, workflow_id: str, approver: ActorIdentity) -> WorkflowState:
        s=self.states[workflow_id]
        if s.status != WorkflowStatus.WAITING_APPROVAL: raise ValueError("workflow is not waiting for approval")
        if approver.actor_id == s.command.actor.actor_id: raise PermissionError("segregation of duties: requester cannot approve")
        if "approver" not in approver.roles: raise PermissionError("approver role required")
        s.approval.approved_by=approver.actor_id; s.approval.approved_at=utcnow(); s.status=WorkflowStatus.APPROVED
        self.audit.append(AuditRecord(workflow_id,"approval.granted",{"risk":s.risk.value},approver.actor_id))
        return s

    def execute(self, workflow_id: str, actor: ActorIdentity) -> WorkflowState:
        s=self.states[workflow_id]
        if s.status != WorkflowStatus.APPROVED: raise PermissionError("approval required before execution")
        result=self.erp.create_draft_journal(s.proposal,s.command.idempotency_key)
        if result.get("state") != "draft": raise RuntimeError("ERP adapter violated draft-only contract")
        s.execution=result; s.status=WorkflowStatus.EXECUTED
        self.audit.append(AuditRecord(workflow_id,"execution.draft_created",{"external_id":result["external_id"]},actor.actor_id))
        actual=self.erp.read_journal(result["external_id"])
        ok=actual.get("state")=="draft" and actual.get("external_id")==result.get("external_id")
        s.verification={"ok":ok,"expected_state":"draft","actual_state":actual.get("state")}
        s.status=WorkflowStatus.VERIFIED if ok else WorkflowStatus.FAILED
        self.audit.append(AuditRecord(workflow_id,"verification.completed",s.verification,actor.actor_id))
        return s
