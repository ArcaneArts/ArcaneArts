---
name: commit
description: Inspect repository changes, combine them with the active conversation, and write a broad git commit that syncs the current working tree by default. Use when Codex should package all local progress into one commit so work can continue elsewhere, and only switch to a narrower folder- or feature-scoped commit when the user explicitly asks for it.
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
- default to a broad sync commit that includes staged, unstaged, and untracked work,
- assume the user wants the whole working tree committed unless they explicitly request a narrower slice,
- switch to a folder- or feature-scoped commit only when the user says so,
- if the user wants everything committed, stage the whole tree deliberately with `git add -A`.

4. Match repository conventions:
- inspect recent commit subjects from the scout output,
- reuse existing prefixes or tone when the repo already has a pattern,
- keep the subject specific and imperative.

5. Write the commit:
- subject line first,
- add a body when conversation context, rationale, follow-up work, or validation matters,
- mention meaningful verification when it strengthens the record.

6. Create the commit:
- by default, commit the full working tree after staging it,
- only limit the file set when the user explicitly asked for a narrower commit.
7. Report:
- commit hash,
- files included,
- important files intentionally left out when there was an explicit narrow scope.

## Default Assumption

- Broad commits are the default.
- Favor syncing the user's current work so they can keep moving on another machine later.
- Do not spend time separating staged versus unstaged work unless the user asked for a narrow commit or exclusion.

## Message Rules

- Describe the actual change, not the tool used to make it.
- Use conversation context for intent that is not obvious from the diff.
- Prefer precise subjects over vague summaries like `updates` or `fix stuff`.
- Broad sync commits can still be truthful and specific, such as `chore(repo): sync local work` or `feat(skills): sync current skill updates`.
- If the change is mostly tests, docs, chores, or release prep, say so explicitly.
- Keep the subject compact; keep the body factual.

## Staged vs Unstaged Rules

1. Treat staged, unstaged, and untracked work as one broad commit by default.
2. If files are partially staged and the user wants a broad sync, stage the remaining hunks too.
3. Only preserve a narrow staged-only commit when the user explicitly asked for a specific folder, feature, or exclusion.
4. Do not split the tree into multiple commits unless the user explicitly requests that workflow.
5. Write the message to match the broad snapshot honestly instead of trying to force artificial precision.

## Conversation Inputs Worth Capturing

- the feature or bug being addressed,
- behavior guarantees or non-goals,
- notable validation steps or test commands,
- important follow-up context the next reader should know.

## Draft-Only Mode

If the user wants help wording a commit but does not want the commit created yet:

1. inspect the same staged and unstaged context,
2. assume a broad sync draft unless the user asked for a narrow scope,
3. draft the subject and optional body,
4. explain what the draft covers and what it leaves out,
5. stop before running `git commit`.

## Stop Conditions

- the user explicitly asks for a narrow scope but the requested boundaries are unclear,
- the body would need to claim validation or intent that did not happen,
- there is nothing meaningful to commit.

## Boundaries and Handoffs

- Use `issuify` for issue write-ups, not commit messages.
- Use `release-readiness-gate` for release GO/NO-GO evidence.
- Use `dart-pub-release` for versioning, changelog, and publish flows.
- Use implementation skills such as `bugfix`, `refine`, `peep-hole-optimize`, or `update-unit-tests` to make the code change first; this skill packages that work into a broad sync commit by default.
- Read [commit-guidelines.md](references/commit-guidelines.md) when commit style or scope is unclear.
