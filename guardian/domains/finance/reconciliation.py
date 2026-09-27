from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal
from typing import Iterable


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
    def rank(self, bank: BankTransaction, gl_rows: Iterable[GLTransaction]) -> list[MatchCandidate]:
        candidates=[]
        for gl in gl_rows:
            score=0.0; reasons=[]
            if bank.amount == gl.amount:
                score += 0.55; reasons.append("exact_amount")
            delta=abs((bank.transaction_date-gl.transaction_date).days)
            if delta == 0:
                score += 0.25; reasons.append("same_date")
            elif delta <= 3:
                score += 0.15; reasons.append("date_within_3_days")
            if bank.reference and gl.reference and bank.reference.casefold() in gl.reference.casefold():
                score += 0.12; reasons.append("reference_overlap")
            if bank.partner and gl.partner and bank.partner.casefold() == gl.partner.casefold():
                score += 0.08; reasons.append("partner_exact")
            if score > 0:
                candidates.append(MatchCandidate(bank.transaction_id, gl.external_id, min(score,1.0), tuple(reasons)))
        return sorted(candidates, key=lambda x:x.score, reverse=True)


def proposal_payload(bank: BankTransaction, candidate: MatchCandidate | None) -> dict:
    return {
        "bank": {**asdict(bank), "transaction_date": bank.transaction_date.isoformat(), "amount": str(bank.amount)},
        "best_match": asdict(candidate) if candidate else None,
        "action": "match_existing" if candidate and candidate.score >= 0.85 else "create_draft_review_required",
    }
