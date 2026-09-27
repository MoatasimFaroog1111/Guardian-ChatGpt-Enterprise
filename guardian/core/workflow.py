from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from guardian.core.models import (
    ActorIdentity,
    ApprovalRequest,
    AuditRecord,
    CommandEnvelope,
    EvidenceItem,
    RiskLevel,
    WorkflowStatus,
    utcnow,
)
from guardian.core.policy import PolicyEngine
from guardian.domains.finance.reconciliation import (
    BankTransaction,
    DomainMatcher,
    GLTransaction,
    proposal_payload,
)


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
    def __init__(
        self,
        audit,
        erp,
        evidence,
        policy: PolicyEngine | None = None,
    ) -> None:
        self.audit = audit
        self.erp = erp
        self.evidence = evidence
        self.policy = policy or PolicyEngine()
        self.states: dict[str, WorkflowState] = {}
        self.idempotency: dict[str, str] = {}

    def submit_bank_reconciliation(
        self,
        command: CommandEnvelope,
    ) -> WorkflowState:
        if command.idempotency_key in self.idempotency:
            workflow_id = self.idempotency[command.idempotency_key]
            return self.states[workflow_id]

        decision = self.policy.evaluate(
            command.intent,
            command.actor,
            command.payload,
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)

        payload = command.payload
        bank_data = payload["bank"]
        bank = BankTransaction(
            bank_data["transaction_id"],
            date.fromisoformat(bank_data["transaction_date"]),
            Decimal(str(bank_data["amount"])),
            bank_data.get("reference", ""),
            bank_data.get("partner", ""),
        )

        gl_rows = [
            GLTransaction(
                row["external_id"],
                date.fromisoformat(row["transaction_date"]),
                Decimal(str(row["amount"])),
                row.get("reference", ""),
                row.get("partner", ""),
                row.get("account", ""),
                row.get("posted", True),
            )
            for row in payload.get("gl_rows", [])
        ]

        ranked = DomainMatcher().rank(bank, gl_rows)
        proposal = proposal_payload(
            bank,
            ranked[0] if ranked else None,
        )

        workflow_id = str(uuid4())
        approval = None
        if decision.requires_approval:
            approval = ApprovalRequest(
                workflow_id,
                decision.risk,
                decision.reason,
                command.actor.actor_id,
            )

        status = (
            WorkflowStatus.WAITING_APPROVAL
            if approval
            else WorkflowStatus.APPROVED
        )

        state = WorkflowState(
            workflow_id,
            command,
            status,
            decision.risk,
            proposal,
            approval,
        )
        self.states[workflow_id] = state
        self.idempotency[command.idempotency_key] = workflow_id

        evidence = [
            EvidenceItem("bank_row", bank_data),
            EvidenceItem(
                "gl_candidates",
                {
                    "count": len(gl_rows),
                    "top": proposal.get("best_match"),
                },
            ),
        ]
        self.evidence.store(workflow_id, evidence)
        self.audit.append(
            AuditRecord(
                workflow_id,
                "proposal.created",
                {
                    "proposal": proposal,
                    "risk": decision.risk.value,
                },
                command.actor.actor_id,
            )
        )
        return state

    def approve(
        self,
        workflow_id: str,
        approver: ActorIdentity,
    ) -> WorkflowState:
        state = self.states[workflow_id]

        if state.status != WorkflowStatus.WAITING_APPROVAL:
            raise ValueError("workflow is not waiting for approval")

        if approver.actor_id == state.command.actor.actor_id:
            raise PermissionError(
                "segregation of duties: requester cannot approve"
            )

        if "approver" not in approver.roles:
            raise PermissionError("approver role required")

        if state.approval is None:
            raise RuntimeError("approval record is missing")

        state.approval.approved_by = approver.actor_id
        state.approval.approved_at = utcnow()
        state.status = WorkflowStatus.APPROVED

        self.audit.append(
            AuditRecord(
                workflow_id,
                "approval.granted",
                {"risk": state.risk.value},
                approver.actor_id,
            )
        )
        return state

    def execute(
        self,
        workflow_id: str,
        actor: ActorIdentity,
    ) -> WorkflowState:
        state = self.states[workflow_id]
        if state.status != WorkflowStatus.APPROVED:
            raise PermissionError(
                "approval required before execution"
            )

        result = self.erp.create_draft_journal(
            state.proposal,
            state.command.idempotency_key,
        )
        if result.get("state") != "draft":
            raise RuntimeError(
                "ERP adapter violated draft-only contract"
            )

        state.execution = result
        state.status = WorkflowStatus.EXECUTED
        self.audit.append(
            AuditRecord(
                workflow_id,
                "execution.draft_created",
                {"external_id": result["external_id"]},
                actor.actor_id,
            )
        )

        actual = self.erp.read_journal(result["external_id"])
        verified = (
            actual.get("state") == "draft"
            and actual.get("external_id") == result.get("external_id")
        )
        state.verification = {
            "ok": verified,
            "expected_state": "draft",
            "actual_state": actual.get("state"),
        }
        state.status = (
            WorkflowStatus.VERIFIED
            if verified
            else WorkflowStatus.FAILED
        )
        self.audit.append(
            AuditRecord(
                workflow_id,
                "verification.completed",
                state.verification,
                actor.actor_id,
            )
        )
        return state
