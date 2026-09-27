import json

from guardian.adapters.local import (
    InMemoryIdempotencyStore,
    InMemoryWorkflowStateStore,
)
from guardian.runtime import (
    build_coordinator,
    config_value,
)


def test_runtime_defaults_to_low_cost_local_adapters(monkeypatch):
    monkeypatch.delenv("GUARDIAN_CONFIG", raising=False)
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


def test_single_secret_overrides_individual_environment(monkeypatch):
    monkeypatch.setenv(
        "GUARDIAN_CONFIG",
        json.dumps(
            {
                "DATABASE_URL": "postgresql://from-secret",
                "GUARDIAN_EDGE_SECRET": "edge-secret",
            }
        ),
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://from-env",
    )

    assert config_value("DATABASE_URL") == "postgresql://from-secret"
    assert config_value("GUARDIAN_EDGE_SECRET") == "edge-secret"
