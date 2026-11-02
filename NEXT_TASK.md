# IRC Media Election Center — Next Task

Last updated November 2, 2026.

## Current status

PR #62 deployed with Mike's explicit approval. Independent official General Election watch collector and browser refresh are operational. See PROJECT_STATE.md for exact source contracts, workflow evidence, schedules and legacy boundaries.

## Operation

The GitHub General Election Watch workflow runs independently of ChatGPT. It targets five-minute collection November 3–4 and hourly collection November 5–17. The open page checks every 30 seconds. Do not replace the workflow with a chat reminder or imply continuous instant returns.

County numbers remain withheld until a county source update after November 3 at 7 p.m. Eastern; state numbers remain withheld until 8 p.m. Eastern with a post-release file timestamp. Pre-election vendor values are not election returns.

## New work

No additional feature is authorized at this checkpoint. For a requested operational fix, inspect the new General workflow, its source-specific health, last-good snapshots and current official payload before changing code. Preserve the candidate/date/coverage gates and existing data. Obtain approval before a new deployment unless the active session already authorizes it.

Do not enable the old 67-county General pipeline merely because the new independent watch works. Legacy Primary recovery is separate and currently has a fail-closed coverage protection failure. Do not weaken that gate.

Preserve the Primary archive, all 67 county map geometries, polling source restrictions and markets. No restricted DDHQ ingestion. Do not touch michaelbolack/IRC-Publishing-Suite.
