# Commit Guidelines

Use these rules when the diff alone is not enough to decide how to commit.

## Subject Line

- Prefer imperative mood: `add`, `fix`, `refactor`, `document`.
- Keep it specific to the real change, even when the commit is a broad sync snapshot.
- Reuse repo prefixes when they already exist, such as `feat:`, `fix:`, `refactor:`, or `test:`.

Good:
- `chore(repo): sync local work`
- `feat(skills): sync current skill updates`
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
- some related work was intentionally left out because the user asked for a narrow commit.

Useful body topics:
- why the change exists,
- what behavior was preserved,
- which tests or checks ran,
- what was deliberately excluded from the commit,
- that this was a broad sync snapshot to continue work elsewhere.

## Scope Rules

- Default to one broad sync commit for the current working tree.
- Include staged, unstaged, untracked, and generated files by default when the user asked to commit their current work.
- Only narrow the commit to a specific folder, feature, or exclusion when the user explicitly asks for that.
- Do not spend time separating multiple themes unless the user asked for a split commit workflow.

## Truthfulness Checks

Before committing, verify that:
- the subject still matches the overall snapshot,
- the body does not claim tests or validation that did not run,
- the broad sync label is still honest for the included work,
- the active conversation does not describe a narrower scope than the staged diff.
