# Guardian Autonomous Enterprise — Implementation Contract

Control flow: Observe → Understand → Evidence → Plan → Validate → Approve → Execute → Verify → Audit → Learn.

## Hard invariants
- Delivery adapters contain no business rules.
- Domain code imports no vendor SDKs.
- Financial writes require approval and are draft-only by default.
- Requester and approver must differ.
- Every execution is independently read back and verified.
- Audit records are hash-chained and append-only through the application API.
- Idempotency keys prevent duplicate external effects.
- Unknown intents fail closed.

## Cost profile
Default runtime is one small Python service + SQLite volume. PostgreSQL, object storage, vector DB, model providers, Telegram, Odoo, GitHub and durable workflow engines are optional adapters. This keeps the baseline near-zero infrastructure cost while retaining migration seams for production scale.
