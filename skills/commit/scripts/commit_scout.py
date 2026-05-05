#!/usr/bin/env python3
"""Summarize staged and unstaged git state for the commit skill."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(root: Path, *args: str, allow_fail: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and not allow_fail:
        stderr = result.stderr.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr or result.returncode}")
    return result.stdout.strip()


def lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def print_section(title: str, content: list[str] | str) -> None:
    print(f"## {title}")
    if isinstance(content, str):
        output = content.strip()
        print(output if output else "(none)")
    else:
        if content:
            for item in content:
                print(item)
        else:
            print("(none)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root or any path inside it")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    try:
        repo_root = Path(run_git(root, "rev-parse", "--show-toplevel"))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    branch = run_git(repo_root, "branch", "--show-current", allow_fail=True) or "(detached HEAD)"
    status = lines(run_git(repo_root, "status", "--short"))
    staged_files = sorted(lines(run_git(repo_root, "diff", "--cached", "--name-only")))
    unstaged_files = sorted(lines(run_git(repo_root, "diff", "--name-only")))
    untracked_files = sorted(lines(run_git(repo_root, "ls-files", "--others", "--exclude-standard")))
    recent_commits = lines(
        run_git(repo_root, "log", "-5", "--pretty=format:%h %s", allow_fail=True)
    )
    staged_stat = lines(run_git(repo_root, "diff", "--cached", "--stat"))
    unstaged_stat = lines(run_git(repo_root, "diff", "--stat"))

    overlapping_files = sorted(set(staged_files) & set(unstaged_files))

    hints: list[str] = []
    if staged_files and not unstaged_files and not untracked_files:
        hints.append("- Staged files already look like a self-contained commit candidate.")
    if not staged_files and (unstaged_files or untracked_files):
        hints.append("- Nothing is staged yet; decide whether to draft-only or stage a coherent slice first.")
    if overlapping_files:
        hints.append(
            "- Some files are both staged and unstaged; check for partially staged hunks before committing."
        )
    if len(staged_files) > 1 or len(unstaged_files) > 1 or len(untracked_files) > 1:
        hints.append("- Review for unrelated work before writing a single commit message.")
    if not hints:
        hints.append("- Inspect the diff and active conversation to determine the cleanest commit scope.")

    print(f"Repository: {repo_root}")
    print(f"Branch: {branch}")
    print()

    print_section("Recent Commits", recent_commits)
    print_section("Status", status)
    print_section("Staged Files", staged_files)
    print_section("Unstaged Files", unstaged_files)
    print_section("Untracked Files", untracked_files)
    print_section("Files In Both Staged And Unstaged Sets", overlapping_files)
    print_section("Staged Diff Stat", staged_stat)
    print_section("Unstaged Diff Stat", unstaged_stat)
    print_section("Scope Hints", hints)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
