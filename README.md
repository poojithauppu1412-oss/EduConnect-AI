# EduConnect AI

**One Platform. Every Opportunity. Smarter Guidance.**

EduConnect AI is being built as a source-backed opportunity discovery and career-guidance platform. Work is being delivered in phases so each feature can be implemented and verified before it is presented as available.

## Phase 1: project foundation

- React, TypeScript, and Vite frontend
- FastAPI backend with OpenAPI documentation at `/docs` and `/redoc`
- PostgreSQL connectivity through the Replit-provided `DATABASE_URL`
- Environment-based settings; secrets are not stored in the repository
- API liveness and database readiness checks

## Run in Replit

The workspace provides `DATABASE_URL` through its environment. Start the web application with:

```bash
npm run dev
```

The preview runs on port `5000`. Vite proxies `/api` requests to FastAPI on port `8000`.

## Local setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL` to a PostgreSQL instance you control.
2. Install frontend dependencies with `npm install`.
3. Install Python dependencies with `uv sync`.
4. Run `npm run dev`.

Do not commit `.env`. Use Replit Secrets for credentials in Replit.

## Checks

```bash
npm run typecheck
npm run build
npm test
```

## Database migrations

SQLAlchemy models define the database schema, and Alembic manages development migrations. After changing models, create and review a migration before applying it:

```bash
npm run db:revision -- -m "describe the schema change"
npm run db:upgrade
npm run db:current
```

Migrations run only when invoked explicitly; the web server does not alter the schema at startup. Replit-managed production schema changes are applied through the Publish flow.

The current phase establishes schema and migrations. Account flows, opportunity APIs, search, ingestion, AI, and notifications are not yet implemented.