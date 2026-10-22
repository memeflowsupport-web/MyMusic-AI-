# Music model evaluation

## First candidate: ACE-Step 1.5

ACE-Step 1.5 is the first candidate to evaluate for MyMusic AI because its project advertises full-song generation, vocal and instrumental workflows, and an MIT licence. Official project information: https://ace-step.github.io/ACE-Step-1.5/ and https://github.com/ace-step/ACE-Step-1.5.

This is a candidate, not an integration or a guarantee of production readiness. Before shipping, verify the exact model checkpoint and its licence, supported hardware, memory use, model download size, dependency requirements, output quality, latency, and commercial terms against the official release artifacts. Do not use a third-party mirror as the source of model weights.

## Hardware and cost reality

Open weights can remove per-song API charges, but do not remove compute, electricity, storage, network, and maintenance costs. A hosted GPU can still cost money even when the model itself is free. We should benchmark on the cheapest suitable hardware before committing to a hosting design.

## Integration plan

1. Pin the exact official model release and record its licence and checksum.
2. Keep model dependencies isolated from the FastAPI API environment where practical.
3. Implement the MusicModelRunner adapter and a health/readiness check.
4. Generate a small, non-commercial test set and measure duration, latency, memory, and failures.
5. Verify generated files can be stored and played back end-to-end.
6. Do not expose public generation until authentication, rate limits, queue limits, and cost controls exist.

## Important distinction

MyMusic AI's own infrastructure and orchestration are being built in this repository. The selected open-weight model remains a third-party component with its own licence and technical limitations; this is not the same as training our own foundation model from scratch. Training our own model would require a suitable licensed dataset, substantial compute, evaluation, and a separate research plan.
