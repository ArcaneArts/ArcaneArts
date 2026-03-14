---
name: peep-hole-optimize
description: Apply low-risk, semantics-preserving micro-optimizations that reduce CPU, memory, allocation, or I/O overhead without major architectural changes. Use when Codex should inspect code for safe local optimizations, implement them conservatively, and validate uncertain improvements with A/B benchmarks before claiming performance gains.
---

# Peep Hole Optimize

Run this skill from repository root.

## Workflow

1. Identify safe candidates from [safe-peephole-catalog.md](references/safe-peephole-catalog.md).
2. Apply only local, semantics-preserving edits.
3. Run existing tests for touched areas.
4. If optimization confidence is not high, run A/B benchmark proof:

```bash
python3 /path/to/skills/peep-hole-optimize/scripts/ab_benchmark.py \
  --baseline-cmd "<baseline command>" \
  --candidate-cmd "<optimized command>" \
  --iterations 25 \
  --warmups 5 \
  --output-json /tmp/bench.json \
  --output-md /tmp/bench.md
```

5. Keep optimization only when:
- output equivalence holds (unless explicitly skipped),
- benchmark shows consistent improvement,
- no test regressions.

## Optimization Rules

- Prefer tiny edits (local substitutions, caching stable values, avoiding redundant allocations).
- Do not redesign architecture, APIs, or behavior.
- Do not apply risky caching with unclear invalidation semantics.
- Revert or skip changes that are not demonstrably better.

## Benchmark Rules

- Benchmark same workload and environment for A/B.
- Use multiple warmups and iterations.
- Compare median latency and stability, not only a single run.
- Report speedup and confidence notes.

## Stop Conditions

- Stop if semantics might change.
- Stop if gains are inconclusive.
- Stop if benchmark cannot be made fair and reproducible.

## Boundaries and Handoffs

- Use `find-optimizations` to discover higher-risk/high-upside opportunities first.
- Use performance regression guard skills to baseline and track long-term drift after changes.
- Use `update-unit-tests` to protect behavior around optimized code paths.
- Do not perform architectural rewrites or high-risk algorithm changes in this skill.
