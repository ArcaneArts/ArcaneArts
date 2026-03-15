---
name: migrate-arcane-flutter-to-arcane-jaspr
description: Stage Arcane Flutter apps into Oracular-shaped Arcane Jaspr migrations with canonical workspace naming, parity gates, and controlled cutover. Use when converting Arcane Flutter apps to arcane_jaspr without changing routes, hooks, services, assets, themes, forms, or package boundaries.
---

# Migrate Arcane Flutter To Arcane Jaspr

Run this skill from the workspace root that contains the source app and any local packages.

## Workflow

1. Prepare the canonical migration workspace:

```bash
python3 /path/to/skills/migrate-arcane-flutter-to-arcane-jaspr/scripts/run_migration.py prepare \
  --source /path/to/source_app \
  --workspace-root /path/to/workspace
```

2. Review the generated artifacts in `<StageName>/reports/`:
- `migration_inventory.json`
- `parity_audit.json`
- `parity_audit.md`
- `manual_parity_checklist.md`

3. Perform the migration only inside `<StageName>/project/`:
- keep the source untouched
- keep package boundaries intact
- use the seeded Oracular Arcane Jaspr template structure
- stop immediately if any 1:1 parity requirement cannot be preserved

4. Re-run the final parity gate after the port is complete:

```bash
python3 /path/to/skills/migrate-arcane-flutter-to-arcane-jaspr/scripts/run_migration.py audit \
  --stage /path/to/MyAppNameToArcaneJaspr
```

5. Promote only after the audit passes:

```bash
python3 /path/to/skills/migrate-arcane-flutter-to-arcane-jaspr/scripts/run_migration.py promote \
  --stage /path/to/MyAppNameToArcaneJaspr \
  --destination /path/to/output_workspace
```

## Operating Rules

- The canonical external reference is [ArcaneArts/Oracular](https://github.com/ArcaneArts/Oracular).
- The staging folder name must be canonical, such as `MyAppNameToArcaneJaspr`.
- The stage layout must remain `source_snapshot/`, `template_seed/`, `project/`, `reports/`, and `backups/`.
- `project/` is the only subtree eligible for cutover.
- Preserve pages, routes, hooks, services, async flows, assets, themes, forms, validation, and package boundaries.
- Keep eligible local packages intact and rewire them with path dependencies.
- Reject any migration that would require wrapper shims, compatibility layers, or behavioral degradation.

## Direction Rules

- Arcane Flutter apps seed `arcane_jaspr_app`.
- Arcane dock, tray, or native-window Flutter apps are not valid inputs for this skill.
- Native-only plugins and native Dart libraries are hard blockers.
- Only pure Dart local packages migrate unchanged across this platform boundary.

Read [oracular-template-contract.md](references/oracular-template-contract.md), [parity-checklist.md](references/parity-checklist.md), [package-eligibility.md](references/package-eligibility.md), and [mapping-rules.md](references/mapping-rules.md) before editing migrated files.
