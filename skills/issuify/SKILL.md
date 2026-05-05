---
name: issuify
description: Hydrate terse bug reports, feature requests, and tracker notes into repository-grounded markdown issue context. Use when the user gives a short issue description and wants Codex to inspect the project, gather the relevant code and docs, and return a copyable "added context" report with touchpoints, fix approach, acceptance criteria, and risks.
---

# Issuify

Run this skill from repository root.

## Workflow

1. Restate the issue in one sentence and infer the most likely subsystem.
2. Search the repo with `rg` for the smallest set of relevant touchpoints:
   - `README.md`
   - `docs/PLAN.md`
   - likely feature folders
   - nearby tests
3. Read only the files needed to answer:
   - where the current behavior lives,
   - whether the behavior is persisted data or display-only,
   - which state/settings/cache layers are involved,
   - whether platform parity matters.
4. Produce a copyable markdown report with these sections:
   - `## Issue`
   - `## Added Context`
   - `## Current Behavior`
   - `## Relevant Touchpoints`
   - `## Fix Approach`
   - `## Acceptance Criteria`
   - `## Risks / Gotchas`
   - `## Open Questions`
5. In `Relevant Touchpoints`, include concrete file paths and one short reason each file matters.
6. In `Fix Approach`, call out the safest insertion point for the change and any state/cache invalidation that must be updated with it.

## Rules

- Make one reasonable assumption when the issue is underspecified, and label it clearly.
- Keep the report concise and flat; avoid filler and nested bullet trees.
- Prefer implementation-aware details over product-generic phrasing.
- If the issue touches editor rendering, settings, caching, or display-only behavior, explicitly note whether toggles should affect stored manuscript data.
- If you cannot find enough context, say what you checked and what remains unknown.
- Do not implement the fix unless the user explicitly asks for code changes too.
