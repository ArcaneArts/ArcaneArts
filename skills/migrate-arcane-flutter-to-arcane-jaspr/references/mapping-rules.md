# Arcane Flutter To Arcane Jaspr Mapping Rules

Use this skill only for Arcane Flutter apps, not generic Flutter apps and not dock or tray projects.

## Primary Target

- Arcane Flutter app -> `arcane_jaspr_app`

## App Shell Mapping

- Replace the Arcane Flutter shell with `ArcaneApp` from `arcane_jaspr`.
- Preserve page decomposition, routing intent, theme behavior, and service wiring.
- Preserve async behavior, loading states, and form semantics.

## Component Mapping

- Rewrite Arcane Flutter imports directly to Arcane Jaspr surfaces.
- Prefer `package:arcane_jaspr/arcane_jaspr.dart`.
- Use `package:arcane_jaspr/html.dart` only when there is no higher-level Arcane Jaspr surface with identical behavior.

## Package Rules

- Only pure Dart local packages migrate unchanged.
- Flutter-bound, plugin-bound, or native-runtime packages are blockers unless parity can be recreated directly inside the migrated app.

## Failure Triggers

- Source depends on tray or window-manager plugins
- Source imports `dart:io`, `dart:ffi`, or `dart:ui` for runtime-critical behavior
- Source is a dock or tray application
- Required local package cannot leave the Flutter/native runtime unchanged
