#!/usr/bin/env python3
"""Scout structural refactor opportunities: large files, long functions, duplication."""

from __future__ import annotations

import argparse
import hashlib
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

STRING_RE = re.compile(r"('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")")
FUNC_START_RE = re.compile(r"^\s*(def|func|function|public|private|protected|static)\b")


@dataclass(frozen=True)
class Finding:
    kind: str
    path: str
    line: int
    severity: str
    summary: str
    evidence: str
    action: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scout low-risk modular refactor opportunities.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument("--large-file-lines", type=int, default=400, help="Large file threshold.")
    parser.add_argument("--long-function-lines", type=int, default=80, help="Long function threshold.")
    parser.add_argument("--dup-window-lines", type=int, default=7, help="Duplicate block window size.")
    parser.add_argument("--max-findings", type=int, default=300, help="Max findings to emit.")
    return parser.parse_args()


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in IGNORE_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            ext = Path(filename).suffix.lower().lstrip(".")
            if ext and ext in SOURCE_EXTENSIONS:
                files.append(Path(dirpath) / filename)
    files.sort()
    return files


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []


def normalize_line(line: str, ext: str) -> str:
    cleaned = STRING_RE.sub('""', line)
    if ext in {"py", "rb"}:
        if "#" in cleaned:
            cleaned = cleaned.split("#", 1)[0]
    else:
        if "//" in cleaned:
            cleaned = cleaned.split("//", 1)[0]
    return re.sub(r"\s+", " ", cleaned).strip()


def find_large_file(rel_path: str, lines: list[str], threshold: int) -> list[Finding]:
    if len(lines) <= threshold:
        return []
    return [
        Finding(
            kind="LARGE_FILE",
            path=rel_path,
            line=1,
            severity="medium",
            summary=f"File has {len(lines)} lines (>{threshold}).",
            evidence=lines[0][:200] if lines else "",
            action="Split by cohesive responsibilities into smaller modules/files.",
        )
    ]


def find_long_functions(rel_path: str, lines: list[str], threshold: int) -> list[Finding]:
    findings: list[Finding] = []
    start_idx = None
    for idx, line in enumerate(lines):
        if FUNC_START_RE.search(line):
            if start_idx is not None:
                length = idx - start_idx
                if length > threshold:
                    findings.append(
                        Finding(
                            kind="LONG_FUNCTION",
                            path=rel_path,
                            line=start_idx + 1,
                            severity="medium",
                            summary=f"Function-like block spans ~{length} lines (>{threshold}).",
                            evidence=lines[start_idx][:200],
                            action="Extract helper methods or split logic by concern.",
                        )
                    )
            start_idx = idx
    if start_idx is not None:
        length = len(lines) - start_idx
        if length > threshold:
            findings.append(
                Finding(
                    kind="LONG_FUNCTION",
                    path=rel_path,
                    line=start_idx + 1,
                    severity="medium",
                    summary=f"Function-like block spans ~{length} lines (>{threshold}).",
                    evidence=lines[start_idx][:200],
                    action="Extract helper methods or split logic by concern.",
                )
            )
    return findings


def build_dup_index(
    root: Path, files: list[Path], window_lines: int
) -> tuple[dict[str, list[tuple[str, int]]], dict[str, str]]:
    index: dict[str, list[tuple[str, int]]] = {}
    sample: dict[str, str] = {}
    for file_path in files:
        rel = str(file_path.relative_to(root))
        ext = file_path.suffix.lower().lstrip(".")
        lines = read_lines(file_path)
        norm = [normalize_line(line, ext) for line in lines]
        if len(norm) < window_lines:
            continue
        for i in range(0, len(norm) - window_lines + 1):
            window = norm[i : i + window_lines]
            if any(not x for x in window):
                continue
            joined = "\n".join(window)
            # Skip tiny/boilerplate-only windows.
            if len(joined) < 80 or len(re.findall(r"[A-Za-z0-9_]+", joined)) < 14:
                continue
            key = hashlib.sha1(joined.encode("utf-8")).hexdigest()
            index.setdefault(key, []).append((rel, i + 1))
            sample.setdefault(key, joined[:220])
    return index, sample


def find_duplicate_blocks(
    root: Path, files: list[Path], window_lines: int, max_findings: int
) -> list[Finding]:
    index, sample = build_dup_index(root, files, window_lines)
    findings: list[Finding] = []
    for key, positions in index.items():
        unique_positions = sorted(set(positions))
        if len(unique_positions) < 2:
            continue
        primary_path, primary_line = unique_positions[0]
        findings.append(
            Finding(
                kind="DUPLICATE_BLOCK",
                path=primary_path,
                line=primary_line,
                severity="high",
                summary=f"Potential duplicated block appears {len(unique_positions)} times.",
                evidence=sample.get(key, ""),
                action="Extract shared helper/module and call from duplicated locations.",
            )
        )
        if len(findings) >= max_findings:
            break
    return findings


def render_text(findings: list[Finding]) -> str:
    if not findings:
        return "No refactor opportunities found with current thresholds."
    lines: list[str] = []
    for f in findings:
        lines.append(f"{f.path}:{f.line}: [{f.kind}] {f.summary}")
        lines.append(f"  severity: {f.severity}")
        lines.append(f"  evidence: {f.evidence}")
        lines.append(f"  action: {f.action}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    files = iter_source_files(root)
    findings: list[Finding] = []

    for file_path in files:
        rel = str(file_path.relative_to(root))
        lines = read_lines(file_path)
        findings.extend(find_large_file(rel, lines, args.large_file_lines))
        findings.extend(find_long_functions(rel, lines, args.long_function_lines))
        if len(findings) >= args.max_findings:
            break

    if len(findings) < args.max_findings:
        remaining = args.max_findings - len(findings)
        findings.extend(
            find_duplicate_blocks(
                root=root,
                files=files,
                window_lines=max(4, args.dup_window_lines),
                max_findings=remaining,
            )
        )

    findings = findings[: args.max_findings]
    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(render_text(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
