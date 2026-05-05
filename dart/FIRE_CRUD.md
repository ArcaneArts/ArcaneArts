# Fire CRUD

[![Pub](https://img.shields.io/pub/v/fire_crud.svg)](https://pub.dev/packages/fire_crud)

A comprehensive Dart package for performing typed, hierarchical CRUD operations on Firestore. Fire CRUD simplifies working with Firestore by providing a model-based approach that handles serialization, nested document structures, efficient querying, real-time streaming, and pagination. It eliminates boilerplate for mapping Firestore data to Dart models, supports parent-child relationships for complex data hierarchies, and integrates seamlessly with [fire_api](https://pub.dev/packages/fire_api) for Firestore interactions.

## Why Fire CRUD?

Firestore's native API is powerful but verbose for typed applications, especially with nested collections. Fire CRUD addresses this by:
- Enabling type-safe models with automatic path generation for hierarchical data.
- Providing utilities for CRUD on individual documents and collections.
- Supporting efficient collection views with caching, streaming windows, and smart pagination to handle large datasets without full loads.
- Offering atomic operations and existence checks for robust data management.
- Reducing repetitive code for serialization/deserialization using artifact functions.

Ideal for Flutter/Dart apps needing scalable, real-time data persistence.

## Installation

Add to your `pubspec.yaml`:

```yaml
dependencies:
  fire_crud: ^latest_version
  fire_api: ^latest_version  # Required for Firestore access

dev_dependencies:
  build_runner: ^latest_version  # If using code generation (optional)
```

Run:
```
flutter pub get
```

### Setup Requirements

Fire CRUD relies on [fire_api](https://pub.dev/packages/fire_api) for Firestore connectivity. Follow its setup guide to initialize Firebase in your app (e.g., via `Firebase.initializeApp()` in `main()`).

## Key Components

### 1. FireModel<T extends ModelCrud>
Represents a model type for Firestore documents or subcollections. Handles:
- Serialization (`toMap`, `fromMap`) and construction.
- Path templating for nested hierarchies (e.g., `parent/{parent.id}/child/{child.id}`).
- Exclusive documents (fixed ID) vs. dynamic collections.

Use for root and child models.

### 2. ModelCrud (Mixin)
Core mixin for your data classes. Provides:
- `documentPath`: Full Firestore path.
- `childModels`: List of `FireModel` for nested children.
- CRUD methods: `get<T>`, `set<T>`, `add<T>`, `delete<T>`, `stream<T>`.
- Collection ops: `walk<T>`, `view<T>`, `paginate<T>`, `streamAll<T>`, `getAll<T>`, `count<T>`.
- Atomic updates: `setAtomic<T>`, `updateAtomic<T>`.
- Parent navigation: `parentModel<T>()`, `parentModelPath()`.

Implements `ModelAccessor` for type-safe access.

### 3. FireCrud (Singleton)
Global entry point (`$crud`). Manages:
- Model registration (`registerModel`, `registerModels`).
- Root-level CRUD: `$get<T>`, `$set<T>`, etc.
- Artifact setup for global serialization: `setupArtifact(fromMap, toMap, construct)`.
- Path resolution: `modelForPath`, `getCrudForDocumentPath`.

Access via `import 'package:fire_crud/fire_crud.dart';` and use `$crud`.

### 4. ModelAccessor (Abstract Interface)
Defines access patterns for models and children. Implemented by `ModelCrud` and `FireCrud`.

### 5. CollectionViewer<T>
Efficient viewer for collections with:
- Indexed access (`getAt(index)`).
- Streaming windows with padding for smooth navigation.
- Caching (up to `memorySize` snapshots).
- Size tracking and auto-retargeting.
- Cleanup for memory management.

Use for large lists with partial loading.

### 6. ModelUtility
Static helpers for:
- Model selection (`selectChildModel<T>`).
- Pagination (`pullPage<T>` returns `ModelPage<T>`).
- Diffing updates (`getUpdates(before, after)` for minimal Firestore ops).
- Flattening/unflattening nested maps.

### 7. ModelPage<T>
Paginated result with `items`, `nextPage()`, and cursors. Supports forward/reverse.

## Defining Models

Models must mix in `ModelCrud` and define `childModels` for nesting.

```dart
import 'package:fire_crud/fire_crud.dart';

// Example: User with settings (unique) and notes (collection)
class User with ModelCrud {
  final String name;
  final int age;

  // Constructor, copyWith, toMap, fromMap (use packages like freezed or json_serializable)
  const User({required this.name, required this.age});

  @override
  List<FireModel> get childModels => [
    // Unique sub-document: users/{userId}/data/settings
    FireModel.artifact<Usersettings>(
      'data',
      exclusiveDocumentId: 'settings',
    ),
    // Collection: users/{userId}/notes/{noteId}
    FireModel.artifact<Note>('notes'),
  ];
}

class Usersettings with ModelCrud {
  final bool darkMode;

  const Usersettings({this.darkMode = false});

  @override
  List<FireModel> get childModels => [];  // Leaf model
}

class Note with ModelCrud {
  final String title;
  final String content;

  const Note({required this.title, required this.content});

  @override
  List<FireModel> get childModels => [];  // Leaf model
}
```

- Use `FireModel.artifact` for registered serialization (see Setup).
- Paths auto-generate: Root `users/{id}`, child `users/{id}/notes/{noteId}`.

## Setup

1. **Initialize Firestore** (via fire_api):
   ```dart
   import 'package:fire_api/fire_api.dart';

   void main() async {
     WidgetsFlutterBinding.ensureInitialized();
     await Firebase.initializeApp();
     runApp(MyApp());
   }
   ```

2. **Register Artifact Functions** (global serialization):
   ```dart
   // In main() or init
   $crud.setupArtifact(
     (map) => YourArtifact.fromMap(map),  // Deserialize
     (obj) => obj.toMap(),                // Serialize
     () => YourArtifact(),                // Construct empty
   );
   ```

3. **Register Root Models**:
   ```dart
   $crud.registerModels([
     FireModel.artifact<User>('users'),
     // Add other roots
   ]);
   ```
   - Call once at app startup.
   - Enables type-safe access via `$crud.$model<User>(id)`.

## Usage

### Basic CRUD on Root Models

```dart
// Create/Add
User newUser = const User(name: 'Alice', age: 30);
User addedUser = await $crud.$add(newUser);  // Auto-ID

// Or with ID
await $crud.$set('user123', newUser);

// Read
User? user = await $crud.$get<User>('user123');

// Update
await $crud.$update<User>('user123', {'age': 31});

// Atomic Update
await $crud.$updateAtomic<User>('user123', (initial) {
  return initial?.copyWith(age: (initial.age ?? 0) + 1) ?? User(name: '', age: 1);
});

// Delete
await $crud.$delete<User>('user123');

// Stream
Stream<User?> userStream = $crud.$stream<User>('user123');
```

### Unique Models (No ID)

For single-instance docs (e.g., settings):
```dart
// Ensure exists (create if absent)
Usersettings settings = await $crud.ensureExistsUnique<Usersettings>(
  const Usersettings(darkMode: true),
);

// Read/Update
Usersettings? current = await $crud.getUnique<Usersettings>();
await $crud.updateUnique<Usersettings>({'darkMode': false});
```

### Nested Models (Children)

Access via parent:
```dart
// From root
User user = $crud.$model<User>('user123');
Usersettings settings = user.modelUnique<Usersettings>();  // Unique child

// Add to collection child
Note newNote = const Note(title: 'Hello', content: 'World');
Note addedNote = await user.$add<Note>(newNote);

// Read child
Note? note = await user.$get<Note>('note456');

// Update child
await user.$update<Note>('note456', {'content': 'Updated'});

// Stream child
Stream<Note?> noteStream = user.$stream<Note>('note456');

// Parent navigation
Note note = ...;
User parentUser = note.parentModel<User>();
```

### Collections

#### Pagination
```dart
// Paginate notes (50 per page)
ModelPage<Note>? page = await user.paginate<Note>(
  pageSize: 20,
  query: (ref) => ref.orderBy('title'),
  reversed: false,
);

List<Note> notes = page?.items ?? [];
ModelPage<Note>? next = await page?.nextPage();
```

#### Streaming All
```dart
Stream<List<Note>> notesStream = user.streamAll<Note>(
  query: (ref) => ref.where('title', isNotEqualTo: '').orderBy('timestamp'),
);
```

#### Walker (Traversal)
```dart
CollectionWalker<Note> walker = user.walk<Note>(
  query: (ref) => ref.orderBy('title'),
);
Note? first = await walker.next();  // Or previous() for reverse
```

#### Viewer (Indexed Access)
```dart
CollectionViewer<Note> viewer = user.view<Note>();
Note? noteAtIndex5 = await viewer.getAt(5);  // Efficient fetch with caching
viewer.stream.listen((updatedViewer) {
  // Handle updates
});
int totalSize = viewer.size;
```

### Advanced Features

#### Existence Checks
```dart
bool exists = await user.$exists<Note>('note456');
bool uniqueExists = await user.existsUnique<Usersettings>();
```

#### Ensure Exists
```dart
// Create if absent
Note ensured = await user.$ensureExists<Note>('note456', defaultNote);
```

#### Change Notification (Diff-Based Update)
```dart
Note before = ...;
Note after = before.copyWith(content: 'New');
await user.$change('note456', before, after);  // Minimal update
```

#### Delete All
```dart
await user.deleteAll<Note>(query: (ref) => ref.where('deleted', isEqualTo: true));
```

## Examples

### Full App Flow
```dart
// main.dart
void main() async {
  // Firebase init...
  $crud.setupArtifact(/* your functions */);
  $crud.registerModels([FireModel.artifact<User>('users')]);
  runApp(MyApp());
}

// In a service
class UserService {
  Future<User> createUser(String name, int age) async {
    User user = User(name: name, age: age);
    return await $crud.$add(user);
  }

  Future<List<Note>> getUserNotes(String userId) async {
    User user = $crud.$model<User>(userId);
    return await user.getAll<Note>(query: (ref) => ref.orderBy('timestamp', descending: true));
  }

  Stream<List<Note>> streamNotes(String userId) {
    User user = $crud.$model<User>(userId);
    return user.streamAll<Note>();
  }
}
```

### Pagination in UI
```dart
class NotesList extends StatefulWidget {
  final String userId;
  NotesList(this.userId);

  @override
  _NotesListState createState() => _NotesListState();
}

class _NotesListState extends State<NotesList> {
  ModelPage<Note>? _currentPage;
  List<Note> _notes = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadNotes();
  }

  Future<void> _loadNotes() async {
    User user = $crud.$model<User>(widget.userId);
    _currentPage = await user.paginate<Note>(pageSize: 20);
    setState(() {
      _notes = _currentPage?.items ?? [];
      _loading = false;
    });
  }

  Future<void> _loadMore() async {
    if (_currentPage != null) {
      ModelPage<Note>? next = await _currentPage!.nextPage();
      if (next != null) {
        setState(() {
          _notes.addAll(next.items);
          _currentPage = next;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return CircularProgressIndicator();
    return ListView.builder(
      itemCount: _notes.length + (_currentPage?.hasMore ?? false ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _notes.length) {
          _loadMore();  // Load on demand
          return CircularProgressIndicator();
        }
        return ListTile(title: Text(_notes[index].title));
      },
    );
  }
}
```

## Best Practices

- **Serialization**: Use consistent `toMap`/`fromMap` (e.g., via `json_annotation` or `freezed`).
- **Performance**: Use `CollectionViewer` for large lists; limit queries with `where`.
- **Hierarchy**: Define `childModels` only for direct subcollections to avoid deep nesting issues.
- **Error Handling**: Wrap ops in try-catch for `FirestoreException`.
- **Testing**: Mock Firestore with `fire_api`'s testing utils.

## Limitations

- Requires explicit model registration.
- Nested paths assume even segment counts (collection/doc pairs).
- No built-in validation; add via model constructors.

For issues or contributions, see [GitHub](https://github.com/your-repo/fire_crud).
