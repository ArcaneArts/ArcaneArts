---
name: find-edge-cases
description: Red-team source code for hypothetical edge cases, complex bugs, and missing handling paths without making code changes. Use when Codex should inspect a codebase for unanticipated inputs, boundary failures, race or state hazards, fragile error handling, and other plausible failure scenarios, then produce an inspection report the user can choose to act on later.
---

# Find Edge Cases

Inspection-only skill. Do not edit code unless the user explicitly asks in a separate step.

Run this skill from repository root.

## Workflow

1. Run scout:

```bash
python3 /path/to/skills/find-edge-cases/scripts/edge_case_scout.py --root .
```

2. Cluster findings by subsystem and risk theme using [risk-taxonomy.md](references/risk-taxonomy.md).
3. Draft hypotheses (not confirmed bugs) with:
- failure scenario,
- triggering input/state,
- expected impact,
- confidence level.

4. For each hypothesis, include a quick validation idea the user can run.
5. Return report sections:
- likely/high-impact hypotheses,
- medium-confidence hypotheses,
- low-confidence watchlist.

## Output Rules

- Label each item as `hypothesis`.
- Include file/line evidence and reasoning.
- Do not claim certainty unless reproducible evidence exists.
- Do not implement fixes in this skill.

## Optional Formats

```bash
# JSON for follow-up tooling
python3 /path/to/skills/find-edge-cases/scripts/edge_case_scout.py --root . --format json

# Cap output for large repos
python3 /path/to/skills/find-edge-cases/scripts/edge_case_scout.py --root . --max-hypotheses 250
```

## Stop Conditions

- Stop short of code changes.
- Stop when evidence is too weak to support any plausible scenario.
- Escalate uncertainty instead of inventing confident conclusions.

## Boundaries and Handoffs

- Use `bugfix` when the user asks to implement clear low-risk fixes.
- Use `qa-harness` when a hypothesis needs manual/visual validation.
- Use `find-optimizations` for performance opportunity discovery (not bug-risk discovery).
- Use `peep-hole-optimize` only after a concrete optimization target is selected.
- Do not edit production code in this skill.
