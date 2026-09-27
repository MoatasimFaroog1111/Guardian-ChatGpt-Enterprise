from guardian.runtime import build_coordinator
from guardian.adapters.local import (
    InMemoryIdempotencyStore,
    InMemoryWorkflowStateStore,
)


def test_runtime_defaults_to_low_cost_local_adapters(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)

    coordinator = build_coordinator()

    assert isinstance(
        coordinator.state_store,
        InMemoryWorkflowStateStore,
    )
    assert isinstance(
        coordinator.idempotency,
        InMemoryIdempotencyStore,
    )
