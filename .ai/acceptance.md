# Acceptance Criteria (Current Stage)

## Provider Adapter
- [x] Adapter can switch between `database_mock`, `vast_ai`, `runpod`, `multi_provider_live`.
- [x] Vast adapter supports offer/submit/status/cancel/cleanup/result.
- [x] Runpod adapter supports offer/submit/status/cancel/cleanup/result.

## Scheduler and State Machine
- [x] Retry keeps provider failover behavior.
- [x] Cancellation goes through provider cancel + cleanup.
- [x] Failure path attempts cleanup before retry/final fail.

## Delivery and Cost Visibility
- [x] Result collection stores artifact entries with downloadable HTTP URL.
- [x] Task run/provider usage is converted to `runtime_seconds` and `provider_cost`.
- [x] Monitoring overview can show adapter key, costs, runtime, and recent failures.

## Deployment Readiness
- [x] Deploy scripts write real provider contract paths.
- [x] Preflight validates provider connectivity/auth paths.
- [ ] Final online live-task acceptance waits on missing production API keys.
