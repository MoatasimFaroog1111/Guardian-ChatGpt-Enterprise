"""Telegram delivery adapter with zero business rules."""

from __future__ import annotations

import os

import httpx


async def forward_reconcile(actor_id: str, payload: dict) -> dict:
    base_url = os.environ.get(
        "GUARDIAN_API_URL",
        "http://localhost:8000",
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{base_url}/v1/finance/bank-reconciliation",
            json=payload,
            headers={"X-Actor-Id": actor_id},
        )
        response.raise_for_status()
        return response.json()
