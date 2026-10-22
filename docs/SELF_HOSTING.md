# Self-hosting guide (planning)

## What can be free
The source code and open-source software licences can cost nothing. Development can start locally or in a suitable free development environment. The static frontend can be published on an eligible free static host.

## What still needs resources
A public backend requires a machine that stays reachable, network access, storage, backups, monitoring, and security updates. AI inference requires CPU/GPU memory and processing time. Training a high-quality music model from scratch may require substantial GPU resources. No software architecture can remove those physical requirements.

## Initial development
1. Run the FastAPI backend locally in a Python environment.
2. Use SQLite for the first prototype; use PostgreSQL when a persistent self-hosted database is available.
3. Keep `.env`, database files, generated audio, datasets, and model weights out of Git.
4. Test endpoints and restore procedures before any public deployment.

## Production checklist (not yet complete)
- HTTPS and trusted reverse proxy.
- Authentication and per-user authorization.
- Request throttling and abuse protection.
- Database migrations, backups, and restore drills.
- Private audio storage and expiring download links.
- Background worker with retry/idempotency strategy.
- Model licence and dataset provenance review.
- Secrets management, structured logs, monitoring, and incident plan.
- Resource quotas and an honest service-availability policy.

This project does not promise unlimited or permanently free compute, storage, bandwidth, or domain registration.
