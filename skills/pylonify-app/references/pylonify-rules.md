# Pylonify Rules

Pylonify by restructuring data flow first, then replacing the transport mechanism.

## Refactor Order

1. Identify where data originates.
2. Identify the smallest subtree that truly needs the data.
3. Move the anchor to that boundary.
4. Remove the old constructor or route plumbing.
5. Add focused context extensions only after the new anchor is stable.

## Explosion Rules

- Split oversized screens into smaller widgets around data boundaries.
- Pull repeated list-item data into item pylons instead of threading the model through helper widgets.
- Separate route-entry widgets from feature-content widgets when the route is mainly transporting data.
- Collapse sibling pylons with `PylonCluster` when they define one feature boundary.

## Replacement Rules

- Replace constructor data threading with `Pylon<T>` only when the value crosses multiple widget boundaries.
- Replace `StatefulWidget` fields plus `setState` with `MutablePylon<T>` when descendants need the same mutable state.
- Replace app-wide singleton or notifier state with `Conduit<T>` only when the scope is truly app-global.
- Replace async builder islands with `PylonFuture<T>` or `PylonStream<T>` when multiple descendants need the resolved value.
- Replace route argument transport with `Pylon.push` when the data should follow the route.

## Cleanup Rules

- Delete redundant mirrored fields after the pylon anchor exists.
- Delete obsolete constructor parameters immediately after all call sites are updated.
- Delete route-argument extraction code once the route reads from Pylon instead.
- Delete trivial helper methods that only existed to forward data through layers.

## Guardrails

- Do not convert every local variable into a pylon.
- Do not widen state scope for convenience.
- Do not keep both a pylon source of truth and an old field source of truth.
- Do not add compatibility wrappers around old state systems unless explicitly requested.
