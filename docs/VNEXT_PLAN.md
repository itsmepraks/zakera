# Zakera vNext: Product and Delivery Plan

**Status:** Accepted working direction; implementation has not started beyond documentation and repository alignment
**Updated:** 2026-09-20
**Working branch:** `codex/zakera-vnext-foundation`
**Baseline:** `f4849c256e7380b09b07e3c4c4a19d72fd4c0e49`

## 1. Decision

Zakera will not be upgraded as a generic AI orchestrator. The existing repository is a broad prototype with useful ideas, but upgrading every provider, route, tool, deployment manifest, and UI path would preserve its accidental complexity without proving a user need.

Zakera vNext will be an **evidence-first release readiness assistant for GitHub teams**.

Its first job is:

> Before I publish release documentation or update a release tracker, tell me exactly which claims are supported by repository, pull request, issue, and CI evidence; identify what is missing or contradictory; and give me a review-ready draft without changing anything unless I approve.

The initial user is a release or documentation owner in a small engineering or open-source team. The trigger is a release candidate, documentation update, or readiness review.

This direction was independently reviewed from product, architecture, and delivery perspectives. All three reviews agreed on a focused, read-only first workflow, a reversible migration, first-class evidence records, and deferred write capabilities. The architecture review additionally recommended direct function tools before MCP and an explicitly local, single-user first slice.

## 2. Product promise

**Positioning:** Zakera turns pull requests, issues, CI results, repository content, and documentation into a claim-by-claim release readiness report. It shows where every conclusion came from and asks before it posts or changes anything.

**Short promise:** Know what is actually ready—and what you can safely say about it.

“Agent harness,” “workflow agent,” and “AI orchestrator” may describe implementation choices, but they are not the customer-facing product.

## 3. Product principles

1. **Evidence before fluency.** A polished statement is not acceptable unless its factual parts have source anchors.
2. **Absence stays visible.** Missing access, missing proof, and unresolved decisions are explicit result states.
3. **Task-first, not chat-first.** Runs have inputs, a versioned workflow, observable stages, and durable artifacts.
4. **Read-only by default.** External mutation is a separate capability with an exact preview and approval.
5. **Observable, not theatrical.** The timeline shows source reads, validations, tool calls, approvals, artifacts, and failures—not hidden reasoning.
6. **One complete workflow before a platform.** New providers, workflows, tools, or infrastructure must follow demonstrated demand.
7. **Small reversible changes.** Legacy behavior remains recoverable while vNext proves itself.

## 4. MVP contract

### 4.1 Inputs

- public GitHub repository identifier;
- exact branch, tag, or commit SHA;
- optional target release/version;
- optional set of proposed claims or draft release notes; and
- optional server-injected GitHub read token for rate limits; credentials are never model input or part of a run snapshot.

The MVP is public-GitHub-only. Local and private-repository adapters require separate security and privacy decisions after the read-only evaluation. The run snapshots the resolved revision, workflow version, model configuration, tool policy, and collection timestamp. A moving branch name alone is never a sufficient evidence identity.

### 4.2 Workflow

1. Validate access and resolve the input to an immutable revision.
2. Collect relevant repository documents, changed files, pull requests, issues, and CI/check results.
3. Normalize each source into a source receipt with repository, revision, canonical URL, locator, timestamp, and content hash where available.
4. Extract proposed factual claims.
5. Link each claim to supporting and contradicting evidence.
6. Classify each claim:
   - `supported`: adequate collected evidence directly supports the claim;
   - `unsupported`: the evidence successfully collected in this run does not adequately support the claim; this does not mean the claim is false;
   - `conflicting`: credible collected evidence supports incompatible conclusions; or
   - `needs_owner_review`: evidence cannot resolve an intent, approval, policy, or product decision.
