# Security Policy

## Project status

Zakera is a pre-alpha framework under redesign. There is no supported production release, hosted Zakera service, or maintained release branch yet. The repository still contains legacy code and documentation that have not been fully security-reviewed.

Do not expose the legacy application to untrusted users or production credentials. Unsafe legacy code-execution and unrestricted file-reading tools are disabled by default and are not security sandboxes.

## Reporting a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/itsmepraks/zakera/security/advisories/new) when it is available for the repository. This keeps sensitive details out of public issues.

If private vulnerability reporting is unavailable, open a public issue containing only a request for a private reporting channel. Do not include exploit details, credentials, personal data, or other sensitive information in that issue.

Useful reports include:

- the affected commit or version;
- a concise description and potential impact;
- minimal reproduction steps;
- relevant configuration assumptions; and
- a suggested mitigation, if known.

Response timing depends on maintainer availability. Receipt, investigation, remediation, and disclosure timing will be communicated through the private report rather than guaranteed in advance.

## Security scope

Examples include:

- authentication or authorization bypasses;
- credential, secret, or personal-data exposure;
- injection vulnerabilities;
- unsafe tool or workspace boundary escapes;
- approval or capability-policy bypasses; and
- supply-chain issues with a concrete effect on Zakera users.

Ordinary bugs, feature requests, and questions can use regular GitHub issues.

## Supported versions

No version is currently supported for production use. Security fixes target the active development branch unless a future release policy states otherwise.
