# MyMusic AI — Production Readiness Checklist

This checklist reflects the current prototype. It is intentionally conservative: the production API disables generation and track-library routes until authentication and abuse controls exist. The music model is not installed or connected, and the application must not claim that queued jobs are completed audio.

## Current known state

- [ ] Authentication and per-user authorization for jobs, tracks, and audio.
- [ ] Rate limits and request-size limits for expensive generation requests.
- [ ] Persistent production database with versioned migrations and backups. The current default is local SQLite; do not assume it survives service restarts or instance replacement.
- [ ] Persistent/private audio object storage. Local audio files on an ephemeral service filesystem are not production storage.
- [ ] A deployed worker/queue that claims jobs, retries safely, and marks jobs failed when generation fails.
- [ ] A real model server and checkpoint configured and verified end-to-end. The ACE-Step adapter alone is not the model.
- [ ] Monitoring, error alerts, retention rules, and operational recovery steps.
- [ ] Frontend status messages that clearly distinguish backend reachable, model connected, job queued, and audio generated.
- [ ] Production smoke tests for health, system status, authentication, job creation, track ownership, and audio access.

## Safe deployment rules

1. Keep ENVIRONMENT=production until authentication and abuse controls are implemented and tested.
2. Do not enable public generation routes merely to make the Studio UI appear functional.
3. Do not switch MUSIC_MODEL_BACKEND to ace_step unless a reachable model service has been configured and verified.
4. Use a managed persistent database and private object storage before storing real users' jobs or audio.
5. Use versioned database migrations; do not rely on create_all at production startup.
6. Keep CORS restricted to the deployed frontend origin.
7. API documentation may be disabled in production, but hiding docs is not a substitute for endpoint authentication.

## Recommended order

1. Implement authentication and ownership checks.
2. Provision persistent database/storage and migrations.
3. Add rate limits, job quotas, and safe worker retry behavior.
4. Update the Studio UI to explain production-disabled routes without misleading users.
5. Deploy and test the worker/model integration only when compute and bandwidth are available.
6. Run production smoke tests before enabling generation for users.

This file is a planning checklist, not evidence that any unchecked item has been completed.
