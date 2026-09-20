# Zakera

> **Project status: prototype under redesign.** The current codebase is an older, agent-generated AI orchestration prototype. It is not production-ready, and several legacy features and operations documents are unverified. Development is now moving toward a smaller, evidence-first vNext.

**Know what is actually ready—and what you can safely say about it.**

Zakera vNext is being designed as an evidence-first release readiness assistant for GitHub teams. Its first workflow will turn repository content, pull requests, issues, CI results, and documentation into a claim-by-claim readiness report. Every factual conclusion must point to evidence, missing or conflicting information must stay visible, and Zakera must ask before it posts or changes anything.

## First supported workflow

Given a repository and a revision, the Release Readiness Audit will:

1. read the relevant code, documentation, pull requests, issues, and checks;
2. classify proposed release claims as supported, unsupported, conflicting, or needing owner review;
3. produce a reviewable Markdown report and a machine-readable result;
4. show the source, revision, and locator behind each factual claim; and
5. make no external changes during the initial read-only release.

The initial product is deliberately a repeatable task, not a general-purpose chat interface or agent platform.

## Current status

| Area | Status |
| --- | --- |
| Legacy FastAPI and Next.js prototype | Present, being evaluated for salvage |
| Run, step, approval, and SSE concepts | Present; behavior may inform vNext |
| Release Readiness Audit | Planned; not implemented yet |
| Evidence and claim ledger | Planned; not implemented yet |
| External write actions | Out of the first release; must require exact-action approval later |
| Long-term memory, proactive scheduling, multi-agent workflows | Not part of vNext MVP |
| Broad provider routing and arbitrary tools | Legacy surface; not a vNext goal |
| Hosted or production deployment | Not supported |

The repository currently contains duplicated and disconnected surfaces, inconsistent database migrations, and legacy tools that are not safe execution sandboxes. The code-execution and unrestricted file-reading tools remain present in the legacy prototype but are excluded from vNext. Do not enable the legacy tool path for untrusted content or expose this repository to untrusted users or production credentials.

## vNext direction

The first implementation will use:

- Next.js for the task, run timeline, evidence, and artifact-review interface;
- a thin FastAPI application for workflow execution and persistence;
- the OpenAI Agents SDK for the initial agent runtime;
- direct, read-only GitHub function tools for the first vertical slice;
- SQLAlchemy with a fresh Alembic history;
- SQLite for single-user local development, with PostgreSQL required before shared deployment;
- server-sent events for observable run updates; and
- Markdown as the first artifact format.

MCP remains a future adapter boundary, not a day-one subsystem. Multi-provider routing, generic workflow builders, multi-agent orchestration, long-term memory, Kubernetes, Terraform, and a large observability stack will be reconsidered only if validated product use requires them.

The complete product, architecture, migration, security, testing, and delivery plan is in [docs/VNEXT_PLAN.md](docs/VNEXT_PLAN.md).

## Trust model

Zakera vNext is governed by four rules:

1. **No evidence, no claim.** Missing evidence is reported, not guessed.
2. **Repository content is untrusted input.** Instructions found in files, issues, or pull requests cannot change tool policy.
3. **Read and write capabilities are separate.** The first release is read-only.
4. **Approval binds to the exact action.** A future write approval must identify the actor, tool, target, arguments, payload, source revision, and expiry. Any change requires a new approval.

## Working with the legacy prototype

The current implementation remains in the repository while vNext is built in isolation. Its historical setup and feature documentation are retained under [`docs/`](docs/README.md), but should be treated as legacy reference unless explicitly marked as verified.

Before publishing a new quick start, the vNext setup commands must be exercised in CI and from a clean checkout. Until then, use the milestone gates in the vNext plan rather than relying on the legacy production or deployment guides.

## Contributing

The highest-value work is currently:

- defining historical release cases for the evaluation set;
- implementing the read-only Release Readiness Audit vertical slice;
- designing evidence and claim semantics;
- writing observable behavior tests for run, artifact, and approval boundaries; and
- containing unsafe or misleading legacy paths without broad rewrites.

Please keep changes small, reversible, and tied to a milestone acceptance gate in the [vNext plan](docs/VNEXT_PLAN.md).

## License

MIT
