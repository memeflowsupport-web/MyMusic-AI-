# Connecting the self-hosted ACE-Step music engine

MyMusic AI's backend includes an ACE-Step HTTP adapter, but it does **not** bundle model weights or host a GPU. A separate machine must run ACE-Step 1.5 and be reachable from the backend.

## 1. Choose a machine

ACE-Step's official installation guide currently lists Python 3.11–3.12, recommends a CUDA GPU, supports other backends/CPU with performance trade-offs, and estimates about 10 GB of disk for core models. It lists 4 GB VRAM for DiT-only mode and 6 GB for LM + DiT; more memory improves model choices and performance. Check the official docs before provisioning: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INSTALL.md

Do not assume a free serverless web host can run the model. The model server needs compatible compute, persistent model storage, and enough time/memory to generate audio.

## 2. Install and launch ACE-Step

Follow the official instructions in the ACE-Step 1.5 repository. On a supported Linux machine, the project documents installation with `uv sync` and launching its REST API with `uv run acestep-api`. The API normally listens on port 8001.

Official API reference: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md

For production, enable ACE-Step API-key authentication and use a long random secret. Keep the model API private to the backend network where possible. Do not expose an unauthenticated model API to the public internet.

## 3. Configure MyMusic AI backend

Set these environment variables on the backend host (do not commit real secrets to Git):

```env
MUSIC_MODEL_BACKEND=ace_step
ACE_STEP_BASE_URL=http://YOUR_PRIVATE_MODEL_HOST:8001
ACE_STEP_API_KEY=REPLACE_WITH_THE_SAME_SECRET_CONFIGURED_ON_ACE_STEP
ACE_STEP_TIMEOUT_SECONDS=900
ACE_STEP_POLL_SECONDS=2
DEFAULT_GENERATION_DURATION_SECONDS=30
```

Replace the example host and secret with your actual private model-server address and API key. The API key must match what the ACE-Step server expects. Keep it in the deployment provider's secret/environment-variable settings, not in browser code or a checked-in `.env` file.

The backend's health response reports `configured_unverified` when `MUSIC_MODEL_BACKEND=ace_step`. This means the adapter is selected; it does **not** prove that the model server is reachable or that a real song can be generated.

## 4. Verify before enabling users

1. Start ACE-Step and wait for its model initialization/download to finish.
2. From the backend host, verify that the private model server's health endpoint responds.
3. Confirm the configured API key works against the model server.
4. Run a test generation and confirm a non-empty WAV file is saved and attached to a successful track record.
5. Check timeout, failure, and disk-space behavior in logs.
6. Keep the MyMusic AI generation endpoints in development-only mode until authentication, per-user quotas/rate limits, authorization, and abuse controls are implemented and tested.

## Current safety boundary

The MyMusic AI generation-job endpoints deliberately return HTTP 503 outside development mode because production authentication and abuse controls are not yet complete. Do not remove that guard merely to make production requests work. Finish and test those controls first.

The model adapter and automated tests verify the integration contract with mocked responses; they are not proof of a live model deployment. No model weights are stored in this repository, and this repository alone cannot generate real audio until a compatible ACE-Step service is installed and configured.
