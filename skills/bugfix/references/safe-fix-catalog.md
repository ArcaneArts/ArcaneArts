# Safe Fix Catalog

Use this catalog to decide whether a scanner finding is safe to patch.

## Low-Risk Fixes (Allowed)

### 1) Off-by-one loop bound

- Pattern: `i <= arr.length` while indexing `arr[i]`
- Safe fix: use `<` for upper bound
- Example:
  - before: `for (int i = 0; i <= arr.length; i++) { use(arr[i]); }`
  - after: `for (int i = 0; i < arr.length; i++) { use(arr[i]); }`

### 2) Python len+1 range

- Pattern: `for i in range(len(items) + 1):`
- Safe fix: remove `+ 1` unless explicit sentinel logic is documented
- Example:
  - before: `for i in range(len(items) + 1):`
  - after: `for i in range(len(items)):`

### 3) Index at length boundary

- Pattern: `items[len(items)]`, `arr[arr.length]`
- Safe fix: use `len(items) - 1` or rewrite with safe loop bound if context is index traversal
- Guardrail: skip if zero-length behavior is unclear

### 4) Wrapped exception missing cause

- Pattern: catching an exception and throwing a new one without passing original cause
- Safe fix: include cause (`new RuntimeException("...", e)`, `throw FooError("...", cause=e)`)
- Goal: preserve diagnostic chain without changing core behavior

## Skip (Not Safe for This Skill)

- Concurrency bugs, locking, races, deadlocks
- Timezone/date logic redesign
- SQL/data migration semantics
- Security/authz policy changes
- Multi-module refactors
- Large control-flow rewrites
- Any fix that needs product/domain interpretation

## Verification Checklist

1. Re-run scanner and ensure finding disappears.
2. Run nearest tests for changed files.
3. Run project analyzer/lint if available.
4. Ensure no new warnings/errors introduced by the patch.
