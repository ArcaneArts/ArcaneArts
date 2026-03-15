# Jaspr To Arcane Jaspr Mapping Rules

Use this skill only for raw Jaspr sources that are not already on `arcane_jaspr`.

## Primary Targets

- Plain Jaspr app -> `arcane_jaspr_app`
- Jaspr static docs/content app -> `arcane_jaspr_docs`

## App Shell Mapping

- Replace the raw Jaspr app shell with `ArcaneApp`.
- Preserve theme intent and brightness behavior.
- Keep route entrypoints and page decomposition intact.

## Component Mapping

- Prefer `package:arcane_jaspr/arcane_jaspr.dart` for migrated app surfaces.
- Use `package:arcane_jaspr/html.dart` only when a direct Arcane surface does not exist.
- Keep raw Jaspr or DOM escape hatches only when they remain valid in the Arcane Jaspr surface and do not alter behavior.

## Docs Mapping

- Static Jaspr docs/content sites must seed `arcane_jaspr_docs`.
- Preserve content folder structure and metadata behavior.
- Preserve generated navigation, page order, and markdown semantics.

## Failure Triggers

- Source already depends on `arcane_jaspr`
- Required Flutter package or plugin dependency
- Unsupported route or lifecycle parity gap
- Required package cannot remain in the Jaspr ecosystem unchanged