7. Validate that every factual statement in the report has at least one valid evidence reference or is explicitly marked unverified.
8. Generate an immutable Markdown report and compact JSON artifact.
9. Present the timeline, claim ledger, missing sources, blockers, owner decisions, and source receipt for review.

### 4.3 Outputs

The Markdown artifact contains:

- audit scope and immutable revision;
- verified changes;
- claim-evidence ledger;
- unsupported or excluded claims;
- conflicting evidence;
- inaccessible or missing sources;
- release blockers;
- owner decisions required;
- limitations of the audit; and
- a source receipt.

The JSON artifact exposes the same claims, classifications, locators, and run metadata for deterministic evaluation.

### 4.4 MVP exclusions

The MVP does not include:

- a generic chat assistant;
- provider selection or provider failover;
- proactive scheduling or habit learning;
- long-term cross-task memory;
- multi-agent orchestration;
- a visual workflow builder;
- arbitrary MCP servers or a tool marketplace;
- code execution or unrestricted filesystem access;
- GitHub writes;
- accounts, MFA, billing, or team administration;
- broad analytics or benchmarking dashboards;
- Kubernetes, Terraform, Jaeger, or Grafana; or
- migration of legacy conversations.

## 5. Evidence semantics

Links alone do not make a result evidence-based. The application must encode what a source can establish.

| Source | Can support | Cannot establish by itself |
| --- | --- | --- |
| Merged pull request | Code was merged at a revision | The behavior shipped or works in production |
| Passing CI check | The named checks passed for a revision | Product approval or complete feature coverage |
| Issue or comment | A request, report, or recorded decision | Implementation unless linked to implementation evidence |
| Documentation file | Current repository wording | Runtime behavior or stakeholder approval |
| Release/deployment record | An artifact or deployment event occurred | End-user behavior unless verified separately |
| Missing/inaccessible source | An evidence gap exists | That the underlying claim is false |

Every `EvidenceRef` records the source type and locator. Claims and evidence have a many-to-many relationship labeled `supports`, `contradicts`, or `context`. Classification rules and report validation remain deterministic application policy, not model discretion alone.

## 6. Experience design

The primary interface has four views:

1. **Start audit:** repository, revision, optional release target, and source-access check.
2. **Run timeline:** observable collection, extraction, validation, and artifact events with explicit partial/failure states.
3. **Evidence review:** claims grouped by status, with source drawers and contradiction details.
4. **Artifact review:** rendered Markdown, JSON download, copy/download actions, and run limitations.

A run must survive refresh. Failed or partial runs remain inspectable. Copying or downloading an artifact is local interaction, not an external write.

After the read-only product meets its quality gate, one future action may be introduced: publish an already prepared GitHub issue or pull-request comment. The user must see the exact repository, target, and body immediately before approval.

## 7. Target architecture

```text
Next.js task and review UI
            |
            v
Thin FastAPI application
  |-- workflow catalog (versioned code)
  |-- run application service
  |-- evidence and artifact services
  |-- approval policy
  |-- append-only run event stream (SSE)
  |-- agent runtime adapter
  |     `-- OpenAI Agents SDK
  |-- tool gateway
  |     |-- GitHub read adapter (MVP)
  |     `-- GitHub write adapter (post-MVP, approval required)
  `-- repositories
        |-- workflow and run
        |-- run event
        |-- source and evidence
        |-- claim and artifact
        `-- approval
```

### 7.1 Technology decisions

| Concern | Decision | Reason |
| --- | --- | --- |
| Web interface | Next.js | Fits the existing repository and the review-heavy UI |
| Application API | Thin FastAPI service | Preserves useful Python behavior and separates policy from UI |
| Agent runtime | OpenAI Agents SDK initially | Provides tool invocation, streaming, tracing, sessions, and resumable human-in-the-loop state |
| Initial tools | Direct typed GitHub function tools | Less transport and trust complexity than day-one MCP |
| MCP | Deferred adapter boundary | Add only when trusted external tool interoperability creates value |
| Persistence | SQLAlchemy 2 + fresh Alembic baseline | The legacy migration graph has multiple roots and dangling revisions |
| Local database | SQLite | Simple single-user development |
| Shared database | PostgreSQL | Required and tested before concurrent or hosted use |
| Events | SSE | One-way run updates fit the existing useful behavior |
| Artifact | Markdown + JSON | Human review plus deterministic evaluation |
| Models | One supported OpenAI model | Avoids rebuilding a provider gateway before product validation |

