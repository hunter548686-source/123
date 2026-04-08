# Deploy Notes (Self-Hosted)

## Online Endpoint
- Main: `https://gpu.144.202.58.159.sslip.io`
- Health: `https://gpu.144.202.58.159.sslip.io/api/health`
- Admin: `https://gpu.144.202.58.159.sslip.io/admin`
- API docs: `https://gpu.144.202.58.159.sslip.io/docs`

## Server Runtime
- Host: `144.202.58.159`
- Repo path: `/opt/stablegpu/repo`
- Env file: `/opt/stablegpu/repo/.env`
- Services:
  - `stablegpu-api.service`
  - `stablegpu-web.service`
  - `stablegpu-worker.service`

## Live Adapter Switch Procedure
1. Set keys:
   - `STABLEGPU_VAST_AI_API_KEY`
   - `STABLEGPU_RUNPOD_API_KEY`
2. Run switch:
   - `bash infra/deploy/switch_to_live_adapter.sh`
3. Run preflight:
   - `python3 infra/deploy/provider_preflight.py`

## Important Defaults Written by Switch Script
- `STABLEGPU_PROVIDER_MARKETPLACE_ADAPTER=multi_provider_live`
- Vast contract paths:
  - `/bundles/`
  - `/asks/{offer_id}/`
  - `/instances/{external_task_id}/`
- Runpod contract paths:
  - `/pods`
  - `/pods/{external_task_id}`
  - `/pods/{external_task_id}/stop`
- `STABLEGPU_RUNPOD_GRAPHQL_URL=https://api.runpod.io/graphql`
- `STABLEGPU_PROVIDER_READY_STATE_IS_SUCCESS=true`

## Current Blocker
- Runpod key not present in current environment, so full live validation is still blocked.
