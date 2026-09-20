# Zakera vNext Status

**Snapshot date:** 2026-09-20
**Baseline commit:** `f4849c256e7380b09b07e3c4c4a19d72fd4c0e49`
**Working branch:** `codex/zakera-vnext-foundation`
**Milestone:** M0 — Truth and containment

This document is the machine-reviewable inventory of the repository surface that exists before vNext implementation. It records what is active, disconnected, unsafe, or unverified; it does not promise that the listed behavior works.

## Status summary

| Area | Verified snapshot | Disposition |
| --- | --- | --- |
| Product | Legacy chat/orchestration prototype | Replace with the Release Readiness Audit |
| Backend | FastAPI; 12 mounted routers from 25 route modules | Characterize the useful run/event behavior; do not expand |
| Frontend | Next.js App Router plus multiple duplicate component trees | Salvage interaction requirements, not implementation wholesale |
| Persistence | SQLAlchemy startup `create_all()` plus inconsistent Alembic graph | New isolated vNext database and migration history |
| Tools | Six auto-discovered built-ins, including unsafe execution/file access | Exclude unsafe tools from vNext; disable legacy defaults in M1 |
| CI/CD | Ten workflow files existed at baseline; six remain on this branch | One temporary test baseline; mutation-capable legacy workflows manual-only |
| Deployment | Kubernetes/Terraform/ECS/GHCR configurations exist | Unverified legacy material; no automatic deployment |
| Runtime | Isolated dependencies installed; maintained tests run, but application startup is not yet verified | Do not publish a quick start yet |

Inventory counts at this baseline:

- 205 tracked Python files;
- 132 tracked TypeScript/TSX files under `src/frontend`;
- 77 files matching the repository’s current test-file patterns;
- 25 API route modules, excluding `__init__.py`;
- 12 mounted FastAPI routers; and
- 10 GitHub Actions workflow files.

## Backend surface

The active application entry point is `src/api/main.py`. It initializes monitoring, metrics, alerts, tracing, CORS, database tables, and the routers below.

### Mounted routers

| Module | Prefix |
| --- | --- |
| `health` | `/api/v1` |
| `monitoring` | `/api/v1` |
| `auth` | `/api/v1/auth` |
| `models` | `/api/v1` |
| `conversations` | `/api/v1` |
| `agent_runs` | `/api/v1` |
| `chat` | `/api/v1` |
| `tools` | `/api/v1` |
| `analytics` | `/api/v1` |
| `search` | `/api/v1` |
| `feedback` | `/api/v1/feedback` |
| `benchmark` | `/v1` |

### Route modules not mounted by `src/api/main.py`

- `analytics_enhanced`
- `auth_enhanced`
- `conversation_export`
- `conversation_stats`
- `conversation_templates`
- `conversations_export`
- `export`
- `health_advanced`
- `prompts`
- `summarization`
- `token_usage`
- `transcribe`
- `usage`

These files are not automatically deleted: some may be imported by tests or other modules. They are outside the active API surface until proven otherwise.

### Behavior worth characterizing in M1

- persisted `AgentRun`, `AgentStep`, and `AgentApproval` records;
- observable run events over SSE;
- approval pause, deny, approve, and resume behavior;
- cancellation and failure behavior;
- ownership checks in the agent-run routes; and
- separation between conversation messages and execution runs.

The chat route and `AgentRunService` contain overlapping orchestration/tool-loop behavior. vNext must have one runtime boundary.

## Persistence

`src/api/database.py` calls `Base.metadata.create_all()` during application startup. This bypasses Alembic as the authoritative schema transition mechanism.

The legacy Alembic graph cannot be treated as one valid linear history:

| Revision | Parent | Finding |
| --- | --- | --- |
| `001` | none | Root |
| `001_conversation_templates` | none | Second root |
| `0005_add_conversation_labels` | `0004` | Parent absent |
| `a7f3c9e21d08` | `0005_add_conversation_labels` | Continues one dangling chain |
| `b8f5a4c91d22` | `a7f3c9e21d08` | Continues chain |
| `c3a7d9e4b6f1` | `b8f5a4c91d22` | Continues chain |
| `002_security_enhancement` | `001_initial` | Parent does not match revision `001` |

M2 therefore uses a distinct database URL, metadata registry, Alembic configuration, script directory, and version table. It must not import the legacy model registry or run legacy `create_all()`.

## Tool surface and safety

The registry dynamically imports every module in `src/tools/builtin` and registers every discovered `Tool` subclass. The bundled surface is:

- calculator;
- web search;
- code executor;
- weather;
- date/time; and
- file reader.

The current approval service treats only the names `code_executor` and `file_reader` as risky. This is a denylist: a newly registered mutating tool would not automatically require approval.

Known high-risk behavior:

- `code_executor` runs model-provided Python with in-process `exec()`; its timeout cannot safely terminate arbitrary code;
- `file_reader` resolves arbitrary paths without a vNext-style allowed-root policy; and
- tool arguments, output, and errors have no complete secret-redaction contract.

This branch now skips both unsafe modules during built-in discovery unless `ZAKERA_ENABLE_UNSAFE_LEGACY_TOOLS=true` is explicitly set for trusted local testing. Focused tests cover the default-off and opt-in boundaries. vNext still uses a capability allowlist and contains no arbitrary execution or filesystem tool.

## Frontend surface

The active Next.js App Router pages are:

- `/` — redirects to `/chat`;
- `/login`;
- `/register`; and
- `/chat` — conversation sidebar, chat interface, and agent-run drawer.

The TypeScript compiler includes all TS/TSX files beneath `src/frontend`. Component implementations are spread across:

