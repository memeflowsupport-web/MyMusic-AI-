# Database migrations

Migrations in this directory are explicit PostgreSQL SQL scripts and are **not** run automatically by the API.

Before enabling authentication in a production environment:

1. Back up the database.
2. Apply `001_create_users.sql` to the configured PostgreSQL database using your database's migration/SQL console.
3. Apply `002_generation_job_owner.sql` to add the nullable owner reference to existing generation jobs.
4. Verify the `users` table and unique email constraint exist.
5. Set `AUTH_SECRET_KEY` to a unique random secret of at least 32 characters in the hosting provider's secret environment settings. Never commit it to Git.
6. Set `AUTH_ENABLED=true` only after registration rate limits, monitoring, and database backups are in place.

`AUTH_ENABLED` defaults to false and the auth endpoints return HTTP 503 until both the feature flag and a sufficiently long secret are configured. Generation and track routes remain separately disabled in production.

The current SQL migration targets PostgreSQL. Local development can continue to use SQLAlchemy's development-only table creation.
