from guardian.core.audit import SQLiteAuditLedger
from guardian.core.models import ActorIdentity, CommandEnvelope, WorkflowStatus
from guardian.core.workflow import WorkflowCoordinator
from guardian.adapters.local import InMemoryERP, InMemoryEvidenceStore


def make(tmp_path): return WorkflowCoordinator(SQLiteAuditLedger(str(tmp_path/"g.db")),InMemoryERP(),InMemoryEvidenceStore())

def payload(): return {"bank":{"transaction_id":"B1","transaction_date":"2026-09-27","amount":"100.00","reference":"INV-1","partner":"ACME"},"gl_rows":[{"external_id":"GL1","transaction_date":"2026-09-27","amount":"100.00","reference":"INV-1","partner":"ACME","account":"101001"}]}

def test_financial_flow_requires_separate_approval_and_stays_draft(tmp_path):
    c=make(tmp_path); requester=ActorIdentity("requester","api",("finance",))
    s=c.submit_bank_reconciliation(CommandEnvelope("finance.bank_reconcile",payload(),requester,"idem-1"))
    assert s.status == WorkflowStatus.WAITING_APPROVAL
    try: c.approve(s.workflow_id,ActorIdentity("requester","api",("approver",))); assert False
    except PermissionError: pass
    c.approve(s.workflow_id,ActorIdentity("cfo","api",("approver",)))
    out=c.execute(s.workflow_id,ActorIdentity("worker","api",("executor",)))
    assert out.status == WorkflowStatus.VERIFIED
    assert out.execution["state"] == "draft"
    assert out.verification["ok"] is True
    assert len(c.audit.list_for_workflow(s.workflow_id)) == 4

def test_idempotency_returns_same_workflow(tmp_path):
    c=make(tmp_path); a=ActorIdentity("u","api",())
    one=c.submit_bank_reconciliation(CommandEnvelope("finance.bank_reconcile",payload(),a,"same"))
    two=c.submit_bank_reconciliation(CommandEnvelope("finance.bank_reconcile",payload(),a,"same"))
    assert one.workflow_id == two.workflow_id
