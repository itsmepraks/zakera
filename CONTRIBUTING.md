# Contributing to Zakera

Zakera is a pre-alpha open-source framework for people to build and run their own personal project agents. Each instance is owner-controlled; the project does not operate a hosted service. The current repository includes a legacy prototype, and the accepted direction and milestone gates are documented in [`docs/VNEXT_PLAN.md`](docs/VNEXT_PLAN.md).

## Current priorities

The highest-value contributions are:

- black-box tests for legacy run events, cancellation, approval, and artifacts;
- contracts for owner profile, project context, reviewable memory, and isolated workspaces;
- the isolated vNext schema and migration baseline;
- one complete personal project run; and
- focused removal or quarantine of misleading legacy surfaces.

Please do not add providers, tools, channels, multi-agent orchestration, provider-specific deployment infrastructure, or broad dependency upgrades without an agreed framework need.

## Development setup

There is no supported clean-install guide yet. Previous setup instructions described the inherited prototype and were not verified end to end. Publishing them here would overstate the state of the project.

Until a clean-checkout setup is added and exercised in CI:

- use the commands in the active GitHub Actions workflows as the maintained verification reference;
- treat other setup and deployment documents as legacy material; and
- describe any local environment assumptions in your pull request.

## Making changes

1. Start from `main` and create a focused branch.
2. Keep the change tied to one milestone outcome.
3. Add tests for observable behavior when behavior changes.
4. Run the relevant maintained backend or frontend checks.
5. Record checks that were not run and explain why.
6. Open a pull request that distinguishes implemented behavior from intended behavior.

## Change principles

- Preserve unrelated work and legacy behavior unless retirement is explicit.
- Prefer small, reversible changes over broad cleanup.
- Do not treat file presence or an agent's statement as proof that behavior works.
- Never include credentials or environment-file values in commits, logs, fixtures, or issues.
- Keep external writes and difficult-to-reverse actions behind exact approval boundaries.
- Surface discovered design debt separately instead of expanding a focused change.

## Reporting issues

Include:

- expected and actual behavior;
- minimal reproduction steps;
- operating system and relevant runtime versions;
- the exact commit or branch; and
- logs with credentials and personal data removed.

Questions, product ideas, and rough proposals are welcome as GitHub issues.
