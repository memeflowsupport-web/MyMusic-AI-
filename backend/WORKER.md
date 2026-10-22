# Background worker and ACE-Step connection

The worker polls queued jobs, claims them conditionally, calls the configured model runner, stores output under an opaque local key, and creates a Track only for non-empty audio with a positive duration.

## Run the API and worker locally

From `backend/`:

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

In another terminal, run:

```bash
python -m app.worker
```

The API and worker must use the same database and audio storage directory. Copy `.env.example` to `.env` and configure `DATABASE_URL` and `AUDIO_STORAGE_DIR` as needed.

## Connect a self-hosted ACE-Step 1.5 server

MyMusic AI now has an HTTP adapter for the documented ACE-Step asynchronous API. It does not install or host the model itself. Install ACE-Step on a machine with suitable compute, start its API on a private network, then set these variables in MyMusic AI's backend environment:

```dotenv
MUSIC_MODEL_BACKEND=ace_step
ACE_STEP_BASE_URL=http://127.0.0.1:8001
ACE_STEP_API_KEY=your-secret-if-configured-on-ACE-Step
ACE_STEP_TIMEOUT_SECONDS=900
ACE_STEP_POLL_SECONDS=2
DEFAULT_GENERATION_DURATION_SECONDS=30
AUDIO_STORAGE_DIR=./audio_storage
```

If ACE-Step is on a different machine, replace `127.0.0.1` with its private reachable address. Do not expose the model service publicly without network restrictions and API-key authentication. Use the same `DATABASE_URL` for the API and worker. Start the ACE-Step API using its official instructions: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INSTALL.md

The adapter submits a `/release_task`, polls `/query_result`, and downloads the resulting WAV through `/v1/audio`. It requests one track at a time and uses the configured default duration (clamped to the model's documented 10–600 second range). Instrumental requests add an explicit no-vocals instruction; actual adherence depends on the model.

## Current limitations and safety

- Default `MUSIC_MODEL_BACKEND=unconfigured` deliberately refuses to fake audio. Change it to `ace_step` only after the ACE-Step service is running.
- This connection has not yet been verified against a running model instance, and no actual song has been generated from this repository yet.
- Generation endpoints return HTTP 503 outside development because authentication and abuse controls are not implemented.
- Local disk storage is for development/single-machine testing. Production needs authenticated users, per-user ownership, rate limits/quotas, private object storage, database migrations, monitoring, backups, retention rules, and a reliable queue.
- If the worker process is killed after claiming a job, that job may remain `running`. An operator can call `fail_stale_running_jobs(session_factory, stale_after_seconds=3600)` from `app.worker` to mark sufficiently old running jobs as failed. First stop all workers and confirm no generation is still active; recovery is deliberately manual to avoid interrupting a slow but healthy model request. The caller should use the same database as the worker.
- Verify the model version, checkpoint and license for your intended use. See `docs/MUSIC_MODEL_EVALUATION.md`.
