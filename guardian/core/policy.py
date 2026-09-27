from __future__ import annotations

from dataclasses import dataclass

from guardian.core.models import ActorIdentity, RiskLevel


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    risk: RiskLevel
    reason: str


class PolicyEngine:
    """Fail-closed policy engine. Financial writes always require approval."""

    def evaluate(
        self,
        intent: str,
        actor: ActorIdentity,
        payload: dict,
    ) -> PolicyDecision:
        del payload

        if not actor.actor_id:
            return PolicyDecision(
                False,
                True,
                RiskLevel.CRITICAL,
                "missing actor identity",
            )
        if intent == "finance.bank_reconcile":
            return PolicyDecision(
                True,
                True,
                RiskLevel.HIGH,
                "financial ERP draft requires human approval",
            )
        if intent.startswith("read.") or intent in {"system.status", "help"}:
            return PolicyDecision(
                True,
                False,
                RiskLevel.LOW,
                "read-only",
            )
        return PolicyDecision(
            False,
            True,
            RiskLevel.CRITICAL,
            "intent not allow-listed",
        )
