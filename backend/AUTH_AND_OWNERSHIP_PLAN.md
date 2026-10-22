# Authentication and ownership implementation plan

## Current safety boundary

Keep `ENVIRONMENT=production`. Generation-job creation/list/detail, track metadata, and audio endpoints must remain disabled in production until authentication, ownership enforcement, durable persistence, and private audio storage are implemented and tested. Hiding API docs is defense-in-depth only; it is not authorization.

## Recommended implementation sequence

### 1. Persistence and migrations
- Provision a durable PostgreSQL database only after the owner approves any paid plan or billing change.
- Add Alembic migrations and run them explicitly during deployment; do not rely on `Base.metadata.create_all` in production.
- Keep database credentials in Render environment variables, never in Git.
- Decide how existing prototype data is handled before applying schema changes.

### 2. User identity
- Add a `users` table with UUID/string ID, normalized unique email, password hash, and created/updated timestamps.
- Hash passwords with a maintained password-hashing library (for example pwdlib with Argon2); never store plaintext passwords.
- Validate password length and request sizes; return generic login errors to reduce account enumeration.
- Add short-lived signed access tokens with a strong secret from environment configuration, token expiry, and explicit algorithm validation.
- Do not provide a default production signing secret. Fail closed at startup if production auth is enabled without a valid secret.
- Add register, login/token, and current-user endpoints with tests for invalid credentials, duplicate email, expiry, and malformed tokens.

### 3. Resource ownership
- Add a non-null owner foreign key to generation jobs and an ownership relationship from tracks through their jobs.
- Filter list queries by the authenticated user.
- For detail, playback, and audio routes, query by both resource ID and authenticated owner; return 404 for resources belonging to another user.
- Ensure background-worker-created tracks inherit ownership from their generation job.
- Add cross-user tests covering job detail, job lists, track detail, track lists, and audio playback.

### 4. Abuse and operational controls
- Add bounded per-user generation limits and request throttling before connecting a costly model.
- Enforce prompt and duration limits server-side.
- Store generated audio in private durable object storage; do not treat Render's ephemeral filesystem as permanent storage.
- Add audit-safe structured logs that never include passwords, bearer tokens, or signing secrets.
- Document retention, deletion, and backup/restore procedures.

### 5. Release gates
- CI must pass unit and integration tests, including ownership-isolation tests.
- Production database migrations must be verified against a disposable test database before release.
- Keep generation disabled until the model runner, queue/worker, persistent database, private audio storage, and monitoring have each been verified.
- Do not claim audio generation works until an end-to-end test produces and plays a real generated audio file.

## Decisions that require owner approval

- Any paid PostgreSQL or object-storage plan.
- A migration or reset that could affect existing production data.
- Enabling production generation or starting model/GPU workloads.

## References
- FastAPI's official docs explain that disabling OpenAPI/docs is not API security and recommend permission dependencies and password hashing: https://fastapi.tiangolo.com/how-to/conditional-openapi/
- OAuth2/JWT implementation guide: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
