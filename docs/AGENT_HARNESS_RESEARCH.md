# Agent Harness Research Memo

Last updated: 2026-06-10

## Executive summary

Zakera is best understood as an AI agent harness: the control layer around one or more language models that makes them useful for real work. The model supplies reasoning and generation. The harness supplies tools, memory, routing, state, approvals, observability, safety boundaries, and user experience.

The strongest agent systems in 2026 are not merely chat apps with tool calling. They are durable, observable execution environments. They make tool use inspectable, preserve state across failures and long tasks, define clear approval gates for risky actions, and treat memory as a first-class product surface.

Zakera's strongest potential position is:

> A provider-flexible, local-friendly, observable agent harness for personal and developer workflows.

That implies a sharper focus than "support every agent feature." Zakera should first make one complete harness loop excellent: user request, context loading, provider routing, tool execution, memory update, trace display, and resumable task state.

## What an agent harness does

An agent harness wraps a model with the machinery required to complete multi-step work:

- Model abstraction: select, call, stream, retry, and compare providers.
- Tool interface: expose external capabilities with typed schemas, permissions, and result handling.
- Memory: manage short-term context, long-term facts, summaries, preferences, and retrieval.
- Orchestration: decide whether the app, a workflow, or the model controls the next step.
- State: persist intermediate work, task status, artifacts, and execution history.
- Human review: pause before sensitive, irreversible, expensive, or ambiguous actions.
- Safety boundaries: sandbox code, isolate browser/computer actions, validate tool inputs and outputs.
- Observability: trace model calls, tool calls, handoffs, guardrails, costs, latency, and failures.
- User experience: show what the agent is doing without flooding the user with raw internals.

The useful mental model is:

> Agent = model + harness.

The harness is where product quality, trust, reliability, and differentiation usually live.

## Best-in-class references

### LangGraph

LangGraph is the strongest reference for stateful production orchestration. Its core strengths are durable execution, human-in-the-loop control, streaming, checkpointing, and graph-shaped workflows. It is less about "magic agents" and more about making agent execution explicit and resumable.

Lesson for Zakera: build a durable run model. Every meaningful step should be persistable, inspectable, and resumable.

### OpenAI Agents SDK

OpenAI's Agents SDK is a strong reference for clean agent primitives: agents, tools, handoffs, guardrails, structured outputs, run state, and tracing. Its concepts are clear and developer-friendly, even when Zakera needs to remain provider-agnostic.

Lesson for Zakera: define crisp local primitives: Agent, Tool, Run, Step, Trace, Guardrail, Approval, MemoryWrite, and Artifact.

### Anthropic agent harness guidance

Anthropic's strongest contribution is conceptual: long-running agents need more than a bigger context window. They need compaction, progress artifacts, initializer agents, incremental work loops, and clear handoff state for the next run. Their managed-agent writing also frames the harness as an evolving assumption layer: as models improve, the harness should be revisited instead of fossilized.

Lesson for Zakera: support long-running work through explicit progress logs, compaction, resumable tasks, and small verified increments.

### Model Context Protocol

MCP is the leading standard for connecting AI applications to external tools, resources, prompts, files, databases, and workflows. It makes tool ecosystems portable across hosts.

Lesson for Zakera: avoid inventing a closed tool universe. Native tools are useful, but MCP compatibility should be part of the long-term harness story.

### CrewAI

CrewAI is a useful reference for role-based multi-agent composition and fast prototyping. It is strongest when the user wants to model a team of agents with goals, roles, memory, tools, and delegation.

Lesson for Zakera: multi-agent features should be introduced only when a single-agent workflow cannot express the task cleanly.

### AutoGen and Microsoft Agent Framework

AutoGen popularized multi-agent collaboration, user proxy agents, and human-in-the-loop patterns. The newer Microsoft direction is relevant mainly for enterprise and .NET/Azure-heavy ecosystems.

Lesson for Zakera: human-in-the-loop should be a first-class interaction pattern, not an afterthought bolted onto tool execution.

### LlamaIndex Workflows

LlamaIndex is strongest around data-aware and RAG-grounded agents. Its workflow model is useful for event-driven orchestration with shared state and explicit steps.

