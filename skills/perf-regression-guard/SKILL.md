---
name: perf-regression-guard
description: Capture and compare repeatable performance benchmarks to detect regressions over time or across changes. Use when Codex should baseline key workloads, run comparable benchmark measurements, and produce pass/fail regression judgments without directly optimizing source code.
---

# Perf Regression Guard

Run this skill from repository root.

## Workflow

1. Capture baseline benchmark:

```bash
python3 /path/to/skills/perf-regression-guard/scripts/perf_guard.py capture \
  --bench-cmd "<benchmark command>" \
  --label baseline-main \
  --output .perf/baseline-main.json
```

2. Capture candidate benchmark using same workload/environment:

```bash
python3 /path/to/skills/perf-regression-guard/scripts/perf_guard.py capture \
  --bench-cmd "<benchmark command>" \
  --label candidate-change \
  --output .perf/candidate-change.json
```

3. Compare and gate:

```bash
python3 /path/to/skills/perf-regression-guard/scripts/perf_guard.py compare \
  --baseline .perf/baseline-main.json \
  --candidate .perf/candidate-change.json \
  --threshold-pct 5
```

4. Report regression status and evidence artifact paths.

## Guard Rules

- Keep command, dataset, and environment consistent between baseline and candidate.
- Use warmups and sufficient iterations to reduce noise.
- Use median and p95 as primary indicators.
- Treat small (<5%) drift as inconclusive unless stable over repeated runs.

See [guard-policy.md](references/guard-policy.md) for thresholds.

## Boundaries and Handoffs

- Use this skill to detect regressions, not to modify code.
- Use `peep-hole-optimize` to implement safe micro-optimizations when a regression is found.
- Use `find-optimizations` to inspect deeper architectural opportunities.
