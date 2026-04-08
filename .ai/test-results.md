# Test Results (2026-04-08)

## Local Automated Tests

### Command
```bash
python -m pytest apps/api/tests apps/worker/tests -q
```

### Result
- `16 passed`

### Notable Coverage in This Round
- Vast adapter real-contract flow:
  - bundles search
  - asks submit
  - instances status/cancel/cleanup/result
- Runpod adapter real-contract flow:
  - GraphQL GPU offers
  - REST pod submit/status/cancel/cleanup/result
- Generic remote adapter contract remains backward compatible.
- Worker flow regression suite remains green.

## Script Validation

### Provider preflight
```bash
python infra/deploy/provider_preflight.py
```

### Current outcome in this environment
- Vast.ai preflight: passes.
- Runpod preflight: fails when key is missing (`missing STABLEGPU_RUNPOD_API_KEY`).
