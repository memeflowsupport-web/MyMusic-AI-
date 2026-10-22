# MyMusic AI — Initial Architecture

## Goal
Build the product and supporting infrastructure incrementally, prioritizing components that can be developed and tested without paid APIs. Zero software-license cost does not mean unlimited compute, storage, electricity, or bandwidth.

## Component boundaries
1. Frontend: public UI only; no secrets or privileged credentials.
2. API: validates requests, applies rate limits and authorization, creates generation jobs.
3. Database: users, track metadata, job state, model version and audit events.
4. Storage: generated audio and permitted training assets; access policies and retention.
5. Queue/worker: claims jobs safely, records progress, retries transient errors and avoids duplicate processing.
6. Model runtime: isolated interface so the model can be swapped without rewriting the product.
7. Operations: health checks, logs, backups, usage metrics and restore tests.

## First implementation decisions
- Keep the initial frontend framework-free.
- Use PostgreSQL for a self-hostable relational database.
- Use a Python API framework when backend implementation begins.
- Define storage and model-runner interfaces before binding to a provider.
- Do not put generated audio, datasets, model weights, credentials or large binary assets in Git.
- GitHub Pages is static hosting, not a backend or AI runtime; review current terms before public launch.
- Avoid adding authentication or payments until server-side security can be implemented and tested.

## Model-development guardrails
- Choose a model only after reviewing architecture, inference requirements, fine-tuning support, model license and commercial rights.
- Training data must have documented permissions for the intended training and distribution.
- Track dataset provenance and model checkpoints.
- Start with small, reproducible experiments and evaluate output quality before scaling.
- Do not advertise text-to-music or vocal generation as working until tests verify it.

## Phone-first workflow
The owner can manage code and review commits through GitHub mobile. Code changes can be committed through GitHub's web interface/API. Training runs on appropriate compute infrastructure, not on GitHub.