The Agents SDK is behind an application adapter. Serialized SDK run state is an opaque checkpoint; application queries never depend on its internal JSON. Permanent domain records use Zakera’s own schema.

### 7.2 Domain model

| Entity | Responsibility |
| --- | --- |
| `WorkflowDefinition` | Versioned input/output contract, instructions, allowed capabilities, and definition hash |
| `Run` | Immutable input/config snapshots, lifecycle state, runtime checkpoint, and error outcome |
| `RunEvent` | Append-only, monotonically sequenced public event; source of the user-visible timeline |
| `SourceSnapshot` | Resolved identity, revision, collection time, access outcome, redacted normalized content or immutable blob reference, and content hash |
| `EvidenceRef` | Typed link from a claim or artifact section to a precise source locator |
| `Claim` | Proposed factual statement, classification, evidence links, and review state |
| `Artifact` | Versioned immutable Markdown or JSON output; revisions create a new version |
| `Approval` | Exact pending action, capability, target, normalized arguments, payload hash, expiry, and decision receipt |

Database constraints enforce legal statuses and uniqueness for `(run_id, event_sequence)` and `(run_id, tool_call_id)`. Approval resolution uses optimistic locking or row locks and an idempotency key.

### 7.3 Run lifecycle

```text
queued -> collecting -> analyzing -> validating -> completed
   |          |            |             |
   +----------+------------+-------------+-> failed
   |          |            |             +-> completed_with_gaps
   +----------+------------+----------------> canceled
   +----------+------------+----------------> interrupted
```

`completed`, `completed_with_gaps`, `failed`, `canceled`, and `interrupted` are terminal states. A partial collection is represented by events and a terminal `completed_with_gaps` result, not a durable `partial` state. Runs continue after a browser disconnect while the API process remains alive, and SSE reconnection replays persisted events. An MVP API restart marks in-flight work `interrupted`; process-level resume is deferred until durable workers/checkpoints exist.

An approval-capable later release may enter `awaiting_approval`, then resume to `executing_action`, `denied`, `expired`, `completed`, or `failed`. Status transitions are application policy and have direct tests.

## 8. Security and privacy boundaries

### 8.1 Capability policy

Tools are classified as `read`, `draft`, `external_write`, `execute`, or `secrets`. Only `read` is automatically allowed in the MVP. Policy is an allowlist enforced in code; adding a new tool never grants it automatic execution.

### 8.2 Approval binding

A future approval binds to:

- authenticated actor;
- run and tool-call IDs;
- capability and exact tool identity;
- repository and target;
- normalized arguments;
- exact payload hash;
- source revision;
- credential scope;
- expiry; and
- idempotency key.

Changed input invalidates the approval. Denial, expiration, restart, double-submit, and concurrent resolution have integration tests.

### 8.3 Untrusted content

Repository files, issue bodies, pull-request text, comments, tool output, and MCP content are untrusted. They may provide data but cannot alter system instructions, allowed tools, repository scope, credential scope, or approval policy.

### 8.4 Legacy hazards

The existing `code_executor` uses in-process Python execution and is not a sandbox. The existing `file_reader` lacks an adequate allowed-root boundary. Neither is part of vNext. If execution is ever required, it must use a disposable isolated environment with no ambient credentials, explicit mounts, network policy, resource/time limits, and output limits.

