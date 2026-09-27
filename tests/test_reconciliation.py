import pytest

from guardian.adapters.local import (
    InMemoryERP,
    InMemoryEvidenceStore,
    InMemoryIdempotencyStore,
    InMemoryWorkflowStateStore,
)
from guardian.core.audit import SQLiteAuditLedger
from guardian.core.models import (
    ActorIdentity,
    CommandEnvelope,
    WorkflowStatus,
)
from guardian.core.workflow import WorkflowCoordinator


def make_coordinator(tmp_path) -> WorkflowCoordinator:
    return WorkflowCoordinator(
        audit=SQLiteAuditLedger(str(tmp_path / "g.db")),
        erp=InMemoryERP(),
        evidence=InMemoryEvidenceStore(),
        state_store=InMemoryWorkflowStateStore(),
        idempotency=InMemoryIdempotencyStore(),
    )


def payload() -> dict:
    return {
        "bank": {
            "transaction_id": "B1",
            "transaction_date": "2026-09-27",
            "amount": "100.00",
            "reference": "INV-1",
            "partner": "ACME",
        },
        "gl_rows": [
            {
                "external_id": "GL1",
                "transaction_date": "2026-09-27",
                "amount": "100.00",
                "reference": "INV-1",
                "partner": "ACME",
                "account": "101001",
            }
        ],
    }


def test_financial_flow_requires_separate_approval_and_stays_draft(
    tmp_path,
) -> None:
    coordinator = make_coordinator(tmp_path)
    requester = ActorIdentity(
        "requester",
        "api",
        ("finance",),
    )
    state = coordinator.submit_bank_reconciliation(
        CommandEnvelope(
            "finance.bank_reconcile",
            payload(),
            requester,
            "idem-1",
        )
    )
    assert state.status == WorkflowStatus.WAITING_APPROVAL

    with pytest.raises(PermissionError):
        coordinator.approve(
            state.workflow_id,
            ActorIdentity(
                "requester",
                "api",
                ("approver",),
            ),
        )

    coordinator.approve(
        state.workflow_id,
        ActorIdentity("cfo", "api", ("approver",)),
    )
    output = coordinator.execute(
        state.workflow_id,
        ActorIdentity("worker", "api", ("executor",)),
    )

    assert output.status == WorkflowStatus.VERIFIED
    assert output.execution["state"] == "draft"
    assert output.verification["ok"] is True
    assert len(
        coordinator.audit.list_for_workflow(state.workflow_id)
    ) == 4


def test_idempotency_survives_state_reload(tmp_path) -> None:
    state_store = InMemoryWorkflowStateStore()
    idempotency = InMemoryIdempotencyStore()
    coordinator = WorkflowCoordinator(
        audit=SQLiteAuditLedger(str(tmp_path / "g.db")),
        erp=InMemoryERP(),
        evidence=InMemoryEvidenceStore(),
        state_store=state_store,
        idempotency=idempotency,
    )
    actor = ActorIdentity("u", "api", ())
    first = coordinator.submit_bank_reconciliation(
        CommandEnvelope(
            "finance.bank_reconcile",
            payload(),
            actor,
            "same",
        )
    )

    restarted = WorkflowCoordinator(
        audit=coordinator.audit,
        erp=coordinator.erp,
        evidence=coordinator.evidence,
        state_store=state_store,
        idempotency=idempotency,
    )
    second = restarted.submit_bank_reconciliation(
        CommandEnvelope(
            "finance.bank_reconcile",
            payload(),
            actor,
            "same",
        )
    )
    assert first.workflow_id == second.workflow_id
