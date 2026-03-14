# Risk Taxonomy

Use these categories for edge-case hypotheses.

## Categories

- `BOUNDARY_INDEX`: off-by-one, out-of-range indexing, empty collection handling.
- `NULL_OR_MISSING`: null/None/nil/missing value paths not handled.
- `ERROR_HANDLING`: swallowed exceptions, broad catches, missing error propagation.
- `ARITHMETIC_DOMAIN`: divide-by-zero, overflow/underflow, invalid numeric domain.
- `STATE_TRANSITION`: impossible or stale state transitions, partial update ordering.
- `CONCURRENCY_OR_REENTRY`: race conditions, re-entrant mutation, shared mutable state.
- `TIME_AND_ORDER`: ordering assumptions, timer delays, timezone and clock drift issues.
- `RESOURCE_LIFECYCLE`: leaks, double-close/dispose, use-after-close semantics.
- `CONFIG_AND_DEFAULTS`: unsafe fallback defaults, environment mismatch assumptions.

## Confidence Levels

- `high`: direct code evidence and realistic trigger are both clear.
- `medium`: evidence exists but trigger conditions are partial or inferred.
- `low`: weak signal; keep as watchlist only.

## Impact Labels

- `high`: crash, data corruption/loss, security-sensitive failure, or major user breakage.
- `medium`: degraded behavior, partial feature failure, noisy error loop.
- `low`: minor incorrect behavior or poor recovery path.

## Hypothesis Format

1. `title`
2. `category`
3. `confidence`
4. `impact`
5. `evidence` (`file:line`, short code cue)
6. `trigger scenario`
7. `possible outcome`
8. `quick validation idea`
