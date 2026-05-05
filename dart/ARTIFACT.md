# Artifact

[![Pub](https://img.shields.io/pub/v/artifact.svg)](https://pub.dev/packages/artifact)

Artifact is a Dart model codegen system with no `part` files and no class mixins/extensions you have to manually wire.

You annotate a class, run the generator, and get:
- map + multi-format serialization/deserialization
- immutable `copyWith` support (delta/reset/delete/append/remove)
- optional runtime reflection metadata
- optional JSON-schema generation
- optional auto-export surface generation

## Project Manifest

For a file-by-file feature map, see [MANIFEST.md](MANIFEST.md).

## Core Design

- Constructor parameters define the serialized model shape.
- Generated APIs are extension-based (`$MyType`, `instance.to`, `$MyType.from`).
- Runtime reflection is generated code metadata, not `dart:mirrors`.

## Install

```bash
flutter pub add artifact
flutter pub add artifact_gen build_runner --dev
```

Generate:

```bash
dart run build_runner build --delete-conflicting-outputs
```

This writes:
- `lib/gen/artifacts.gen.dart`
- `lib/gen/exports.gen.dart` (if export rules are enabled)

## Quick Start

```dart
import 'package:artifact/artifact.dart';
import 'gen/artifacts.gen.dart';

@artifact
class MyModel {
  final int value;
  final double otherValue;

  const MyModel({this.value = 4, required this.otherValue});
}
```

## Serialization / Deserialization

```dart
MyModel model = const MyModel(otherValue: 2.5);

Map<String, dynamic> map = model.toMap();
String json = model.to.json;
String pretty = model.to.jsonPretty;
String yaml = model.to.yaml;
String toon = model.to.toon;
String toml = model.to.toml;
String props = model.to.props;
String bson = model.to.bson;

MyModel fromMap = $MyModel.fromMap(map);
MyModel fromJson = $MyModel.from.json(json);
MyModel fromYaml = $MyModel.from.yaml(yaml);
MyModel fromBson = $MyModel.from.bson(bson);
```

## CopyWith (Immutable Updates)

Generated `copyWith` supports:
- direct field replacement
- `resetField` for default resets
- `deleteField` for nullable named fields
- `deltaField` for numeric fields
- `appendField` / `removeField` for `List` and `Set`

```dart
@artifact
class Stats {
  final int hp;
  final String? note;
  final List<int> history;

  const Stats({this.hp = 10, this.note, this.history = const <int>[]});
}

Stats s = const Stats(hp: 10, note: 'a', history: <int>[1, 2]);

Stats next = s.copyWith(
  deltaHp: 5,
  deleteNote: true,
  appendHistory: <int>[3],
  removeHistory: <int>[1],
);
```

## Reflection (Optional)

Enable with `@Artifact(reflection: true)`.

```dart
class Property {
  const Property();
}

const Artifact model = Artifact(reflection: true);

@model
class Person {
  @Property()
  final String firstName;

  @Property()
  final String? lastName;

  const Person({required this.firstName, this.lastName});
}
```

Use reflection metadata:

```dart
Person(firstName: 'A').to.json; // ensure generated registration is loaded

ArtifactTypeMirror? type = ArtifactReflection.typeOf(Person);
ArtifactMirror mirror = ArtifactReflection.instanceOf(
  const Person(firstName: 'A', lastName: 'B'),
)!;

for (ArtifactFieldInfo field in type!.annotatedFields<Property>()) {
  print('${field.name}: ${field.fieldType}');
}

ArtifactMirror updated = mirror.setFieldValue('lastName', null);
```

Cross-type queries are available via both `ArtifactReflection` and `ArtifactAccessor`:
- class annotations
- field annotations
- method annotations
- extends / mixin / interface filters

## Schema Generation (Optional)

Enable with `@Artifact(generateSchema: true)` and use:

```dart
Map<String, dynamic> schema = $MyModel.schema;
```

## Custom Codecs

Register per type with `@codec(...)` on classes/fields/ctors/methods.

```dart
class Weird {
  final int raw;
  const Weird(this.raw);
}

class WeirdCodec extends ArtifactCodec<int, Weird> {
  const WeirdCodec();

  @override
  Weird? decode(int? value) => value == null ? null : Weird(value);

  @override
  int? encode(Weird? value) => value?.raw;
}

@artifact
class UsesCodec {
  @codec(WeirdCodec())
  final Weird data;

  const UsesCodec({this.data = const Weird(7)});
}
```

## Auto Exporting

In `pubspec.yaml`:

```yaml
artifact:
  export: true
```

Use `@internal` to hide declarations and `@external` to force explicit export surface selection.

## Testing

Runtime generated API tests:

```bash
dart run build_runner build --delete-conflicting-outputs
dart test test/generated
```

Generator integration tests:

```bash
cd artifact_gen
dart test
```

## Notes

- There is no attachment-specific generated API anymore (`getAttachment`, `rootAttachments`, etc).
  Use normal annotations and reflection queries (`getAnnotations<T>`, `withAnnotation<T>`, `annotatedFields<T>`) instead.
- `events.dart` now provides event annotations only (`EventHandler`, `EventPriority`), not a runtime event bus.
- Model serialization is constructor-driven; fields not represented by constructor parameters are excluded.
