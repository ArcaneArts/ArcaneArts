#!/usr/bin/env python3
"""Inspect source for plausible high-impact optimization opportunities."""

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
PY_LOOP_RE = re.compile(r"^\s*(for|while)\b")
CSTYLE_LOOP_RE = re.compile(r"\b(for|while)\s*\(")


@dataclass(frozen=True)
class LoopRule:
    rule_id: str
    title: str
    category: str
    regex: re.Pattern[str]
    extensions: set[str]
    expected_gain: str
    risk: str
    complexity: str
    confidence: str
    hypothesis: str
    validation_plan: str


@dataclass(frozen=True)
class Opportunity:
    path: str
    line: int
    opportunity_id: str
    title: str
    category: str
    expected_gain: str
    risk: str
    complexity: str
    confidence: str
    evidence: str
    hypothesis: str
    validation_plan: str


LOOP_RULES = (
    LoopRule(
        rule_id="SORT_INSIDE_LOOP",
        title="Sorting inside loop may amplify time complexity",
        category="ALGORITHM_COMPLEXITY",
        regex=re.compile(r"(?:\.sort\s*\(|\bsorted\s*\(|Collections\.sort\s*\()"),
        extensions=SOURCE_EXTENSIONS,
        expected_gain="high",
        risk="medium",
        complexity="medium",
        confidence="medium",
        hypothesis="Repeated sort work may dominate runtime in larger inputs.",
        validation_plan="Profile representative workload and compare with pre-sort, caching, or batched sort strategy.",
    ),
    LoopRule(
        rule_id="SYNC_IO_INSIDE_LOOP",
        title="Blocking I/O inside loop may throttle throughput",
        category="SYNC_IO_HOT_PATH",
        regex=re.compile(
            r"(?:readFileSync|writeFileSync|fs\.readFileSync|Files\.readAll|FileInputStream|"
            r"FileOutputStream|readAsStringSync|open\s*\(|requests\.)"
        ),
        extensions={"cs", "dart", "go", "java", "js", "jsx", "kt", "php", "py", "rb", "ts", "tsx"},
        expected_gain="high",
        risk="high",
        complexity="high",
        confidence="low",
        hypothesis="Synchronous I/O in iterative path can serialize work and increase latency.",
        validation_plan="Capture per-iteration I/O timing and compare with batching, caching, or async strategy.",
    ),
    LoopRule(
        rule_id="ALLOCATION_INSIDE_LOOP",
        title="Frequent allocations inside loop may increase GC pressure",
        category="HOT_PATH_ALLOCATION",
        regex=re.compile(
            r"(?:\bnew\s+[A-Za-z_][A-Za-z0-9_]*\s*\(|"
            r"\bArrayList\s*\(|\bHashMap\s*\(|\blist\s*\(|\bdict\s*\()"
        ),
        extensions=SOURCE_EXTENSIONS,
        expected_gain="medium",
        risk="medium",
        complexity="medium",
        confidence="low",
        hypothesis="Hot-path object creation may cause avoidable allocation churn and GC pauses.",
        validation_plan="Use allocation profiler to compare object counts before/after pooling or reuse.",
    ),
    LoopRule(
        rule_id="REGEX_COMPILE_INSIDE_LOOP",
        title="Regex compile in loop may repeat expensive setup work",
        category="REGEX_OR_PARSING_HOT_PATH",
        regex=re.compile(r"(?:re\.compile\(|Pattern\.compile\(|RegExp\(|new\s+Regex\s*\()"),
        extensions={"cs", "dart", "java", "js", "jsx", "kt", "py", "ts", "tsx"},
        expected_gain="medium",
        risk="low",
        complexity="low",
        confidence="high",
        hypothesis="Repeated regex compilation may be avoidable with a cached or static compiled pattern.",
        validation_plan="Benchmark repeated calls with compile-per-iteration vs precompiled pattern.",
    ),
    LoopRule(
        rule_id="QUERY_INSIDE_LOOP",
        title="Possible N+1 query/call pattern inside loop",
        category="N_PLUS_ONE_OR_CHATTER",
        regex=re.compile(
            r"(?:executeQuery|query\s*\(|findBy|findOne|findAll|select\s+.*\s+from|db\.[A-Za-z_])",
            re.IGNORECASE,
        ),
        extensions={"cs", "dart", "go", "java", "js", "jsx", "kt", "php", "py", "rb", "ts", "tsx"},
        expected_gain="high",
        risk="high",
        complexity="high",
        confidence="low",
        hypothesis="Per-item query/call sequence may create N+1 behavior and high latency at scale.",
        validation_plan="Trace query count per request/work unit and evaluate batching or prefetch alternatives.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scout for potential high-impact performance optimization opportunities."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: current directory).")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "--max-opportunities",
        type=int,
        default=400,
        help="Maximum opportunities to emit (default: 400).",
    )
    parser.add_argument(
        "--loop-window",
        type=int,
        default=24,
        help="Lines to inspect after loop start (default: 24).",
    )
    parser.add_argument(
        "--include-ext",
        default="",
        help="Optional comma-separated extension allowlist (without dots).",
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
        return set(SOURCE_EXTENSIONS)
    selected: set[str] = set()
    for part in value.split(","):
        ext = part.strip().lower().lstrip(".")
        if ext:
            selected.add(ext)
    return selected


def build_ignore_dirs(extra: list[str]) -> set[str]:
    combined = set(IGNORE_DIRS)
    combined.update(name for name in extra if name)
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


def strip_strings_and_comments(line: str, ext: str) -> str:
    cleaned = STRING_RE.sub('""', line)
    if ext in {"py", "rb"}:
        if "#" in cleaned:
            cleaned = cleaned.split("#", 1)[0]
    else:
        if "//" in cleaned:
            cleaned = cleaned.split("//", 1)[0]
    return cleaned


def is_loop_start(cleaned_line: str, ext: str) -> bool:
    if ext in {"py", "rb"}:
        return bool(PY_LOOP_RE.search(cleaned_line))
    return bool(CSTYLE_LOOP_RE.search(cleaned_line))


def make_opportunity(
    rel_path: str,
    line_num: int,
    rule_id: str,
    title: str,
    category: str,
    expected_gain: str,
    risk: str,
    complexity: str,
    confidence: str,
    evidence: str,
    hypothesis: str,
    validation_plan: str,
) -> Opportunity:
    return Opportunity(
        path=rel_path,
        line=line_num,
        opportunity_id=rule_id,
        title=title,
        category=category,
        expected_gain=expected_gain,
        risk=risk,
        complexity=complexity,
        confidence=confidence,
        evidence=evidence.strip()[:260],
        hypothesis=hypothesis,
        validation_plan=validation_plan,
    )


def scan_file(path: Path, root: Path, loop_window: int) -> list[Opportunity]:
    rel_path = str(path.relative_to(root))
    ext = path.suffix.lower().lstrip(".")
    raw_lines = read_lines(path)
    if not raw_lines:
        return []

    cleaned_lines = [strip_strings_and_comments(line, ext) for line in raw_lines]
    opportunities: list[Opportunity] = []

    for idx, cleaned in enumerate(cleaned_lines):
        if not is_loop_start(cleaned, ext):
            continue

        # Nested loops are often a high-leverage optimization opportunity.
        for inner in range(idx + 1, min(len(cleaned_lines), idx + 1 + loop_window)):
            if is_loop_start(cleaned_lines[inner], ext):
                opportunities.append(
                    make_opportunity(
                        rel_path=rel_path,
                        line_num=idx + 1,
                        rule_id="NESTED_LOOP_HOT_PATH",
                        title="Nested loops may produce superlinear behavior",
                        category="ALGORITHM_COMPLEXITY",
                        expected_gain="high",
                        risk="high",
                        complexity="high",
                        confidence="medium",
                        evidence=raw_lines[idx],
                        hypothesis=(
                            "Nested iteration in this region may become a performance bottleneck "
                            "for larger input sizes."
                        ),
                        validation_plan=(
                            "Collect runtime vs input-size curve and profile hotspots; "
                            "evaluate indexing, caching, or algorithmic rewrite options."
                        ),
                    )
                )
                break

        for j in range(idx + 1, min(len(cleaned_lines), idx + 1 + loop_window)):
            probe = cleaned_lines[j]
            if not probe.strip():
                continue
            for rule in LOOP_RULES:
                if ext not in rule.extensions:
                    continue
                if not rule.regex.search(probe):
                    continue
                opportunities.append(
                    make_opportunity(
                        rel_path=rel_path,
                        line_num=j + 1,
                        rule_id=rule.rule_id,
                        title=rule.title,
                        category=rule.category,
                        expected_gain=rule.expected_gain,
                        risk=rule.risk,
                        complexity=rule.complexity,
                        confidence=rule.confidence,
                        evidence=raw_lines[j],
                        hypothesis=rule.hypothesis,
                        validation_plan=rule.validation_plan,
                    )
                )

    return opportunities


def dedupe(items: list[Opportunity]) -> list[Opportunity]:
    seen = set()
    output: list[Opportunity] = []
    for item in items:
        key = (item.path, item.line, item.opportunity_id)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def rank_key(item: Opportunity) -> tuple[int, int, int, str, int]:
    gain_order = {"high": 0, "medium": 1, "low": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    risk_order = {"low": 0, "medium": 1, "high": 2}
    return (
        gain_order.get(item.expected_gain, 3),
        confidence_order.get(item.confidence, 3),
        risk_order.get(item.risk, 3),
        item.path,
        item.line,
    )


def render_text(items: list[Opportunity]) -> str:
    if not items:
        return "No optimization opportunities found by current heuristics."

    lines: list[str] = []
    for item in items:
        lines.append(f"{item.path}:{item.line}: [opportunity] {item.title}")
        lines.append(
            f"  category: {item.category}; expected_gain: {item.expected_gain}; "
            f"risk: {item.risk}; complexity: {item.complexity}; confidence: {item.confidence}"
        )
        lines.append(f"  evidence: {item.evidence}")
        lines.append(f"  hypothesis: {item.hypothesis}")
        lines.append(f"  validate: {item.validation_plan}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    extensions = normalize_extensions(args.include_ext)
    ignore_dirs = build_ignore_dirs(args.ignore_dir)

    all_items: list[Opportunity] = []
    for path in iter_source_files(root, extensions, ignore_dirs):
        if len(all_items) >= args.max_opportunities:
            break
        scanned = scan_file(path, root=root, loop_window=max(4, args.loop_window))
        remaining = max(args.max_opportunities - len(all_items), 0)
        all_items.extend(scanned[:remaining])

    all_items = dedupe(all_items)
    all_items.sort(key=rank_key)

    if args.format == "json":
        print(json.dumps([asdict(item) for item in all_items], indent=2))
    else:
        print(render_text(all_items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
