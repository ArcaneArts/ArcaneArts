# Refactor Patterns

Use these patterns for low-risk de-spaghettification.

## Preferred Patterns

- `EXTRACT_SHARED_HELPER`: Move duplicated logic into one reusable function/class.
- `SPLIT_LARGE_FILE`: Split oversized file by cohesive concerns, keep stable imports/exports.
- `SPLIT_LARGE_CLASS`: Extract collaborator objects/services from god classes.
- `ISOLATE_SIDE_EFFECTS`: Separate pure computation from I/O and stateful operations.
- `NORMALIZE_INPUT_ADAPTER`: Centralize repetitive input sanitation/validation logic.
- `CONSOLIDATE_ERROR_MAPPING`: Share error translation logic instead of duplicate branches.

## Safety Rules

1. Preserve external behavior and API contracts by default.
2. Keep refactor commits focused and small.
3. Add regression coverage near extracted logic.
4. Avoid changing performance strategy and business semantics in the same step.

## Avoid in This Skill

- Full architecture rewrites.
- Protocol/schema migrations.
- Large behavior changes hidden inside refactor diffs.
- Cross-team boundary changes without explicit approval.