Secrets are server-side only and are never included in model/tool arguments or run snapshots. Tool arguments, output, errors, traces, and event payloads pass through a defined redaction layer before persistence or display. Browser storage must not hold long-lived bearer credentials in a hosted release.

### 8.5 Model-bound data and retention

Before the first live audit, the UI discloses which selected public-repository excerpts, issue or pull-request text, and check metadata may be sent to the configured model provider. Only the minimum excerpts needed for the workflow are sent. Source size, file type, per-source byte, token, cost, and run-time limits are configured and shown before execution. Secret-like content is redacted or excluded before model submission.

The MVP does not accept private repositories. Application artifacts, events, and redacted source snapshots remain local until the user deletes the local database; the M0/M2 decisions must define a deletion command and maximum default retention before any hosted use. Agents SDK/provider tracing is disabled for content-bearing runs unless its data handling is explicitly configured, disclosed, and verified. Private-repository support requires a later threat review covering consent, credential storage, provider retention, local retention, and deletion.

## 9. Migration strategy

Use a strangler-style migration in the same repository:

1. preserve Git history and the last prototype commit;
2. document the legacy boundary honestly;
3. build vNext in an isolated namespace with a new database and migration history;
4. characterize useful legacy behavior as black-box acceptance tests;
5. reimplement only the behavior the vNext workflow needs;
6. remove active legacy paths only after equivalent vNext behavior is verified; and
7. keep each milestone independently reviewable and reversible.

Do not repair the legacy Alembic graph as the foundation for vNext. Do not mass-upgrade dependencies, merge automated dependency updates, or reorganize all legacy files before the product slice exists. Do not migrate legacy conversations unless valuable user data is identified and an export/import rehearsal succeeds.

The vNext application uses a distinct database URL, SQLAlchemy metadata registry, Alembic configuration/script location, and Alembic version table. It never imports legacy models or runs the legacy `Base.metadata.create_all()`. A coexistence test proves that starting or migrating either application does not modify the other database or schema.

### 9.1 Salvage as behavior

- Run, step/event, and approval concepts;
- the visible run timeline and approval-preview interaction;
- SSE framing and reconnect expectations;
- ownership checks on run access;
- existing approval scenarios as acceptance-test input; and
- separation between a persisted run and chat messages.

### 9.2 Rewrite or retire

- SQLAlchemy models and migration history;
- custom orchestration/tool loop and provider selection;
- conversation memory;
- tool manager and unsafe built-in tools;
- authentication before hosted beta;
- duplicated frontend components and stores;
- unmounted API routes;
- provider matrix and routing;
- generic chat as the product shell; and
- unused deployment/observability infrastructure.

## 10. Repository shape

The exact folder names may be decided in the foundation PR, but vNext must be visibly isolated. Preferred shape:

```text
apps/
  api/                 FastAPI application and workflow runtime
  web/                 Next.js task and review interface
packages/
  contracts/           Generated/shared API and event contracts
evaluations/
  release_readiness/   Versioned fixtures, gold labels, and scorecards
docs/
  vnext/               Product, architecture, decisions, and status as they grow
legacy/                Not required; Git history may be the cleaner archive
```

Moving old code into `legacy/` is not itself progress and can keep it in CI/scanner scope. Prefer a new active namespace and preserve the old implementation in Git until removal is safe.

### 10.1 Rollback boundaries

| Milestone | Rollback mechanism |
| --- | --- |
| M0 | Revert the documentation/workflow change; restore branch-protection references only after the previous check is verified |
| M1 | Keep legacy safety changes behind default-off feature flags where necessary; rollback never re-enables unsafe tools for untrusted use |
| M2 | Disable the separate vNext entry points and retain the separate vNext database; legacy startup and data remain untouched |
| M3–M5 | Disable the vNext entry point or GitHub read adapter; persisted read-only runs remain inspectable |
| M6 | Server-side write-capability kill switch plus immediate write-credential revocation; approved artifacts remain as audit records |
| M7+ | Roll back application traffic to the last verified build and restore from tested backups |

