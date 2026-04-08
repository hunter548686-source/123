# Stage Spec (Current)

## Stage Goal
Move provider execution from mock-style endpoints to real provider contracts while keeping the website workflow stable:
- quote -> schedule -> execute -> review -> delivery

## Scope

### Web System Layer
- Keep existing task creation/list/detail/admin flows unchanged.
- Keep artifact download API compatible with real provider artifact URLs.
- Keep monitoring dashboard consuming real adapter/runtime/cost aggregates.

### Agent / Scheduling Layer
- Keep three-stage workflow roles:
  - GPT-5.4 planning
  - local execution path (optional)
  - GPT-5.4 review
- Keep retry/failover/cancel/cleanup behavior deterministic.

### Provider Adapter Layer
- Implement real contracts:
  - Vast.ai: `bundles -> asks -> instances`
  - Runpod: `GraphQL gpuTypes -> REST pods`
- Normalize provider payloads into internal marketplace objects.

### Local Execution Layer
- No production routing change: local executor remains a development execution tool, not the platform runtime backend.

## Non-Goals
- No migration to “local-only compute” architecture.
- No unrelated frontend redesign.
- No non-essential refactor outside provider and deploy path.

## Constraints
- Minimal correct changes first.
- Keep `database_mock` compatible.
- Every change must remain testable and traceable in `.ai/`.
