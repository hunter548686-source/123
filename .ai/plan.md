# Execution Plan (Current Stage)

## P1 Provider Contract Upgrade
- [x] Replace Vast adapter with real lifecycle endpoints.
- [x] Replace Runpod adapter with GraphQL offers + REST pod lifecycle.
- [x] Keep normalized contract output for scheduler compatibility.

## P2 State and Reliability
- [x] Keep retry/failover path working with new adapters.
- [x] Keep cancel -> cleanup chain working.
- [x] Keep result collection producing artifacts and usage metrics.

## P3 Config and Deployment
- [x] Update config defaults and `.env.example` to real provider paths.
- [x] Update live switch script to upsert full real contract paths.
- [x] Update provider preflight to validate real provider paths.

## P4 Validation
- [x] Add/adjust adapter unit tests for Vast and Runpod real contracts.
- [x] Run full API + worker regression tests.
- [x] Deploy new code to VPS and verify service health.

## P5 Remaining Blocked Item
- [ ] Inject missing production provider keys and run final live task acceptance.
