"""Telegram delivery adapter. Intentionally contains zero business rules.
Wire Telegram updates to the Command Center API; all policy remains in core.
"""
from __future__ import annotations
import os, httpx

async def forward_reconcile(actor_id: str, payload: dict) -> dict:
    base=os.environ.get("GUARDIAN_API_URL","http://localhost:8000")
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f"{base}/v1/finance/bank-reconciliation",json=payload,headers={"X-Actor-Id":actor_id})
        r.raise_for_status(); return r.json()
