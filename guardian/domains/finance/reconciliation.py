from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class BankTransaction:
    transaction_id: str
    transaction_date: date
    amount: Decimal
    reference: str = ""
    partner: str = ""


@dataclass(frozen=True)
class GLTransaction:
    external_id: str
    transaction_date: date
    amount: Decimal
    reference: str = ""
    partner: str = ""
    account: str = ""
    posted: bool = True


@dataclass(frozen=True)
class MatchCandidate:
    bank_transaction_id: str
    gl_external_id: str
    score: float
    reasons: tuple[str, ...]


class DomainMatcher:
    def rank(
        self,
        bank: BankTransaction,
        gl_rows: Iterable[GLTransaction],
    ) -> list[MatchCandidate]:
        candidates: list[MatchCandidate] = []

        for gl_row in gl_rows:
            score = 0.0
            reasons: list[str] = []

            if bank.amount == gl_row.amount:
                score += 0.55
                reasons.append("exact_amount")

            date_delta = abs(
                (bank.transaction_date - gl_row.transaction_date).days
            )
            if date_delta == 0:
                score += 0.25
                reasons.append("same_date")
            elif date_delta <= 3:
                score += 0.15
                reasons.append("date_within_3_days")

            if (
                bank.reference
                and gl_row.reference
                and bank.reference.casefold()
                in gl_row.reference.casefold()
            ):
                score += 0.12
                reasons.append("reference_overlap")

            if (
                bank.partner
                and gl_row.partner
                and bank.partner.casefold() == gl_row.partner.casefold()
            ):
                score += 0.08
                reasons.append("partner_exact")

            if score > 0:
                candidates.append(
                    MatchCandidate(
                        bank.transaction_id,
                        gl_row.external_id,
                        min(score, 1.0),
                        tuple(reasons),
                    )
                )

        return sorted(
            candidates,
            key=lambda candidate: candidate.score,
            reverse=True,
        )


def proposal_payload(
    bank: BankTransaction,
    candidate: MatchCandidate | None,
) -> dict:
    return {
        "bank": {
            **asdict(bank),
            "transaction_date": bank.transaction_date.isoformat(),
            "amount": str(bank.amount),
        },
        "best_match": asdict(candidate) if candidate else None,
        "action": (
            "match_existing"
            if candidate and candidate.score >= 0.85
            else "create_draft_review_required"
        ),
    }
