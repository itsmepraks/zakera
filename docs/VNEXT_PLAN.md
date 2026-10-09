# Zakera vNext: Product and Delivery Plan

**Status:** Accepted working direction
**Updated:** 2026-10-09
**Working branch:** `codex/zakera-vnext-foundation`
**Legacy baseline:** `f4849c256e7380b09b07e3c4c4a19d72fd4c0e49`

## 1. Decision

Zakera vNext will be a **personal project operator for one owner**.

It will remember approved context about the owner's goals, preferences, decisions, projects, and unfinished work. Given an outcome, it will create a plan, work through safe steps, produce artifacts, verify observable results, and pause before consequential actions.

This replaces the earlier proposal to make release readiness the product. Evidence-grounded release review remains useful as an evaluation case and possible project skill, but it is not Zakera's identity.

The project will not attempt to match the breadth of a universal life assistant or autonomous software company. The first goal is one trustworthy, end-to-end personal project workflow.

## 2. Product thesis

**Promise:** Zakera remembers what matters, keeps your projects moving, and shows its work before anything important changes.

**Primary user:** one technical or creative owner managing several ongoing projects.

**Core problem:** useful context, decisions, and unfinished work are scattered across chats, repositories, notes, and browser research. General assistants repeatedly reconstruct that context, while highly autonomous agents can act without enough visibility or control.

**Differentiator:** trusted continuity.

- **Personal:** the owner chooses what Zakera knows and remembers.
- **Persistent:** projects and open loops survive beyond one chat.
- **Capable:** Zakera performs bounded work, not only conversation.
- **Inspectable:** plans, sources, tool activity, artifacts, failures, and uncertainty remain visible.
- **Controlled:** access is explicit and consequential actions require exact approval.

## 3. Inspiration and boundaries

| Inspiration | Principle to adopt | What not to copy yet |
| --- | --- | --- |
| Muse | Long-term goals, personal continuity, background progress, owner-controlled access | Universal consumer scope, payments, or secure-VM claims |
| OpenClaw | User-owned state, local-first operation, replaceable models and tools, channel adapters | Large plugin marketplace, many channels, or unrestricted host tools |
| Instinct | Low-friction interaction and awareness of the owner's active work | Invisible computer control or broad life administration |
| Devin | Durable task workspace, explicit planning, progress visibility, testing, and reviewable results | Developer-only identity, autonomy marketing, or parallel agent teams |

Zakera's product language must describe intended behavior separately from implemented behavior. Inspiration is not affiliation, compatibility, or feature parity.

## 4. First complete workflow: Personal Project Run

### 4.1 Inputs

- a selected project;
- a plain-language outcome;
- optional constraints and completion criteria;
- owner-approved profile and project context;
- explicitly enabled read sources; and
- an isolated workspace when file changes are allowed.

### 4.2 Workflow

1. Resolve the project, permissions, available context, and requested outcome.
2. Restate scope, uncertainty, and completion criteria.
3. Create a reviewable plan with bounded steps.
4. Gather only allowed context and sources.
5. Perform read, analysis, drafting, or isolated workspace actions.
6. Record public run events, artifacts, evidence, failures, and blockers.
7. Verify observable results in proportion to the task.
8. Request approval for any external write or difficult-to-reverse action.
9. Produce a final artifact and concise project update.
10. Propose memory changes for owner review; do not silently make durable personal inferences.

### 4.3 Initial task classes

- research a decision and produce a source-backed brief;
- understand a repository or document set;
- draft or revise project documentation;
- plan a feature or creative project;
- prepare and test code changes in an isolated workspace; and
- summarize progress, blockers, decisions, and next actions for an existing project.

### 4.4 MVP completion gate

The first workflow is complete only when a user can:

- create or select a project;
- start a run with an explicit outcome;
- inspect the plan and live/replayed progress;
- see which context and tools were used;
- receive a persisted artifact;
- cancel a running task;
- recover an inspectable terminal state after failure;
- review proposed memory changes; and
- verify that no unapproved external write occurred.

## 5. MVP exclusions

The first release does not include:

- a universal life assistant;
- payments, purchases, booking, or financial actions;
- unrestricted browser, desktop, shell, or filesystem control;
- autonomous email, messaging, social posting, or account changes;
- proactive scheduling or work that starts without explicit opt-in;
- multi-agent teams or automatic delegation;
- a public tool/plugin marketplace;
- many model providers or automatic model routing;
- shared accounts, teams, roles, or billing;
- hosted production deployment;
- Kubernetes, Terraform, or a large observability stack; or
- migration of legacy conversations or credentials.

## 6. Experience

The initial web interface has five surfaces:

