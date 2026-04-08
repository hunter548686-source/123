# Test Plan (Current Stage)

## 1) Unit / Contract Tests
- File: `apps/api/tests/test_provider_marketplace.py`
- Cover:
  - database mock adapter
  - generic remote adapter
  - Vast real-contract lifecycle
  - Runpod GraphQL+REST lifecycle
  - missing base URL failure path

## 2) End-to-End API Workflow Tests
- File: `apps/api/tests/test_auth_wallet_tasks.py`
- Cover:
  - auth + wallet + quote + task create
  - worker processing
  - task detail/events/runs/artifacts
  - artifact download endpoint
  - admin monitoring endpoint

## 3) Worker Flow Tests
- File: `apps/worker/tests/test_worker_flow.py`
- Cover:
  - retry after first failure
  - cancel flow to terminal cancelled state

## 4) Deploy Script Validation
- Script:
  - `infra/deploy/provider_preflight.py`
- Validate:
  - Vast bundles query path
  - Runpod REST auth + GraphQL offers query path

## 5) Regression Command
```bash
python -m pytest apps/api/tests apps/worker/tests -q
```
