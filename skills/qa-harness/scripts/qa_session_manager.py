#!/usr/bin/env python3
"""Create and manage QA harness sessions for manual + log-assisted validation."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def slugify(value: str, max_len: int = 32) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        slug = "qa-session"
    return slug[:max_len].rstrip("-")


def detect_framework(root: Path) -> str:
    pubspec = root / "pubspec.yaml"
    if pubspec.exists():
        return "dart-package"

    mods_toml = root / "src" / "main" / "resources" / "META-INF" / "mods.toml"
    if mods_toml.exists():
        return "minecraft-mod"

    if (root / "package.json").exists():
        return "node-lib"

    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "python-lib"

    if (root / "pom.xml").exists() or (root / "build.gradle").exists():
        return "java-lib"

    return "generic"


def framework_setup_hint(framework: str) -> str:
    if framework == "dart-package":
        return (
            "1. flutter create harness_app\n"
            "2. Add parent package as path dependency in harness_app/pubspec.yaml\n"
            "3. Build minimal UI for each scenario and emit QA_EVT logs\n"
            "4. Run: flutter run"
        )
    if framework == "minecraft-mod":
        return (
            "1. Add temporary instrumentation around target mechanic\n"
            "2. Emit QA_EVT logs for key transitions and values\n"
            "3. Run existing dev-client task for the mod\n"
            "4. Execute in-game checklist scenarios"
        )
    if framework == "node-lib":
        return (
            "1. Create harness app under harness_app (console or tiny UI)\n"
            "2. Link local package/module from repository root\n"
            "3. Emit QA_EVT logs for each scenario\n"
            "4. Run harness command and capture logs"
        )
    if framework == "python-lib":
        return (
            "1. Create harness script/app under harness_app\n"
            "2. Import local package from repository root\n"
            "3. Emit QA_EVT logs for checkpoints\n"
            "4. Run harness and capture output logs"
        )
    if framework == "java-lib":
        return (
            "1. Create small runner app/module under harness_app\n"
            "2. Depend on local module artifacts\n"
            "3. Emit QA_EVT logs at checkpoints\n"
            "4. Run harness and capture logs"
        )
    return (
        "1. Create minimal harness under harness_app\n"
        "2. Call target APIs with deterministic scenarios\n"
        "3. Emit QA_EVT logs for pass/fail checkpoints\n"
        "4. Run harness and capture logs"
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_session(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 1

    framework = args.framework
    if framework == "auto":
        framework = detect_framework(root)

    session_name = args.session
    if not session_name:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        session_name = f"{stamp}-{slugify(args.goal)}"

    session_dir = root / ".qa" / session_name
    if session_dir.exists():
        print(f"Session already exists: {session_dir}")
        return 1

    harness_dir = session_dir / "harness_app"
    logs_dir = session_dir / "logs"
    artifacts_dir = session_dir / "artifacts"

    harness_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    session_json = {
        "created_at_utc": utc_now(),
        "root": str(root),
        "session": session_name,
        "goal": args.goal,
        "framework": framework,
        "harness_dir": str(harness_dir),
        "log_prefix": "QA_EVT",
    }

    instructions = (
        f"# QA Session: {session_name}\n\n"
        f"Goal: {args.goal}\n\n"
        "## Harness Setup\n\n"
        f"{framework_setup_hint(framework)}\n\n"
        "## Test Checklist\n\n"
        "1. Setup scenario\n"
        "2. Run normal/happy path\n"
        "3. Run boundary/edge path\n"
        "4. Run failure/error path\n\n"
        "## Expected Logging\n\n"
        "Emit structured logs with prefix `QA_EVT`, for example:\n\n"
        'QA_EVT {"event":"button_click","status":"pass","details":"Action succeeded"}\n\n'
        "## Return Artifacts\n\n"
        f"- Log file(s): {logs_dir}\n"
        f"- Screenshots/videos (if visual): {artifacts_dir}\n"
        "- Notes in OBSERVATIONS.md\n"
    )

    observations = (
        "# Observations\n\n"
        "- What was tested:\n"
        "- What looked correct:\n"
        "- What failed or looked wrong:\n"
        "- Open questions:\n"
    )

    summary = (
        "# QA Summary\n\n"
        f"Session: {session_name}\n\n"
        "- Status: pending\n"
        "- Pass events: 0\n"
        "- Fail events: 0\n"
        "- Info events: 0\n"
        "- Warn events: 0\n"
    )

    write_text(session_dir / "SESSION.json", json.dumps(session_json, indent=2) + "\n")
    write_text(session_dir / "TEST_INSTRUCTIONS.md", instructions)
    write_text(session_dir / "OBSERVATIONS.md", observations)
    write_text(session_dir / "SUMMARY.md", summary)
    write_text(session_dir / "qa_events.jsonl", "")
    write_text(harness_dir / ".gitkeep", "")
    write_text(logs_dir / ".gitkeep", "")
    write_text(artifacts_dir / ".gitkeep", "")

    print(f"Initialized QA session: {session_dir}")
    print(f"Detected framework: {framework}")
    return 0


def parse_event_payload(payload: str) -> dict[str, Any]:
    payload = payload.strip()
    if not payload:
        return {"event": "empty", "status": "info", "details": ""}
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
        return {"event": "non_object", "status": "info", "details": str(data)}
    except json.JSONDecodeError:
        return {"event": "raw_line", "status": "info", "details": payload}


def collect_events(args: argparse.Namespace) -> int:
    session_dir = Path(args.session).resolve()
    events_path = session_dir / "qa_events.jsonl"
    if not session_dir.exists():
        print(f"Session path does not exist: {session_dir}")
        return 1

    if not events_path.exists():
        write_text(events_path, "")

    prefix = args.prefix
    collected = 0
    out_lines: list[str] = []

    for log_file_value in args.log_file:
        log_file = Path(log_file_value).resolve()
        if not log_file.exists():
            print(f"Log file not found (skipping): {log_file}")
            continue

        for raw in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if prefix not in raw:
                continue
            payload = raw.split(prefix, 1)[1].strip()
            event = parse_event_payload(payload)
            wrapped = {
                "ingested_at_utc": utc_now(),
                "source_log": str(log_file),
                "event": event.get("event", "unknown"),
                "status": event.get("status", "info"),
                "details": event.get("details", ""),
                "context": event.get("context", {}),
                "raw": raw,
            }
            out_lines.append(json.dumps(wrapped))
            collected += 1

    if out_lines:
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(out_lines) + "\n")

    print(f"Collected {collected} QA events into {events_path}")
    return 0


def summarize_events(args: argparse.Namespace) -> int:
    session_dir = Path(args.session).resolve()
    events_path = session_dir / "qa_events.jsonl"
    summary_path = Path(args.output).resolve() if args.output else session_dir / "SUMMARY.md"

    if not session_dir.exists():
        print(f"Session path does not exist: {session_dir}")
        return 1

    events: list[dict[str, Any]] = []
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    events.append(data)
            except json.JSONDecodeError:
                continue

    counts = {"pass": 0, "fail": 0, "info": 0, "warn": 0, "other": 0}
    for event in events:
        status = str(event.get("status", "info")).lower()
        if status in counts:
            counts[status] += 1
        else:
            counts["other"] += 1

    fail_examples: list[str] = []
    for event in events:
        if str(event.get("status", "")).lower() != "fail":
            continue
        detail = str(event.get("details", "")).strip()
        name = str(event.get("event", "unknown")).strip()
        fail_examples.append(f"- {name}: {detail or '(no detail)'}")
        if len(fail_examples) >= 10:
            break

    overall = "pass" if counts["fail"] == 0 and len(events) > 0 else "needs-review"
    if len(events) == 0:
        overall = "no-data"

    summary = (
        "# QA Summary\n\n"
        f"Session: {session_dir.name}\n\n"
        f"- Status: {overall}\n"
        f"- Total events: {len(events)}\n"
        f"- Pass events: {counts['pass']}\n"
        f"- Fail events: {counts['fail']}\n"
        f"- Warn events: {counts['warn']}\n"
        f"- Info events: {counts['info']}\n"
        f"- Other events: {counts['other']}\n\n"
    )

    if fail_examples:
        summary += "## Failure Highlights\n\n" + "\n".join(fail_examples) + "\n"
    else:
        summary += "## Failure Highlights\n\n- None recorded.\n"

    write_text(summary_path, summary)
    print(f"Wrote summary: {summary_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage QA harness sessions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_cmd = subparsers.add_parser("init", help="Create a new QA session scaffold.")
    init_cmd.add_argument("--root", default=".", help="Repository root (default: .).")
    init_cmd.add_argument("--goal", required=True, help="What the QA session should validate.")
    init_cmd.add_argument(
        "--framework",
        default="auto",
        choices=(
            "auto",
            "dart-package",
            "minecraft-mod",
            "node-lib",
            "python-lib",
            "java-lib",
            "generic",
        ),
        help="Framework override; default auto-detect.",
    )
    init_cmd.add_argument(
        "--session",
        default="",
        help="Optional custom session name. Default uses timestamp + goal slug.",
    )

    collect_cmd = subparsers.add_parser("collect", help="Collect QA_EVT lines from log files.")
    collect_cmd.add_argument("--session", required=True, help="Path to session directory.")
    collect_cmd.add_argument(
        "--log-file",
        action="append",
        required=True,
        help="Path to a log file. Repeat flag for multiple files.",
    )
    collect_cmd.add_argument(
        "--prefix",
        default="QA_EVT",
        help="Log prefix used to identify structured QA events.",
    )

    summarize_cmd = subparsers.add_parser("summarize", help="Summarize collected QA events.")
    summarize_cmd.add_argument("--session", required=True, help="Path to session directory.")
    summarize_cmd.add_argument(
        "--output",
        default="",
        help="Optional output path for summary markdown. Defaults to SESSION/SUMMARY.md.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init":
        return init_session(args)
    if args.command == "collect":
        return collect_events(args)
    if args.command == "summarize":
        return summarize_events(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
