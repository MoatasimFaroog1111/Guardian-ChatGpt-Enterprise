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

## Secrets

Do not put production credentials in GitHub files. Use provider secret stores:

- Fly secrets: `DATABASE_URL`, Upstash, R2, edge secret and model credentials.
- Cloudflare Worker secret: `EDGE_SHARED_SECRET`.
- GitHub Actions secrets: deployment tokens only.
- Pages contains no private token.

Use the same random value for Fly `GUARDIAN_EDGE_SECRET` and Worker
`EDGE_SHARED_SECRET`. This blocks direct mutation calls to the backend while
keeping `/health` available to the platform.

## Cloudflare

The Worker is intentionally thin. It performs network boundary duties only:
CORS, route forwarding and edge-secret injection. It does not approve, classify,
match, post, or verify financial transactions.

Pages is static and has no paid runtime requirement. Before deployment set the
GitHub repository variable `GUARDIAN_API_BASE` to the deployed Worker origin.

## Neon

Set `DATABASE_URL` to the pooled Neon connection string with TLS. The runtime
creates the minimal schema automatically; `deploy/neon/schema.sql` is also
provided for explicit provisioning/review.

## Upstash

Set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`. The adapter
uses REST commands rather than a persistent Redis socket, which fits serverless
and low-idle-cost deployments.

## R2

Create a private bucket and use an R2 API token limited to that bucket. Configure
the S3-compatible endpoint and credentials from `.env.example`.

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
