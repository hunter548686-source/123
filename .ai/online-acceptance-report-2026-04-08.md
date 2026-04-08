# Online Acceptance Report (2026-04-08)

## Scope
- HTTPS availability
- Web/API reachability
- worker/service health
- provider live-switch readiness

## Environment
- Server: `144.202.58.159`
- Domain: `gpu.144.202.58.159.sslip.io`
- Deploy path: `/opt/stablegpu/repo`

## Verified
1. HTTPS works:
   - `https://gpu.144.202.58.159.sslip.io` -> 200
2. API health works:
   - `https://gpu.144.202.58.159.sslip.io/api/health` -> `{"status":"ok"}`
3. Admin/docs entry works:
   - `/admin` and `/docs` reachable
4. Service stack runs:
   - `stablegpu-api.service`, `stablegpu-web.service`, `stablegpu-worker.service`
5. Provider contract code is upgraded:
   - Vast real path contract implemented
   - Runpod GraphQL+REST contract implemented
   - deployment scripts updated to write real path defaults

## Current Blocker
- Missing production `STABLEGPU_RUNPOD_API_KEY` in current environment.
- Therefore full `multi_provider_live` online acceptance cannot be fully closed yet.

## Final Acceptance Steps
1. Inject keys:
   - `STABLEGPU_VAST_AI_API_KEY`
   - `STABLEGPU_RUNPOD_API_KEY`
2. Execute:
   - `bash infra/deploy/switch_to_live_adapter.sh`
   - `python3 infra/deploy/provider_preflight.py`
3. Run one live task:
   - verify provider dispatch
   - verify task result artifact
   - verify cost/runtime in monitoring overview