An emergency rollback never runs a down-migration against user data. Schema changes use forward fixes or restoration into a separately verified database.

## 11. Delivery milestones

Every milestone is one or more small pull requests. A milestone does not start because the prior code was written; it starts after the prior acceptance gate is met.

### M0 — Truth and containment

**Goal:** establish an honest baseline and stop accidental expansion.

Work:

- synchronize the default branch and record the baseline SHA;
- create the vNext working branch;
- update the root README and documentation index;
- record product, architecture, persistence, and security decisions;
- inventory mounted routes, active UI paths, migrations, tools, and CI workflows;
- choose one authoritative required CI workflow;
- make deployment manual-only and remove scheduled jobs that exercise invalid endpoints;
- decide whether an annotated legacy tag is useful; create it only with owner approval; and
- select 10 historical release/readiness cases without yet tuning the system to their answers.

Gate:

- public documentation contains no unverified production claim;
- all links in the active documentation index resolve;
- the baseline commit and legacy status are recorded;
- no scheduled or automatic production mutation path remains;
- required CI checks cannot pass by ignoring lint, type, test, or security failures; and
- the initial evaluation cases and scoring rubric are frozen.

**Current progress:** on 2026-09-20, `git pull --ff-only` in the main checkout returned `Already up to date`, and the main checkout, this branch baseline, and `origin/main` resolved to `f4849c256e7380b09b07e3c4c4a19d72fd4c0e49`. The vNext branch, README, plan, active-surface inventory, workflow containment, evaluation schema, and first two blinded case inputs are complete locally. Live GitHub settings showed no classic protection or rulesets, after which four obsolete workflows were removed. Secret-finding triage, strict vNext CI, and eight additional evaluation cases remain undone.

### M1 — Characterization and safety

**Goal:** preserve only useful observable behavior and disable dangerous defaults.

Work:

- add black-box tests for the legacy run lifecycle, event stream, cancellation, approval pause/resume, and artifact-independent behavior worth retaining;
- make unsafe code execution and unrestricted file reading unavailable under default configuration;
- add a source/component/endpoint inventory to vNext status documentation;
- identify the minimal legacy test subset that is a meaningful regression gate; and
- quarantine or clearly label non-authoritative deployment instructions.

Gate:

- maintained legacy characterization tests pass;
- unsafe tools cannot execute under default configuration;
- the active legacy surface is documented;
- no product behavior is expanded; and
- changed safety behavior is verified at the API boundary.

### M2 — Isolated vNext foundation

**Goal:** create the smallest runnable task system without connecting real external sources.

Work:

- create isolated API and web entry points;
- define shared request, response, and event contracts;
- implement a fresh database and linear Alembic baseline;
- configure a distinct vNext database URL, metadata registry, Alembic script location, and version table without importing legacy models;
- implement `WorkflowDefinition`, `Run`, `RunEvent`, `SourceSnapshot`, `EvidenceRef`, `Claim`, and `Artifact`;
- implement legal state transitions and an append-only event store;
- add a hard-coded, versioned Release Readiness workflow definition;
- expose health, create-run, get-run, list-events, and get-artifact endpoints; and
- render a minimal start form, run page, and placeholder artifact view.

Gate:

- a blank database upgrades to head and downgrades in test;
- starting or migrating either legacy or vNext leaves the other database/schema unchanged;
- API health and lifecycle integration tests pass;
- frontend unit tests and production build pass;
- a fixture-only run persists events and an artifact;
- refresh preserves the run view; and
- legacy entry points remain unchanged.

### M3 — Read-only Release Readiness Audit

**Goal:** deliver the complete value loop against evidence without external writes.

Work:

