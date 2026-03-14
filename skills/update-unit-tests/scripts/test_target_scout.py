#!/usr/bin/env python3
"""Scout low-scaffolding unit-test targets in a repository."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SOURCE_EXTENSIONS = {
    "c",
    "cc",
    "cpp",
    "cs",
    "cxx",
    "dart",
    "go",
    "java",
    "js",
    "jsx",
    "kt",
    "php",
    "py",
    "rb",
    "rs",
    "swift",
    "ts",
    "tsx",
}

IGNORE_DIRS = {
    ".dart_tool",
    ".git",
    ".idea",
    ".next",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "tmp",
    "vendor",
}

TEST_PATH_MARKERS = {"test", "tests", "__tests__", "spec", "specs"}
TEST_FILE_RE = re.compile(r"(^test_|_test\.|\.test\.|_spec\.|\.spec\.)")
FUNCTION_RE = re.compile(
    r"^\s*(?:def|func|fn|function|public|private|protected|static)\b", re.MULTILINE
)
HEAVY_KEYWORDS_RE = re.compile(
    r"(?:http|socket|grpc|kafka|redis|mysql|postgres|sqlite|mongodb|firebase|filesystem|"
    r"subprocess|thread|mutex|synchronized)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Target:
    source_file: str
    line_count: int
    function_like_count: int
    heavy_keyword_hits: int
    likely_simple: bool
    existing_tests: list[str]
    suggested_test_paths: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List source files likely suitable for low-scaffolding unit tests."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: current dir).")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--max-targets",
        type=int,
        default=200,
        help="Max number of targets to emit (default: 200).",
    )
    return parser.parse_args()


def is_test_file(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if TEST_PATH_MARKERS & lower_parts:
        return True
    return bool(TEST_FILE_RE.search(path.name.lower()))


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in IGNORE_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            ext = Path(filename).suffix.lower().lstrip(".")
            if not ext or ext not in SOURCE_EXTENSIONS:
                continue
            path = Path(dirpath) / filename
            if is_test_file(path.relative_to(root)):
                continue
            files.append(path)
    files.sort()
    return files


def list_test_files(root: Path) -> set[str]:
    result: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in IGNORE_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            path = Path(dirpath) / filename
            rel = path.relative_to(root)
            if is_test_file(rel):
                result.add(str(rel))
    return result


def guess_test_paths(rel_source: Path) -> list[str]:
    stem = rel_source.stem
    suffix = rel_source.suffix
    parent = rel_source.parent

    candidates = [
        parent / f"{stem}_test{suffix}",
        parent / f"{stem}.test{suffix}",
        parent / f"{stem}_spec{suffix}",
        parent / f"{stem}.spec{suffix}",
        Path("test") / parent / f"{stem}_test{suffix}",
        Path("tests") / parent / f"{stem}_test{suffix}",
        Path("__tests__") / parent / f"{stem}.test{suffix}",
    ]

    unique: list[str] = []
    seen = set()
    for candidate in candidates:
        text = str(candidate)
        if text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def build_target(root: Path, path: Path, known_tests: set[str]) -> Target | None:
    text = read_text(path)
    if not text:
        return None

    rel_source = path.relative_to(root)
    lines = text.splitlines()
    line_count = len(lines)
    function_like_count = len(FUNCTION_RE.findall(text))
    heavy_hits = len(HEAVY_KEYWORDS_RE.findall(text))

    suggestions = guess_test_paths(rel_source)
    existing = [candidate for candidate in suggestions if candidate in known_tests]

    likely_simple = (
        line_count <= 400 and function_like_count > 0 and heavy_hits <= 3
    )

    return Target(
        source_file=str(rel_source),
        line_count=line_count,
        function_like_count=function_like_count,
        heavy_keyword_hits=heavy_hits,
        likely_simple=likely_simple,
        existing_tests=existing,
        suggested_test_paths=suggestions[:3],
    )


def render_text(targets: list[Target]) -> str:
    if not targets:
        return "No candidate unit-test targets found."

    lines: list[str] = []
    for item in targets:
        simple_text = "yes" if item.likely_simple else "no"
        existing = ", ".join(item.existing_tests) if item.existing_tests else "(none)"
        suggested = ", ".join(item.suggested_test_paths)
        lines.append(f"{item.source_file}")
        lines.append(
            f"  simple: {simple_text}; lines: {item.line_count}; "
            f"functions: {item.function_like_count}; heavy-keywords: {item.heavy_keyword_hits}"
        )
        lines.append(f"  existing-tests: {existing}")
        lines.append(f"  suggested-tests: {suggested}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    known_tests = list_test_files(root)
    targets: list[Target] = []

    for path in iter_source_files(root):
        if len(targets) >= args.max_targets:
            break
        target = build_target(root, path, known_tests)
        if target is None:
            continue
        targets.append(target)

    targets.sort(
        key=lambda item: (
            0 if item.likely_simple else 1,
            0 if not item.existing_tests else 1,
            item.source_file,
        )
    )

    if args.format == "json":
        print(json.dumps([asdict(item) for item in targets], indent=2))
    else:
        print(render_text(targets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
