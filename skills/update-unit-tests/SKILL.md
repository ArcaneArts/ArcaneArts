---
name: update-unit-tests
description: Create, update, and extend unit tests for low-scaffolding code paths. Use when Codex should add missing tests for simple functions, boundary behavior, and error handling, or when existing unit tests need maintenance after code changes without introducing large integration-test infrastructure.
---

# Update Unit Tests

Run this skill from repository root.

## Workflow

1. Discover candidates:

```bash
python3 /path/to/skills/update-unit-tests/scripts/test_target_scout.py --root .
```

2. Select only simple targets from [test-scope.md](references/test-scope.md):
- pure functions and deterministic transforms,
- boundary checks,
- input validation and error paths,
- bug-prone utility behavior likely to regress.

3. Create or update tests in the existing project test framework.
4. Keep test edits focused:
- avoid large fixture systems,
- avoid network/database/integration wiring,
- prefer small table-driven or parameterized cases.

5. Run nearest test command(s) for touched tests and source files.
6. Report:
- tests created/updated,
- skipped targets and reasons,
- remaining high-risk untested areas.

## Test Content Requirements

- Cover at least one success path, one boundary/edge path, and one failure/error path when applicable.
- Use concrete, stable assertions (not snapshots unless already standard in repo).
- Avoid asserting incidental implementation details.

## Update Existing Tests

When code changes invalidate tests:

1. Preserve original intent first.
2. Update expected values/messages only when behavior intentionally changed.
3. Add a regression case for the changed logic.
4. Keep naming clear (`returns_x_when_y`, `throws_when_invalid_z`).

## Stop Conditions

- Stop if testing requires heavy scaffolding or external systems.
- Stop if intent of changed behavior is ambiguous.
- Stop if no reliable assertion can be made without overspecifying internals.

## Boundaries and Handoffs

- Use this skill for lightweight automated tests; prefer deterministic unit-level coverage.
- Use `qa-harness` for manual/visual/integration-like validation.
- Use `bugfix` for implementing low-risk code fixes discovered during test work.
- Use edge-case inspection skills to generate additional scenario ideas before writing tests.
