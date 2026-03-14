---
name: release-readiness-gate
description: Aggregate quality signals into a release GO/NO-GO decision before publishing. Use when Codex should collect evidence from tests, QA, bug and edge-case review, performance guard checks, and release dry-runs, then produce a clear readiness summary without performing the publish step itself.
---

# Release Readiness Gate

Run this skill from repository root.

## Workflow

1. Initialize gate session:

```bash
python3 /path/to/skills/release-readiness-gate/scripts/release_gate.py init --root . --version 1.2.3
```

2. Fill checks from evidence produced by other skills:
- `update-unit-tests` (test health),
- `qa-harness` (manual validation),
- `find-edge-cases` / `bug-repro-lab` (risk review),
- `perf-regression-guard` (performance regression status),
- release dry-run (`dart-pub-release --dry-run`).

3. Record each check:

```bash
python3 /path/to/skills/release-readiness-gate/scripts/release_gate.py record \
  --gate .release-gate/<session> \
  --check unit-tests \
  --status pass \
  --evidence "dart test passed"
```

4. Summarize GO/NO-GO decision:

```bash
python3 /path/to/skills/release-readiness-gate/scripts/release_gate.py summarize --gate .release-gate/<session>
```

## Decision Rules

- `NO-GO` if any required check is `fail` or still `pending`.
- `GO-WARN` when required checks pass but warnings exist.
- `GO` when all required checks pass and warnings are resolved/accepted.

See [gate-policy.md](references/gate-policy.md) for default required checks.

## Boundaries and Handoffs

- This skill aggregates evidence and decisions; it does not publish.
- Hand off to `dart-pub-release` only after `GO` or accepted `GO-WARN`.
- Do not implement bug/perf fixes inside this skill.
