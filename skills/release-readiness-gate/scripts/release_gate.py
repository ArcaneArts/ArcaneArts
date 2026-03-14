#!/usr/bin/env python3
"""Manage release readiness gate sessions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

VALID_STATUS = {"pass", "warn", "fail", "skip", "pending"}
REQUIRED_DEFAULTS = [
    "unit-tests",
    "qa-validation",
    "edge-case-review",
    "perf-regression",
    "release-dry-run",
    "changelog-ready",
]
OPTIONAL_DEFAULTS = [
    "manual-smoke",
    "docs-updated",
    "known-issues-reviewed",
]


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        slug = "release"
    return slug[:max_len].rstrip("-")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_gate(gate_dir: Path) -> dict[str, Any]:
    gate_json = gate_dir / "GATE.json"
    if not gate_json.exists():
        raise RuntimeError(f"Missing gate file: {gate_json}")
    return json.loads(gate_json.read_text(encoding="utf-8"))


def save_gate(gate_dir: Path, payload: dict[str, Any]) -> None:
    write_text(gate_dir / "GATE.json", json.dumps(payload, indent=2) + "\n")


def init_gate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    session = args.session
    if not session:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        version_text = slugify(args.version or "unversioned")
        session = f"{stamp}-{version_text}"

    gate_dir = root / ".release-gate" / session
    if gate_dir.exists():
        print(f"Gate already exists: {gate_dir}")
        return 1
    gate_dir.mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, Any]] = []
    for name in REQUIRED_DEFAULTS:
        checks.append({"name": name, "required": True, "status": "pending", "evidence": "", "notes": ""})
    for name in OPTIONAL_DEFAULTS:
        checks.append({"name": name, "required": False, "status": "pending", "evidence": "", "notes": ""})

    payload = {
        "created_at_utc": now_utc(),
        "session": session,
        "version": args.version or "",
        "root": str(root),
        "checks": checks,
    }
    save_gate(gate_dir, payload)

    checklist = (
        "# Release Checklist\n\n"
        "Update statuses using release_gate.py record.\n\n"
        "## Required\n\n"
        + "\n".join(f"- [ ] {c}" for c in REQUIRED_DEFAULTS)
        + "\n\n## Optional\n\n"
        + "\n".join(f"- [ ] {c}" for c in OPTIONAL_DEFAULTS)
        + "\n"
    )
    write_text(gate_dir / "CHECKLIST.md", checklist)
    write_text(gate_dir / "EVIDENCE.md", "# Release Evidence\n\n")
    write_text(gate_dir / "SUMMARY.md", "# Release Decision\n\n- Status: pending\n")

    print(f"Initialized release gate: {gate_dir}")
    return 0


def record_check(args: argparse.Namespace) -> int:
    gate_dir = Path(args.gate).resolve()
    if not gate_dir.exists():
        print(f"Gate path does not exist: {gate_dir}")
        return 1
    if args.status not in VALID_STATUS:
        print(f"Invalid status '{args.status}', choose from {sorted(VALID_STATUS)}")
        return 1

    payload = load_gate(gate_dir)
    checks = payload.get("checks", [])
    target = None
    for check in checks:
        if check.get("name") == args.check:
            target = check
            break
    if target is None:
        print(f"Unknown check '{args.check}'")
        return 1

    target["status"] = args.status
    target["evidence"] = args.evidence
    target["notes"] = args.notes
    target["updated_at_utc"] = now_utc()
    save_gate(gate_dir, payload)
    print(f"Recorded check {args.check}={args.status}")
    return 0


def summarize_gate(args: argparse.Namespace) -> int:
    gate_dir = Path(args.gate).resolve()
    if not gate_dir.exists():
        print(f"Gate path does not exist: {gate_dir}")
        return 1

    payload = load_gate(gate_dir)
    checks = payload.get("checks", [])

    required = [c for c in checks if c.get("required")]
    warns = [c for c in checks if c.get("status") == "warn"]
    req_fail = [c for c in required if c.get("status") == "fail"]
    req_pending = [c for c in required if c.get("status") == "pending"]

    if req_fail or req_pending:
        verdict = "NO-GO"
    elif warns:
        verdict = "GO-WARN"
    else:
        verdict = "GO"

    summary = [
        "# Release Decision",
        "",
        f"- Status: {verdict}",
        f"- Version: {payload.get('version', '') or '(unspecified)'}",
        "",
        "## Check Status",
        "",
    ]
    for check in checks:
        tag = "required" if check.get("required") else "optional"
        summary.append(
            f"- {check.get('name')}: {check.get('status')} ({tag})"
            + (f" - evidence: {check.get('evidence')}" if check.get("evidence") else "")
        )

    summary_text = "\n".join(summary) + "\n"
    write_text(gate_dir / "SUMMARY.md", summary_text)
    print(summary_text)
    return 0 if verdict != "NO-GO" else 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage release readiness gates.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize a new release gate.")
    p_init.add_argument("--root", default=".", help="Repository root.")
    p_init.add_argument("--version", default="", help="Release version label.")
    p_init.add_argument("--session", default="", help="Optional session name.")

    p_rec = sub.add_parser("record", help="Record status for one check.")
    p_rec.add_argument("--gate", required=True, help="Gate session path.")
    p_rec.add_argument("--check", required=True, help="Check name.")
    p_rec.add_argument("--status", required=True, help="Status value.")
    p_rec.add_argument("--evidence", default="", help="Evidence text.")
    p_rec.add_argument("--notes", default="", help="Optional notes.")

    p_sum = sub.add_parser("summarize", help="Summarize gate decision.")
    p_sum.add_argument("--gate", required=True, help="Gate session path.")

    return p


def main() -> int:
    args = parser().parse_args()
    if args.cmd == "init":
        return init_gate(args)
    if args.cmd == "record":
        return record_check(args)
    if args.cmd == "summarize":
        return summarize_gate(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
