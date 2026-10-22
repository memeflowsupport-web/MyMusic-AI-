# Temporary free-GPU experiment (Google Colab)

This is an experimental bridge for testing the existing MyMusic AI ACE-Step adapter without renting a GPU. Open the notebook in this repository:

- `notebooks/MyMusic_AI_Free_GPU_Experiment.ipynb`

## How to use

1. Open the notebook in Google Colab and select **Runtime → Change runtime type → GPU**, if free GPU access is offered.
2. Run cells in order. The first installation/model download can take a while and requires disk space.
3. Enter a long, temporary API key when prompted. Do not commit or share it.
4. Wait for ACE-Step to initialize, then wait for the Cloudflare quick-tunnel URL.
5. In the **backend host's secret/environment settings**, set:
   ```env
   MUSIC_MODEL_BACKEND=ace_step
   ACE_STEP_BASE_URL=https://YOUR-TEMPORARY-TUNNEL.trycloudflare.com
   ACE_STEP_API_KEY=THE_SAME_TEMPORARY_KEY
   ACE_STEP_TIMEOUT_SECONDS=900
   ACE_STEP_POLL_SECONDS=2
   DEFAULT_GENERATION_DURATION_SECONDS=30
   ```
6. Restart the backend so it reads the new settings. Keep generation endpoints in development-only mode while authentication, quotas, and abuse controls are incomplete.
7. Run a test from a controlled development environment and verify that a non-empty WAV file is actually returned and saved.

## Important limitations and security

- Free GPU availability, session length, and quotas are controlled by Colab and are not guaranteed. This is not an always-on hosting plan.
- A quick tunnel URL is public and temporary. This notebook configures ACE-Step API-key authentication; nevertheless, use only for controlled tests, rotate the temporary key afterward, and stop the tunnel/runtime when finished.
- Never place the key in frontend JavaScript, source control, screenshots, or public messages. Configure it only as a backend secret.
- The current adapter expects the documented ACE-Step async API and the returned audio URL to remain on the configured model-server host. Verify compatibility with the current ACE-Step release before relying on it.
- The backend health field `configured_unverified` only means the adapter is selected; it is not proof of successful generation.
- Do not make this a public user-facing service. A temporary notebook can disconnect at any time, and MyMusic AI's production generation endpoints intentionally remain disabled until production security controls are implemented.

## Official references

- ACE-Step install guide: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INSTALL.md
- ACE-Step API reference: https://ace-step.github.io/ACE-Step-1.5/en/API
- Google Colab FAQ: https://research.google.com/colaboratory/faq.html
