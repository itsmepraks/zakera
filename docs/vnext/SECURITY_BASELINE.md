# Zakera vNext Security and Dependency Baseline

**Snapshot date:** 2026-09-20
**Pull request:** [#66](https://github.com/itsmepraks/zakera/pull/66)
**Scope:** legacy repository containment before vNext runtime implementation

This record separates verified findings from scanner configuration failures. It does not declare the legacy application secure and does not waive any vulnerability.

## Secret scanning

The first pull-request run of `gitleaks/gitleaks-action@v2` failed before scanning with HTTP 403 because the workflow token lacked pull-request read access. The workflow now grants only `pull-requests: read` in addition to its existing permissions.

The next live pull-request run completed the Secret Scanning job successfully. No secret value, match, or fingerprint was copied into this repository or this document.

Disposition: **scanner operational; no finding was reported by the successful PR run**.

## GitHub dependency review

`actions/dependency-review-action@v4` does not currently reach dependency analysis. GitHub reports that Dependency Review is unsupported for this repository until Dependency Graph and the applicable GitHub Advanced Security capability are enabled.

Disposition: **configuration/platform blocker, not a clean dependency result**. The unsupported job was removed from the active workflow rather than marked non-blocking or misrepresented as a passing audit. Enabling repository security features is an owner-level GitHub setting decision; until a supported blocking replacement exists, the absence remains explicit and local ecosystem audits provide the evidence below.

## Locked frontend audit

Command executed from `src/frontend`:

```sh
npm audit --json
```

Result for the committed lockfile:

| Severity | Count |
| --- | ---: |
| Critical | 1 |
| High | 14 |
| Moderate | 4 |
| Low | 0 |
| Total | 19 |

Direct packages participating in findings were:

- `next` — critical; the offered remediation is a semver-major upgrade;
- `postcss` — high; the offered remediation is coupled to a semver-major Next.js upgrade;
- `eslint-config-next` — high; the offered remediation is semver-major;
- `@typescript-eslint/eslint-plugin` — high;
- `@typescript-eslint/parser` — high; and
- `react-syntax-highlighter` — moderate; the offered remediation is semver-major.

Transitive findings include `@next/eslint-plugin-next`, TypeScript ESLint internals, `baseline-browser-mapping`, `brace-expansion`, `browserslist`, `glob`, `js-yaml`, `minimatch`, `nanoid`, `prismjs`, and `refractor`.

Disposition: **unresolved legacy dependency risk**. Do not run a blanket `npm audit fix`. The frontend already has documented type/build debt, and the primary remediation paths cross major framework versions. vNext must begin on a supported dependency baseline; any legacy upgrade must be an isolated, tested migration.

## Installed Python environment audit

An ephemeral `pip-audit` invocation inspected the local `.venv` installation without modifying project dependencies. It audited 135 installed distributions and reported one affected package:

| Package | Installed | Advisory | Fixed version reported |
| --- | --- | --- | --- |
| `ecdsa` | `0.19.2` | `PYSEC-2026-1325` | None |

The current Python inputs are range-based `requirements.txt` and `pyproject.toml` files rather than a committed lockfile. This environment result is therefore useful evidence for this checkout, not a reproducible declaration about every installation.

Disposition: **unresolved transitive risk plus reproducibility gap**. Determine whether vNext needs the authentication dependency chain that introduces `ecdsa`; avoid carrying it forward if it is outside the read-only MVP.

## Policy for the next slices

- Never paste detected secret material into issues, logs, documentation, or baselines.
- Do not use a global scanner ignore or a non-blocking failure flag.
- Give each genuine finding one disposition: revoked, remediated, or narrowly fingerprinted false positive.
- Treat scanner/platform failure separately from a clean scan.
- Keep legacy dependency remediation separate from the isolated vNext dependency baseline.
- Require the vNext namespace to pass blocking dependency and secret checks from its first executable slice.

## Next actions

1. Decide whether to enable the repository features required by GitHub Dependency Review or replace that job with supported ecosystem-native audits.
2. Define the supported Node.js, Next.js, Python, and database versions for the isolated M2 foundation.
3. Remove unnecessary vulnerable dependency chains from vNext rather than inheriting the legacy dependency set.
4. Keep the current legacy audit results visible until each direct dependency path is either upgraded, isolated, or retired.
