# QA Checklist Template

Copy this into `.qa/<session>/TEST_INSTRUCTIONS.md` and fill values.

## Goal

- Validate: `<feature/mechanic/rendering flow>`
- Build/Run command: `<exact command>`
- Logs expected at: `<path>`

## Steps

1. Setup:
   - Do: `<action>`
   - Expect: `<expected state>`
2. Scenario A:
   - Do: `<action>`
   - Expect: `<expected output>`
3. Scenario B:
   - Do: `<action>`
   - Expect: `<expected output>`
4. Edge Case:
   - Do: `<boundary input>`
   - Expect: `<error/guard behavior>`

## Artifacts to Return

- Log file path:
- Screenshot/video paths (if visual):
- Notes for subjective behavior:

## Pass/Fail Rule

- Pass when all mandatory expected outcomes match and no high-severity visual/mechanical defects are observed.
