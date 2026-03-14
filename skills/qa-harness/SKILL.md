---
name: qa-harness
description: Build runnable QA harnesses for manual validation of complex behavior and capture results back to Codex. Use when code needs user-observable testing (visual output, rendering, gameplay/mechanics, interactive flows) by creating a subproject or temporary instrumentation, giving clear test instructions, collecting structured logs, and summarizing pass/fail outcomes after the run.
---

# Qa Harness

Run this skill from repository root.

## Workflow

1. Initialize QA session:

```bash
python3 /path/to/skills/qa-harness/scripts/qa_session_manager.py init --root . --goal "What behavior should be validated"
```

2. Read generated session files:
- `.qa/<session>/TEST_INSTRUCTIONS.md`
- `.qa/<session>/SESSION.json`
- `.qa/<session>/SUMMARY.md`

3. Build harness according to detected framework playbook in [framework-playbooks.md](references/framework-playbooks.md):
- Dart package: create Flutter subproject with path dependency to parent package.
- Minecraft mod: add temporary instrumentation and launch client.
- Generic library: create minimal console/UI harness that calls target APIs.

4. Instrument observable checkpoints with structured lines prefixed by `QA_EVT`.
5. Ask user to execute scenarios from `TEST_INSTRUCTIONS.md`.
6. Collect logs after run:

```bash
python3 /path/to/skills/qa-harness/scripts/qa_session_manager.py collect --session .qa/<session> --log-file /path/to/run.log
python3 /path/to/skills/qa-harness/scripts/qa_session_manager.py summarize --session .qa/<session>
```

7. Combine:
- structured log events,
- user observations,
- screenshots/video notes when needed.

8. Report pass/fail and next actions.

## Logging Contract

- Emit machine-readable checkpoints with `QA_EVT`.
- Preferred line format:

```text
QA_EVT {"event":"name","status":"pass|fail|info|warn","details":"...","context":{"key":"value"}}
```

- Use this for assertions that agent can interpret without follow-up.
- Use `OBSERVATIONS.md` for user-visible behavior that cannot be inferred from logs (visual glitches, animation quality, subjective UX issues).

## Required Output to User

- Exact command(s) to run harness.
- Step-by-step checklist of what to click/do/observe.
- Expected results per step.
- What artifacts to return (log path, screenshot path, optional comments).

## Stop Conditions

- Stop if harness setup requires production data access.
- Stop if requested instrumentation risks persistent side effects.
- Stop and ask for direction when expected behavior is ambiguous.

## Boundaries and Handoffs

- Use this skill for manual, interactive, visual, or mechanics-heavy validation.
- Use `update-unit-tests` for automated low-scaffolding unit tests.
- Use bug inspection skills (`find-edge-cases`, bug reproduction workflows) to define scenarios before harness work.
- Do not publish or release from this skill; hand off to release skills after validation.
