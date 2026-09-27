from __future__ import annotations

import httpx


class UpstashIdempotencyStore:
    """Uses Upstash Redis REST so no long-lived Redis connection is required."""

    def __init__(
        self,
        rest_url: str,
        token: str,
        namespace: str = "guardian:idem",
    ) -> None:
        self.rest_url = rest_url.rstrip("/")
        self.token = token
        self.namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def _command(self, command: list[str]) -> object:
        response = httpx.post(
            self.rest_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json=command,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("result")

    def get(self, key: str) -> str | None:
        result = self._command(["GET", self._key(key)])
        return str(result) if result is not None else None

    def put(
        self,
        key: str,
        workflow_id: str,
        ttl_seconds: int = 86400,
    ) -> None:
        self._command(
            [
                "SET",
                self._key(key),
                workflow_id,
                "EX",
                str(ttl_seconds),
                "NX",
            ]
        )
