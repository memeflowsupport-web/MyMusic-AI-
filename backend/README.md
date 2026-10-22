# MyMusic AI API

Initial self-hostable FastAPI + SQLAlchemy foundation. It stores generation requests as queued jobs; **it does not generate audio yet**.

## Local development

Python 3.11 or newer is recommended.

```sh
cd backend
python -m venv .venv
# Activate the environment, then:
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Open `/docs` for interactive API documentation and `/health` for a health check.

The default development database is SQLite so the prototype can run without a separate database server. For a self-hosted PostgreSQL instance, set `DATABASE_URL` in the untracked `.env`, for example `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`. Never commit that value or expose it to frontend JavaScript.

## Endpoints

- `GET /` — service information.
- `GET /health` — API and database health; reports the music engine as not connected.
- `POST /api/v1/generation-jobs` — validates and records a queued job; returns HTTP 202.
- `GET /api/v1/generation-jobs` — lists recent jobs.
- `GET /api/v1/generation-jobs/{job_id}` — fetches a job.

## Important limitations

- No authentication, user isolation, rate limiting, worker, model, or audio storage is implemented yet. Do not expose this prototype publicly as a production service.
- Job creation records a request only; it does not start music generation.
- Development mode creates tables automatically for convenience. Production should use reviewed, versioned migrations.
- Configure explicit trusted CORS origins for the deployment.
- Run tests with `pytest`.
