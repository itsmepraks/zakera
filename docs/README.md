# Zakera documentation

## Current direction

- [Zakera vNext product and delivery plan](VNEXT_PLAN.md) — authoritative product scope, architecture, migration strategy, security boundaries, milestones, and acceptance gates.
- [Zakera vNext status](vnext/STATUS.md) — verified legacy surface inventory, CI containment, and remaining unknowns.
- [Security and dependency baseline](vnext/SECURITY_BASELINE.md) — live scanner status, verified audit results, and unresolved risk dispositions.
- [CI/CD audit](vnext/CI_CD_AUDIT.md) — live workflow evidence, unsafe deployment findings, and the ordered remediation plan.
- [Release readiness evaluation experiment](../evaluations/release_readiness/README.md) — an earlier evidence-grounding experiment retained as useful test material, not the current product definition.
- [Agent harness research](AGENT_HARNESS_RESEARCH.md) — earlier research that informed the vNext direction; it is background material, not the product contract.

## Legacy prototype documentation

The documents below describe the older orchestration prototype. They are retained for historical reference and code archaeology. They have not all been verified against the active application and must not be treated as current production guidance.

### Setup and architecture

- [Legacy quick start](quickstart.md)
- [Environment variables](ENVIRONMENT_VARIABLES.md)
- [Architecture overview](architecture.md)
- [Memory system](MEMORY_SYSTEM.md)
- [Database persistence](DATABASE_PERSISTENCE.md)

### API, providers, and tools

- [API integration guide](api-integration-guide.md)
- [Provider integration guide](PROVIDER_INTEGRATION_GUIDE.md)
- [Local models](LOCAL_MODELS.md)
- [Tool system](tools.md)
- [Tool examples](tools-examples.md)

### Operations and security

- [Monitoring setup](MONITORING_SETUP.md)
- [Production deployment](PRODUCTION_DEPLOYMENT.md)
- [Caching strategy](CACHING_STRATEGY.md)
- [Rate limiting](RATE_LIMITING.md)
- [Security guide](SECURITY.md)
- [Troubleshooting](TROUBLESHOOTING.md)

### Development

- [CI/CD setup](ci-cd-setup.md)
- [CI/CD quick reference](ci-cd-quick-reference.md)
- [Testing](TESTING.md)

When a legacy document conflicts with [the vNext plan](VNEXT_PLAN.md), the vNext plan governs new work. A setup guide will become authoritative again only after its commands run in required CI and from a clean checkout.
