---
name: bug-repro-lab
description: Build deterministic bug reproduction artifacts for complex or uncertain failures without implementing fixes. Use when Codex should transform a bug report or hypothesis into repeatable steps, reproducible inputs, captured logs/artifacts, and a reproducibility summary that can hand off cleanly to bugfix or QA skills.
---

# Bug Repro Lab

Run this skill from repository root.

## Workflow

1. Initialize reproduction session:

```bash
python3 /path/to/skills/bug-repro-lab/scripts/repro_session.py init --root . --issue "Short bug statement"
```

2. Fill generated files:
- `.repro/<session>/REPRO_STEPS.md`
- `.repro/<session>/OBSERVED.md`
- `.repro/<session>/EXPECTED.md`

3. Execute reproduction steps repeatedly and capture artifacts/logs.
4. Record each run:

```bash
python3 /path/to/skills/bug-repro-lab/scripts/repro_session.py record \
  --session .repro/<session> \
  --status reproduced \
  --log-file /path/to/run.log \
  --notes "short note"
```

5. Summarize reproducibility:

```bash
python3 /path/to/skills/bug-repro-lab/scripts/repro_session.py summarize --session .repro/<session>
```

6. Hand off summary + artifacts to fix or QA skills.

## Reproduction Quality Rules

- Keep steps deterministic and minimal.
- Include exact setup/input values.
- Capture at least 3 runs for intermittent issues when possible.
- Separate observed vs expected behavior clearly.

See [repro-quality.md](references/repro-quality.md) for rating guidance.

## Boundaries and Handoffs

- Use this skill to reproduce; do not implement fixes here.
- Use `bugfix` after reproduction is stable and local.
- Use `qa-harness` when reproduction requires interactive/visual flows.
- Use `find-edge-cases` to generate additional hypotheses if repro fails.
