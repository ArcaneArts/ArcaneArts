#!/usr/bin/env python3
"""Automate Dart/Flutter package release and publish steps."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

SEMVER_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)
VERSION_LINE_RE = re.compile(r"^(\s*version\s*:\s*)([^\s#]+)(\s*(?:#.*)?)$")
CONVENTIONAL_PREFIX_RE = re.compile(r"^[a-z]+(?:\([^)]+\))?!?:\s*")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump pubspec version, update changelog, commit, and publish."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to package repository root (default: current directory).",
    )
    parser.add_argument(
        "--pubspec",
        default="pubspec.yaml",
        help="Path to pubspec.yaml (relative to --repo unless absolute).",
    )
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to changelog file (relative to --repo unless absolute).",
    )
    parser.add_argument(
        "--bump",
        choices=("patch", "minor", "major"),
        default="patch",
        help="Semantic version bump type (default: patch).",
    )
    parser.add_argument(
        "--commit-message",
        default="chore(release): {version}",
        help="Commit message template. {version} and {bump} are supported placeholders.",
    )
    parser.add_argument(
        "--skip-commit",
        action="store_true",
        help="Skip git add/commit step.",
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Skip `flutter pub publish --force` step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without writing, committing, or publishing.",
    )
    return parser.parse_args()


def run_cmd(
    cmd: list[str], cwd: Path, capture: bool = True, check: bool = True
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=capture,
    )
    if check and proc.returncode != 0:
        cmd_text = " ".join(cmd)
        detail = proc.stderr.strip() if proc.stderr else proc.stdout.strip()
        raise RuntimeError(f"Command failed: {cmd_text}\n{detail}")
    return proc


def resolve_path(repo: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo / path


def read_pubspec_version(pubspec_path: Path) -> str:
    if not pubspec_path.exists():
        raise RuntimeError(f"pubspec file not found: {pubspec_path}")
    lines = pubspec_path.read_text(encoding="utf-8").splitlines(keepends=True)
    for line in lines:
        match = VERSION_LINE_RE.match(line.rstrip("\n"))
        if match:
            return match.group(2)
    raise RuntimeError(f"No parseable `version:` line found in {pubspec_path}")


def bump_semver(current_version: str, bump: str) -> str:
    match = SEMVER_RE.match(current_version)
    if not match:
        raise RuntimeError(f"Version is not valid semantic version: {current_version}")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))

    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    return f"{major}.{minor}.{patch}"


def update_pubspec(pubspec_path: Path, new_version: str, dry_run: bool) -> None:
    lines = pubspec_path.read_text(encoding="utf-8").splitlines(keepends=True)
    replaced = False
    for idx, line in enumerate(lines):
        match = VERSION_LINE_RE.match(line.rstrip("\n"))
        if not match:
            continue
        lines[idx] = f"{match.group(1)}{new_version}{match.group(3)}\n"
        replaced = True
        break
    if not replaced:
        raise RuntimeError(f"No parseable `version:` line found in {pubspec_path}")
    if not dry_run:
        pubspec_path.write_text("".join(lines), encoding="utf-8")


def normalize_subject(subject: str) -> str:
    value = subject.strip()
    if not value:
        return ""
    value = CONVENTIONAL_PREFIX_RE.sub("", value)
    value = value.rstrip(".")
    return value


def find_release_base_tag(repo: Path) -> str | None:
    proc = run_cmd(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=repo,
        capture=True,
        check=False,
    )
    tag = (proc.stdout or "").strip()
    if proc.returncode != 0 or not tag:
        return None
    return tag


def collect_commit_subjects(repo: Path, base_tag: str | None) -> list[str]:
    if base_tag:
        cmd = ["git", "log", "--pretty=format:%s", "--no-merges", f"{base_tag}..HEAD"]
    else:
        cmd = ["git", "log", "--pretty=format:%s", "--no-merges", "-n", "30"]
    proc = run_cmd(cmd, cwd=repo, capture=True, check=False)
    raw_subjects = [line for line in (proc.stdout or "").splitlines() if line.strip()]

    seen = set()
    cleaned: list[str] = []
    for subject in raw_subjects:
        normalized = normalize_subject(subject)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)

    if cleaned:
        return cleaned
    return ["Maintenance release"]


def build_changelog_entry(new_version: str, bullets: list[str]) -> str:
    today = dt.date.today().isoformat()
    lines = [f"## {new_version} - {today}", ""]
    lines.extend(f"- {item}" for item in bullets)
    lines.append("")
    return "\n".join(lines)


def update_changelog(
    changelog_path: Path, new_version: str, entry: str, dry_run: bool
) -> None:
    if changelog_path.exists():
        existing = changelog_path.read_text(encoding="utf-8")
    else:
        existing = "# Changelog\n\nAll notable changes to this project are documented in this file.\n"

    if re.search(rf"^##\s+{re.escape(new_version)}(?:\s|$)", existing, flags=re.MULTILINE):
        raise RuntimeError(f"CHANGELOG already contains version {new_version}")

    lines = existing.splitlines(keepends=False)

    insert_at = 0
    if lines and lines[0].startswith("#"):
        insert_at = 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1

    prefix = lines[:insert_at]
    suffix = lines[insert_at:]
    new_lines: list[str] = []
    new_lines.extend(prefix)
    if new_lines and new_lines[-1].strip() != "":
        new_lines.append("")
    new_lines.extend(entry.rstrip().splitlines())
    new_lines.append("")
    if suffix:
        if suffix[0].strip() != "":
            new_lines.append("")
        new_lines.extend(suffix)

    new_content = "\n".join(new_lines).rstrip() + "\n"

    if not dry_run:
        changelog_path.write_text(new_content, encoding="utf-8")


def ensure_git_repo(repo: Path) -> None:
    proc = run_cmd(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo,
        capture=True,
        check=False,
    )
    if proc.returncode != 0 or (proc.stdout or "").strip() != "true":
        raise RuntimeError(f"Not a git repository: {repo}")


def rel_for_git(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def do_commit(
    repo: Path,
    pubspec_path: Path,
    changelog_path: Path,
    message: str,
    dry_run: bool,
) -> None:
    file_args = [rel_for_git(pubspec_path, repo), rel_for_git(changelog_path, repo)]
    if dry_run:
        print(f"[dry-run] git add {' '.join(file_args)}")
        print(f"[dry-run] git commit -m {message!r}")
        return
    run_cmd(["git", "add", *file_args], cwd=repo, capture=True, check=True)
    run_cmd(["git", "commit", "-m", message], cwd=repo, capture=True, check=True)


def do_publish(repo: Path, dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] flutter pub publish --force")
        return
    proc = subprocess.run(
        ["flutter", "pub", "publish", "--force"],
        cwd=str(repo),
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("`flutter pub publish --force` failed")


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    pubspec_path = resolve_path(repo, args.pubspec)
    changelog_path = resolve_path(repo, args.changelog)

    dry_run = bool(args.dry_run)
    skip_commit = bool(args.skip_commit or dry_run)
    skip_publish = bool(args.skip_publish or dry_run)

    try:
        ensure_git_repo(repo)
        current_version = read_pubspec_version(pubspec_path)
        new_version = bump_semver(current_version, args.bump)
        base_tag = find_release_base_tag(repo)
        bullets = collect_commit_subjects(repo, base_tag)
        entry = build_changelog_entry(new_version, bullets)

        print(f"Current version: {current_version}")
        print(f"Next version:    {new_version} ({args.bump} bump)")
        if base_tag:
            print(f"Changelog source: commits since tag {base_tag}")
        else:
            print("Changelog source: latest commit subjects (no tag found)")

        update_pubspec(pubspec_path, new_version, dry_run=dry_run)
        update_changelog(changelog_path, new_version, entry, dry_run=dry_run)
        print(f"Updated {pubspec_path}")
        print(f"Updated {changelog_path}")

        if not skip_commit:
            message = args.commit_message.format(version=new_version, bump=args.bump)
            do_commit(
                repo=repo,
                pubspec_path=pubspec_path,
                changelog_path=changelog_path,
                message=message,
                dry_run=dry_run,
            )
            print("Committed release files.")
        else:
            print("Skipped git commit.")

        if not skip_publish:
            do_publish(repo, dry_run=dry_run)
            print("Published package.")
        else:
            print("Skipped publish.")

        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Release failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
