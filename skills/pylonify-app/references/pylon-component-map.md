# Pylon Component Map

Use the smallest Pylon surface that matches the data-flow shape.

## `Pylon<T>`

Use for immutable values that are being passed through multiple widget constructors only so descendants can read them.

Good fits:

- current user or permissions inside a subtree
- selected model for a detail route
- list item data for extracted row widgets
- configuration or feature flags scoped to a subtree

## `MutablePylon<T>`

Use for mutable screen or subtree state that currently sits in `StatefulWidget` fields and is updated through `setState`.

Good fits:

- filters
- draft forms
- selected tab or panel
- local edit state

Prefer `rebuildChildren: false` with `watchPylon` when only narrow parts of the subtree should rebuild.

## `PylonCluster`

Use when multiple adjacent pylons define one coherent boundary and nesting them individually would add shape noise.

Good fits:

- route data + feature flags + local mode
- auth user + org + active workspace

## `PylonFuture<T>`

Use when a future result should become anchored data for descendants instead of staying trapped inside one `FutureBuilder`.

Good fits:

- load-on-open screens
- initial configuration fetches
- detail resource fetches

## `PylonStream<T>`

Use when stream emissions should become anchored data for descendants instead of staying trapped inside one `StreamBuilder`.

Good fits:

- live counters
- notifications
- socket-fed records
- database listeners

## `Conduit<T>`

Use only for app-global state that must be readable and writable across multiple routes or major feature boundaries.

Good fits:

- authenticated user
- current theme mode
- app-wide badge counts
- session-wide notifications

## `PylonPort<T>`

Use only for browser URL state with a valid codec.

Good fits:

- filters reflected in query parameters
- selected IDs in web detail views
- shareable page state

## `BuildContext` extensions

Use small extensions for stable typed access once a pylon shape is correct.

Good fits:

- `BuildContext.user`
- `BuildContext.currentWorkspace`
- `BuildContext.setDraftFilter(...)`

Do not create large extension bags that hide unrelated behavior.
