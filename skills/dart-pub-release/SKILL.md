---
name: dart-pub-release
description: Automate Dart and Flutter package releases to pub.dev. Use when Codex needs to publish a package by selecting the next semantic version (default patch bump), generating a changelog section from recent git commits, updating pubspec.yaml, committing release files, and running flutter pub publish --force.
---

# Dart Pub Release

Run this skill from the package root (the directory that contains `pubspec.yaml`).

## Quick Release

Run the bundled release script with default patch bump:

```bash
python3 /path/to/skills/dart-pub-release/scripts/release_dart_package.py
```

This performs the full release flow:

1. Read current `pubspec.yaml` version.
2. Compute next version (patch by default).
3. Build a new `CHANGELOG.md` section from recent git commit subjects.
4. Update `pubspec.yaml` and `CHANGELOG.md`.
5. Commit release files.
6. Run `flutter pub publish --force`.

## Bump Selection

Use patch unless the user explicitly asks for a different bump.

```bash
# Minor bump
python3 /path/to/skills/dart-pub-release/scripts/release_dart_package.py --bump minor

# Major bump
python3 /path/to/skills/dart-pub-release/scripts/release_dart_package.py --bump major
```

## Safety and Preview

Preview the release without writing files, committing, or publishing:

```bash
python3 /path/to/skills/dart-pub-release/scripts/release_dart_package.py --dry-run
```

Skip only publish:

```bash
python3 /path/to/skills/dart-pub-release/scripts/release_dart_package.py --skip-publish
```

## Expected Files

- `pubspec.yaml` must contain `version: x.y.z` (pre-release/build suffixes are accepted and removed on bump).
- `CHANGELOG.md` is updated or created automatically.

## Failure Handling

- Stop immediately if `pubspec.yaml` has no parseable version.
- Stop if git commit fails.
- Stop if `flutter pub publish --force` fails; report command output and do not retry automatically.
