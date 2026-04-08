# Must Fix

1. Inject production provider keys on server:
   - `STABLEGPU_VAST_AI_API_KEY`
   - `STABLEGPU_RUNPOD_API_KEY`

Impact:
- Without keys, `multi_provider_live` cannot complete full online acceptance for real provider dispatch.
