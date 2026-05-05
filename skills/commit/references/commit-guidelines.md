# Commit Guidelines

Use these rules when the diff alone is not enough to decide how to commit.

## Subject Line

- Prefer imperative mood: `add`, `fix`, `refactor`, `document`.
- Keep it specific to the real change.
- Reuse repo prefixes when they already exist, such as `feat:`, `fix:`, `refactor:`, or `test:`.

Good:
- `feat(skills): add commit skill for diff-aware git commits`
- `fix(parser): guard empty token streams`
- `test(cache): cover stale entry eviction`

Weak:
- `misc updates`
- `changes`
- `final fixes`

## Commit Body

Add a body when one or more of these are true:
- the user conversation adds intent not obvious from the diff,
- the change has important constraints or non-goals,
- validation details would help future readers,
- some related work was intentionally left out.

Useful body topics:
- why the change exists,
- what behavior was preserved,
- which tests or checks ran,
- what was deliberately excluded from the commit.

## Scope Rules

- Prefer one commit per coherent change.
- Do not mix refactors, bug fixes, generated files, and experiments unless they are inseparable.
- If staged and unstaged work clearly represent different ideas, commit only the intended slice.
- If untracked files are documentation, fixtures, or tests for the same change, include them deliberately rather than accidentally.

## Truthfulness Checks

Before committing, verify that:
- the subject still matches every included file,
- the body does not claim tests or validation that did not run,
- the commit does not hide unrelated work under a broad label,
- the active conversation does not describe a different goal than the staged diff.
