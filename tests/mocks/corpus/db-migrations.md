# PostgreSQL Database User and Schema Migration Policy

Microservices onboarding to PostgreSQL must follow strict environment separation between automated staging CI/CD migrations and change-controlled production DDL operations.

## Staging vs Production Schema Alterations

Staging databases allow automated schema migrations via GitLab CI/CD runners using the dedicated pipeline service account, whereas direct production DDL or table drops require a formal `/demandes` platform change ticket.

```bash
kubectl get jobs -n <namespace> -l component=db-migration
alembic current --verbose
```

## Escalation Criteria for Elevated Grants

Requests for new PostgreSQL roles, `GRANT ALL` privileges, or production schema overrides must escalate to the Data Engineering project with the target database name, environment, and requested grants.
