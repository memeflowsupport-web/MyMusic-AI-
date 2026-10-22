# Background worker

The worker polls queued jobs and conditionally claims them before processing. It stores output under an opaque local storage key and creates a Track record only when a model runner returns non-empty audio and a positive duration.

## Run locally

From backend/, install dependencies with `pip install -e ".[dev]"`. Run the API in one terminal with `uvicorn app.main:app --reload`, and the worker in another with `python -m app.worker`.

The API and worker must use the same database and audio storage directory. Set `AUDIO_STORAGE_DIR` in the environment or configure `audio_storage_dir` in `.env`.

## Current limitation

The default runner is intentionally unconfigured. It fails jobs with a clear message rather than returning fake audio. No music model is installed or integrated yet. Implement MusicModelRunner only after selecting a model whose licence permits the intended use.

Local disk storage is for development and single-machine testing, not multi-instance production. Production needs private object storage, authentication and authorization, request limits, monitoring, backups, retention rules, and a reliable queue/worker deployment. The generation API now returns HTTP 503 outside development until authentication and abuse controls are configured.
