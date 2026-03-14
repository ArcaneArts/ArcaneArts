---
name: find-optimizations
description: Inspect source code for high-impact performance optimization opportunities without modifying code. Use when Codex should red-team the codebase for potential throughput, latency, memory, or allocation improvements that may require deeper follow-up due to edge cases or complex behavior tradeoffs.
---

# Find Optimizations

Inspection-only skill. Do not modify source code in this skill.

Run this skill from repository root.

## Workflow

1. Run scout:

```bash
python3 /path/to/skills/find-optimizations/scripts/optimization_scout.py --root .
```

2. Group opportunities by subsystem and category using [optimization-taxonomy.md](references/optimization-taxonomy.md).
3. Draft each item as an `opportunity` (not a guaranteed issue):
- hypothesis of bottleneck,
- why it might be expensive,
- expected upside if optimized,
- risk/complexity notes,
- how to validate with profiling or benchmark.

4. Return a report with:
- high-upside candidates,
- medium-upside candidates,
- low-confidence watchlist.

## Output Rules

- Label each item `opportunity`.
- Include file/line evidence and concrete reasoning.
- Include `expected_gain`, `risk`, and `complexity`.
- Include a validation plan (microbenchmark, profiler, trace, or load scenario).
- Do not implement optimization changes in this skill.

## Optional Formats

```bash
# JSON output for tooling
python3 /path/to/skills/find-optimizations/scripts/optimization_scout.py --root . --format json

# Limit opportunities in huge repos
python3 /path/to/skills/find-optimizations/scripts/optimization_scout.py --root . --max-opportunities 300
```

## Stop Conditions

- Stop short of source code changes.
- Escalate uncertainty when evidence is weak.
- Avoid definitive claims without profiling evidence.

## Boundaries and Handoffs

- Use `peep-hole-optimize` for implementation of low-risk micro-optimizations.
- Use `qa-harness` when optimization impact is tied to visual/interactive behavior.
- Use `update-unit-tests` to add regression tests after optimization edits are accepted.
- Use performance regression tracking skills to monitor drift over time.
- Do not implement optimization changes in this skill.
