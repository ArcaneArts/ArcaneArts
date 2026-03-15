# Anti-Patterns

Avoid these during Pylon adoption.

## Over-Globalizing With `Conduit<T>`

If only one screen or one route needs the data, `Conduit<T>` is too wide.

## Keeping Duplicate Sources Of Truth

Do not keep:

- a `MutablePylon<T>` and a mirrored `State` field
- a `Conduit<T>` and a separate singleton cache for the same UI value
- route arguments and a matching `Pylon<T>` carrying the same object

## Pylon Everywhere

Do not wrap leaf widgets with Pylons when direct local variables are simpler and no boundary crossing exists.

## Large Extension Bags

Do not hide half the app behind one giant `BuildContext` extension file. Keep extensions narrow and domain-specific.

## Async Islands Left Half-Converted

Do not keep a `FutureBuilder` or `StreamBuilder` around the outer shell while descendants separately reach for the same data through another path.

## Route Parity Mistakes

If a route needs the data on the next screen, either:

- keep it in the pylon chain with `Pylon.push`, or
- make it a true global with `Conduit<T>`

Do not duplicate transport mechanisms.
