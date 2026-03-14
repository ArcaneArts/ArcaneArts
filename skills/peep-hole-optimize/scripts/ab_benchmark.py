#!/usr/bin/env python3
"""Run simple A/B command benchmarks with optional output equivalence checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunResult:
    duration_ns: int
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Stats:
    iterations: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare baseline vs candidate command runtime with repeated measurements."
    )
    parser.add_argument("--baseline-cmd", required=True, help="Baseline shell command.")
    parser.add_argument("--candidate-cmd", required=True, help="Candidate shell command.")
    parser.add_argument(
        "--workdir",
        default=".",
        help="Working directory for commands (default: current directory).",
    )
    parser.add_argument("--warmups", type=int, default=5, help="Warmup runs per command.")
    parser.add_argument(
        "--iterations", type=int, default=20, help="Measured runs per command."
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=120.0,
        help="Timeout per command run in seconds.",
    )
    parser.add_argument(
        "--skip-output-compare",
        action="store_true",
        help="Skip stdout equivalence checks.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path to write machine-readable results JSON.",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Optional path to write markdown report.",
    )
    return parser.parse_args()


def run_once(cmd: str, cwd: Path, timeout_sec: float) -> RunResult:
    start = time.perf_counter_ns()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    elapsed = time.perf_counter_ns() - start
    return RunResult(
        duration_ns=elapsed,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def ns_to_ms(value: int) -> float:
    return value / 1_000_000.0


def percentile_ms(samples_ns: list[int], percentile: float) -> float:
    if not samples_ns:
        return 0.0
    sorted_vals = sorted(samples_ns)
    idx = max(0, min(len(sorted_vals) - 1, math.ceil(percentile * len(sorted_vals)) - 1))
    return ns_to_ms(sorted_vals[idx])


def build_stats(samples_ns: list[int]) -> Stats:
    samples_ms = [ns_to_ms(v) for v in samples_ns]
    return Stats(
        iterations=len(samples_ns),
        mean_ms=statistics.fmean(samples_ms),
        median_ms=statistics.median(samples_ms),
        p95_ms=percentile_ms(samples_ns, 0.95),
        min_ms=min(samples_ms),
        max_ms=max(samples_ms),
        stdev_ms=statistics.pstdev(samples_ms) if len(samples_ms) > 1 else 0.0,
    )


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_series(
    name: str,
    cmd: str,
    cwd: Path,
    warmups: int,
    iterations: int,
    timeout_sec: float,
) -> tuple[list[RunResult], list[RunResult]]:
    warmup_results: list[RunResult] = []
    measured_results: list[RunResult] = []

    for _ in range(warmups):
        result = run_once(cmd, cwd=cwd, timeout_sec=timeout_sec)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"{name} warmup failed: {detail}")
        warmup_results.append(result)

    for i in range(iterations):
        result = run_once(cmd, cwd=cwd, timeout_sec=timeout_sec)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"{name} measured run {i + 1} failed: {detail}")
        measured_results.append(result)

    return warmup_results, measured_results


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_markdown(
    baseline_cmd: str,
    candidate_cmd: str,
    baseline_stats: Stats,
    candidate_stats: Stats,
    output_equivalent: bool | None,
    baseline_stable: bool,
    candidate_stable: bool,
    speedup: float,
    improvement_pct: float,
    verdict: str,
) -> str:
    eq_text = "skipped" if output_equivalent is None else ("yes" if output_equivalent else "no")
    return (
        "# A/B Benchmark Report\n\n"
        "## Commands\n\n"
        f"- Baseline: `{baseline_cmd}`\n"
        f"- Candidate: `{candidate_cmd}`\n\n"
        "## Results (ms)\n\n"
        "| Variant | mean | median | p95 | min | max | stdev |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
        f"| baseline | {baseline_stats.mean_ms:.3f} | {baseline_stats.median_ms:.3f} | {baseline_stats.p95_ms:.3f} | {baseline_stats.min_ms:.3f} | {baseline_stats.max_ms:.3f} | {baseline_stats.stdev_ms:.3f} |\n"
        f"| candidate | {candidate_stats.mean_ms:.3f} | {candidate_stats.median_ms:.3f} | {candidate_stats.p95_ms:.3f} | {candidate_stats.min_ms:.3f} | {candidate_stats.max_ms:.3f} | {candidate_stats.stdev_ms:.3f} |\n\n"
        "## Comparison\n\n"
        f"- Output equivalent: **{eq_text}**\n"
        f"- Baseline output stable: **{'yes' if baseline_stable else 'no'}**\n"
        f"- Candidate output stable: **{'yes' if candidate_stable else 'no'}**\n"
        f"- Median speedup (baseline/candidate): **{speedup:.3f}x**\n"
        f"- Median improvement: **{improvement_pct:.2f}%**\n"
        f"- Verdict: **{verdict}**\n"
    )


def main() -> int:
    args = parse_args()
    cwd = Path(args.workdir).resolve()
    if not cwd.exists():
        print(f"Working directory does not exist: {cwd}")
        return 1
    if args.iterations < 1:
        print("--iterations must be >= 1")
        return 1
    if args.warmups < 0:
        print("--warmups must be >= 0")
        return 1

    try:
        _, baseline_runs = run_series(
            name="baseline",
            cmd=args.baseline_cmd,
            cwd=cwd,
            warmups=args.warmups,
            iterations=args.iterations,
            timeout_sec=args.timeout_sec,
        )
        _, candidate_runs = run_series(
            name="candidate",
            cmd=args.candidate_cmd,
            cwd=cwd,
            warmups=args.warmups,
            iterations=args.iterations,
            timeout_sec=args.timeout_sec,
        )
    except RuntimeError as exc:
        print(f"Benchmark failed: {exc}")
        return 1
    except subprocess.TimeoutExpired as exc:
        print(f"Benchmark timeout: {exc}")
        return 1

    baseline_durations = [r.duration_ns for r in baseline_runs]
    candidate_durations = [r.duration_ns for r in candidate_runs]
    baseline_stats = build_stats(baseline_durations)
    candidate_stats = build_stats(candidate_durations)

    baseline_hashes = [stable_hash(r.stdout) for r in baseline_runs]
    candidate_hashes = [stable_hash(r.stdout) for r in candidate_runs]
    baseline_stable = len(set(baseline_hashes)) == 1
    candidate_stable = len(set(candidate_hashes)) == 1

    output_equivalent: bool | None = None
    if not args.skip_output_compare:
        output_equivalent = baseline_hashes[0] == candidate_hashes[0]

    speedup = baseline_stats.median_ms / candidate_stats.median_ms
    improvement_pct = (baseline_stats.median_ms - candidate_stats.median_ms) / baseline_stats.median_ms * 100.0

    verdict = "keep-candidate"
    if output_equivalent is False:
        verdict = "reject-candidate-output-mismatch"
    elif improvement_pct < 5.0:
        verdict = "inconclusive-small-gain"
    elif not baseline_stable or not candidate_stable:
        verdict = "inconclusive-unstable-output"

    payload = {
        "workdir": str(cwd),
        "baseline_cmd": args.baseline_cmd,
        "candidate_cmd": args.candidate_cmd,
        "warmups": args.warmups,
        "iterations": args.iterations,
        "timeout_sec": args.timeout_sec,
        "baseline_stats": asdict(baseline_stats),
        "candidate_stats": asdict(candidate_stats),
        "baseline_output_stable": baseline_stable,
        "candidate_output_stable": candidate_stable,
        "output_equivalent": output_equivalent,
        "speedup_median_x": speedup,
        "improvement_pct_median": improvement_pct,
        "verdict": verdict,
        "baseline_durations_ms": [ns_to_ms(v) for v in baseline_durations],
        "candidate_durations_ms": [ns_to_ms(v) for v in candidate_durations],
    }

    md = render_markdown(
        baseline_cmd=args.baseline_cmd,
        candidate_cmd=args.candidate_cmd,
        baseline_stats=baseline_stats,
        candidate_stats=candidate_stats,
        output_equivalent=output_equivalent,
        baseline_stable=baseline_stable,
        candidate_stable=candidate_stable,
        speedup=speedup,
        improvement_pct=improvement_pct,
        verdict=verdict,
    )

    print(md)

    if args.output_json:
        write_text(Path(args.output_json).resolve(), json.dumps(payload, indent=2) + "\n")
    if args.output_md:
        write_text(Path(args.output_md).resolve(), md + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
