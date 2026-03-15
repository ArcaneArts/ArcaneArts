# Oracular Template Contract

The canonical reference for template shape and target taxonomy is [ArcaneArts/Oracular](https://github.com/ArcaneArts/Oracular).

Use the local Oracular checkout for file copying when it is available, but keep the seeded output aligned with the GitHub template contract.

## Supported Target Templates

- `arcane_jaspr_app`: Arcane Jaspr client-style web app
- `arcane_jaspr_docs`: Arcane Jaspr static docs/content site
- `arcane_app`: base Arcane Flutter app
- `arcane_beamer_app`: Arcane Flutter app with heavier routing
- `arcane_dock_app`: Arcane Flutter desktop dock/tray app

## Deterministic Selection Rules

- Jaspr SPA or client app -> `arcane_jaspr_app`
- Jaspr docs or static content -> `arcane_jaspr_docs`
- Arcane Jaspr app with heavier route structure -> `arcane_beamer_app`
- Standard Arcane Jaspr app -> `arcane_app`
- Standard Arcane Flutter app -> `arcane_jaspr_app`
- Arcane Flutter dock or tray app is not eligible for Jaspr migration unless dock behavior is absent

## Staged Output Shape

The canonical stage root is `<SourceName>To<TargetLabel>` and must contain:

- `source_snapshot/`
- `template_seed/`
- `project/`
- `reports/`
- `backups/`

Inside `project/`, preserve the Oracular-style workspace shape:

- the migrated target app in its own package directory
- copied local packages under `packages/` when eligible
- `.oracular_deps/` when the selected target is `arcane_jaspr_docs`

## Cutover Rules

- Never cut over directly from `template_seed/`.
- Never edit `source_snapshot/`.
- Promote only from `project/` after a clean parity audit.
