#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import yaml


PROVIDER_IMPORTS = (
    "package:provider/",
    "package:flutter_riverpod/",
    "package:riverpod/",
    "package:flutter_bloc/",
    "package:bloc/",
    "package:get_it/",
)
PYLON_MARKERS = (
    "package:pylon/pylon.dart",
    "Pylon<",
    "MutablePylon<",
    "Conduit<",
    "PylonFuture<",
    "PylonStream<",
    "PylonPort<",
    "context.pylon<",
    "context.modPylon<",
    "Pylon.push(",
)
WIDGET_CLASS_PATTERN = re.compile(
    r"class\s+([A-Za-z0-9_]+)\s+extends\s+(StatelessWidget|StatefulWidget)\b"
)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "scan":
        return scan_app(args)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan a Flutter app for Pylonify candidates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Create a Pylonify report.")
    scan_parser.add_argument("--root", default=".", help="Flutter app root.")
    scan_parser.add_argument("--session", default="", help="Optional session name.")
    scan_parser.add_argument("--out-dir", default="", help="Optional output directory.")

    return parser


def scan_app(args: argparse.Namespace) -> int:
    root: Path = Path(args.root).resolve()
    pubspec_path: Path = root / "pubspec.yaml"
    if not pubspec_path.exists():
        print(f"Missing pubspec.yaml at {root}")
        return 1

    pubspec: dict[str, Any] = load_yaml(pubspec_path)
    package_name: str = str(pubspec.get("name") or root.name)
    session: str = args.session or f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slugify(package_name)}"
    out_dir: Path = Path(args.out_dir).resolve() if args.out_dir else root / ".pylonify" / session
    if out_dir.exists():
        print(f"Output already exists: {out_dir}")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    lib_root: Path = root / "lib"
    dart_files: list[Path] = list_dart_files(lib_root) if lib_root.exists() else []
    file_records: list[dict[str, Any]] = [scan_file(root, path) for path in dart_files]

    summary: dict[str, Any] = build_summary(root, pubspec, file_records)
    candidates: list[dict[str, Any]] = build_candidates(file_records)
    inventory: dict[str, Any] = {
        "package_name": package_name,
        "root": str(root),
        "session": session,
        "out_dir": str(out_dir),
        "summary": summary,
        "files": file_records,
    }

    write_json(out_dir / "inventory.json", inventory)
    write_json(out_dir / "candidates.json", {"candidates": candidates})
    write_text(out_dir / "report.md", render_report(package_name, summary, candidates))

    print(f"Pylonify report created: {out_dir}")
    print(f"Candidates found: {len(candidates)}")
    return 0


def load_yaml(path: Path) -> dict[str, Any]:
    parsed: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def slugify(value: str) -> str:
    slug: str = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "app"


