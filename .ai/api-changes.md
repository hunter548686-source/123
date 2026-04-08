# API Changes (2026-04-08)

## Summary
This round moved provider integration from generic mock-style task paths to real provider contracts:
- Vast.ai: `bundles -> asks -> instances`
- Runpod: `GraphQL gpuTypes -> REST pods`

## Config Defaults Updated
- `STABLEGPU_VAST_AI_SUBMIT_PATH=/asks/{offer_id}/`
- `STABLEGPU_VAST_AI_STATUS_PATH_TEMPLATE=/instances/{external_task_id}/`
- `STABLEGPU_VAST_AI_CANCEL_PATH_TEMPLATE=/instances/{external_task_id}/`
- `STABLEGPU_VAST_AI_RESULT_PATH_TEMPLATE=/instances/{external_task_id}/`
- `STABLEGPU_VAST_AI_CLEANUP_PATH_TEMPLATE=/instances/{external_task_id}/`
- `STABLEGPU_RUNPOD_GRAPHQL_URL=https://api.runpod.io/graphql`
- `STABLEGPU_RUNPOD_OFFERS_PATH=/gpu-types` (kept for compatibility, GraphQL is used for offers)
- `STABLEGPU_RUNPOD_SUBMIT_PATH=/pods`
- `STABLEGPU_RUNPOD_STATUS_PATH_TEMPLATE=/pods/{external_task_id}`
- `STABLEGPU_RUNPOD_CANCEL_PATH_TEMPLATE=/pods/{external_task_id}/stop`
- `STABLEGPU_RUNPOD_RESULT_PATH_TEMPLATE=/pods/{external_task_id}`
- `STABLEGPU_RUNPOD_CLEANUP_PATH_TEMPLATE=/pods/{external_task_id}`
- `STABLEGPU_PROVIDER_READY_STATE_IS_SUCCESS=true`

## Provider Adapter Behavior Changes
- Vast adapter now:
  - posts to `/bundles/` for offers
  - resolves `offer_id` from quote/raw payload or fresh offers
  - creates instances via `PUT /asks/{offer_id}/`
  - uses instance lifecycle for status/cancel/cleanup/result
- Runpod adapter now:
  - fetches GPU offers via GraphQL `gpuTypes`
  - resolves `gpuTypeId` from quote/raw payload or fresh offers
  - creates pods via `POST /pods`
  - uses pod lifecycle for status/cancel/cleanup/result

## Deployment Script Changes
- `infra/deploy/switch_to_live_adapter.sh` now force-upserts all provider contract paths to avoid stale `/tasks` routes in old `.env`.
- `infra/deploy/install_linux.sh` now writes the same contract defaults when initializing env.
- `infra/deploy/provider_preflight.py` now validates:
  - Vast bundles query (POST)
  - Runpod REST auth + GraphQL `gpuTypes` query

## Tests Updated
- `apps/api/tests/test_provider_marketplace.py`
  - Added Vast real-contract lifecycle test.
  - Added Runpod GraphQL+REST lifecycle test.
  - Kept generic remote adapter contract test.
