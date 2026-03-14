#!/usr/bin/env python3
"""Create and track bug reproduction sessions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


VALID_STATUSES = {"reproduced", "intermittent", "not-reproduced"}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        slug = "issue"
    return slug[:max_len].rstrip("-")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_session(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    session = args.session
    if not session:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        session = f"{stamp}-{slugify(args.issue)}"

    session_dir = root / ".repro" / session
    if session_dir.exists():
        print(f"Session already exists: {session_dir}")
        return 1

    (session_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (session_dir / "logs").mkdir(parents=True, exist_ok=True)

    meta = {
        "created_at_utc": now_utc(),
        "session": session,
        "root": str(root),
        "issue": args.issue,
        "status": "open",
    }
    write_text(session_dir / "SESSION.json", json.dumps(meta, indent=2) + "\n")
    write_text(
        session_dir / "REPRO_STEPS.md",
        "# Reproduction Steps\n\n1. Setup:\n2. Action:\n3. Observe:\n",
    )
    write_text(
        session_dir / "OBSERVED.md",
        "# Observed Behavior\n\n- Actual output:\n- Error details:\n",
    )
    write_text(
        session_dir / "EXPECTED.md",
        "# Expected Behavior\n\n- Expected output:\n- Expected side effects:\n",
    )
    write_text(session_dir / "RUNS.jsonl", "")
    write_text(
        session_dir / "SUMMARY.md",
        "# Repro Summary\n\n- Stable: no\n- Reproduced runs: 0\n- Intermittent runs: 0\n- Not reproduced runs: 0\n",
    )

    print(f"Initialized reproduction session: {session_dir}")
    return 0


def load_session(session_dir: Path) -> dict[str, Any]:
    meta_path = session_dir / "SESSION.json"
    if not meta_path.exists():
        raise RuntimeError(f"Missing SESSION.json in {session_dir}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def copy_log_if_needed(log_file: Path, dest_dir: Path) -> str:
    if not log_file.exists():
        return ""
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = dest_dir / f"{stamp}-{log_file.name}"
    target.write_text(log_file.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return str(target)


def record_run(args: argparse.Namespace) -> int:
    session_dir = Path(args.session).resolve()
    if not session_dir.exists():
        print(f"Session path does not exist: {session_dir}")
        return 1
    if args.status not in VALID_STATUSES:
        print(f"Invalid status '{args.status}'. Choose from: {sorted(VALID_STATUSES)}")
        return 1

    _ = load_session(session_dir)

    log_path = ""
    if args.log_file:
        log_path = copy_log_if_needed(Path(args.log_file).resolve(), session_dir / "logs")

    record = {
        "recorded_at_utc": now_utc(),
        "status": args.status,
        "notes": args.notes,
        "log_path": log_path,
    }
    runs_path = session_dir / "RUNS.jsonl"
    with runs_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")

    print(f"Recorded run in {runs_path}")
    return 0


def summarize(args: argparse.Namespace) -> int:
    session_dir = Path(args.session).resolve()
    if not session_dir.exists():
        print(f"Session path does not exist: {session_dir}")
        return 1

    runs_path = session_dir / "RUNS.jsonl"
    if not runs_path.exists():
        print(f"No runs file found: {runs_path}")
        return 1

    rows: list[dict[str, Any]] = []
    for line in runs_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    counts = {k: 0 for k in VALID_STATUSES}
    for row in rows:
        status = str(row.get("status", "")).strip()
        if status in counts:
            counts[status] += 1

    total = sum(counts.values())
    reproducible_ratio = (counts["reproduced"] / total) if total else 0.0
    stable = reproducible_ratio >= 0.8 and counts["reproduced"] >= 3

    summary = (
        "# Repro Summary\n\n"
        f"- Total runs: {total}\n"
        f"- Reproduced runs: {counts['reproduced']}\n"
        f"- Intermittent runs: {counts['intermittent']}\n"
        f"- Not reproduced runs: {counts['not-reproduced']}\n"
        f"- Reproduced ratio: {reproducible_ratio:.2f}\n"
        f"- Stable: {'yes' if stable else 'no'}\n"
    )
    write_text(session_dir / "SUMMARY.md", summary)
    print(f"Wrote summary: {session_dir / 'SUMMARY.md'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage bug reproduction sessions.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize reproduction session.")
    p_init.add_argument("--root", default=".", help="Repository root.")
    p_init.add_argument("--issue", required=True, help="Short bug statement.")
    p_init.add_argument("--session", default="", help="Optional session name.")

    p_record = sub.add_parser("record", help="Record one reproduction attempt.")
    p_record.add_argument("--session", required=True, help="Session directory path.")
    p_record.add_argument("--status", required=True, help="Run status.")
    p_record.add_argument("--notes", default="", help="Optional run notes.")
    p_record.add_argument("--log-file", default="", help="Optional log file path.")

    p_summary = sub.add_parser("summarize", help="Summarize reproduction stability.")
    p_summary.add_argument("--session", required=True, help="Session directory path.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "init":
        return init_session(args)
    if args.cmd == "record":
        return record_run(args)
    if args.cmd == "summarize":
        return summarize(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
