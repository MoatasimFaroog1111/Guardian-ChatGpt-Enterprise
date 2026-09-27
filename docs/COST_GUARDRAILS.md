# Cost Guardrails

1. Keep Fly `min_machines_running = 0` until latency requirements justify an
   always-on Machine.
2. Keep large files out of Postgres; put them in R2 and persist hashes/keys.
3. Use Upstash only for short-lived coordination and idempotency.
4. Route ordinary text/accounting tasks to CPU or external LLM APIs; invoke GPU
   only for workloads that require a self-hosted model.
5. Prefer Modal free monthly compute credits during development; compare actual
   RunPod per-second cost for sustained inference before switching.
6. Add explicit per-workflow token/GPU budgets before autonomous GPU execution.
7. Set provider budget alerts before adding paid credentials.
8. When the backend stays busy for most of the month, compare its measured Fly
   bill with a Hetzner VPS + self-hosted Coolify and migrate only when the
   steady-state saving exceeds the operational burden.
