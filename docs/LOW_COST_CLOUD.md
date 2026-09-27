# Low-Cost Cloud Architecture

## Default production path

```text
Browser / Telegram
       |
Cloudflare Pages
       |
Cloudflare Worker (edge policy + secret injection)
       |
Fly.io container (FastAPI)
       |
       +--> Neon PostgreSQL
       |      audit + workflow state + evidence metadata
       |
       +--> Upstash Redis REST
       |      idempotency / short-lived coordination
       |
       +--> Cloudflare R2
       |      documents, large evidence, model artifacts
       |
       +--> Modal / RunPod
              GPU only when an AI task requires it
```

## Cost rule

Never keep GPU capacity warm by default. Start with one small autoscaling Fly
Machine and set `min_machines_running = 0`. Use Neon scale-to-zero, the Upstash
free tier, and R2 Standard free allowance. If steady CPU usage makes Fly more
expensive than a small VPS, move the same Docker image to Hetzner + self-hosted
Coolify.

## Durable data ownership

- Neon is the system of record for workflow state and audit metadata.
- R2 stores large immutable objects. Store only object keys/hashes in Postgres.
- Upstash is not the accounting source of truth. It is disposable coordination
  infrastructure.
- GPU providers never own enterprise state.
- Cloudflare Worker never contains domain or accounting rules.

## One-secret production configuration

Fly.io requires only one application secret:

`GUARDIAN_CONFIG`

It is a JSON object that can contain all sensitive runtime values:

```json
{
  "DATABASE_URL": "postgresql://...",
  "GUARDIAN_EDGE_SECRET": "...",
  "UPSTASH_REDIS_REST_URL": "https://...",
  "UPSTASH_REDIS_REST_TOKEN": "...",
  "R2_ENDPOINT_URL": "https://...",
  "R2_ACCESS_KEY_ID": "...",
  "R2_SECRET_ACCESS_KEY": "...",
  "R2_BUCKET": "guardian-enterprise"
}
```

The runtime first reads `GUARDIAN_CONFIG`, then falls back to individual
environment variables for local development. This keeps Fly configuration to
one secret while preserving provider independence.

Cloudflare Worker still stores only its matching `EDGE_SHARED_SECRET`.

## Cloudflare

The Worker is intentionally thin. It performs network boundary duties only:
CORS, route forwarding and edge-secret injection. It does not approve, classify,
match, post, or verify financial transactions.

Pages is static and has no paid runtime requirement. Before deployment set the
GitHub repository variable `GUARDIAN_API_BASE` to the deployed Worker origin.

## Neon

Set `DATABASE_URL` inside `GUARDIAN_CONFIG` to the pooled Neon connection
string with TLS. The runtime creates the minimal schema automatically;
`deploy/neon/schema.sql` is also provided for explicit provisioning/review.

## Upstash

Add `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` to the same
`GUARDIAN_CONFIG` JSON object when Upstash is enabled.

## R2

Add the R2 endpoint and bucket-scoped credentials to `GUARDIAN_CONFIG` when
R2 is enabled.

## Fly.io

`fly.toml` is configured for a 512 MB shared CPU Machine, autostart enabled,
autostop enabled, and zero minimum running Machines. Pick the closest practical
region to the database/users before production.

## Hetzner + Coolify fallback

Use `deploy/coolify/docker-compose.yml` on a small Hetzner Cloud server when
the service becomes continuously busy. Self-hosted Coolify is free software;
the VPS remains the billable component.

## GPU

`GPUProviderRouter` supports Modal and RunPod. Configure either provider.
Modal is selected first when both are configured; callers may explicitly select
a provider. GPU use is synchronous in v0.2 and should move behind a durable job
queue before long-running production inference.