1. **Projects** — goals, status, approved context, open loops, and recent artifacts.
2. **Start run** — outcome, constraints, context scopes, tools, and completion criteria.
3. **Run timeline** — plan, progress, tool activity, evidence, approvals, failures, and cancellation.
4. **Artifact review** — rendered output, files, verification, limitations, and download/copy actions.
5. **Memory review** — proposed memories with accept, edit, reject, and forget controls.

Conversation may support these tasks, but chat is not the primary data model. Runs, projects, artifacts, approvals, and memories are durable product objects.

## 7. Target architecture

```text
Next.js project and run UI
             |
             v
Thin FastAPI application
  |-- project service
  |-- run application service
  |-- reviewable memory service
  |-- artifact and verification service
  |-- append-only run event stream (SSE)
  |-- capability and approval policy
  |-- agent runtime adapter
  |-- typed tool gateway
  |-- isolated workspace adapter
  `-- repositories
        |-- profile and project
        |-- run, step, and event
        |-- memory proposal and record
        |-- artifact and verification
        `-- grant, approval, and receipt
```

### 7.1 Technology decisions

| Concern | Decision | Reason |
| --- | --- | --- |
| Interface | Next.js | Fits the inherited repository and review-heavy workflow |
| API | Thin FastAPI application | Preserves useful Python behavior while keeping policy outside the model |
| Persistence | New SQLAlchemy 2 metadata and Alembic history | The legacy migration graph is not a reliable foundation |
| Initial database | SQLite | Appropriate for one local owner |
| Events | Persisted events with SSE delivery | Supports observable progress and replay |
| Runtime | Adapter boundary with one supported implementation | Avoids coupling product state to one SDK while preventing premature provider sprawl |
| Tools | Typed direct adapters first | Easier to authorize, validate, and test than arbitrary plugins |
| Workspace | Isolated per-run directory with explicit allowed roots | Prevents the legacy unrestricted file boundary |
| Artifacts | Files plus structured metadata | Keeps results useful outside the chat UI |

PostgreSQL, durable workers, additional model providers, MCP, native apps, and messaging channels are deferred until the local single-user workflow passes its gates.

### 7.2 Domain model

| Entity | Responsibility |
| --- | --- |
| `OwnerProfile` | Explicit preferences and stable owner-authored context |
| `Project` | Goal, status, approved context, open loops, and policies |
| `ProjectSource` | Allowed repository, document, URL, or connector scope |
| `Run` | Outcome, context snapshot, plan version, status, and terminal result |
| `RunStep` | Bounded unit of work with status and verification outcome |
| `RunEvent` | Append-only public event for timeline and replay |
| `Artifact` | Versioned file or structured result produced by a run |
| `MemoryProposal` | Candidate durable context awaiting owner review |
| `MemoryRecord` | Accepted memory with provenance, scope, and lifecycle controls |
| `ToolGrant` | Capability and target scope allowed for a run |
| `Approval` | Exact pending consequential action and owner decision |
| `ActionReceipt` | Immutable result of an approved external action |

### 7.3 Run lifecycle

```text
queued -> planning -> working -> verifying -> completed
   |         |           |           |
   +---------+-----------+-----------+-> failed
   +---------+-----------+-------------> canceled
   +---------+-----------+-------------> completed_with_gaps
                       |
                       +-> awaiting_approval -> working
```

Terminal states are `completed`, `completed_with_gaps`, `failed`, and `canceled`. An API restart marks in-flight work `interrupted` until durable recovery is deliberately implemented. The product must never imply that background work is durable before that gate passes.

## 8. Memory model

Memory is a user-facing product feature, not an opaque model side effect.

### 8.1 Memory scopes

- **Owner profile:** explicit preferences that apply broadly.
- **Project memory:** decisions, constraints, vocabulary, and open loops for one project.
- **Run context:** immutable context snapshot used for one run.
- **Transient scratch state:** implementation state that expires and is never presented as personal memory.

### 8.2 Memory rules

- The agent may propose but not silently create durable personal memories.
- Every memory has provenance, scope, creation time, and an owner-visible reason.
- The owner can accept, edit, reject, forget, export, or disable memory.
- Sensitive values and credentials are never stored as conversational memory.
- Conflicting memories remain visible until the owner resolves them.
- Deleted memory must stop appearing in newly created run snapshots.

## 9. Capability and approval policy

Tools are classified as:

- `read` — inspect an allowed source;
- `draft` — create an artifact without external side effects;
- `workspace_write` — change files only inside an isolated run workspace;
- `external_write` — change an external system;
- `execute` — run code or commands in a bounded environment; or
- `secrets` — access credentials without exposing them to model context.

Only explicitly granted capabilities are available to a run. Adding a tool grants no authority by default.

