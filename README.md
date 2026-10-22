# MyMusic AI

An independent music-AI and infrastructure project. The long-term goal is to develop and operate our own music-generation model and supporting services, minimizing dependence on paid third-party music-generation APIs.

## Current status

- Responsive static landing page exists; it does not generate audio.
- A Python/FastAPI backend foundation exists with generation-job and track models, local audio storage, a background worker, and automated tests.
- A model-runner interface is implemented. The default runner explicitly refuses to fake output when no model is configured.
- An ACE-Step 1.5 HTTP adapter is implemented and covered by mocked integration tests.
- **A live model is not installed or connected yet.** Selecting the ACE-Step backend only selects the adapter; it does not prove the model is reachable.
- Generation job endpoints intentionally remain development-only (HTTP 503 outside development) until production authentication and abuse controls are implemented.

## Project principles

- Phone-first project management through GitHub.
- Minimize ongoing costs and external dependencies, while acknowledging that real model inference requires suitable compute and storage.
- Use open-source components where sensible, after reviewing their licenses and usage terms.
- Keep model serving, database, and storage portable.
- Use only training data with documented rights suitable for the intended use.
- Never commit passwords, access tokens, private keys, or production secrets.
- Make feature status and limitations clear; never pretend a song was generated if the model did not return audio.

## Architecture

- Frontend: static HTML/CSS/JavaScript landing page.
- Backend: Python API service in `backend/`.
- Database: SQLAlchemy models, with SQLite for local development and PostgreSQL supported by configuration.
- Audio storage: local storage adapter with generated keys and path-traversal protections.
- Generation: queue/worker pattern with job state tracking.
- Model integration: explicit runner interface, unconfigured runner, and ACE-Step HTTP adapter.
- Tests: GitHub Actions workflow runs the backend test suite on pushes to `main` and pull requests.

## Important docs

- [Backend setup](backend/README.md)
- [Worker operations](backend/WORKER.md)
- [Self-hosting overview](docs/SELF_HOSTING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Music model evaluation](docs/MUSIC_MODEL_EVALUATION.md)
- [Connect a self-hosted ACE-Step model server](docs/MODEL_SERVER_SETUP.md)

## Development quick start

From the `backend/` directory:

```bash
python -m venv .venv
# Activate the virtual environment for your operating system
python -m pip install -e ".[dev]"
python -m pytest -q
uvicorn app.main:app --reload
```

Use `backend/.env.example` as a reference for local configuration. Never commit a real `.env` file or production secrets.

## Production warning

The backend and adapter foundations are not a production-ready public music-generation service yet. Before opening generation to users, implement and test authentication, authorization, per-user quotas/rate limits, abuse controls, deployment secrets, persistent production storage, monitoring, backups, and operational recovery. Do not remove the development-only endpoint guard as a shortcut.

Static hosting can serve the frontend, but it cannot run the Python API or a GPU music model. A real generation deployment needs a separate backend and a compatible model server with enough compute, memory, storage, and generation time.

## Licensing

No project-wide software or model license has been selected yet. Do not assume the project or future model is open for reuse until a license is added. Review third-party dependencies, model weights, and datasets individually before commercial use.