- implement a repository allowlist;
- implement typed GitHub reads for repository metadata, exact revision, files, pull requests, issues, and checks;
- normalize source receipts and inaccessible-source results;
- implement claim extraction and evidence linking;
- implement deterministic classification validation;
- render the Markdown and JSON artifacts;
- persist partial and failed outcomes; and
- support cancellation and SSE reconnection.

Gate:

- a frozen fixture produces stable structured output;
- one owner-authorized public test repository completes read-only;
- every factual assertion in report prose is traceable to collected evidence or explicitly labeled unverified;
- unsupported, conflicting, and inaccessible sources are never silently upgraded to support;
- repository content cannot broaden permissions;
- cancellation and failure states persist; an API restart marks active runs `interrupted`; and
- there are zero external mutations.

### M4 — Review-quality trace UX

**Goal:** make the audit understandable and usable without reading raw logs.

Work:

- finish the task-start flow and access validation;
- show a compact event timeline with partial/failure receipts;
- add claim filters and source drawers;
- render the artifact with copy and download actions;
- display workflow/model/tool-policy snapshots and limitations; and
- add keyboard, focus, responsive, and basic accessibility behavior.

Gate:

- Playwright covers the happy path and inaccessible-source path in a real browser;
- refresh and reconnect preserve state;
- no action occurs without visible user intent;
- source locators are reachable or explicitly unavailable; and
- the interface is usable with keyboard-only navigation.

### M5 — Read-only evaluation and usefulness gate

**Goal:** decide with evidence whether Zakera is useful enough to continue.

Work:

- replay the 10 frozen historical cases;
- manually score material-claim recall, evidence relationships, and all four classifications;
- measure audit time, editing time, completion, latency, and cost;
- add adversarial prompt-injection and stale/force-pushed revision fixtures;
- run interruption, SSE reconnect, and concurrency tests;
- test PostgreSQL semantics before any shared deployment; and
- interview at least two intended users if the tool is moving beyond personal use.

Gate:

- 100% of factual assertions in report prose are traceable to a valid anchor or explicitly labeled unverified;
- at least 95% of claim-to-evidence relationship labels are correct;
- at least 90% of material gold claims are surfaced, so the system cannot pass by omitting difficult claims;
- every required source is retrieved or has an explicit inaccessible/unavailable receipt;
- zero fabricated sources or claims;
- at least 0.90 macro-F1 across `supported`, `unsupported`, `conflicting`, and `needs_owner_review` against the human gold set;
- at least 8 of 10 reports need no more than 15 minutes of editing;
- median human audit time falls by at least 50% from the recorded baseline;
- at least 90% of runs complete, and failures identify the unavailable source;
- zero unauthorized external actions;
- end-to-end report time is no more than 10 minutes for the evaluation profile.

Failure to meet the gate means fix, narrow, or stop. It does not justify adding more platform features.

Before this evaluation starts, freeze the repository/source-count limits, timeout, token and cost caps, baseline timing method, material-claim definition, valid-anchor rules, fabricated-claim rules, and editing-score rubric. The workflow must then be voluntarily used for three consecutive real release cycles before the product direction is considered validated for hosted-beta investment; that continuation gate does not delay declaring the technical MVP complete or an isolated M6 sandbox experiment.

### M6 — Durable approval and one sandbox write action

**Goal:** prove exact-action consent without creating a general write system.

This milestone begins only after M5 passes.

Work:

- persist opaque Agents SDK run state for interruption/resume;
- add the `Approval` model and capability policy;
- add a server-side write-capability kill switch;
- use a separate least-privilege GitHub write credential;
- produce a proposed issue or pull-request comment as an immutable draft artifact;
- display the exact target and payload immediately before approval;
- revalidate actor, target, source revision, credential scope, payload hash, and expiry on execution; and
- record an immutable result or failure receipt.

Gate:

- no write can occur before a matching approval;
- only the exact approved payload can execute;
- changed arguments require a new approval;
- denial, expiry, restart, and double-submit behave correctly;
- an idempotency key prevents duplicate publication;
- disabling the kill switch or revoking the credential blocks all writes without affecting read-only audits; and
- integration uses a mock or dedicated sandbox repository, never production by default.

