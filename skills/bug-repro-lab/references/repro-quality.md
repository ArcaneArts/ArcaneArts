# Repro Quality

Use this rubric to decide whether a reproduction is actionable.

## Ratings

- `stable`: reproduces consistently (>=80% of attempts).
- `intermittent`: reproduces sometimes with recognizable trigger pattern.
- `not-reproduced`: cannot reproduce with current steps/environment.

## Minimum Artifact Set

1. `REPRO_STEPS.md` with exact sequence.
2. `OBSERVED.md` and `EXPECTED.md`.
3. At least one log or screenshot/video artifact.
4. Run history with statuses and timestamps.

## Determinism Checklist

1. Pin environment details (OS/runtime/version/build).
2. Pin input data and seed values if applicable.
3. Remove unrelated background dependencies when possible.
4. Keep reproduction path as short as possible.

## Handoff Trigger

Hand off to fix implementation only when:

- failure mode is clear,
- at least one stable or intermittent run is documented,
- reproduction artifacts are attached.
