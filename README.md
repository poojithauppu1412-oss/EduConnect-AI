# EduConnect AI

**One Platform. Every Opportunity. Smarter Guidance.**

EduConnect AI is being built as a source-backed opportunity discovery and career-guidance platform. Work is being delivered in phases so each feature can be implemented and verified before it is presented as available.

## Phase 1: project foundation

- React, TypeScript, and Vite frontend
- FastAPI backend with OpenAPI documentation at `/docs` and `/redoc`
- PostgreSQL connectivity through the Replit-provided `DATABASE_URL`
- Environment-based settings; secrets are not stored in the repository
- API liveness and database readiness checks

## Phase 2: database schema

- SQLAlchemy models define the 28 application tables.
- Alembic applies reviewed schema migrations explicitly.

## Phase 3: authentication

- Replit-managed Clerk provides sign-up, sign-in, and browser sessions.
- FastAPI verifies Clerk session cookies before returning authenticated data.
- Local user records are linked to verified Clerk email identities on first profile access.
- New accounts receive the standard `USER` role; administrative roles are never granted during public sign-up.

## Phase 4: user profile

- `/api/v1/profile` creates, reads, and updates the signed-in user's profile in PostgreSQL.
- Profile information includes education, skills, certifications, experience, career preferences, and exam preferences.
- Profile completion is calculated from saved fields; profile updates cannot target another user.
- The frontend provides an editable, responsive profile form with explicit save and error states.

## Phases 5–6: opportunity discovery

- Opportunity search supports full-text queries, filters, sorting, and pagination.
- Administrative create, update, and archive endpoints require an administrative role. Public listings require source and official links, a verification time, and active status.
- The signed-in dashboard includes discovery, source-linked details, and user-scoped saved opportunities.
- No sample opportunity records are seeded or displayed. The dashboard stays empty until reviewed listings exist.

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

## Current product status

Phases 1–6 are implemented in development. No opportunity records are currently seeded, and no scheduled ingestion, recommendations, AI answers, or notifications are active. The app does not display fabricated opportunities or chatbot responses. Source-backed listings appear only after review; scheduled ingestion and production readiness have not been verified.