Lesson for Zakera: memory and retrieval should be workflow-aware. Context should be selected deliberately, not dumped into prompts.

### Google ADK

Google's Agent Development Kit is a code-first framework for building, evaluating, debugging, and deploying agents, including multi-agent systems. Its enterprise posture emphasizes lifecycle tooling as much as agent primitives.

Lesson for Zakera: agent development needs a lifecycle: scaffold, run, inspect, evaluate, deploy, and monitor.

### Pydantic AI

Pydantic AI is a useful reference for typed outputs, structured validation, tool schemas, and Python-native developer ergonomics.

Lesson for Zakera: type boundaries matter. Tool inputs, model outputs, memory records, and run events should be schema-validated wherever possible.

## Core harness patterns

### Single-agent tool loop

A single model receives instructions, chooses tools, observes results, and continues until it can answer or complete the task.

Best for:
- Chat with search/tools
- Simple research
- Code helper actions
- Personal assistant tasks

Risk:
- Easy to make opaque
- Can loop or overuse tools
- Needs step limits and trace display

### App-owned workflow

The application owns the sequence: classify intent, gather context, call model, validate output, execute tool, persist result.

Best for:
- Production workflows
- Compliance-sensitive tasks
- Repeated automations
- Tasks with known structure

Risk:
- Less flexible
- More engineering upfront

### Graph or state-machine orchestration

The task is represented as nodes, edges, interrupts, checkpoints, and resumable state.

Best for:
- Long-running workflows
- Multi-step business processes
- Human approvals
- Failure recovery

Risk:
- Can become over-modeled before product-market clarity

### Multi-agent delegation

Specialized agents collaborate, critique, review, or hand off work.

Best for:
- Planning plus execution
- Research plus synthesis
- Generator/evaluator loops
- Complex tasks with separable roles

Risk:
- Token/cost growth
- Harder debugging
- Often unnecessary for MVP

### Computer/browser harness

The agent acts through browser or desktop controls, often in a sandbox with screenshots and action APIs.

Best for:
- Web workflows without APIs
- QA and form-filling
- End-user automation

Risk:
- Fragile
- Security-sensitive
- Requires strict isolation and approvals

### Long-running resumable harness

The agent works across sessions using compaction, persistent progress logs, artifacts, task state, and incremental goals.

Best for:
- Software development
- Research projects
- Data analysis
- Complex operational work

Risk:
- State corruption
- Hidden drift
- Requires disciplined checkpoint design

## Product use cases for Zakera

### 1. Multi-provider agent workbench

Let users compare providers, route tasks, see latency/cost, and switch between hosted and local models.

Why Zakera fits:
- Existing provider layer is one of the repo's strongest assets.

### 2. Personal workflow assistant

Run personal tasks with memory, tool use, reminders, summaries, and user approvals.

Why Zakera fits:
- The product narrative already points toward proactive assistance and habits.

### 3. Developer harness

Inspect repos, edit files, run tests, summarize changes, and create traceable work sessions.

Why Zakera fits:
- Developer workflows are high-value, tool-heavy, and benefit from observability.

### 4. Knowledge and memory assistant

Search documents, conversations, notes, and user preferences with explicit memory controls.

Why Zakera fits:
- Memory is central to the vision, but it needs a clearer user-facing model.

### 5. Ops and monitoring assistant

Explain service health, alerts, performance, and deployment issues.

Why Zakera fits:
- The repo already has monitoring, health checks, metrics, and deployment artifacts.

### 6. Local/private AI harness

Expose local models, local files, and local workflows with a privacy-forward design.

Why Zakera fits:
- Provider flexibility and local Ollama support can distinguish it from cloud-first SDKs.

## What Zakera should copy

- From LangGraph: durable state, checkpoints, interrupts, resumable runs.
- From OpenAI Agents SDK: clean primitives, traces, guardrails, handoffs, structured run results.
- From Anthropic: long-running work discipline, compaction, progress artifacts, incremental sessions.
- From MCP: interoperable tools and resources.
- From Pydantic AI: typed schemas and validation-first developer ergonomics.
- From LlamaIndex: deliberate context retrieval and workflow-aware memory.
- From CrewAI: simple role abstractions when multi-agent work is genuinely needed.

