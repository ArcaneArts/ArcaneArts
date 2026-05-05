---
name: commit
description: Inspect staged and unstaged repository changes, combine them with the active conversation, and write a focused git commit with an accurate message and scope. Use when Codex should prepare or create a commit for current work, decide whether unstaged edits belong with staged ones, and keep unrelated changes out of the commit.
---

# Commit

Run this skill from repository root.

## Workflow

1. Gather commit context:

```bash
python3 /path/to/skills/commit/scripts/commit_scout.py --root .
```

2. Read the active conversation for:
- the user goal,
- promised behavior changes,
- constraints or caveats,
- validation already run.

3. Decide commit scope:
- prefer one coherent logical change,
- treat staged and unstaged changes as separate inputs,
- stage additional files only when they clearly belong to the same change,
- keep unrelated or uncertain work out of the commit.

4. Match repository conventions:
- inspect recent commit subjects from the scout output,
- reuse existing prefixes or tone when the repo already has a pattern,
- keep the subject specific and imperative.

5. Write the commit:
- subject line first,
- add a body when conversation context, rationale, follow-up work, or validation matters,
- mention meaningful verification when it strengthens the record.

6. Create the commit using only the intended files.
7. Report:
- commit hash,
- files included,
- important files intentionally left out.

## Message Rules

- Describe the actual change, not the tool used to make it.
- Use conversation context for intent that is not obvious from the diff.
- Prefer precise subjects over vague summaries like `updates` or `fix stuff`.
- If the change is only tests, docs, chores, or release prep, say so explicitly.
- Keep the subject compact; keep the body factual.

## Staged vs Unstaged Rules

1. If staged files already form a clean change, commit only staged files.
2. If unstaged files clearly complete that same change, stage them deliberately first.
3. If staged and unstaged work are unrelated, do not blend them into one commit.
4. If a file is partially staged, inspect carefully before adding more hunks.
5. Never force a commit message to cover unrelated work just because it is present.

## Conversation Inputs Worth Capturing

- the feature or bug being addressed,
- behavior guarantees or non-goals,
- notable validation steps or test commands,
- important follow-up context the next reader should know.

## Draft-Only Mode

If the user wants help wording a commit but does not want the commit created yet:

1. inspect the same staged and unstaged context,
2. draft the subject and optional body,
3. explain what the draft covers and what it leaves out,
4. stop before running `git commit`.

## Stop Conditions

- multiple unrelated changes are mixed together,
- scope cannot be determined honestly from the diff and conversation,
- the commit would require speculative staging,
- another person's unexpected edits are present and ownership is unclear,
- there is nothing meaningful to commit.

## Boundaries and Handoffs

- Use `issuify` for issue write-ups, not commit messages.
- Use `release-readiness-gate` for release GO/NO-GO evidence.
- Use `dart-pub-release` for versioning, changelog, and publish flows.
- Use implementation skills such as `bugfix`, `refine`, `peep-hole-optimize`, or `update-unit-tests` to make the code change first; this skill packages that work into a clean commit.
- Read [commit-guidelines.md](references/commit-guidelines.md) when commit style or scope is unclear.
