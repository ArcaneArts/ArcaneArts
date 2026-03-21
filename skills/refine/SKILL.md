---
name: refine
description: Refactor codebases toward cleaner modular structure by reducing duplication, extracting reusable components, and splitting oversized files/classes while preserving semantics. Use when Codex should de-spaghettify code with low-risk structural improvements that improve maintainability and editability without changing product behavior.
---

# Refine

Run this skill from repository root.

## Workflow

1. Scout refactor candidates:

```bash
python3 /path/to/skills/refine/scripts/refine_scout.py --root .
```

2. Prioritize low-risk candidates from [refactor-patterns.md](references/refactor-patterns.md):
- duplicate logic extraction,
- split oversized files/classes,
- isolate utility modules,
- simplify high-fan-in helper code.

3. Apply small, behavior-preserving refactors:
- extract shared helpers,
- split cohesive chunks into new files,
- keep public APIs stable unless explicitly allowed.

4. Validate after each refactor slice:
- run relevant tests and static analysis,
- ensure no semantic drift,
- add/update tests when needed.

5. Report:
- what moved/extracted,
- duplication reduced,
- follow-up candidates.

## Refactor Rules

- Prefer incremental slices over giant rewrites.
- Keep adapters/wrappers when migrating call sites gradually.
- Avoid changing business behavior in the same step as structural cleanup.
- Preserve error-handling and side-effect order.

## Boundaries and Handoffs

- Use `update-unit-tests` to add regression coverage around extracted/shared code.
- Use `qa-harness` when refactors affect visual or interactive behavior.
- Use `peep-hole-optimize` only for performance-focused micro-tuning after structure is cleaned.
- Do not use this skill for broad architecture redesign unless user explicitly requests it.
