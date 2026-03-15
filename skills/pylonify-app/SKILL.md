---
name: pylonify-app
description: Refactor Flutter apps toward Pylon-driven data flow by exploding prop-drilled widget trees into scoped Pylon anchors, MutablePylon state, Conduit globals, and async/url pylons where they fit cleanly. Use when a Flutter app is carrying too much data through constructors, duplicated fields, route arguments, FutureBuilder or StreamBuilder chains, or ad hoc global state.
---

# Pylonify App

Run this skill from the Flutter app root.

## Workflow

1. Scan the app and generate a Pylonification report:

```bash
python3 /path/to/skills/pylonify-app/scripts/pylonify_scan.py scan --root .
```

2. Read the generated artifacts in `.pylonify/<session>/`:
- `report.md`
- `inventory.json`
- `candidates.json`

3. Explode the app by data-flow boundary before editing:
- app-global state
- route-level state
- screen-level mutable state
- subtree-level immutable data
- list item data
- async data
- web URL state

4. Apply Pylon surfaces by scope:
- `Pylon<T>` for immutable values that are being drilled through constructors or route plumbing
- `MutablePylon<T>` for screen or subtree mutable state that should stop living in local fields and `setState` islands
- `PylonCluster` when adjacent pylons should be flattened into one boundary
- `PylonFuture<T>` and `PylonStream<T>` when descendants need async data beyond a single builder
- `Conduit<T>` only for real app-wide, cross-route state
- `PylonPort<T>` only for browser URL state with codecs
- focused `BuildContext` extensions only for stable domain reads and mutations

5. Clean up after anchoring data:
- remove prop-drilled constructor parameters
- remove duplicated stored fields that only mirror ancestor data
- remove route argument plumbing that Pylon can preserve directly
- remove trivial pass-through methods whose only job was moving data downward
- keep package and feature boundaries intact

6. Verify the refactor:
- run analyzer, tests, and the relevant app build
- confirm state scope did not widen accidentally
- confirm no compatibility wrappers or duplicate sources of truth remain

## Operating Rules

- The canonical reference is [ArcaneArts/pylon](https://github.com/ArcaneArts/pylon).
- Prefer the nearest stable scope. Do not promote local state to `Conduit<T>` unless it is truly global.
- Keep explicit types.
- Do not add code comments.
- Do not introduce wrapper or adapter layers just to keep old data flow alive.
- Leave simple leaf-local values alone when a pylon would add more indirection than value.
- Prefer removing constructor data plumbing over stacking Pylons on top of the old flow.

Read [pylon-component-map.md](references/pylon-component-map.md), [pylonify-rules.md](references/pylonify-rules.md), and [anti-patterns.md](references/anti-patterns.md) before making edits.
