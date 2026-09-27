# Branching and Delivery Policy

## Permanent branches

### `main`
Production/releasable branch. Direct feature development is prohibited.

### `develop`
Integration branch for completed feature branches before promotion to `main`.

## Short-lived branches

- `feature/<scope>-<description>`
- `fix/<scope>-<description>`
- `hotfix/<description>`
- `release/<version>` when release stabilization is needed

## Required gates

Every merge into `develop` or `main` should pass:

1. Ruff/static checks.
2. Unit/integration tests.
3. Architecture/security checks where applicable.
4. Human PR review for financial/execution-affecting changes.
5. No committed secrets.

## Merge policy

Use squash merge for feature/fix branches. Promote `develop` to `main` using an explicit release PR. Financial adapters remain draft-only until their separate production-readiness gate is satisfied.
