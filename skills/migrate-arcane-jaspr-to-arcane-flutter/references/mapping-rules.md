# Arcane Jaspr To Arcane Flutter Mapping Rules

Use this skill only for Arcane Jaspr apps, not raw Jaspr and not static docs/content sites.

## Primary Targets

- Standard Arcane Jaspr app -> `arcane_app`
- Router-heavy Arcane Jaspr app -> `arcane_beamer_app`

## App Shell Mapping

- Replace the Arcane Jaspr shell with the selected Arcane Flutter app shell.
- Preserve route boundaries, page decomposition, and theme intent.
- Keep service connections and async behavior intact.

## Component Mapping

- Keep direct Arcane component intent where a Flutter Arcane counterpart exists.
- Rewrite Arcane Jaspr imports to Arcane Flutter imports directly.
- Do not preserve `html.dart` or `web.dart` escape hatches through wrapper layers.

## Package Rules

- Only pure Dart local packages migrate unchanged.
- Jaspr-bound or web-only local packages are blockers unless they can be rewritten directly into the app with exact parity.

## Failure Triggers

- Source is a docs/static Arcane Jaspr site
- Source depends on `package:web/`, `dart:html`, `html.dart`, or `web.dart` with no direct Flutter parity
- Required local package cannot leave the Jaspr/web runtime unchanged
