# Zakera CI/CD Audit

**Snapshot date:** 2026-09-20
**Live verification:** [PR #66](https://github.com/itsmepraks/zakera/pull/66)
**Scope:** all tracked GitHub Actions workflows, supporting label/Dependabot configuration, and referenced deployment artifacts

## Conclusion

The repository does not have a trustworthy deployment pipeline. The two mutation-capable workflows describe different release paths, mix placeholder and real destructive commands, and contradict the checked-in infrastructure. They should be removed from the active Actions surface until a deployment target is deliberately designed and rehearsed.

The test workflow is useful only as a legacy characterization check. It does not prove a production build or a clean lint/type baseline. Security and maintenance workflows have several repairable configuration issues, some of which PR #66 has already exposed and corrected.

## Workflow inventory and disposition

| Workflow | Current evidence | Disposition |
| --- | --- | --- |
| `test.yml` | Maintained backend subset and frontend Jest run in PRs; lint/type/build are known exclusions | Retained and renamed as legacy characterization; not the vNext required gate |
| `security.yml` | CodeQL plus Gitleaks are meaningful; Gitleaks now passes after a minimum permission fix; Dependency Review is unsupported by current repository settings | Retain code/secret scanning; unsupported dependency job removed and ecosystem-audit gap tracked explicitly |
| `lint-pr-title.yml` | Failed on the initial PR title and passed after correction | Retain with read-only permissions |
| `pr-labels.yml` | Initially failed due to missing checkout and obsolete labeler schema; passed after both fixes | Retain as repository maintenance, not a product-quality gate |
| `cd.yml` | No verified target; EKS Terraform conflicts with ECS commands; multiple checks are suppressed | Removed from active workflows on this branch |
| `release.yml` | Publishes images/releases through an unverified path; no frontend build; release metadata is internally inconsistent | Removed from active workflows on this branch |

The earlier `ci.yml`, `ci-cd-multi-env.yml`, `performance.yml`, and `badges.yml` definitions were already removed after live GitHub settings showed no branch protection or ruleset depended on their check names.

## Deployment workflow findings

### Infrastructure and runtime disagree

- Root Terraform provisions EKS and Kubernetes/Helm providers.
- `cd.yml` searches for and mutates ECS services.
- The workflow supplies `image_tag`, but root Terraform defines no such variable.
- The workflow reads `load_balancer_url`, but root Terraform defines no such output.
- Terraform's backend defaults to a production state key while the workflow overrides only the key string and does not prove that separate staging state or infrastructure exists.

### Safety gates are ineffective

- The workflow can be dispatched from an arbitrary ref and immediately pushes images and applies Terraform.
- It uses long-lived AWS access-key secrets instead of a scoped, short-lived identity flow.
- It pushes a mutable `latest` tag.
- Trivy runs after the image is pushed and uses `exit-code: '0'`, so critical/high findings cannot stop deployment.
- Staging smoke tests use `continue-on-error: true`.
- Production backup failure is swallowed.
- Rollback references an undefined `PREVIOUS_TASK_DEF` and also swallows rollback failure.
- Post-deployment migration and CDN steps are placeholders but report as successful.
- Release creation is allowed to fail without failing deployment.
- The final summary always says the pipeline completed, even when earlier jobs fail.

### Unverified external assumptions

The workflows name AWS accounts/resources, ECR repositories, state buckets, ECS clusters, RDS instances, Slack webhooks, and `zakera.app` endpoints. Their existence and ownership have not been established. No workflow should touch them until the target, credentials, environment approvals, rollback path, and recovery drill are verified.

## Release workflow findings

- The manually entered version is not converted into a tag/ref before Docker metadata calculates semver tags.
- Shell substitution appears inside an action input (`BUILD_DATE=$(date ...)`) where it is not evaluated as a shell command.
- Backend tests run, but frontend tests, TypeScript checks, and a production frontend build do not.
- Images are published before the GitHub release is created.
- `actions/create-release@v1` is a legacy action and the workflow does not establish a deliberate modern release contract.
- Generated notes link to `UPGRADE.md`, which does not exist.
- The staging deployment contains only placeholder echo commands.
- The deploy job references build output without directly depending on the build job.
- The requested `release_type` input is never used.

## Test workflow findings

- The original name and final `CI Success` job overstated the proof provided by the workflow; both are now explicitly legacy-characterization labels.
- The ignored Flake8 and TypeScript steps were removed rather than displayed as successful checks; their known failures remain documented debt.
- No frontend production build runs.
- No Python type check, migration test, deterministic evaluation smoke test, or dependency audit runs.
- Python dependencies are installed from broad ranges rather than a lockfile.
- Tokenizer initialization can require undeclared network access.
- Non-blocking Codecov upload steps were removed from the required characterization path.
- Placeholder provider keys look structurally similar to real credentials and are unnecessary for most maintained tests.

This workflow should remain narrow and honest while vNext is isolated. Existing legacy debt must not be relabeled as a passing vNext gate.

## Security and maintenance findings

- Gitleaks required `pull-requests: read`; after adding it, the live Secret Scanning check passed.
- GitHub Dependency Review fails before analysis because the repository lacks the required platform capability.
- The label workflow lacked checkout and used a pre-v5 configuration schema; both are now corrected and live-verified.
- Several actions emit Node.js 20 deprecation warnings on the current hosted runner and need a separate, tested action-version refresh.
- Actions use mutable major-version tags rather than commit-SHA pinning.
- Dependabot groups broad backend and frontend updates, which is risky while the legacy application already has unresolved type/build and dependency debt.

## Target CI shape

Use two explicitly different checks during migration:

1. **Legacy characterization** — a small, stable backend/frontend behavior subset. Its name must not imply production readiness.
2. **vNext required CI** — blocking format/lint/type, unit/integration tests, frontend production build, blank-database migration, deterministic evaluation smoke, secret scan, and supported dependency audit for the isolated vNext paths.

There should be no deployment or release workflow until a hosted-beta decision establishes a real target. When deployment returns, it should build once, scan before publishing, use immutable digests, authenticate with short-lived identity, require protected environments, validate migrations and smoke tests, and rehearse rollback before production access is granted.

## Ordered remediation

1. Add explicit least-privilege permissions and concurrency/timeouts to the remaining maintenance workflows.
2. Make tokenizer-dependent tests hermetic.
3. Define supported toolchain versions and create strict vNext CI alongside the first isolated executable slice.
4. Address action runtime deprecations and pin third-party actions in a dedicated supply-chain hardening slice.
5. Consider a new CD design only after the hosted-beta gate and target-infrastructure decision.
