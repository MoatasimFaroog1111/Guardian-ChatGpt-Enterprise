# Guardian-ChatGpt-Enterprise

A low-cost, production-oriented implementation of **Guardian Autonomous Enterprise**: a human-controlled AI command center, agent runtime, and enterprise domain platform built around Clean Architecture, DDD, Ports & Adapters, evidence-first execution, human approval, independent verification, and immutable audit.

## Core safety invariant

`Observe → Understand → Evidence → Plan → Validate → Approve → Execute → Verify → Audit → Learn`

The LLM never writes directly to ERP systems. Delivery channels such as Telegram contain no business rules. Financial execution goes through typed ports, policy gates, approval, draft-only adapters, verification, and audit.

## Included now

- Guardian Command Center API
- Policy engine with fail-closed behavior
- Workflow coordinator
- Segregation of Duties / self-approval prevention
- Idempotency guard
- Hash-chained audit ledger
- Evidence handling contracts
- Bank reconciliation vertical slice
- Draft-only ERP adapter
- Independent post-action verifier
- Telegram delivery adapter boundary
- Enterprise domain catalog
- Docker / Docker Compose
- GitHub Actions CI with manual `workflow_dispatch`
- Automated tests

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
uvicorn guardian.api.app:app --reload
```

Open: `http://127.0.0.1:8000/docs`

## Docker

```bash
docker compose up --build
```

## Financial workflow

1. `POST /v1/finance/bank-reconciliation` with `X-Actor-Id`.
2. The workflow moves to `waiting_approval`.
3. A different authorized actor approves it.
4. Execution creates an ERP **draft only**.
5. An independent verifier reads back actual state.
6. Audit events are chained and available for inspection.

## Repository strategy

- `main` — protected, releasable code only.
- `develop` — integration branch for approved feature work.
- `feature/*` — isolated implementation branches.
- `fix/*` — non-emergency fixes.
- `hotfix/*` — urgent production corrections branched from `main`.
- `release/*` — stabilization only when a formal release window is needed.

Normal flow: `feature/* → develop → main` through Pull Requests and green CI.

## Live integrations

The default implementation intentionally uses an in-memory ERP adapter to prevent accidental production financial writes. Real Odoo, Telegram, model-provider, storage, and workflow adapters must be added behind the ports in `guardian/core/ports.py`, with credentials supplied only via environment variables or deployment secret stores.

## Cost strategy

The baseline avoids mandatory paid infrastructure. It runs locally or on a small container service and can start with in-process adapters. PostgreSQL/object storage/durable workflow engines can be introduced only when workload and reliability requirements justify them.