- `src/frontend/app/components`;
- `src/frontend/components`; and
- `src/frontend/src/components`.

There are also multiple chat stores and duplicate chat/message/history components. File presence does not establish that a component is reachable from an active page. vNext will introduce a separate task-first entry point rather than consolidating this entire tree before validation.

## Version and product metadata

| Location | Value |
| --- | --- |
| `pyproject.toml` | `0.5.0` |
| FastAPI application and tracing | `0.7.0` |
| Frontend package | `0.7.0` |

This branch replaces the Python package’s “production-ready” description and Beta classifier with candid prototype/pre-alpha metadata. The version mismatch remains documented; changing package identity or publishing a package is outside this containment patch.

## CI/CD inventory and containment

### Temporary automatic baseline

`.github/workflows/test.yml` remains the temporary automatic legacy characterization workflow for pushes to its configured branch patterns and pull requests to `main`. It runs a maintained backend subset plus frontend Jest tests.

It is not yet the target CI gate:

- Python lint remains non-blocking;
- TypeScript type checking remains non-blocking;
- Codecov upload failure remains non-blocking; and
- it does not test a fresh vNext migration or production frontend build.

Those weaknesses are recorded debt, not hidden success. New vNext paths must receive blocking format, lint, type, test, build, migration, and evaluation checks from their first commit.

Local baseline results on 2026-09-20:

- maintained backend selection: 99 passed;
- focused agent-run service selection: 5 passed;
- frontend Jest: 8 suites and 117 tests passed;
- frontend TypeScript check: failed with 38 legacy errors across duplicate/disconnected component trees; and
- frontend production build: application compilation succeeded, then failed during the same TypeScript validation.

The first backend run also revealed that tokenizer initialization downloads encoding data at test time. After that asset was cached, the suite passed. Tests must not depend on undeclared network access in the target vNext CI.

`npm ci` reported 19 vulnerabilities in the locked legacy dependency tree: 4 moderate, 14 high, and 1 critical. No blanket `npm audit fix` or dependency upgrade was applied because that would mix unrelated migration risk into the containment slice.

### Workflow disposition in this patch

| Workflow | Trigger after containment | Reason |
| --- | --- | --- |
| `test.yml` | automatic | Temporary maintained legacy test baseline |
| `security.yml` | automatic + weekly + manual | Retain security visibility; CodeQL is blocking |
| `lint-pr-title.yml` | pull request | Narrow repository policy check |
| `pr-labels.yml` | pull request | Narrow repository-maintenance action |
| `cd.yml` | manual only | Builds, publishes, and deploys with Terraform/ECS |
| `release.yml` | manual only | Publishes images and creates releases |
| `ci.yml` | removed on this branch | Duplicate CI with ignored lint/type failures |
| `ci-cd-multi-env.yml` | removed on this branch | Duplicate CI plus image publishing/deployment |
| `performance.yml` | removed on this branch | Stale endpoints and repeated scheduled failures |
| `badges.yml` | removed on this branch | Scheduled runs performed no maintained update |

The live GitHub settings were inspected before these deletions. On 2026-09-20, the repository showed no classic branch-protection rules and no repository rulesets, so no required status check depended on the removed workflow names. Recent Actions history showed daily Performance Testing failures and successful no-op Update Badges runs.

PR #66 provided the first live integration evidence for this branch. Secret Scanning initially failed before scanning because Gitleaks lacked pull-request read permission; after adding the minimum read-only permission, the job passed. The PR labeler also passed after its missing checkout and obsolete v5 configuration schema were corrected. Dependency Review remains blocked because GitHub reports that the repository does not have the required Dependency Graph/Advanced Security capability. The verified audit results and dispositions are recorded in [the security and dependency baseline](SECURITY_BASELINE.md).

## What this slice changes

- makes mutation-capable legacy deployment and release workflows explicit-dispatch only;
- stops scheduled or automatic stale performance and badge jobs;
- removes duplicate `ci.yml` and the combined multi-environment pipeline after verifying no required-check dependency;
- removes CodeQL’s silent-failure override;
- establishes this inventory; and
- adds a blinded evaluation case format and the first two inputs.
- makes unsafe legacy code-execution and unrestricted file-reading tools unavailable by default.
- removes unsupported “production-ready” and Beta claims from Python package metadata.
- removes four obsolete workflow definitions after verifying that GitHub has no branch protection or rulesets depending on them.

## What remains unverified

- a clean local installation and application startup;
- the full legacy pytest suite outside the maintained CI selection;
- a passing legacy TypeScript check and production build;
- a supported dependency-review mechanism for this repository;
- the existence or health of any deployment target;
- whether any legacy user data has value; and
- whether the legacy deployment workflows are safe even when manually dispatched.

## Verification performed for this slice

- all six remaining workflow files parse as YAML;
- all evaluation JSON and schema files parse as JSON;
- both unsafe-tool discovery boundary tests pass with Python's standard `unittest` runner;
- the maintained backend selection passes 99 of 99 tests;
- the focused agent-run service selection passes 5 of 5 tests;
- frontend Jest passes all 8 suites and 117 tests;
- both evaluation revisions resolve to commits in repository history;
- all active documentation-index links resolve; and
- `git diff --check` reports no whitespace errors.

Workflow parsing proves syntax, not GitHub Actions runtime semantics. The manual-only deployment/release triggers and retained automatic checks must still be observed in a pull request.

## Next M0/M1 actions

1. Add black-box tests for the useful run/event/approval behavior.
2. Make tokenizer-dependent tests hermetic.
3. Review and freeze eight more evaluation inputs before implementing against them.
4. Decide whether to enable GitHub's required dependency-review capability or use supported ecosystem-native checks.
