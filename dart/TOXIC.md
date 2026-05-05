# TOXIC

Extension utilities for Dart primitives, collections, and async types.

## Workspace Setup (Local Development)

### Prerequisites

- Dart SDK `>=3.5.0 <4.0.0` (this repo's current `pubspec.lock` resolves against Dart 3.5+).
- Git.

### Clone and Install

```bash
git clone https://github.com/ArcaneArts/toxic.git
cd toxic
dart pub get
```

### Optional Dev Tooling (Recommended for contributors)

The repository currently includes `analysis_options.yaml` with `flutter_lints`, and running `dart test` requires `package:test`, but neither is pinned in `pubspec.yaml` yet.

If you want local analysis/tests to run cleanly in your workspace, add them once:

```bash
dart pub add --dev flutter_lints test
```

### Verify Workspace

```bash
dart analyze
dart test
```

## Using TOXIC in a Dart Project

### Add Dependency

```yaml
dependencies:
  toxic: ^1.3.8
```

### Import

```dart
import 'package:toxic/toxic.dart';
```

## Extension Highlights

- `TInt`: `lerpTo`, `plural`, `format`, `formatCompact`, `isPrime`.
- `TString`: `roadkill`, `camelCase`, `randomCase`, `reversed`, `capitalizeWords`, path helpers.
- `TDouble`: `percent`, `format`, `formatCompact`, `lerpTo`, degree/radian helpers.
- `TFuture`: `thenRun`, `thenWait`, nullable helpers (`bang`, `or`, `showErrors`).
- `TMap`: merge/remove operators, sorting helpers, compute variants, `flip`/`flipFlat`.
- `TIterableInt` and `TIterableDouble`: numeric operators plus `sum`, `average`, `median`, `mode`.
- `TList` and `TSet`: element add/remove operators and list reordering/random helpers.
- `TIterable`: selection, grouping, deduplication, chunking, mapping, sorting, and more.

## Correct Usage Examples

```dart
import 'package:toxic/toxic.dart';

void main() async {
  int count = 2;
  print(count.lerpTo(10, 0.5)); // 6.0
  print(count.plural("apple", "apples")); // apples
  print(count.format()); // locale dependent
  print(count.formatCompact()); // compact format

  String text = "Hello World";
  print(text.roadkill); // hello_world
  print(text.camelCase); // helloWorld
  print(text.capitalizeWords()); // Hello World

  double value = 0.123;
  print(value.percent(2)); // 12.30%
  print(value.format()); // locale dependent
  print(value.formatCompact); // compact format (getter)
  print(value.lerpTo(1.0, 0.5)); // 0.5615

  Future<int> futureValue = Future.value(5);
  await futureValue.thenRun((v) => print("Value: $v"));

  Map<String, int> map1 = {"a": 1, "b": 2};
  Map<String, int> map2 = {"c": 3};
  print(map1 + map2); // {a: 1, b: 2, c: 3}
}
```