An approval binds to the owner, run, tool, capability, target, normalized arguments, payload hash, source revision where relevant, expiry, and idempotency key. Any material change invalidates the approval.

External content is untrusted data. Instructions in repositories, websites, documents, issues, or tool output cannot change capability policy, memory policy, or approval requirements.

## 10. Workspace and execution safety

- Each run receives a dedicated workspace and explicit allowed roots.
- Host paths, environment variables, and credentials are unavailable by default.
- Command execution is absent until a real containment boundary is selected and tested.
- Time, output, storage, and network limits are required before execution is enabled.
- Workspace changes are reviewable artifacts; they do not become external writes automatically.
- Cancellation must stop child work or record precisely what could not be stopped.

The legacy in-process Python executor is not a sandbox and will not be reused.

## 11. Privacy and data ownership

- Local-first storage is the default for the single-user release.
- Credentials are server-managed and referenced by handles, never stored in prompts or run artifacts.
- Logs and artifacts apply deterministic secret redaction before persistence.
- Source access is scoped per project and snapshotted per run.
- Export and deletion behavior must be testable before personal memory is considered complete.
- Telemetry is off unless explicitly enabled and documented.

## 12. Verification strategy

### 12.1 Required test layers

- domain tests for lifecycle, memory, capability, and approval transitions;
- repository tests against a fresh vNext database;
- integration tests for event ordering, replay, cancellation, and artifacts;
- adapter contract tests for every tool and runtime boundary;
- frontend tests for project, run, approval, error, and memory-review states;
- one production frontend build;
- blank-database migration up and down tests; and
- deterministic workflow evaluations using recorded or synthetic sources.

### 12.2 Evaluation dimensions

- task completion against explicit criteria;
- correct use of approved context;
- unsupported claim rate;
- plan and artifact usefulness;
- action-policy compliance;
- memory proposal precision and privacy;
- cancellation and failure honesty; and
- reproducibility at a pinned configuration.

The existing release-readiness cases remain useful evidence-grounding fixtures. New personal-project cases must cover research, writing, repository work, memory conflicts, unavailable sources, denied approvals, cancellation, and failed verification.

## 13. Migration strategy

The legacy application remains recoverable while vNext is built in isolation.

- Do not consolidate the duplicated legacy frontend before the replacement path exists.
- Do not repair the legacy Alembic graph into the vNext database.
- Do not inherit the full provider or tool registry.
- Do not migrate legacy conversations, users, credentials, or telemetry by default.
- Reuse a behavior only after black-box characterization proves it is valuable.
- Remove or archive a legacy surface only when its replacement or retirement is explicit.

## 14. Milestones

### M0 — Truth and containment

- honest README, package metadata, and documentation index;
- unsafe legacy tools disabled by default;
- mutation-capable deployment automation removed;
- CI describes only what it actually verifies; and
- repository risks and unsupported paths are documented.

### M1 — Characterize useful behavior

- black-box tests for run events, approval, cancellation, and artifacts;
- written salvage/replace decisions for each boundary; and
- at least eight additional evaluation inputs reviewed before implementation tuning.

### M2 — Isolated foundation

- new vNext package and frontend route boundaries;
- fresh schema and migration history;
- owner profile, project, run, event, artifact, and memory-proposal records;
- capability policy and isolated workspace contract; and
- strict CI for the new paths.

### M3 — Personal Project Run

- one end-to-end workflow meeting the MVP completion gate;
- persisted timeline and artifacts;
- deterministic verification and evaluation results; and
- no unapproved external writes.

### M4 — Approved actions

- one narrow external write adapter selected from demonstrated need;
- exact preview, approval, idempotency, and immutable receipt;
- retry and ambiguous-outcome handling; and
- adversarial policy tests.

### M5 — Continuity

- restart-safe execution or honest interruption recovery;
- opt-in background continuation;
- explicit notification rules; and
- proactive suggestions only after relevance, privacy, and dismissal controls pass evaluation.

## 15. Public presentation gate

Before presenting Zakera as runnable on a website or public repository:

- verify a clean local install from documented commands;
- provide one real screenshot or demo from the active interface;
- publish only tested capabilities;
- show the current milestone and known limitations;
- remove or clearly quarantine unsupported deployment material;
- verify license, repository description, topics, homepage, and social preview; and
- ensure CI is green without paid or unavailable repository features.

## 16. Open decisions

The following remain intentionally unresolved until their milestone:

- the first supported runtime/model implementation;
- the isolation mechanism required before command execution;
- the first external write action;
- whether the first website is documentation-only or an interactive local demo;
- the threshold for enabling durable background work; and
- whether release-readiness evaluation becomes an optional skill or stays test-only.

These decisions must be driven by the first complete workflow, not by feature parity with the inspiration products.