def list_dart_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.dart"):
        if any(part in {".dart_tool", "build", ".git"} for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def scan_file(root: Path, path: Path) -> dict[str, Any]:
    text: str = path.read_text(encoding="utf-8", errors="replace")
    imports: list[str] = re.findall(r"""(?:import|export|part)\s+['"]([^'"]+)['"]""", text)
    provider_import_hits: list[str] = [item for item in imports if item.startswith(PROVIDER_IMPORTS)]
    widget_class_names: list[str] = [match.group(1) for match in WIDGET_CLASS_PATTERN.finditer(text)]
    widget_constructor_param_counts: dict[str, int] = {
        class_name: count_constructor_params(text, class_name) for class_name in widget_class_names
    }
    relative_path: Path = path.relative_to(root)
    rel_path: str = relative_path.as_posix()
    top_dir: str = relative_path.parts[1] if len(relative_path.parts) > 2 else "(root)"

    record: dict[str, Any] = {
        "path": rel_path,
        "top_dir": top_dir,
        "pylon_usage_count": sum(text.count(marker) for marker in PYLON_MARKERS),
        "stateful_widgets": len(re.findall(r"\bextends StatefulWidget\b", text)),
        "stateless_widgets": len(re.findall(r"\bextends StatelessWidget\b", text)),
        "set_state_count": text.count("setState("),
        "future_builder_count": text.count("FutureBuilder<"),
        "stream_builder_count": text.count("StreamBuilder<"),
        "route_arg_count": count_route_args(text),
        "query_state_count": count_query_state(text),
        "provider_import_count": len(provider_import_hits),
        "value_notifier_count": count_any(text, ("ValueNotifier<", "ChangeNotifier", "StateNotifier", "Cubit<", "Bloc<", "BehaviorSubject<")),
        "list_builder_count": count_any(text, ("ListView.builder", "GridView.builder", "SliverList", "List.generate(")),
        "context_extension_count": len(re.findall(r"\bextension\s+[A-Za-z0-9_]*\s+on\s+BuildContext\b", text)),
        "constructor_param_counts": widget_constructor_param_counts,
        "imports": imports,
    }
    return record


def count_constructor_params(text: str, class_name: str) -> int:
    pattern: re.Pattern[str] = re.compile(
        rf"{re.escape(class_name)}\s*\(\s*\{{(.*?)\}}\s*\)",
        re.DOTALL,
    )
    match: re.Match[str] | None = pattern.search(text)
    if match is None:
        return 0
    body: str = match.group(1)
    param_hits: list[str] = re.findall(r"\b(?:required\s+)?this\.[A-Za-z0-9_]+\b", body)
    return len(param_hits)


def count_route_args(text: str) -> int:
    patterns: tuple[str, ...] = (
        "RouteSettings(",
        ".settings.arguments",
        "ModalRoute.of(context)",
        "Navigator.pushNamed",
        "Navigator.of(context).pushNamed",
        "Navigator.push(",
    )
    return count_any(text, patterns)


def count_query_state(text: str) -> int:
    patterns: tuple[str, ...] = (
        "Uri.base",
        "queryParameters",
        "queryParametersAll",
    )
    return count_any(text, patterns)


def count_any(text: str, patterns: tuple[str, ...]) -> int:
    return sum(text.count(pattern) for pattern in patterns)


def build_summary(root: Path, pubspec: dict[str, Any], file_records: list[dict[str, Any]]) -> dict[str, Any]:
    dependencies: dict[str, Any] = pubspec.get("dependencies") or {}
    if not isinstance(dependencies, dict):
        dependencies = {}
    feature_scores: dict[str, int] = {}
    for record in file_records:
        top_dir: str = str(record["top_dir"])
        feature_scores[top_dir] = feature_scores.get(top_dir, 0) + candidate_weight(record)
    sorted_features: list[dict[str, Any]] = [
        {"feature": key, "score": feature_scores[key]}
        for key in sorted(feature_scores, key=lambda item: feature_scores[item], reverse=True)
    ]
    return {
        "root": str(root),
        "uses_pylon_already": "pylon" in dependencies,
        "dependency_names": sorted(str(name) for name in dependencies.keys()),
        "file_count": len(file_records),
        "stateful_widget_count": sum(int(record["stateful_widgets"]) for record in file_records),
        "set_state_count": sum(int(record["set_state_count"]) for record in file_records),
        "future_builder_count": sum(int(record["future_builder_count"]) for record in file_records),
        "stream_builder_count": sum(int(record["stream_builder_count"]) for record in file_records),
        "route_arg_count": sum(int(record["route_arg_count"]) for record in file_records),
        "query_state_count": sum(int(record["query_state_count"]) for record in file_records),
        "provider_import_count": sum(int(record["provider_import_count"]) for record in file_records),
        "value_notifier_count": sum(int(record["value_notifier_count"]) for record in file_records),
        "pylon_usage_count": sum(int(record["pylon_usage_count"]) for record in file_records),
        "top_features": sorted_features[:8],
    }


def candidate_weight(record: dict[str, Any]) -> int:
    param_score: int = max([int(value) for value in dict(record["constructor_param_counts"]).values()] or [0])
    score: int = 0
    score += int(record["set_state_count"]) * 2
    score += int(record["future_builder_count"]) * 2
    score += int(record["stream_builder_count"]) * 2
    score += int(record["route_arg_count"])
    score += int(record["value_notifier_count"]) * 2
    score += int(record["provider_import_count"]) * 3
    score += max(param_score - 2, 0)
    return score


def build_candidates(file_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in file_records:
        path: str = str(record["path"])
        param_score: int = max([int(value) for value in dict(record["constructor_param_counts"]).values()] or [0])
        if param_score >= 4:
            candidates.append(
                candidate_entry(
                    "Pylon<T>",
                    path,
                    3 + param_score,
                    f"Widget constructors carry up to {param_score} forwarded fields; anchor immutable subtree data instead of drilling it.",
                )
            )
        if int(record["set_state_count"]) > 0 and int(record["stateful_widgets"]) > 0:
            candidates.append(
                candidate_entry(
                    "MutablePylon<T>",
                    path,
                    5 + int(record["set_state_count"]),
                    f"StatefulWidget plus {record['set_state_count']} setState call(s) suggests screen or subtree mutable state that can be anchored.",
                )
            )
        if int(record["future_builder_count"]) > 0:
            candidates.append(
                candidate_entry(
                    "PylonFuture<T>",
                    path,
                    4 + int(record["future_builder_count"]),
                    f"Contains {record['future_builder_count']} FutureBuilder occurrence(s); promote async results into descendant-visible pylon data.",
                )
            )
        if int(record["stream_builder_count"]) > 0:
            candidates.append(
                candidate_entry(
                    "PylonStream<T>",
                    path,
                    4 + int(record["stream_builder_count"]),
                    f"Contains {record['stream_builder_count']} StreamBuilder occurrence(s); promote stream emissions into descendant-visible pylon data.",
                )
            )
        if int(record["provider_import_count"]) > 0 or int(record["value_notifier_count"]) > 0:
            candidates.append(
                candidate_entry(
                    "Conduit<T> or scoped Pylon",
                    path,
                    5 + int(record["provider_import_count"]) + int(record["value_notifier_count"]),
                    "Contains provider/notifier style state; re-scope it to nearest Pylon boundary or Conduit only if it is truly app-global.",
                )
            )
        if int(record["route_arg_count"]) > 0:
            candidates.append(
                candidate_entry(
                    "Pylon.push / route pylons",
                    path,
                    3 + int(record["route_arg_count"]),
                    f"Contains {record['route_arg_count']} route transport pattern(s); remove argument plumbing when data should follow the route.",
                )
            )
        if int(record["query_state_count"]) > 0:
            candidates.append(
                candidate_entry(
                    "PylonPort<T>",
                    path,
                    4 + int(record["query_state_count"]),
                    "Reads query or URL state; use PylonPort only if the browser URL should remain the source of truth.",
                )
            )
        if int(record["list_builder_count"]) > 0 and param_score >= 2:
            candidates.append(
                candidate_entry(
                    "Item pylons / PylonCluster",
                    path,
                    3 + int(record["list_builder_count"]) + param_score,
                    "List-building plus forwarded constructor data suggests extracting item pylons or clustered subtree anchors.",
                )
            )
    candidates.sort(key=lambda item: int(item["score"]), reverse=True)
    return candidates


def candidate_entry(kind: str, path: str, score: int, reason: str) -> dict[str, Any]:
    return {"kind": kind, "path": path, "score": score, "reason": reason}


def render_report(package_name: str, summary: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "# Pylonify Report",
        "",
        f"- Package: `{package_name}`",
        f"- Uses pylon already: `{summary['uses_pylon_already']}`",
        f"- Dart files scanned: `{summary['file_count']}`",
        f"- Existing pylon markers: `{summary['pylon_usage_count']}`",
        f"- Stateful widgets: `{summary['stateful_widget_count']}`",
        f"- setState calls: `{summary['set_state_count']}`",
        f"- FutureBuilder count: `{summary['future_builder_count']}`",
        f"- StreamBuilder count: `{summary['stream_builder_count']}`",
        f"- Route transport count: `{summary['route_arg_count']}`",
        f"- Query or URL state count: `{summary['query_state_count']}`",
        f"- Provider/notifier signals: `{summary['provider_import_count'] + summary['value_notifier_count']}`",
        "",
        "## Feature Explosion Order",
    ]
    if summary["top_features"]:
        for feature in summary["top_features"]:
            lines.append(f"- `{feature['feature']}` score `{feature['score']}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Top Pylonify Candidates"])
    if candidates:
        for candidate in candidates[:20]:
            lines.append(f"- `{candidate['kind']}` in `{candidate['path']}` score `{candidate['score']}`: {candidate['reason']}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Refactor Direction",
            "- Explode the highest-scoring feature areas first.",
            "- Anchor immutable subtree data with `Pylon<T>` before cleaning constructor plumbing.",
            "- Convert mutable screen islands to `MutablePylon<T>` before extracting smaller widgets.",
            "- Use `Conduit<T>` only for true app-wide cross-route state.",
            "- Replace async builder islands with `PylonFuture<T>` or `PylonStream<T>` when descendants need the data.",
            "- Keep extensions small and typed after the data boundary is stable.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
