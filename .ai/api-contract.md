# API Contract (Current Stage)

## Goal
Define the real provider adapter contract used by worker execution:
1. `list_offers`
2. `submit_task`
3. `get_task_status`
4. `cancel_task`
5. `cleanup_task`
6. `collect_task_result`

The scheduler consumes normalized objects only:
- `ProviderMarketplaceTaskHandle`
- `ProviderMarketplaceTaskStatus`
- `ProviderMarketplaceCancelResult`
- `ProviderMarketplaceCleanupResult`
- `ProviderMarketplaceResult`

---

## Vast.ai Adapter Contract

### Offer Fetch
- Endpoint: `POST {VAST_BASE_URL}/bundles/`
- Input body: availability filters (verified/rentable/limit/order)
- Output mapping:
  - `offer_id` from `id|ask_id|ask|bundle_id`
  - `gpu_type` from `gpu_name|gpu|model_name`
  - `price_per_hour` from `dph_total|dph|hourly_cost`

### Task Submit
- Endpoint: `PUT {VAST_BASE_URL}/asks/{offer_id}/`
- Body source: `task.input_payload.provider_runtime` + stable defaults
- Handle mapping:
  - `external_task_id` from `new_contract|instance_id|id|contract_id`
  - provider fixed to `vast.ai`

### Status Query
- Endpoint: `GET {VAST_BASE_URL}/instances/{id}/`
- Status normalization:
  - `running/ready/online` -> `succeeded` (when `provider_ready_state_is_success=true`)
  - `creating/loading/starting` -> `provisioning`
  - `offline/error/failed` -> `failed`
  - `destroyed/terminated/exited` -> `cancelled`

### Cancel / Cleanup
- Cancel endpoint: `DELETE {VAST_BASE_URL}/instances/{id}/`
- Cleanup endpoint: `DELETE {VAST_BASE_URL}/instances/{id}/`
- 404 during cleanup is treated as already cleaned.

### Result Collection
- Endpoint: `GET {VAST_BASE_URL}/instances/{id}/`
- Produces at least one artifact (`runtime_manifest`) with an HTTP URL.
- Produces usage:
  - `billable_seconds`
  - `provider_cost`
  - `hourly_price`

---

## Runpod Adapter Contract

### Offer Fetch (GraphQL)
- Endpoint: `{RUNPOD_GRAPHQL_URL}?api_key=...`
- Query: `gpuTypes + lowestPrice`
- Output mapping:
  - `gpu_type` from `displayName|id`
  - `price_per_hour` from `lowestPrice.uninterruptablePrice|minimumBidPrice`
  - raw payload keeps `id` for submit routing.

### Task Submit (REST)
- Endpoint: `POST {RUNPOD_BASE_URL}/pods`
- Body source: `task.input_payload.provider_runtime` + stable defaults
- Requires resolved `gpuTypeId` from quote/raw offer.
- Handle mapping:
  - `external_task_id` from `id|podId`

### Status Query
- Endpoint: `GET {RUNPOD_BASE_URL}/pods/{id}`
- Status normalization:
  - `RUNNING` -> `succeeded` (when `provider_ready_state_is_success=true`)
  - `EXITED` -> `succeeded`
  - `CREATED/STARTING` -> `provisioning`
  - `TERMINATED/ERROR/FAILED` -> `failed`

### Cancel / Cleanup
- Cancel endpoint: `POST {RUNPOD_BASE_URL}/pods/{id}/stop`
- Cleanup endpoint: `DELETE {RUNPOD_BASE_URL}/pods/{id}`
- 404 during cleanup is treated as already cleaned.

### Result Collection
- Endpoint: `GET {RUNPOD_BASE_URL}/pods/{id}`
- Produces artifact (`runtime_manifest`) with Runpod console URL.
- Produces usage:
  - `billable_seconds` (derived from start/status timestamps)
  - `provider_cost`
  - `hourly_price`

---

## Internal API Surfaces Using This Contract
- Worker scheduler execution loop: `apps/worker/worker/scheduler.py`
- Monitoring aggregation:
  - `GET /api/admin/monitoring/overview`
  - `GET /api/tasks/{task_id}`
  - `GET /api/tasks/{task_id}/artifacts/{artifact_id}/download`
