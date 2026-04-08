# Execution Summary (2026-04-08)

## Stage
Execution stage for real provider adapter upgrade.

## Completed
- Replaced provider adapter contract from generic `/tasks` style to real provider lifecycle:
  - Vast.ai: `POST /bundles/`, `PUT /asks/{offer_id}/`, `GET/DELETE /instances/{id}/`
  - Runpod: GraphQL `gpuTypes` + REST `/pods` lifecycle
- Added robust provider mapping logic:
  - offer/gpu resolution from quote snapshot or provider query fallback
  - normalized status mapping to worker state machine
  - cancel + cleanup + result collection for both providers
  - runtime/cost extraction and artifact generation for delivery chain continuity
- Updated deployment scripts to enforce real path defaults during live switch.
- Updated preflight checker to validate real Vast + Runpod paths (including Runpod GraphQL).
- Added/updated automated tests for real adapter contracts.

## In Progress
- Final live server switch validation with real keys (blocked by missing Runpod key in current environment).

## Pending
- Inject production keys and run one end-to-end live task on `multi_provider_live`.
- Update online acceptance report with real provider execution evidence.

## Risk / Assumptions
- Current environment still lacks `STABLEGPU_RUNPOD_API_KEY`; live Runpod verification cannot pass until key is provided.
- `provider_ready_state_is_success=true` is enabled to keep lifecycle stable for MVP dispatch; this can be tightened in next round for strict “job-finished” semantics.

## Next Step
- Run on server:
  - `bash infra/deploy/switch_to_live_adapter.sh`
  - `python3 infra/deploy/provider_preflight.py`
  - `python3 -m apps.worker.worker.main --limit 1`
- Then record final evidence in `.ai/online-acceptance-report-2026-04-08.md`.
