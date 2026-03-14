#!/usr/bin/env python3
"""Inspect source for plausible edge-case hypotheses without modifying code."""

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


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    title: str
    regex: re.Pattern[str]
    extensions: set[str]
    confidence: str
    impact: str
    trigger_scenario: str
    outcome: str
    validation_idea: str


@dataclass(frozen=True)
class Hypothesis:
    path: str
    line: int
    rule_id: str
    category: str
    title: str
    confidence: str
    impact: str
    evidence: str
    trigger_scenario: str
    possible_outcome: str
    validation_idea: str


LINE_RULES = (
    Rule(
        rule_id="DIVIDE_BY_VARIABLE",
        category="ARITHMETIC_DOMAIN",
        title="Division by variable may hit zero divisor edge case",
        regex=re.compile(
            r"(?<!/)\b[A-Za-z_][A-Za-z0-9_.)\]]*\s*/\s*(?!\d+(?:\.\d+)?\b)([A-Za-z_][A-Za-z0-9_.]*)"
        ),
        extensions={"c", "cc", "cpp", "cs", "cxx", "dart", "go", "java", "js", "jsx", "kt", "php", "rs", "swift", "ts", "tsx"},
        confidence="medium",
        impact="high",
        trigger_scenario="Input or runtime state sets divisor to 0.",
        outcome="Runtime exception, NaN/Infinity propagation, or broken control flow.",
        validation_idea="Run scenario with zero divisor and verify explicit guard or error handling.",
    ),
    Rule(
        rule_id="MODULO_BY_VARIABLE",
        category="ARITHMETIC_DOMAIN",
        title="Modulo by variable may fail on zero",
        regex=re.compile(r"\b[A-Za-z_][A-Za-z0-9_.)\]]*\s*%\s*(?!\d+\b)([A-Za-z_][A-Za-z0-9_.]*)"),
        extensions={"c", "cc", "cpp", "cs", "cxx", "dart", "go", "java", "js", "jsx", "kt", "php", "rs", "swift", "ts", "tsx"},
        confidence="medium",
        impact="high",
        trigger_scenario="Modulo operand becomes zero due to configuration/input.",
        outcome="Crash or exception on modulus operation.",
        validation_idea="Exercise modulo path with zero input and confirm graceful handling.",
    ),
    Rule(
        rule_id="INDEX_PLUS_ONE",
        category="BOUNDARY_INDEX",
        title="Index expression with +1 may overrun collection boundary",
        regex=re.compile(r"\[[^\]\n]*\+\s*1[^\]\n]*\]"),
        extensions=SOURCE_EXTENSIONS,
        confidence="medium",
        impact="high",
        trigger_scenario="Current index points to last element while code accesses next index.",
        outcome="Out-of-range access or undefined behavior.",
        validation_idea="Run with single-element and last-index scenarios.",
    ),
    Rule(
        rule_id="INDEX_MINUS_ONE",
        category="BOUNDARY_INDEX",
        title="Index expression with -1 may underflow on first element",
        regex=re.compile(r"\[[^\]\n]*-\s*1[^\]\n]*\]"),
        extensions=SOURCE_EXTENSIONS,
        confidence="medium",
        impact="high",
        trigger_scenario="Loop or lookup executes when index is 0.",
        outcome="Negative index bug, panic, or wrong fallback element.",
        validation_idea="Execute first-element path and inspect bounds behavior.",
    ),
    Rule(
        rule_id="INCLUSIVE_LENGTH_BOUND",
        category="BOUNDARY_INDEX",
        title="Inclusive length/size bound can produce off-by-one iteration",
        regex=re.compile(
            r"(?:<=\s*[A-Za-z_][A-Za-z0-9_.]*(?:\.length\b|\.size\s*\(\s*\)|\.count\b)|"
            r"range\s*\(\s*len\s*\([^)]*\)\s*\+\s*1\s*\))"
        ),
        extensions=SOURCE_EXTENSIONS,
        confidence="high",
        impact="medium",
        trigger_scenario="Collection length is used as reachable index.",
        outcome="Loop runs one extra step and may access invalid element.",
        validation_idea="Test empty and exact-length boundary inputs.",
    ),
    Rule(
        rule_id="BROAD_CATCH_RETURN",
        category="ERROR_HANDLING",
        title="Broad exception handling may hide root failures",
        regex=re.compile(
            r"(?:except\s+Exception\s*:\s*(?:pass|return\b)|catch\s*\(\s*(?:Exception|Throwable|\.\.\.)[^)]*\)\s*\{)"
        ),
        extensions={"cs", "dart", "java", "js", "jsx", "kt", "php", "py", "ts", "tsx"},
        confidence="medium",
        impact="medium",
        trigger_scenario="Unexpected exception occurs and is swallowed or normalized.",
        outcome="Silent data loss, hard-to-debug behavior, or misleading success.",
        validation_idea="Inject failure in dependency call and confirm visibility/propagation.",
    ),
    Rule(
        rule_id="EMPTY_CATCH_BLOCK",
        category="ERROR_HANDLING",
        title="Empty catch block may suppress critical failures",
        regex=re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"),
        extensions={"cs", "dart", "java", "js", "jsx", "kt", "php", "ts", "tsx"},
        confidence="high",
        impact="medium",
        trigger_scenario="Exception path executes and control returns with no signal.",
        outcome="Failure masking and inconsistent downstream state.",
        validation_idea="Force exception in guarded section and check user-visible behavior.",
    ),
    Rule(
        rule_id="FORCE_UNWRAP",
        category="NULL_OR_MISSING",
        title="Force unwrap/non-null assertion may fail on missing data",
        regex=re.compile(r"(?:!!|[A-Za-z_][A-Za-z0-9_]*!\b)"),
        extensions={"dart", "kt", "swift"},
        confidence="medium",
        impact="high",
        trigger_scenario="Optional value becomes null during edge flow.",
        outcome="Immediate runtime crash due to assertion failure.",
        validation_idea="Run with intentionally missing/null value path.",
    ),
    Rule(
        rule_id="UNHANDLED_PARSE",
        category="ERROR_HANDLING",
        title="Parsing call may throw on malformed input",
        regex=re.compile(
            r"(?:\bint\.parse\(|\bdouble\.parse\(|\bInteger\.parseInt\(|\bDouble\.parseDouble\(|"
            r"\bstrconv\.(?:Atoi|ParseFloat|ParseInt)\(|\bstd::(?:stoi|stol|stoll|stof|stod|stold)\()"
        ),
        extensions={"c", "cc", "cpp", "dart", "go", "java", "kt"},
        confidence="low",
        impact="medium",
        trigger_scenario="Unexpected or malformed external input reaches parse call.",
        outcome="Unhandled parse exception and request/session failure.",
        validation_idea="Feed malformed input and confirm safe fallback/error response.",
    ),
    Rule(
        rule_id="RISK_TODO",
        category="CONFIG_AND_DEFAULTS",
        title="Risk-marked TODO/FIXME indicates known unhandled scenario",
        regex=re.compile(r"(TODO|FIXME|HACK).*(edge|null|error|race|overflow|bounds|later)", re.IGNORECASE),
        extensions=SOURCE_EXTENSIONS,
        confidence="low",
        impact="medium",
        trigger_scenario="Known deferred work intersects production flow.",
        outcome="Behavior gap under uncommon conditions.",
        validation_idea="Audit the noted path and run the deferred case explicitly.",
    ),
)

