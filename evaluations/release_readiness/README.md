# Release Readiness Evaluation Set

This directory defines the blinded evaluation inputs for Zakera vNext. Cases describe the audit request and required source categories, but do not store expected classifications or answer text beside implementation-visible inputs.

## Rules

1. Freeze case inputs before using them to tune the workflow.
2. Resolve every repository ref to the exact commit in the case file.
3. Do not add gold labels, expected prose, or acceptable omissions to `cases/`.
4. Store human gold annotations separately with restricted evaluation access when scoring is implemented.
5. Treat unavailable sources as results; never silently remove them from the denominator.
6. A material claim is a statement that could change a release, documentation, approval, support, or deployment decision.
7. Every material gold claim counts toward recall, including difficult or unsupported claims.

## Case file fields

- `id`: stable case identifier;
- `title`: human-readable scenario name;
- `repository`: public GitHub `owner/name`;
- `revision`: immutable commit SHA;
- `target`: release or readiness decision being audited;
- `proposed_claims`: statements the workflow must investigate, not assumed truths;
- `required_source_categories`: source families that must be collected or explicitly receipted as unavailable;
- `constraints`: permissions and scope for the run; and
- `frozen_at`: date the input was frozen.

Files are validated against [`case.schema.json`](case.schema.json). The first two cases exercise this repository’s legacy product claims and agent-run slice. They are inputs only; their eventual gold answers must be authored independently.

## Planned scoring

- 100% of factual report prose is anchored or explicitly labeled unverified;
- at least 95% correct claim-to-evidence relationship labels;
- at least 90% material-claim recall;
- at least 0.90 macro-F1 across all four claim classifications;
- every required source retrieved or explicitly receipted as unavailable;
- zero fabricated claims or sources; and
- zero external mutations during read-only evaluation.
