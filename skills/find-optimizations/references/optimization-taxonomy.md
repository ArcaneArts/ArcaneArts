# Optimization Taxonomy

Use this taxonomy to classify optimization opportunities.

## Categories

- `ALGORITHM_COMPLEXITY`: nested loops, repeated scans, repeated sorting.
- `HOT_PATH_ALLOCATION`: frequent object/string/list allocation in tight paths.
- `SYNC_IO_HOT_PATH`: blocking filesystem/network calls in request/render loops.
- `REGEX_OR_PARSING_HOT_PATH`: repeated compile/parse work that could be cached.
- `N_PLUS_ONE_OR_CHATTER`: repetitive query/call patterns instead of batching.
- `REDUNDANT_COMPUTATION`: deterministic recomputation that could be memoized/precomputed.
- `STATE_OR_CACHE_STRATEGY`: opportunities for caching, pooling, or lifecycle tuning.

## Expected Gain Labels

- `high`: likely large throughput/latency win if hypothesis is confirmed.
- `medium`: meaningful improvement likely in moderate workloads.
- `low`: minor improvement or narrow scenario win.

## Risk Labels

- `high`: behavior correctness or edge-case risk is significant.
- `medium`: manageable risk with careful tests and profiling.
- `low`: low behavior risk if implemented carefully.

## Complexity Labels

- `high`: architecture or subsystem redesign required.
- `medium`: localized but non-trivial refactor needed.
- `low`: narrow scoped change likely sufficient.

## Opportunity Format

1. `title`
2. `category`
3. `expected_gain`
4. `risk`
5. `complexity`
6. `confidence`
7. `evidence` (`file:line`, code clue)
8. `hypothesis`
9. `validation_plan`