SWITCH_START_RE = re.compile(r"\bswitch\s*\(")
DEFAULT_CASE_RE = re.compile(r"\bdefault\s*:")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scout for plausible edge-case hypotheses from source patterns."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: current directory).")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "--max-hypotheses",
        type=int,
        default=400,
        help="Maximum hypotheses to emit (default: 400).",
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
    out = set()
    for part in value.split(","):
        ext = part.strip().lower().lstrip(".")
        if ext:
            out.add(ext)
    return out


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


STRING_RE = re.compile(r"('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")")


def strip_strings_and_comments(line: str, ext: str) -> str:
    # Remove quoted literals first so comment delimiters inside strings do not confuse parsing.
    cleaned = STRING_RE.sub('""', line)

    if ext in {"py", "rb"}:
        if "#" in cleaned:
            cleaned = cleaned.split("#", 1)[0]
    else:
        if "//" in cleaned:
            cleaned = cleaned.split("//", 1)[0]

    return cleaned


def make_hypothesis(
    rel_path: str,
    line_num: int,
    rule: Rule,
    snippet: str,
) -> Hypothesis:
    return Hypothesis(
        path=rel_path,
        line=line_num,
        rule_id=rule.rule_id,
        category=rule.category,
        title=rule.title,
        confidence=rule.confidence,
        impact=rule.impact,
        evidence=snippet.strip()[:240],
        trigger_scenario=rule.trigger_scenario,
        possible_outcome=rule.outcome,
        validation_idea=rule.validation_idea,
    )