## What Zakera should avoid

- Do not become only a provider aggregator. Provider routing is a feature, not the whole product.
- Do not expose half-wired features as if they are complete.
- Do not add multi-agent orchestration before the single-agent run loop is excellent.
- Do not hide memory writes. Users need to inspect, edit, and revoke memory.
- Do not treat observability as only Prometheus metrics. Agent traces are product UX.
- Do not make the frontend a playground of disconnected components. The UI should serve the harness loop.
- Do not build a closed tool ecosystem if MCP compatibility is feasible.

## Suggested Zakera architecture direction

### Harness primitives

Zakera should introduce or formalize these concepts:

- `Agent`: instructions, model preferences, allowed tools, memory policy, guardrail policy.
- `Run`: one user-visible task execution, with status, owner, timestamps, cost, and result.
- `Step`: an LLM call, tool call, approval request, memory operation, handoff, or validation event.
- `Tool`: typed capability with schema, permission level, timeout, and result contract.
- `Approval`: a resumable pause before sensitive actions.
- `Trace`: ordered run events suitable for user display and debugging.
- `Artifact`: files, summaries, plans, reports, code patches, or structured outputs created by a run.
- `MemoryRecord`: explicit saved fact/preference/context item with source and expiry/revocation options.
- `Policy`: limits around tools, cost, models, data access, and autonomy.

### MVP harness loop

The first serious milestone should be:

1. User starts a task from the UI.
2. Zakera creates a `Run`.
3. Zakera loads conversation and memory context.
4. Model manager selects a provider.
5. Agent may call one or more tools.
6. Each model/tool action becomes a trace `Step`.
7. Risky tool calls require an `Approval`.
8. Final answer and artifacts are saved.
9. Useful memory writes are proposed or recorded.
10. User can inspect the run trace afterward.

This is more important than adding another provider or another advanced deployment manifest.

## Immediate roadmap recommendation

### Phase 1: Make the harness spine real

- Define `Run` and `Step` persistence.
- Normalize tool schemas and execution results.
- Add trace capture for model calls and tool calls.
- Make one chat path use the run/step model end to end.
- Show the trace in the frontend in a compact "agent activity" panel.

### Phase 2: Make trust visible

- Add approval gates for high-risk tools.
- Add memory inspection and deletion.
- Add per-run model, token, latency, and cost metadata.
- Add task status: queued, running, waiting_for_approval, failed, completed.

### Phase 3: Make long-running work possible

- Add resumable runs.
- Add compaction/summarization checkpoints.
- Add progress artifacts.
- Add retry/failure recovery semantics.

### Phase 4: Expand interoperability

- Add MCP client support.
- Add importable/exportable tool definitions.
- Add plugin-like tool registration.
- Add provider capability registry.

### Phase 5: Add advanced orchestration selectively

- Add workflow graphs only for repeated multi-step tasks.
- Add multi-agent handoffs only where roles improve results.
- Add browser/computer harness only inside strict sandboxes.

## Zakera positioning

Working positioning:

> Zakera is an open-source AI agent harness for running useful workflows across models, tools, and memory, with transparent traces and local-first control.

Shorter:

> A transparent, provider-flexible harness for personal and developer AI agents.

What makes it distinct:

- Provider freedom instead of model lock-in.
- Local/private mode as a first-class path.
- Memory the user can inspect and control.
- Agent traces as part of the product experience.
- Practical workflows over abstract multi-agent theater.

## Source notes

- OpenAI Agents SDK: agents, tools, handoffs, guardrails, state/results, tracing.
- LangGraph: durable execution, streaming, human-in-the-loop, stateful orchestration.
- Anthropic engineering posts: effective agents, long-running harnesses, managed agents.
- Model Context Protocol: standard external tool/resource/prompt connections.
- CrewAI docs: role-based agents, crews, flows, tools, memory, observability.
- AutoGen docs: multi-agent collaboration and human-in-the-loop.
- LlamaIndex docs: agents, workflows, event-driven orchestration, memory/RAG.
- Google ADK docs: code-first build/debug/deploy lifecycle for enterprise agents.
- Pydantic AI docs: typed outputs, tool schemas, structured validation.
