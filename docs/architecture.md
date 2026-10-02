# Initial architecture

EduConnect AI uses a React + TypeScript + Vite frontend and a Python + FastAPI backend. Vite serves the preview on port `5000` and forwards `/api` traffic to FastAPI on port `8000`. Application code uses relative API paths so the same frontend works behind the Replit preview proxy.

FastAPI reads configuration from environment variables and connects to the Replit-managed PostgreSQL database via `DATABASE_URL`. The readiness endpoint runs a read-only `SELECT 1`. SQLAlchemy models are the schema source of truth, and Alembic applies explicit development migrations.

## Current endpoints

- `GET /api/health/live` — confirms that the API process responds.
- `GET /api/health/ready` — confirms API readiness and PostgreSQL connectivity.
- `/docs` and `/redoc` — generated FastAPI documentation.

The system currently exposes foundation and health checks only. It does not yet provide opportunity, account, ingestion, or AI functionality.