def scan_line_rules(path: Path, rel_path: str, lines: list[str]) -> list[Hypothesis]:
    ext = path.suffix.lower().lstrip(".")
    hypotheses: list[Hypothesis] = []

    for line_num, raw in enumerate(lines, start=1):
        cleaned = strip_strings_and_comments(raw, ext).strip()
        if not cleaned:
            continue
        for rule in LINE_RULES:
            if ext not in rule.extensions:
                continue
            if not rule.regex.search(cleaned):
                continue
            hypotheses.append(make_hypothesis(rel_path, line_num, rule, raw))
    return hypotheses


def scan_switch_without_default(path: Path, rel_path: str, lines: list[str]) -> list[Hypothesis]:
    ext = path.suffix.lower().lstrip(".")
    if ext not in {"c", "cc", "cpp", "cs", "cxx", "dart", "go", "java", "js", "jsx", "kt", "php", "rs", "swift", "ts", "tsx"}:
        return []

    hypotheses: list[Hypothesis] = []
    for idx, raw in enumerate(lines):
        if not SWITCH_START_RE.search(raw):
            continue

        brace_depth = raw.count("{") - raw.count("}")
        has_opened = "{" in raw
        block_lines = [raw]
        j = idx + 1
        while j < len(lines):
            cur = lines[j]
            block_lines.append(cur)
            if "{" in cur:
                has_opened = True
            brace_depth += cur.count("{")
            brace_depth -= cur.count("}")
            if has_opened and brace_depth <= 0:
                break
            j += 1

        block_text = "\n".join(block_lines)
        if DEFAULT_CASE_RE.search(block_text):
            continue

        rule = Rule(
            rule_id="SWITCH_NO_DEFAULT",
            category="STATE_TRANSITION",
            title="Switch statement without default may miss unknown state/value",
            regex=re.compile(r"$^"),
            extensions=set(),
            confidence="medium",
            impact="medium",
            trigger_scenario="Unexpected enum/value is introduced or deserialized.",
            outcome="Unhandled state causes silent no-op, fallthrough bug, or incomplete behavior.",
            validation_idea="Inject unexpected value and verify explicit handling path.",
        )
        hypotheses.append(make_hypothesis(rel_path, idx + 1, rule, raw))
    return hypotheses


def dedupe_hypotheses(hypotheses: list[Hypothesis]) -> list[Hypothesis]:
    seen = set()
    deduped: list[Hypothesis] = []
    for item in hypotheses:
        key = (item.path, item.line, item.rule_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def rank_key(item: Hypothesis) -> tuple[int, int, str, int]:
    impact_order = {"high": 0, "medium": 1, "low": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    return (
        impact_order.get(item.impact, 3),
        confidence_order.get(item.confidence, 3),
        item.path,
        item.line,
    )


def render_text(hypotheses: list[Hypothesis]) -> str:
    if not hypotheses:
        return "No edge-case hypotheses found by heuristics."

    lines: list[str] = []
    for h in hypotheses:
        lines.append(f"{h.path}:{h.line}: [hypothesis] {h.title}")
        lines.append(f"  category: {h.category}; confidence: {h.confidence}; impact: {h.impact}")
        lines.append(f"  evidence: {h.evidence}")
        lines.append(f"  trigger: {h.trigger_scenario}")
        lines.append(f"  outcome: {h.possible_outcome}")
        lines.append(f"  validate: {h.validation_idea}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    extensions = normalize_extensions(args.include_ext)
    ignore_dirs = build_ignore_dirs(args.ignore_dir)

    hypotheses: list[Hypothesis] = []
    files = iter_source_files(root, extensions, ignore_dirs)
    for path in files:
        if len(hypotheses) >= args.max_hypotheses:
            break
        rel_path = str(path.relative_to(root))
        lines = read_lines(path)
        if not lines:
            continue

        batch: list[Hypothesis] = []
        batch.extend(scan_line_rules(path, rel_path, lines))
        batch.extend(scan_switch_without_default(path, rel_path, lines))
        batch = dedupe_hypotheses(batch)

        remaining = max(args.max_hypotheses - len(hypotheses), 0)
        hypotheses.extend(batch[:remaining])

    hypotheses = dedupe_hypotheses(hypotheses)
    hypotheses.sort(key=rank_key)

    if args.format == "json":
        print(json.dumps([asdict(h) for h in hypotheses], indent=2))
    else:
        print(render_text(hypotheses))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