### M7 — Hosted beta

**Goal:** add the minimum operational controls needed for a small invited-user beta after repeated value is proven.

Potential work:

- real session authentication and encrypted credentials/checkpoints;
- worker isolation or a durable job runner;
- retention, quotas, backup/restore, and audit export;
- managed PostgreSQL and a minimal web/API-worker deployment;

Gate:

- authentication, tenant isolation, encryption, retention, deletion, backup/restore, quotas, and audit export are verified;
- PostgreSQL concurrency and worker restart/resume tests pass;
- security review covers model-provider and GitHub data flow; and
- operational rollback is rehearsed.

### M8 — Evidence-led expansion

Potential additions include a second workflow, trusted MCP integration, scheduled runs, another model/provider, or multi-agent orchestration.

Each item requires a concrete use case, owner, threat review, acceptance test, and evidence that the existing simpler system is insufficient.

## 12. Test and evaluation strategy

### Unit tests

- state-transition rules;
- capability and approval policy;
- source normalization and content hashing;
- evidence classification;
- report validation and rendering;
- redaction; and
- idempotency keys.

### Contract tests

- GitHub adapter request/response fixtures;
- model structured-output schema;
- shared API/event contracts; and
- serialization of opaque runtime checkpoints.

### Integration tests

- blank database migration;
- complete and partial run lifecycles;
- monotonic event sequencing;
- SSE reconnect and cancellation;
- artifact immutability/versioning;
- approval deny/approve/expire/resume/double-submit; and
- PostgreSQL concurrency behavior before hosted use.

### End-to-end tests

- create an audit from the UI and inspect its report;
- unavailable source path;
- refresh during an active run;
- keyboard navigation and visible focus;
- artifact copy/download; and
- the post-MVP exact-action approval flow.

### Evaluation harness

Evaluation fixtures use no live network and include material gold claims, all four classifications, evidence-relationship labels, required sources, and acceptable source locators. Live GitHub smoke tests are opt-in and use an owner-authorized public test repository. Evaluation data is versioned separately from implementation so changing code cannot silently rewrite the expected task.

## 13. CI and delivery policy

One authoritative required workflow should run:

1. formatting and linting;
2. Python and TypeScript type checks;
3. backend unit and integration tests;
4. frontend unit tests and production build;
5. migration checks on a blank database;
6. deterministic evaluation smoke fixtures; and
7. secret scanning.

Required checks do not use `|| true`, `--exit-zero`, or `continue-on-error`. Nightly, performance, and deployment workflows are introduced only when they exercise real maintained paths and have an owner. Deployment is manual until hosted-beta requirements exist.

CI moves to that target without hiding the prototype’s existing debt:

1. inventory every workflow, trigger, ignored failure, and current branch-protection check;
2. classify existing failures as active-vNext blockers, retained legacy characterization debt, obsolete paths, or security findings;
3. require clean lint, type, test, build, migration, and evaluation checks for the new vNext namespace from its first commit;
4. retain one explicit legacy characterization check without letting it authorize vNext regressions;
5. triage each secret finding as revoked, remediated, or a narrow fingerprinted false-positive baseline—never a global ignored failure;
6. update branch protection to the authoritative check; and
7. only then delete or disable duplicate workflows.

Every pull request records:

- milestone and acceptance gate affected;
- observable behavior changed;
- tests executed and results;
- security or data-boundary changes;
- screenshots for user-facing behavior; and
- rollback approach.

## 14. Initial issue sequence

