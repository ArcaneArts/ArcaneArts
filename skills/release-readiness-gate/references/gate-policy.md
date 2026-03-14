# Release Gate Policy

Default checks for release decisioning.

## Required Checks

- `unit-tests`
- `qa-validation`
- `edge-case-review`
- `perf-regression`
- `release-dry-run`
- `changelog-ready`

## Optional Checks

- `manual-smoke`
- `docs-updated`
- `known-issues-reviewed`

## Status Values

- `pass`
- `warn`
- `fail`
- `skip`
- `pending`

## GO Rules

1. `NO-GO` when any required check is `fail`.
2. `NO-GO` when any required check is `pending`.
3. `GO-WARN` when all required checks are `pass` but one or more checks are `warn`.
4. `GO` when required checks are `pass` and warnings are resolved or accepted.
