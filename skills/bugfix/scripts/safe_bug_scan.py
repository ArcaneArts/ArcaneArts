#!/usr/bin/env python3
"""Scan source files for low-risk bug patterns suitable for safe fixes."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_SOURCE_EXTENSIONS = {
    "c",
    "cc",
    "cpp",
    "cs",
    "cxx",
    "dart",
    "go",
    "h",
    "hpp",
    "java",
    "js",
    "jsx",
    "kt",
    "m",
    "mm",
    "php",
    "py",
    "rb",
    "rs",
    "swift",
    "ts",
    "tsx",
}

DEFAULT_IGNORE_DIRS = {
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


@dataclass(frozen=True)
class LinePattern:
    bug_id: str
    summary: str
    regex: re.Pattern[str]
    extensions: set[str]
    fix_hint: str
    risk: str = "low"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    bug_id: str
    summary: str
    risk: str
    snippet: str
    fix_hint: str


LINE_PATTERNS = (
    LinePattern(
        bug_id="OFF_BY_ONE_CSTYLE_LEQ_LENGTH",
        summary="C-style loop uses <= with length/size bound",
        regex=re.compile(
            r"\bfor\s*\([^;\n]*;[^;\n]*<=\s*[^;\n]*(?:\.length\b|\.size\s*\(\s*\)|len\s*\()"
        ),
        extensions={
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
            "rs",
            "swift",
            "ts",
            "tsx",
        },
        fix_hint="If loop indexes the same collection, replace <= with <.",
    ),
    LinePattern(
        bug_id="OFF_BY_ONE_PY_RANGE_LEN_PLUS_ONE",
        summary="Python range(len(x)+1) likely iterates one step too far",
        regex=re.compile(
            r"\bfor\b[^\n]*\bin\s+range\s*\(\s*len\s*\([^)]*\)\s*\+\s*1\s*\)"
        ),
        extensions={"py"},
        fix_hint="Use range(len(x)) unless explicit sentinel iteration is required.",
    ),
    LinePattern(
        bug_id="INDEX_AT_LENGTH_BOUNDARY",
        summary="Index expression uses length directly, likely out of bounds",
        regex=re.compile(
            r"\[\s*(?:len\s*\([^)]*\)|[A-Za-z_][\w.]*\.(?:length\b|size\s*\(\s*\)))\s*\]"
        ),
        extensions=DEFAULT_SOURCE_EXTENSIONS,
        fix_hint="Length is one past last valid index; use safe bounds or -1 when intended.",
    ),
)

CATCH_START_RE = re.compile(r"\bcatch\s*\(")
THROW_NEW_RE = re.compile(r"\bthrow\s+new\s+([A-Za-z_][\w.]*)\s*\((.*)\)\s*;")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find low-risk bug candidates for safe source-level fixes."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=500,
        help="Maximum number of findings to emit (default: 500).",
    )
    parser.add_argument(
        "--include-ext",
        default="",
        help="Comma-separated extension allowlist (without dots).",
    )
    parser.add_argument(
        "--ignore-dir",
        action="append",
        default=[],
        help="Directory name to ignore. Repeatable.",
    )
    return parser.parse_args()


def normalize_extensions(value: str) -> set[str]:
    if not value.strip():
        return set(DEFAULT_SOURCE_EXTENSIONS)
    result = set()
    for part in value.split(","):
        ext = part.strip().lower().lstrip(".")
        if ext:
            result.add(ext)
    return result


def build_ignore_dirs(user_ignores: list[str]) -> set[str]:
    combined = set(DEFAULT_IGNORE_DIRS)
    combined.update(name for name in user_ignores if name)
    return combined


def iter_source_files(root: Path, extensions: set[str], ignore_dirs: set[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in ignore_dirs and not name.startswith(".")
        ]
        for filename in filenames:
            ext = Path(filename).suffix.lower().lstrip(".")
            if not ext or ext not in extensions:
                continue
            files.append(Path(dirpath) / filename)
    files.sort()
    return files


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []


def scan_line_patterns(path: Path, rel_path: str, lines: list[str]) -> list[Finding]:
    ext = path.suffix.lower().lstrip(".")
    findings: list[Finding] = []
    for line_num, raw in enumerate(lines, start=1):
        snippet = raw.strip()
        for pattern in LINE_PATTERNS:
            if ext not in pattern.extensions:
                continue
            if not pattern.regex.search(raw):
                continue
            findings.append(
                Finding(
                    path=rel_path,
                    line=line_num,
                    bug_id=pattern.bug_id,
                    summary=pattern.summary,
                    risk=pattern.risk,
                    snippet=snippet,
                    fix_hint=pattern.fix_hint,
                )
            )
    return findings


def scan_missing_exception_cause(path: Path, rel_path: str, lines: list[str]) -> list[Finding]:
    ext = path.suffix.lower().lstrip(".")
    if ext not in {"java", "kt"}:
        return []

    findings: list[Finding] = []
    in_catch = False
    brace_depth = 0
    waiting_for_open_brace = False

    for line_num, raw in enumerate(lines, start=1):
        line = raw.strip()

        if not in_catch and CATCH_START_RE.search(raw):
            waiting_for_open_brace = True
            open_count = raw.count("{")
            close_count = raw.count("}")
            if open_count > 0:
                in_catch = True
                waiting_for_open_brace = False
                brace_depth = open_count - close_count
                if brace_depth <= 0:
                    in_catch = False
                    brace_depth = 0
                continue

        if waiting_for_open_brace and "{" in raw:
            in_catch = True
            waiting_for_open_brace = False
            brace_depth = raw.count("{") - raw.count("}")
            if brace_depth <= 0:
                in_catch = False
                brace_depth = 0
                continue

        if in_catch:
            throw_match = THROW_NEW_RE.search(raw)
            if throw_match:
                exception_type = throw_match.group(1)
                arguments = throw_match.group(2)
                if "," not in arguments:
                    findings.append(
                        Finding(
                            path=rel_path,
                            line=line_num,
                            bug_id="WRAPPED_EXCEPTION_MISSING_CAUSE",
                            summary="Exception is rethrown without preserving caught cause",
                            risk="low",
                            snippet=line,
                            fix_hint=(
                                "Pass the caught exception as cause "
                                f"(for example: new {exception_type}(message, e))."
                            ),
                        )
                    )

            brace_depth += raw.count("{")
            brace_depth -= raw.count("}")
            if brace_depth <= 0:
                in_catch = False
                brace_depth = 0

    return findings


def scan_file(path: Path, root: Path) -> list[Finding]:
    rel_path = str(path.relative_to(root))
    lines = read_lines(path)
    if not lines:
        return []

    findings: list[Finding] = []
    findings.extend(scan_line_patterns(path, rel_path, lines))
    findings.extend(scan_missing_exception_cause(path, rel_path, lines))
    return findings


def render_text(findings: list[Finding]) -> str:
    if not findings:
        return "No candidate safe-bug findings."

    lines: list[str] = []
    counts = Counter(f.bug_id for f in findings)

    for finding in findings:
        lines.append(f"{finding.path}:{finding.line}: [{finding.bug_id}] {finding.summary}")
        lines.append(f"  risk: {finding.risk}")
        lines.append(f"  snippet: {finding.snippet}")
        lines.append(f"  hint: {finding.fix_hint}")

    lines.append("")
    lines.append("Summary:")
    for bug_id in sorted(counts):
        lines.append(f"- {bug_id}: {counts[bug_id]}")
    lines.append(f"- total: {len(findings)}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    extensions = normalize_extensions(args.include_ext)
    ignore_dirs = build_ignore_dirs(args.ignore_dir)

    findings: list[Finding] = []
    for path in iter_source_files(root, extensions, ignore_dirs):
        if len(findings) >= args.max_findings:
            break
        file_findings = scan_file(path, root)
        remaining = max(args.max_findings - len(findings), 0)
        findings.extend(file_findings[:remaining])

    findings.sort(key=lambda f: (f.path, f.line, f.bug_id))

    if args.format == "json":
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(render_text(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