1. **M0: active-surface and CI inventory** — prerequisite for all code changes.
2. **M0: select and freeze 10 evaluation cases** — can proceed alongside inventory.
3. **M0: consolidate required CI and disable invalid scheduled/deploy paths** — depends on inventory.
4. **M1: characterize run/event lifecycle** — depends on selected legacy behavior.
5. **M1: disable unsafe tools by default** — independent safety slice.
6. **M2: approve vNext folder and contract layout** — depends on architecture decisions in this plan.
7. **M2: fresh schema and migration baseline** — depends on folder layout.
8. **M2: fixture-only run lifecycle and minimal UI** — depends on contracts and schema.
9. **M3: GitHub read adapter and source receipts** — depends on run lifecycle.
10. **M3: claim ledger, validation, and artifacts** — depends on evidence model and adapter.
11. **M4: trace/evidence/artifact review UI** — depends on stable API contracts.
12. **M5: run the frozen read-only evaluation** — begins after the read-only UI is complete.
13. **M6: exact-action approval and one sandbox comment write** — begins only if M5 passes.
14. **M7: hosted-beta controls and operational rehearsal** — begins only after repeated real use validates the direction.
15. **M8: consider the next requested capability** — requires evidence that the simpler product is insufficient.

## 15. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The release-readiness niche is useful personally but not a product | Require repeated use and two-user validation before platform investment |
| Evidence links look credible but do not prove the claim | Encode source semantics and manually score a frozen gold set |
| Repository prompt injection broadens behavior | Enforce tool and repository policy in code, independent of content |
| A moving ref makes evidence stale | Resolve and store immutable revisions and hashes |
| GitHub permissions expose or mutate data | Public repositories and read-only access in MVP; separate least-privilege write credential only after M5 |
| Model output varies | Structured output, deterministic validation, golden fixtures, artifact checks |
| SQLite hides concurrency problems | Keep local single-user scope; require PostgreSQL CI before shared use |
| SDK internals leak into the product model | Adapter boundary and opaque checkpoint storage |
| Legacy code keeps expanding maintenance scope | New isolated namespace, explicit active inventory, no broad repair effort |
| The team adds infrastructure instead of user value | Milestone gates and explicit exclusions |

## 16. Open decisions

These decisions do not block M0 documentation work, but must be resolved before their noted milestone:

- exact `apps/` versus `vnext/` repository layout — before M2;
- which OpenAI model and structured-output contract — before M3;
- definition and ownership of the 10 historical cases — during M0;
- maximum repository size, source count, token budget, latency, and cost — before M3 acceptance;
- whether any legacy user data has value — before deleting any legacy persistence path;
- the dedicated GitHub sandbox repository — before M6; and
- hosted data retention and privacy policy — before M7.

## 17. Definition of vNext MVP done

Zakera vNext is an MVP only when:

- a user can start a Release Readiness Audit for an exact allowed repository revision;
- the run is observable, durable across refresh, cancellable, and honest about partial failure;
- it produces Markdown and JSON artifacts with a claim-evidence ledger;
- every factual claim is supported or explicitly marked otherwise;
- the browser exposes no provider or GitHub credentials;
- no external mutation path exists in the read-only release;
- the required CI suite passes without ignored failures;
- the frozen 10-case evaluation meets the M5 quality thresholds.

That is the **technical MVP**. Three consecutive voluntary real-release uses are the separate product-validation gate for M7 hosted-beta investment. M6 is an optional, isolated sandbox experiment after the read-only quality gate; it is not part of the technical MVP. Anything beyond the technical MVP is an expansion, not a prerequisite.

## 18. Immediate next work

The next implementation slice is M0, not application scaffolding:

1. inventory the active API, UI, persistence, tools, workflows, and CI paths in a machine-reviewable status document;
2. select the authoritative CI workflow and propose the smallest containment patch;
3. define the 10-case evaluation template and add the first two cases without answer leakage;
4. define ADRs for the product boundary, runtime/tool boundary, fresh persistence baseline, and read-only security policy; and
5. review these documents before creating vNext runtime code.

This sequencing prevents a second agent-generated architecture from appearing before the product contract and proof standard are agreed.
