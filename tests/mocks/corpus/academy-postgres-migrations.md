# Academy: Safe Zero-Downtime PostgreSQL Schema Migrations

This Platform Academy guide walks through expand-and-contract PostgreSQL migrations using Alembic and pgvector without blocking active application connections.

## Pre-Migration Lock Checks

Always verify active locks and current Alembic revision before applying DDL changes in staging or requesting a production change window.

```bash
alembic current --verbose
alembic history --indicate-current
```
