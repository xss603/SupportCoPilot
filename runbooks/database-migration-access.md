# Runbook: Database User & Schema Migration Permissions

## Description
Guidelines for onboarding a microservice to PostgreSQL or requesting administrative schema alterations on staging and production environments.

## Policies:
- Direct DDL / schema modification on production databases requires an official platform change ticket (`/demandes`).
- Staging databases allow automated schema migrations via CI/CD runners using the service's dedicated pipeline user.

## Escalation Criteria:
- If a developer requests a new database user, elevated permissions (`GRANT ALL`), or production table drops/alterations, **set `requires_platform_request = true`**.
- Platform request priority should be set to:
  - `high` for production blockers
  - `medium` for staging/dev requests
- The ticket payload must include the target database name, target environment, and requested grants.
