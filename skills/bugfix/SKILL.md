---
name: bugfix
description: Perform a source-level safe bugfix pass across a repository. Use when Codex should scan all source files, identify low-risk defects (especially off-by-one errors, runtime crash risks, and straightforward error-handling flaws), apply only unambiguous fixes, and verify behavior without introducing complex edge-case changes.
---

# Bugfix

Run this skill from repository root.

## Workflow

1. Run scanner:

```bash
python3 /path/to/skills/bugfix/scripts/safe_bug_scan.py --root .
```

2. Review findings and keep only low-risk classes from [safe-fix-catalog.md](references/safe-fix-catalog.md).
3. Apply minimal patches only; avoid refactors and behavior redesign.
4. Run project checks/tests relevant to touched files.
5. Report:
- fixed findings (with file/line references),
- skipped findings (with explicit reason),
- any residual risk.

## Safe-Fix Rules

- Fix only clear, local defects where intent is obvious.
- Prefer one-line or tightly scoped edits.
- Preserve API shape and existing control flow.
- Skip any issue requiring domain assumptions or multi-module redesign.

## Supported Low-Risk Classes

- Off-by-one loop bounds (`<= length` where indexing uses same collection).
- Python `range(len(x) + 1)` iteration mistakes.
- Direct indexing at length boundary (`arr[arr.length]`, `items[len(items)]`).
- Exception wrapping that drops root cause in catch blocks.

See fix templates and skip rules in [safe-fix-catalog.md](references/safe-fix-catalog.md).

## Scanner Options

```bash
# JSON output for tooling
python3 /path/to/skills/bugfix/scripts/safe_bug_scan.py --root . --format json

# Limit output for large repos
python3 /path/to/skills/bugfix/scripts/safe_bug_scan.py --root . --max-findings 200
```

## Stop Conditions

- Stop when a candidate is ambiguous.
- Stop when fix requires semantic redesign.
- Stop when verification cannot confirm safety.

## Boundaries and Handoffs

- Use `find-edge-cases` to generate hypothetical complex or uncertain bug scenarios before fixing.
- Use `qa-harness` when validation requires user-observable behavior (visual/rendering/mechanics).
- Use `update-unit-tests` to expand automated regression coverage after applying fixes.
- Use `peep-hole-optimize` for performance-oriented edits rather than correctness bug fixes.
- Do not use this skill for large refactors, architecture changes, or high-uncertainty bug classes.
