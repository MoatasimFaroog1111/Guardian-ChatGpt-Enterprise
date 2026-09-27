from __future__ import annotations

import os

import httpx


class GPUProviderRouter:
    """On-demand GPU routing. No GPU is kept alive by this service."""

    def __init__(self) -> None:
        self.runpod_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
        self.runpod_api_key = os.getenv("RUNPOD_API_KEY")
        self.modal_url = os.getenv("MODAL_GPU_URL")
        self.modal_token = os.getenv("MODAL_TOKEN")

    def available(self) -> list[str]:
        providers = []
        if self.modal_url:
            providers.append("modal")
        if self.runpod_endpoint_id and self.runpod_api_key:
            providers.append("runpod")
        return providers

    def invoke(
        self,
        payload: dict,
        provider: str | None = None,
        timeout_seconds: float = 120,
    ) -> dict:
        selected = provider or (
            "modal"
            if self.modal_url
            else "runpod"
        )

        if selected == "modal":
            if not self.modal_url:
                raise RuntimeError("Modal GPU endpoint is not configured")
            headers = {}
            if self.modal_token:
                headers["Authorization"] = f"Bearer {self.modal_token}"
            response = httpx.post(
                self.modal_url,
                json=payload,
                headers=headers,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return response.json()

        if selected == "runpod":
            if not self.runpod_endpoint_id or not self.runpod_api_key:
                raise RuntimeError("RunPod endpoint is not configured")
            response = httpx.post(
                (
                    "https://api.runpod.ai/v2/"
                    f"{self.runpod_endpoint_id}/runsync"
                ),
                json={"input": payload},
                headers={
                    "Authorization": f"Bearer {self.runpod_api_key}",
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return response.json()

        raise ValueError(f"unsupported GPU provider: {selected}")
