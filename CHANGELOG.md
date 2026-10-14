# Changelog

All notable changes to Zakera are documented here.

## Unreleased

### Direction

- Repositioned Zakera as a pre-alpha open-source framework for owner-controlled personal agents.
- Defined trusted continuity, inspectable execution, reviewable memory, explicit capability grants, and exact-action approval as the core product principles.
- Clarified that Zakera is not a hosted service; users will own and operate their own instances.
- Added the vNext product, architecture, migration, verification, and milestone plan.

### Safety and repository maintenance

- Disabled the unsafe legacy code-execution and unrestricted file-reading tools by default.
- Removed contradictory and unverified deployment, release, duplicate CI, performance, and badge workflows.
- Replaced the old test pipeline with an honestly scoped legacy characterization gate.
- Retained a lightweight secret scan and removed unsupported CodeQL and Dependency Review jobs by owner decision.
- Made tokenizer-dependent tests deterministic and declared SQLAlchemy's asyncio dependency explicitly.
- Documented known legacy build, migration, dependency, and deployment limitations without claiming production readiness.

### Documentation

- Rebuilt the README around the framework direction, present implementation status, architecture, safety boundaries, and roadmap.
- Marked inherited setup, operations, security, and deployment material as legacy and unverified.
- Replaced unverified contributor setup commands with milestone-aligned contribution guidance.

## Legacy prototype

The inherited prototype includes a FastAPI backend, Next.js frontend, conversation and model-selection paths, run and approval concepts, a broad provider surface, tool infrastructure, and historical deployment assets. Presence in the repository does not establish that each feature is connected, supported, secure, or production-ready.
