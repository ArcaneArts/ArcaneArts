# Framework Playbooks

Use these playbooks to build the smallest runnable QA harness for manual verification.

## Dart Package -> Flutter QA App

1. Create subproject:
   - `flutter create .qa/<session>/harness_app`
2. Add parent package path dependency in `.qa/<session>/harness_app/pubspec.yaml`.
3. Build focused UI controls:
   - one control per scenario (button/toggle/input),
   - visible output panel,
   - log output with `QA_EVT`.
4. Run:
   - `flutter run` from harness app directory.

## Minecraft Mod

1. Add temporary debug hooks around target mechanic.
2. Emit `QA_EVT` logs for important transitions:
   - entry/exit conditions,
   - values affecting rendering/mechanics,
   - pass/fail checkpoints.
3. Launch dev client with existing mod run task.
4. Provide user checklist for exact in-game steps and expected outcomes.

## Java/Node/Python/Library Projects

1. Create minimal harness under `.qa/<session>/harness_app`:
   - console app for algorithmic behavior,
   - lightweight UI app for visual or interaction behavior.
2. Link local parent package/module.
3. Add scenario switches/inputs and print `QA_EVT` checkpoint lines.
4. Run harness and collect logs.

## Visual/Rendering Guidance

- Include a simple control panel for deterministic states.
- Print exact rendering parameters into `QA_EVT` events.
- Ask for screenshots only where visual correctness cannot be inferred from logs.

## Cleanup Rule

- Keep all QA scaffolding under `.qa/<session>` by default.
- Remove temporary instrumentation after conclusion unless user asks to retain it.
