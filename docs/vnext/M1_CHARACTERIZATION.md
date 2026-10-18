# M1 Agent-Run Characterization

**Status:** First slice verified
**Date:** 2026-10-17
**Baseline:** `fea845c5e5f579a1a5ba3b76da32033318042c5c`
**Scope:** legacy run lifecycle, approvals, ownership, cancellation, and artifacts

This document records behavior observed before vNext implementation. A passing characterization test means the behavior is understood; it does not make the legacy implementation part of the target architecture.

## Verified observations

| Boundary | Evidence | Observed legacy behavior | vNext decision |
| --- | --- | --- | --- |
| Run lifecycle | Black-box service test | At the service-generator boundary, a successful run emits a stable start/step/response/done sequence and persists three ordered steps. The public HTTP/SSE translation remains uncharacterized. | **Salvage the observable lifecycle concept. Replace the implementation with persisted append-only run events.** |
| Failure | Black-box service test | A provider exception emits `agent.step.error` followed by `agent.error`, persists a failed run, and does not create an assistant message. The original model-call step incorrectly remains `started`. | **Salvage explicit terminal failure. Replace the status and event model so every begun step reaches a terminal state.** |
| Approval | Black-box service test | Multiple risky calls remain blocked until every pending approval is resolved; then all approved calls execute. Their order is not a reliable contract because approvals are reloaded by timestamp without a deterministic tie-break. | **Salvage pause/review/resume semantics. Replace the name-based risky-tool denylist, legacy approval payload, and ambiguous ordering.** |
| Ownership | Router-level HTTP test | A user can inspect their run; another owner's run returns the same 404 response as a missing run. | **Salvage non-disclosing owner isolation and make it a repository/service invariant.** |
| Cancellation | Router route-table and HTTP test | The mounted agent-run router has no cancellation route; the expected `POST /agent-runs/{id}/cancel` path returns 404. | **Build new. Cancellation is required before the first complete workflow.** |
| Artifacts | Router-level HTTP test | The agent-run detail response has no top-level `artifacts` field. Broader legacy export behavior is outside this slice. | **Build a run-owned artifact contract with versioned metadata, provenance, and verification records.** |

## Important limitations

- Legacy `AgentStep` rows are operational records, but public events are synthesized in memory while a request runs; they are not a durable replayable event stream.
- Approval policy is a denylist containing `code_executor` and `file_reader`. Adding a new mutating tool does not require approval by default.
- Legacy approval records do not bind all of the vNext-required fields such as normalized arguments, payload hash, expiry, source revision, or idempotency key.
- Approval resume returns a result but does not expose the same live event stream contract as the initial run.
- Approved calls are reloaded by `created_at` without a persisted request sequence or deterministic tie-break, so execution order is not a contract.
- A failed provider call leaves its original model step in `started` while adding a separate failed error step.
- The full application test client invokes global startup database initialization even when route dependencies are overridden. The characterization harness therefore mounts the run router in isolation; vNext must have an independently testable application boundary.

## Reproduction

Run the focused suite with Python 3.12:

```bash
pytest tests/test_agent_run_service.py tests/test_agent_run_characterization.py -q --tb=short --timeout=60
```

The first slice contains ten passing tests: five earlier service tests and five new characterization tests.

## Next characterization slice

1. Record rejection behavior when more than one approval is pending.
2. Characterize list ordering and pagination for runs.
3. Characterize SSE translation at the chat route boundary.
4. Freeze eight additional evaluation inputs covering personal-project research, writing, repository work, memory conflict, unavailable sources, denied approval, cancellation, and failed verification.
