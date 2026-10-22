-- Migration 002: attach generation jobs to account owners.
-- Existing jobs remain owner_id NULL and are visible only to anonymous development requests.
-- Apply only after 001_create_users.sql; back up the database first.
BEGIN;
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS owner_id VARCHAR(36);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_generation_jobs_owner_id_users'
    ) THEN
        ALTER TABLE generation_jobs
        ADD CONSTRAINT fk_generation_jobs_owner_id_users
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS ix_generation_jobs_owner_id ON generation_jobs(owner_id);
COMMIT;
