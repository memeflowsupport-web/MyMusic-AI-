# MyMusic AI API

Self-hostable FastAPI + SQLAlchemy foundation for MyMusic AI. The API records generation requests, and a separate polling worker can claim queued jobs, call a model adapter, save returned audio, and create track records. **Real music generation is not connected yet**: the default model runner deliberately fails with a clear error instead of returning fake audio.

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

Open `/docs` for interactive API documentation and `/health` for a health check. The generation-job API is deliberately disabled when `ENVIRONMENT` is not `development` until authentication and abuse controls are implemented.

## Worker

Run the worker in a second terminal from the `backend` directory:

```sh
python -m app.worker
```

It polls the queue and processes one job at a time. Until a real `MusicModelRunner` is configured, queued jobs will become `failed` with a clear explanation. Do not run the worker in production yet: stale-job recovery, durable queue guarantees, and production monitoring are not implemented.

## Configuration

The default development database is SQLite. For a self-hosted PostgreSQL instance, set `DATABASE_URL` in the untracked `.env`, for example `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`. Never commit that value or expose it to frontend JavaScript.

Set `AUDIO_STORAGE_DIR` to choose the local directory for audio files. Local storage is suitable only for development or a single-host prototype; production should use private object storage with access controls and backups.

## Endpoints

- `GET /` — service information.
- `GET /health` — API and database health; the music engine reports as not connected.
- `POST /api/v1/generation-jobs` — validates and records a queued job in development mode.
- `GET /api/v1/generation-jobs` — lists recent jobs in development mode.
- `GET /api/v1/generation-jobs/{job_id}` — fetches a job in development mode.

## Verification

Run the automated backend tests:

```sh
python -m pytest -q
```

A GitHub Actions workflow runs this test command on pushes to `main` and pull requests.

## Not production-ready

Authentication, user isolation, rate limiting, queue limits, stale-job recovery, a real music model, secure audio delivery, and production database migrations remain unfinished. Do not expose generation endpoints publicly. Development mode creates tables automatically for convenience; production should use reviewed, versioned migrations. Configure explicit trusted CORS origins for deployment.
