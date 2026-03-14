# Unit Test Scope

Use this scope to keep the skill focused on practical, low-scaffolding unit tests.

## Good Targets

- Pure helper functions and data transformations
- Parsers/formatters with deterministic outputs
- Input validators
- Small branching business logic
- Error mapping and exception translation
- Regressions for recently fixed bugs

## Test Types to Prefer

- Happy-path behavior
- Boundary conditions (empty, min/max, off-by-one)
- Invalid inputs and expected failures
- Regression tests for specific bug scenarios

## Skip for This Skill

- Full integration/end-to-end tests
- Network-dependent behavior without existing mocks
- Database migrations and transactional integration
- Concurrency race tests requiring timing orchestration
- UI snapshot-heavy suites with fragile baselines
- Large fixture harnesses that require broad scaffolding

## Update Rules

1. Modify existing tests before creating new files when the target already has test coverage.
2. Keep updates minimal and aligned with changed source behavior.
3. If behavior changed intentionally, add a regression assertion and update old expectations.
4. If behavior changed unintentionally, keep old test and fix code instead.

## Assertion Quality Checklist

1. Assert business-relevant outcomes, not internal implementation details.
2. Assert explicit error types/messages only when they are part of contract.
3. Keep one reason-to-fail per assertion block.
4. Avoid brittle ordering assertions unless ordering is guaranteed behavior.
