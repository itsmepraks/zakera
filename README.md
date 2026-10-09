# Zakera

> **Project status: pre-alpha redesign.** Zakera currently contains an older, agent-generated FastAPI and Next.js prototype. The product direction is defined below, but the new experience is not implemented yet and the repository is not ready for production use.

**A personal project operator that remembers what matters, keeps work moving, and leaves you in control.**

Zakera is being redesigned for one owner with many ongoing projects. Instead of starting every conversation from zero, it will carry forward approved context about your goals, preferences, decisions, and unfinished work. Give it an outcome; Zakera should assemble a plan, work through safe steps, produce useful artifacts, and pause before consequential actions.

The goal is not maximum autonomy. The goal is **trusted continuity**: useful work over time, with visible progress and exact control over what the agent can read or change.

## Why Zakera

Most assistants are either disposable chats or powerful agents with too little context and too much access. Zakera is exploring a more personal middle ground:

- **Personal continuity** — projects, decisions, preferences, and open loops persist with the owner's knowledge.
- **Real execution** — the agent can research, plan, draft, inspect, test, and prepare changes instead of only answering questions.
- **Inspectable work** — plans, sources, tool activity, artifacts, failures, and pending decisions remain visible.
- **Owner control** — access is explicit, memory is reviewable, and consequential actions require approval.
- **User-owned foundations** — local-first storage and replaceable models or tools are preferred where practical.

Zakera's strongest idea is the combination of personalization and evidence: it should know enough to be useful without asking for blind trust.

## First product slice

The first complete workflow will be a **personal project run** for technical and creative work:

1. choose a project and describe an outcome;
2. load only the profile, project context, and sources allowed for that run;
3. create a reviewable plan with clear completion criteria;
4. perform read, analysis, drafting, and isolated workspace steps;
5. show progress, evidence, artifacts, blockers, and uncertainty;
6. ask for approval before any external write or difficult-to-reverse action; and
7. save a concise project update and proposed memory changes for review.

Early tasks may include researching a decision, understanding a repository, drafting documentation, planning a feature, preparing code changes in an isolated workspace, and maintaining a project brief. Broad life administration, unrestricted computer control, and autonomous external communication are later possibilities—not MVP promises.

## Inspiration

Zakera learns from several products without attempting to clone them:

| Project | What Zakera takes from it |
| --- | --- |
| [Muse](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/) | A personal agent should understand long-term goals, continue useful work, and give the owner control over access. |
| [OpenClaw](https://github.com/openclaw/openclaw) | State should be user-owned where practical; models, tools, and interaction channels should be replaceable boundaries. |
| [Instinct](https://instinct.com/) | The interface should feel natural and low-friction, and the agent should understand what the owner is working on. |
| [Devin](https://devin.ai/) | Longer tasks need a durable workspace, an explicit plan, observable progress, verification, and reviewable results. |

Zakera is an independent personal project and is not affiliated with these products or companies.

## Current reality

| Area | Current state |
| --- | --- |
| Legacy application | FastAPI backend and Next.js frontend are present |
| Conversations and model selection | Present in the legacy prototype |
| Run, step, event, and approval concepts | Present; retained as material to characterize |
| Unsafe code and unrestricted file tools | Disabled by default in the legacy prototype |
| Personal profile and project context | Planned |
| Reviewable long-term memory | Planned |
| Durable background execution | Planned |
| Browser, desktop, messaging, or voice control | Not implemented |
| Secure execution sandbox | Not implemented |
| Hosted service or production deployment | Not supported |

The repository also contains duplicated frontend surfaces, inconsistent database migrations, legacy dependency debt, and operations documents that have not been verified. File presence is not treated as proof that a feature works.

## Product principles

1. **One owner first.** Build a genuinely useful personal agent before a team platform.
2. **Context is permissioned.** A run receives only the profile, project, source, and credential scopes it needs.
3. **Memory is reviewable.** The agent proposes durable memories; the owner can accept, edit, reject, or forget them.
4. **Read, draft, and act are different capabilities.** New tools receive no authority by default.
5. **Approval binds to the exact action.** Changing the target, arguments, or payload requires new approval.
6. **Work must be inspectable.** Progress, evidence, artifacts, failures, and uncertainty remain visible.
7. **Verification is part of execution.** A task is not complete because an agent says it is.
8. **Small, reversible slices win.** Prove one end-to-end workflow before adding channels, agents, or infrastructure.

## Directional architecture

```text
Web interface
  -> thin application API
      -> project and run service
      -> reviewable memory service
      -> append-only event timeline
      -> policy and approval engine
      -> agent runtime adapter
      -> typed tool gateway
      -> isolated workspace adapter
      -> local SQLite repositories
```

The current direction keeps Next.js and a thin FastAPI service, introduces a fresh database and migration history for vNext, and keeps the agent runtime behind an adapter. SQLite is the first local store. Shared hosting, PostgreSQL, durable workers, and additional interaction channels come only after the single-user workflow is proven.

See the [vNext product and delivery plan](docs/VNEXT_PLAN.md) and the [verified repository status](docs/vnext/STATUS.md) for detailed boundaries and milestones.

## Roadmap

- **M0 — Truth and containment:** document the inherited system, disable unsafe defaults, and simplify CI. In progress.
- **M1 — Characterize useful legacy behavior:** lock down run events, approval, cancellation, and artifacts with black-box tests.
- **M2 — Isolated foundation:** create the new profile, project, run, memory, policy, and artifact boundaries without importing legacy state.
- **M3 — Personal project run:** deliver one complete read/draft/workspace workflow with visible progress and verification.
- **M4 — Approved actions:** add narrowly scoped external writes with exact previews, approval receipts, and idempotency.
- **M5 — Continuity:** add restart-safe execution and opt-in background or proactive work only after recovery behavior is proven.

## Running the project

There is intentionally no endorsed quick start yet. The checked-in setup guides describe the legacy prototype and have not been revalidated from a clean checkout. Publishing commands that merely look plausible would be misleading.

A supported local setup will be added when it is exercised in CI and verified from a clean machine. Until then, treat documentation under [`docs/`](docs/README.md) as either current planning material or explicitly labeled legacy reference.

## Contributing

The highest-value work is currently:

- defining the personal profile, project context, and memory-review contracts;
- adding black-box tests for run events, cancellation, approval, and artifact behavior;
- implementing the isolated vNext data model and migration baseline;
- building the first personal project run end to end; and
- removing misleading or unsafe legacy surfaces without broad rewrites.

Keep changes focused, reversible, and tied to a milestone acceptance gate. Do not add new providers, channels, multi-agent orchestration, or deployment infrastructure without a demonstrated need.

## License

MIT
