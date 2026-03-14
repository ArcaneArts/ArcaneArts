#!/usr/bin/env python3
"""Capture and compare benchmark artifacts for performance regression guarding."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Run:
    duration_ns: int
    returncode: int
    stdout_hash: str
    stderr_hash: str


@dataclass(frozen=True)
class Stats:
    iterations: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def ns_to_ms(value: int) -> float:
    return value / 1_000_000.0


def pctl(samples: list[int], percentile: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ns_to_ms(ordered[idx])


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_stats(samples: list[int]) -> Stats:
    ms = [ns_to_ms(v) for v in samples]
    return Stats(
        iterations=len(samples),
        mean_ms=statistics.fmean(ms),
        median_ms=statistics.median(ms),
        p95_ms=pctl(samples, 0.95),
        min_ms=min(ms),
        max_ms=max(ms),
        stdev_ms=statistics.pstdev(ms) if len(ms) > 1 else 0.0,
    )


def run_cmd(cmd: str, cwd: Path, timeout: float) -> Run:
    start = time.perf_counter_ns()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter_ns() - start
    return Run(
        duration_ns=elapsed,
        returncode=proc.returncode,
        stdout_hash=hash_text(proc.stdout or ""),
        stderr_hash=hash_text(proc.stderr or ""),
    )


def capture(args: argparse.Namespace) -> int:
    cwd = Path(args.workdir).resolve()
    if not cwd.exists():
        print(f"Workdir does not exist: {cwd}")
        return 1
    if args.iterations < 1:
        print("--iterations must be >= 1")
        return 1

    warmup_runs: list[Run] = []
    measured_runs: list[Run] = []
    try:
        for _ in range(args.warmups):
            run = run_cmd(args.bench_cmd, cwd=cwd, timeout=args.timeout_sec)
            if run.returncode != 0:
                print("Warmup command failed.")
                return 1
            warmup_runs.append(run)
        for _ in range(args.iterations):
            run = run_cmd(args.bench_cmd, cwd=cwd, timeout=args.timeout_sec)
            if run.returncode != 0:
                print("Measured command failed.")
                return 1
            measured_runs.append(run)
    except subprocess.TimeoutExpired as exc:
        print(f"Command timed out: {exc}")
        return 1

    stats = build_stats([r.duration_ns for r in measured_runs])
    stable_out = len({r.stdout_hash for r in measured_runs}) == 1

    payload: dict[str, Any] = {
        "captured_at_utc": now_utc(),
        "label": args.label,
        "cmd": args.bench_cmd,
        "workdir": str(cwd),
        "warmups": args.warmups,
        "iterations": args.iterations,
        "timeout_sec": args.timeout_sec,
        "stats": asdict(stats),
        "stdout_stable": stable_out,
        "durations_ms": [ns_to_ms(r.duration_ns) for r in measured_runs],
    }

    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote benchmark artifact: {out}")
    return 0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline).resolve()
    candidate_path = Path(args.candidate).resolve()
    if not baseline_path.exists() or not candidate_path.exists():
        print("Missing baseline or candidate artifact.")
        return 1

    base = load_json(baseline_path)
    cand = load_json(candidate_path)
    b_median = float(base["stats"]["median_ms"])
    c_median = float(cand["stats"]["median_ms"])
    b_p95 = float(base["stats"]["p95_ms"])
    c_p95 = float(cand["stats"]["p95_ms"])

    median_delta_pct = ((c_median - b_median) / b_median) * 100.0
    p95_delta_pct = ((c_p95 - b_p95) / b_p95) * 100.0
    threshold = float(args.threshold_pct)
    warn = float(args.warn_pct)

    if median_delta_pct > threshold:
        verdict = "fail"
        exit_code = 2
    elif median_delta_pct > warn:
        verdict = "warn"
        exit_code = 0
    else:
        verdict = "pass"
        exit_code = 0

    if not bool(cand.get("stdout_stable", True)):
        verdict = "fail"
        exit_code = 2

    report = (
        "# Perf Regression Comparison\n\n"
        f"- Baseline: {baseline_path}\n"
        f"- Candidate: {candidate_path}\n"
        f"- Baseline median (ms): {b_median:.3f}\n"
        f"- Candidate median (ms): {c_median:.3f}\n"
        f"- Median delta (%): {median_delta_pct:.2f}\n"
        f"- Baseline p95 (ms): {b_p95:.3f}\n"
        f"- Candidate p95 (ms): {c_p95:.3f}\n"
        f"- P95 delta (%): {p95_delta_pct:.2f}\n"
        f"- Threshold (%): {threshold:.2f}\n"
        f"- Warn (%): {warn:.2f}\n"
        f"- Verdict: {verdict}\n"
    )
    print(report)

    if args.output_md:
        out = Path(args.output_md).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")

    return exit_code


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Capture and compare perf benchmark artifacts.")
    sub = p.add_subparsers(dest="action", required=True)

    cap = sub.add_parser("capture", help="Capture one benchmark artifact.")
    cap.add_argument("--bench-cmd", required=True, help="Benchmark command.")
    cap.add_argument("--label", default="run", help="Artifact label.")
    cap.add_argument("--output", required=True, help="Output JSON path.")
    cap.add_argument("--workdir", default=".", help="Working directory.")
    cap.add_argument("--warmups", type=int, default=5, help="Warmup runs.")
    cap.add_argument("--iterations", type=int, default=20, help="Measured runs.")
    cap.add_argument("--timeout-sec", type=float, default=120.0, help="Per-run timeout seconds.")

    cmp = sub.add_parser("compare", help="Compare baseline and candidate artifacts.")
    cmp.add_argument("--baseline", required=True, help="Baseline JSON path.")
    cmp.add_argument("--candidate", required=True, help="Candidate JSON path.")
    cmp.add_argument("--threshold-pct", type=float, default=5.0, help="Fail threshold.")
    cmp.add_argument("--warn-pct", type=float, default=2.0, help="Warn threshold.")
    cmp.add_argument("--output-md", default="", help="Optional markdown report output path.")

    return p


def main() -> int:
    args = parser().parse_args()
    if args.action == "capture":
        return capture(args)
    if args.action == "compare":
        return compare(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
