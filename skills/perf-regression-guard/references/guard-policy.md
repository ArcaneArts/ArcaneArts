# Perf Guard Policy

Use these defaults unless the repository specifies stricter performance SLOs.

## Defaults

- Warmups: `5`
- Measured iterations: `20`
- Regression threshold: `5%` median slowdown
- Warning threshold: `2%` to `5%` median slowdown

## Interpretation

- `pass`: candidate median is not slower than baseline by threshold.
- `warn`: small slowdown within warning band; investigate with repeated run.
- `fail`: slowdown exceeds threshold or candidate output is unstable.

## Evidence Requirements

1. Baseline and candidate JSON artifacts.
2. Commands used for both runs.
3. Environment notes (machine class, load, runtime version).
4. Median and p95 comparisons.

## Noise Controls

1. Avoid benchmarking on highly loaded machines when possible.
2. Keep other workloads minimal during benchmark.
3. Use same data volume and code path for A/B.
