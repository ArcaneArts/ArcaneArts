# Safe Peephole Catalog

Use this list to keep optimizations low-risk and local.

## Safe Optimization Patterns

- `CACHE_STABLE_LOOKUP`: Cache repeated property/length/metadata lookups in a hot loop.
- `HOIST_CONSTANT_WORK`: Move invariant computation out of repeated paths.
- `PRECOMPILE_REGEX`: Reuse compiled regex instead of recompiling each call.
- `AVOID_REDUNDANT_CONVERSIONS`: Remove repeated parse/format/boxing conversions.
- `REDUCE_TEMP_ALLOCATION`: Reuse buffers/objects when lifecycle is clear and local.
- `BATCH_SMALL_WRITES`: Combine tiny repeated writes into buffered or chunked writes.
- `EARLY_EXIT_GUARDS`: Skip expensive logic quickly when no-op conditions are known.
- `CHEAPER_COLLECTION_OP`: Replace repeated linear membership checks with set/map where local and safe.

## Risky Patterns (Skip in This Skill)

- Caches requiring complex invalidation or cross-thread synchronization.
- Changes that alter ordering guarantees or floating-point semantics.
- Concurrency model changes.
- Algorithmic rewrites across modules.
- Altering error-handling behavior or fallback semantics.
- GPU/rendering pipeline changes without explicit visual verification plan.

## A/B Proof Expectations

1. Keep baseline and candidate outputs equivalent.
2. Use at least 5 warmups and 20 measured iterations for small microbenchmarks.
3. Prefer median and p95 comparison over single-run numbers.
4. Treat speedups under 5% as inconclusive unless effect is very stable.
5. Include benchmark command, environment notes, and raw result artifact path.
