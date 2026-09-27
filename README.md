# Guardian-ChatGpt-Enterprise

A low-cost, production-oriented implementation of **Guardian Autonomous Enterprise**: a human-controlled AI command center, agent runtime, and enterprise domain platform built around Clean Architecture, DDD, Ports & Adapters, evidence-first execution, human approval, independent verification, and immutable audit.

## Core safety invariant

`Observe → Understand → Evidence → Plan → Validate → Approve → Execute → Verify → Audit → Learn`

The LLM never writes directly to ERP systems. Delivery channels such as Telegram contain no business rules. Financial execution goes through typed ports, policy gates, approval, draft-only adapters, verification, and audit.

## Included now

- Guardian Command Center API
- Policy engine with fail-closed behavior
- Workflow coordinator with durable state port
- Segregation of Duties / self-approval prevention
- Idempotency guard with optional Upstash Redis REST
- Hash-chained audit ledger with optional Neon/PostgreSQL persistence
- Evidence handling contracts
- Cloudflare R2 object-store adapter
- Modal / RunPod on-demand GPU router
- Bank reconciliation vertical slice
- Draft-only ERP adapter
- Independent post-action verifier
- Telegram delivery adapter boundary
- Cloudflare Worker edge gateway
- Cloudflare Pages operator console
- Fly.io scale-to-zero manifest
- Hetzner + Coolify fallback compose file
- Docker / Docker Compose
- GitHub Actions CI and manual deployment workflows
- Automated tests

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
uvicorn guardian.api.app:app --reload
```

Open: `http://127.0.0.1:8000/docs`

## Low-cost production stack

```text
Cloudflare Pages
       |
Cloudflare Worker
       |
Fly.io FastAPI container
  |       |       |
Neon   Upstash    R2
                  |
             Modal / RunPod
             only on demand
```

The same Docker image can move to a Hetzner VPS managed by self-hosted Coolify if
steady CPU usage becomes cheaper there than serverless/container billing.

See:
- `docs/LOW_COST_CLOUD.md`
- `docs/COST_GUARDRAILS.md`

## Financial workflow

1. `POST /v1/finance/bank-reconciliation` with `X-Actor-Id`.
2. The workflow moves to `waiting_approval`.
3. A different authorized actor approves it.
4. Execution creates an ERP **draft only**.
5. An independent verifier reads back actual state.
6. Audit events are chained and available for inspection.

## Repository strategy

- `main` — releasable code only.
- `develop` — integration branch.
- `feature/*` — isolated feature work.
- `fix/*` — non-emergency fixes.
- `hotfix/*` — urgent production corrections.
- `release/*` — stabilization when needed.

Normal flow: `feature/* → develop → main` through Pull Requests and green CI.

## Production secrets

No production secret belongs in Git. Use Fly/Cloudflare/GitHub provider secret
stores. The backend can optionally require `GUARDIAN_EDGE_SECRET`, while the
Cloudflare Worker injects the matching secret so mutation traffic enters through
the edge gateway.

## ERP safety

The default ERP implementation remains in-memory and draft-only. A real Odoo
adapter must implement the existing port and pass production-readiness tests
before it is enabled.
