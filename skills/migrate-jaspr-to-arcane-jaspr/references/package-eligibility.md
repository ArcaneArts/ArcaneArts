# Package Eligibility

Preserve package boundaries. Do not fold packages into the app.

## Auto-Migrate Unchanged

- Pure Dart models
- DTOs and serializers
- Validation and parsing logic
- Non-platform business logic
- Shared utilities with no UI runtime dependency

## Never Auto-Migrate Across Platforms

- Packages importing `package:flutter/`
- Packages importing `package:arcane/arcane.dart` when targeting Jaspr
- Packages importing `package:jaspr/` or `package:arcane_jaspr/` when targeting Flutter
- Packages using `dart:ui`
- Packages using DOM or native window APIs on the wrong target platform
- Packages depending on tray, window, or desktop-native plugins

## Jaspr To Arcane Jaspr Rules

- Jaspr-local packages may migrate when they stay inside the Jaspr ecosystem.
- Flutter or native-runtime packages remain ineligible.
- Required ineligible packages are a hard stop.

## Rewiring Rules

- Copy eligible local packages unchanged under `project/packages/<package-name>`.
- Keep the original `name:` in each copied package pubspec.
- Rewire consuming apps or copied packages with relative path dependencies.
- Do not convert a local package into inline app code.
