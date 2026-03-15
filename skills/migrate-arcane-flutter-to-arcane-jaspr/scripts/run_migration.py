from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml


ORACULAR_REFERENCE_URL = "https://github.com/ArcaneArts/Oracular"
SKIP_NAMES = {
    ".dart_tool",
    ".git",
    ".github",
    ".idea",
    ".gradle",
    "build",
    "Pods",
    "node_modules",
    ".DS_Store",
    "pubspec.lock",
    ".flutter-plugins",
    ".flutter-plugins-dependencies",
    ".packages",
}
TEXT_EXTENSIONS = {
    ".dart",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".txt",
    ".sh",
    ".xml",
    ".plist",
    ".xcconfig",
    ".xcscheme",
    ".pbxproj",
    ".swift",
    ".kt",
    ".kts",
    ".gradle",
    ".properties",
    ".cc",
    ".h",
    ".cmake",
    ".html",
    ".js",
    ".css",
    ".entitlements",
    ".storyboard",
    ".xib",
    ".xcworkspacedata",
}
NATIVE_FLUTTER_PACKAGES = {
    "tray_manager",
    "window_manager",
    "screen_retriever",
    "flutter_acrylic",
    "launch_at_startup",
    "bitsdojo_window",
    "system_tray",
    "hotkey_manager",
    "menubar",
}
WEB_ONLY_IMPORT_PREFIXES = (
    "dart:html",
    "dart:js",
    "dart:js_util",
    "dart:js_interop",
    "package:web/",
    "package:js/",
    "package:arcane_jaspr/html.dart",
    "package:arcane_jaspr/web.dart",
)
FLUTTER_ONLY_IMPORT_PREFIXES = (
    "package:flutter/",
    "package:arcane/",
    "dart:ui",
    "dart:ffi",
)
JASPR_ONLY_IMPORT_PREFIXES = (
    "package:jaspr/",
    "package:arcane_jaspr/",
)
TEMPLATE_PACKAGE_NAMES = (
    "arcane_jaspr_docs",
    "arcane_jaspr_app",
    "arcane_beamer_app",
    "arcane_dock_app",
    "arcane_cli_app",
    "arcane_app",
)
DISPLAY_NAME_REPLACEMENTS = (
    "Arcane Template",
    "Arcane Beamer",
    "Arcane Dock",
    "Arcane CLI",
    "Arcane Jaspr Docs",
    "Arcane Jaspr",
)
SKILL_CONFIGS: dict[str, dict[str, Any]] = {
    "migrate-jaspr-to-arcane-jaspr": {
        "default_target_label": "ArcaneJaspr",
        "allowed_templates": {"arcane_jaspr_app", "arcane_jaspr_docs"},
    },
    "migrate-arcane-jaspr-to-arcane-flutter": {
        "default_target_label": "ArcaneFlutter",
        "allowed_templates": {"arcane_app", "arcane_beamer_app"},
    },
    "migrate-arcane-flutter-to-arcane-jaspr": {
        "default_target_label": "ArcaneJaspr",
        "allowed_templates": {"arcane_jaspr_app"},
    },
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "prepare":
        return prepare_stage(args)
    if args.command == "audit":
        return audit_stage(Path(args.stage).resolve(), emit_console=True)
    if args.command == "promote":
        return promote_stage(args)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage and audit Arcane platform migrations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Create the staged migration workspace.")
    prepare_parser.add_argument("--source", required=True, help="Source app root.")
    prepare_parser.add_argument("--workspace-root", default="", help="Workspace root containing the source app and local packages.")
    prepare_parser.add_argument("--destination", default="", help="Final output workspace path.")
    prepare_parser.add_argument("--stage-root", default="", help="Explicit stage root path.")
    prepare_parser.add_argument("--oracular-root", default="", help="Explicit Oracular repo root.")
    prepare_parser.add_argument("--template", default="", help="Explicit target template override.")

    audit_parser = subparsers.add_parser("audit", help="Run the parity audit against a prepared stage.")
    audit_parser.add_argument("--stage", required=True, help="Stage root path.")

    promote_parser = subparsers.add_parser("promote", help="Promote the staged project after a clean audit.")
    promote_parser.add_argument("--stage", required=True, help="Stage root path.")
    promote_parser.add_argument("--destination", default="", help="Override the destination root.")

    return parser


def prepare_stage(args: argparse.Namespace) -> int:
    skill_name: str = detect_skill_name()
    config: dict[str, Any] = SKILL_CONFIGS[skill_name]
    source_root: Path = Path(args.source).resolve()
    if not (source_root / "pubspec.yaml").exists():
        print(f"Source app must contain pubspec.yaml: {source_root}")
        return 1

    workspace_root: Path = Path(args.workspace_root).resolve() if args.workspace_root else source_root.parent
    if not workspace_root.exists():
        print(f"Workspace root does not exist: {workspace_root}")
        return 1

    oracular_root: Path | None = discover_oracular_root(args.oracular_root, workspace_root, source_root)
    if oracular_root is None:
        print("Unable to locate a local Oracular checkout with templates/.")
        return 1

    source_pubspec: dict[str, Any] = load_yaml(source_root / "pubspec.yaml")
    source_name: str = str(source_pubspec.get("name") or source_root.name)
    scan: dict[str, Any] = scan_project(source_root, source_pubspec)
    profile: dict[str, str] = classify_source(source_root, source_pubspec, scan)

    selected_template: str = select_template(skill_name, profile, args.template)
    target_label: str = template_target_label(selected_template, str(config["default_target_label"]))
    stage_name: str = f"{pascal_case(source_name)}To{target_label}"
    stage_root: Path = Path(args.stage_root).resolve() if args.stage_root else workspace_root / stage_name
    if stage_root.exists():
        print(f"Stage root already exists: {stage_root}")
        return 1

    destination_root: Path = Path(args.destination).resolve() if args.destination else workspace_root / f"{source_name}_migrated"
    template_root: Path = oracular_root / "templates" / selected_template
    if not template_root.exists():
        print(f"Template not found in Oracular: {template_root}")
        return 1

    stage_dirs: dict[str, Path] = {
        "source_snapshot": stage_root / "source_snapshot",
        "template_seed": stage_root / "template_seed",
        "project": stage_root / "project",
        "reports": stage_root / "reports",
        "backups": stage_root / "backups",
    }
    for directory in stage_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    snapshot_root: Path = stage_dirs["source_snapshot"] / source_root.name
    copy_tree(source_root, snapshot_root)

    template_seed_root: Path = stage_dirs["template_seed"] / selected_template
    copy_tree(template_root, template_seed_root)

    target_package_name: str = source_name
    app_root: Path = stage_dirs["project"] / target_package_name
    copy_tree(template_root, app_root)
    apply_template_replacements(app_root, target_package_name, pascal_case(source_name), source_package_domain(source_name))

    source_dependency_refs: dict[str, dict[str, str]] = dependency_refs(source_pubspec, source_root)
    package_records: list[dict[str, Any]] = discover_local_packages(workspace_root, source_root, source_dependency_refs, skill_name)
    copied_packages: list[dict[str, Any]] = []
    blockers: list[str] = build_blockers(skill_name, profile, scan, package_records, selected_template)

    if selected_template == "arcane_jaspr_docs":
        blockers.extend(stage_docs_dependencies(stage_dirs["project"], workspace_root, oracular_root))

    packages_root: Path = stage_dirs["project"] / "packages"
    for record in package_records:
        if not record["required"] or not record["eligible"]:
            continue
        packages_root.mkdir(parents=True, exist_ok=True)
        package_target: Path = packages_root / record["name"]
        copy_tree(Path(record["source_path"]), package_target)
        copied_packages.append(record)

    app_pubspec_path: Path = app_root / "pubspec.yaml"
    update_target_pubspec(app_pubspec_path, target_package_name, source_dependency_refs, copied_packages, app_root, stage_dirs["project"])
    for record in copied_packages:
        package_pubspec_path: Path = packages_root / record["name"] / "pubspec.yaml"
        rewire_copied_package_pubspec(package_pubspec_path, copied_packages, record["name"])

    checklist_path: Path = stage_dirs["reports"] / "manual_parity_checklist.md"
    write_manual_checklist(checklist_path, source_name, selected_template, profile, scan, package_records, copied_packages)

    session: dict[str, Any] = {
        "skill_name": skill_name,
        "source_root": str(source_root),
        "workspace_root": str(workspace_root),
        "destination_root": str(destination_root),
        "stage_root": str(stage_root),
        "oracular_root": str(oracular_root),
        "oracular_reference_url": ORACULAR_REFERENCE_URL,
        "selected_template": selected_template,
        "source_package_name": source_name,
        "target_package_name": target_package_name,
        "target_label": target_label,
        "stage_name": stage_name,
        "project_root": str(stage_dirs["project"]),
        "app_root": str(app_root),
        "template_seed_root": str(template_seed_root),
        "source_snapshot_root": str(snapshot_root),
        "reports_root": str(stage_dirs["reports"]),
        "checklist_path": str(checklist_path),
        "profile": profile,
        "scan": scan,
        "packages": package_records,
        "copied_packages": [record["name"] for record in copied_packages],
        "blockers": unique_strings(blockers),
    }
    write_json(stage_dirs["reports"] / "migration_inventory.json", build_inventory(session))
    write_json(stage_dirs["reports"] / "session.json", session)
    write_prepare_audit(stage_dirs["reports"] / "parity_audit.json", stage_dirs["reports"] / "parity_audit.md", session, checklist_path)

    print(f"Prepared stage: {stage_root}")
    print(f"Selected template: {selected_template}")
    print(f"Parity blockers: {len(session['blockers'])}")
    print(f"Audit report: {stage_dirs['reports'] / 'parity_audit.md'}")
    if session["blockers"]:
        return 1
    return 0


def audit_stage(stage_root: Path, emit_console: bool) -> int:
    session_path: Path = stage_root / "reports" / "session.json"
    if not session_path.exists():
        print(f"Missing session manifest: {session_path}")
        return 1
    session: dict[str, Any] = load_json(session_path)
    checklist_path: Path = Path(session["checklist_path"])
    app_root: Path = Path(session["app_root"])
    project_root: Path = Path(session["project_root"])
    blockers: list[str] = list(session.get("blockers", []))
    dynamic_blockers: list[str] = []
    unchecked_items: list[str] = unchecked_checklist_items(checklist_path)

    if not app_root.exists():
        dynamic_blockers.append(f"Missing staged app root: {app_root}")
    if not (app_root / "pubspec.yaml").exists():
        dynamic_blockers.append(f"Missing staged app pubspec: {app_root / 'pubspec.yaml'}")

    for package_name in session.get("copied_packages", []):
        staged_package_root: Path = project_root / "packages" / package_name
        if not (staged_package_root / "pubspec.yaml").exists():
            dynamic_blockers.append(f"Missing staged local package: {staged_package_root}")

    if session.get("selected_template") == "arcane_jaspr_docs":
        for dependency_name in ("arcane_jaspr", "arcane_lexicon"):
            dependency_root: Path = project_root / ".oracular_deps" / dependency_name
            if not (dependency_root / "pubspec.yaml").exists():
                dynamic_blockers.append(f"Missing staged docs dependency: {dependency_root}")

    status: str = "pass"
    if blockers or dynamic_blockers or unchecked_items:
        status = "fail"

    audit: dict[str, Any] = {
        "status": status,
        "source_root": session["source_root"],
        "stage_root": session["stage_root"],
        "selected_template": session["selected_template"],
        "blockers": blockers,
        "dynamic_blockers": dynamic_blockers,
        "unchecked_items": unchecked_items,
        "oracular_reference_url": session["oracular_reference_url"],
    }
    write_json(stage_root / "reports" / "parity_audit.json", audit)
    write_text(stage_root / "reports" / "parity_audit.md", render_audit_markdown(audit))
    if emit_console:
        print(f"Audit status: {status}")
        print(f"Audit report: {stage_root / 'reports' / 'parity_audit.md'}")
    return 0 if status == "pass" else 1


def promote_stage(args: argparse.Namespace) -> int:
    stage_root: Path = Path(args.stage).resolve()
    if audit_stage(stage_root, emit_console=False) != 0:
        print(f"Parity audit must pass before promotion: {stage_root / 'reports' / 'parity_audit.md'}")
        return 1

    session: dict[str, Any] = load_json(stage_root / "reports" / "session.json")
    project_root: Path = Path(session["project_root"])
    destination_root: Path = Path(args.destination).resolve() if args.destination else Path(session["destination_root"])
    backups_root: Path = stage_root / "backups"
    if destination_root.exists():
        backup_root: Path = backups_root / destination_root.name
        if backup_root.exists():
            shutil.rmtree(backup_root)
        shutil.move(str(destination_root), str(backup_root))
    copy_tree(project_root, destination_root)
    print(f"Promoted project to: {destination_root}")
    return 0


def detect_skill_name() -> str:
    return Path(__file__).resolve().parents[1].name


def discover_oracular_root(explicit: str, workspace_root: Path, source_root: Path) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).resolve())
    env_value: str | None = os.environ.get("ORACULAR_ROOT")
    if env_value:
        candidates.append(Path(env_value).resolve())
    script_root: Path = Path(__file__).resolve()
    for parent in [workspace_root, workspace_root.parent, source_root.parent, source_root.parent.parent, script_root.parents[4], script_root.parents[5]]:
        candidates.append(parent / "Oracular")
    seen: set[str] = set()
    for candidate in candidates:
        key: str = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if (candidate / "templates").exists():
            return candidate
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    parsed: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_tree(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore_names)


def ignore_names(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in SKIP_NAMES}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def pascal_case(text: str) -> str:
    tokens: list[str] = re.split(r"[^A-Za-z0-9]+", text)
    result: str = "".join(token.capitalize() for token in tokens if token)
    return result or "App"


def source_package_domain(source_name: str) -> str:
    normalized: str = re.sub(r"[^a-z0-9]+", "", source_name.lower())
    return f"art.arcane.{normalized or 'app'}"


def scan_project(source_root: Path, pubspec: dict[str, Any]) -> dict[str, Any]:
    imports: set[str] = set()
    route_score: int = 0
    hook_score: int = 0
    service_score: int = 0
    form_score: int = 0
    async_score: int = 0
    asset_entries: list[str] = flutter_assets(pubspec)
    if (source_root / "content").exists():
        asset_entries.append("content/")
    dart_file_count: int = 0
    dependency_names: list[str] = sorted(all_dependency_names(pubspec))
    for dart_file in list_dart_files(source_root):
        dart_file_count += 1
        text: str = read_text(dart_file)
        imports.update(re.findall(r"""(?:import|export|part)\s+['"]([^'"]+)['"]""", text))
        route_score += count_matches(text, r"\b(Beamer|GoRouter|RouterDelegate|RouteInformationParser|Navigator|AppRouter|RoutePath)\b")
        hook_score += count_matches(text, r"\b(useState|useEffect|useMemoized|HookWidget|HookConsumerWidget|StatefulWidget|setState\s*\()\b")
        service_score += count_matches(text, r"\b[A-Z][A-Za-z0-9]*(Service|Repository|Provider|Controller)\b")
        form_score += count_matches(text, r"\b(Form|TextFormField|TextInput|validator:|DropdownButton|Combobox)\b")
        async_score += count_matches(text, r"\b(async|await|Future<|Stream<|FutureBuilder|StreamBuilder)\b")
    import_list: list[str] = sorted(imports)
    web_only_items: list[str] = sorted(item for item in import_list if starts_with_any(item, WEB_ONLY_IMPORT_PREFIXES))
    flutter_only_items: list[str] = sorted(item for item in import_list if starts_with_any(item, FLUTTER_ONLY_IMPORT_PREFIXES))
    jaspr_only_items: list[str] = sorted(item for item in import_list if starts_with_any(item, JASPR_ONLY_IMPORT_PREFIXES))
    native_dependency_names: list[str] = sorted(set(dependency_names) & NATIVE_FLUTTER_PACKAGES)
    return {
        "dart_file_count": dart_file_count,
        "imports": import_list,
        "route_score": route_score,
        "hook_score": hook_score,
        "service_score": service_score,
        "form_score": form_score,
        "async_score": async_score,
        "asset_entries": sorted(unique_strings(asset_entries)),
        "dependency_names": dependency_names,
        "web_only_items": web_only_items,
        "flutter_only_items": flutter_only_items,
        "jaspr_only_items": jaspr_only_items,
        "native_dependency_names": native_dependency_names,
    }


def classify_source(source_root: Path, pubspec: dict[str, Any], scan: dict[str, Any]) -> dict[str, str]:
    dependency_names: set[str] = set(scan["dependency_names"])
    imports: list[str] = list(scan["imports"])
    has_flutter: bool = has_flutter_sdk(pubspec) or any((source_root / name).exists() for name in ("android", "ios", "linux", "macos", "windows"))
    has_jaspr: bool = "jaspr" in dependency_names or any(item.startswith("package:jaspr/") for item in imports)
    has_arcane_jaspr: bool = "arcane_jaspr" in dependency_names or any(item.startswith("package:arcane_jaspr/") for item in imports)
    has_arcane_flutter: bool = "arcane" in dependency_names or any(item.startswith("package:arcane/") for item in imports)
    jaspr_mode: str = str((pubspec.get("jaspr") or {}).get("mode") or "")
    has_arcane_lexicon: bool = "arcane_lexicon" in dependency_names
    platform: str = "unknown"
    if has_flutter:
        platform = "arcane_flutter" if has_arcane_flutter else "flutter"
    elif has_arcane_jaspr or has_arcane_lexicon:
        platform = "arcane_jaspr"
    elif has_jaspr:
        platform = "jaspr"
    shape: str = "standard"
    if jaspr_mode == "static" or has_arcane_lexicon or (source_root / "content").exists():
        shape = "docs"
    elif scan["native_dependency_names"]:
        shape = "dock"
    elif "beamer" in dependency_names or scan["route_score"] >= 6:
        shape = "router_heavy"
    return {"platform": platform, "shape": shape}


def select_template(skill_name: str, profile: dict[str, str], explicit_template: str) -> str:
    allowed_templates: set[str] = set(SKILL_CONFIGS[skill_name]["allowed_templates"])
    if explicit_template:
        if explicit_template not in allowed_templates:
            raise SystemExit(f"Template {explicit_template} is not allowed for {skill_name}")
        return explicit_template
    if skill_name == "migrate-jaspr-to-arcane-jaspr":
        return "arcane_jaspr_docs" if profile["shape"] == "docs" else "arcane_jaspr_app"
    if skill_name == "migrate-arcane-jaspr-to-arcane-flutter":
        return "arcane_beamer_app" if profile["shape"] == "router_heavy" else "arcane_app"
    return "arcane_jaspr_app"


def template_target_label(template_name: str, default_target_label: str) -> str:
    if template_name == "arcane_jaspr_docs":
        return "ArcaneJasprDocs"
    return default_target_label


def dependency_refs(pubspec: dict[str, Any], source_root: Path) -> dict[str, dict[str, str]]:
    refs: dict[str, dict[str, str]] = {}
    for section_name in ("dependencies", "dev_dependencies"):
        section: dict[str, Any] = pubspec.get(section_name) or {}
        if not isinstance(section, dict):
            continue
        for package_name, spec in section.items():
            entry: dict[str, str] = {"section": section_name, "resolved_path": ""}
            if isinstance(spec, dict) and "path" in spec:
                entry["resolved_path"] = str((source_root / str(spec["path"])).resolve())
            refs[str(package_name)] = entry
    return refs


def discover_local_packages(
    workspace_root: Path,
    source_root: Path,
    source_dependency_refs: dict[str, dict[str, str]],
    skill_name: str,
) -> list[dict[str, Any]]:
    package_dirs: dict[str, Path] = {}
    for candidate in candidate_package_dirs(workspace_root):
        if candidate == source_root:
            continue
        if not (candidate / "pubspec.yaml").exists():
            continue
        pubspec: dict[str, Any] = load_yaml(candidate / "pubspec.yaml")
        package_name: str = str(pubspec.get("name") or candidate.name)
        package_dirs[package_name] = candidate
    for dependency_name, ref in source_dependency_refs.items():
        if not ref["resolved_path"]:
            continue
        dependency_root: Path = Path(ref["resolved_path"])
        if (dependency_root / "pubspec.yaml").exists():
            package_dirs[dependency_name] = dependency_root
    records: list[dict[str, Any]] = []
    for package_name in sorted(package_dirs):
        package_root: Path = package_dirs[package_name]
        package_pubspec: dict[str, Any] = load_yaml(package_root / "pubspec.yaml")
        required_ref: dict[str, str] | None = source_dependency_refs.get(package_name)
        if required_ref is None:
            for dependency_name, ref in source_dependency_refs.items():
                if ref["resolved_path"] and Path(ref["resolved_path"]) == package_root:
                    required_ref = {"section": ref["section"], "resolved_path": ref["resolved_path"]}
                    break
        eligibility: dict[str, Any] = package_eligibility(skill_name, package_root, package_pubspec)
        records.append(
            {
                "name": package_name,
                "source_path": str(package_root),
                "required": required_ref is not None,
                "section": required_ref["section"] if required_ref else "",
                "eligible": eligibility["eligible"],
                "reasons": eligibility["reasons"],
            }
        )
    return records


def candidate_package_dirs(workspace_root: Path) -> list[Path]:
    candidates: list[Path] = []
    if (workspace_root / "pubspec.yaml").exists():
        candidates.append(workspace_root)
    for child in sorted(workspace_root.iterdir()):
        if not child.is_dir() or child.name in SKIP_NAMES:
            continue
        if (child / "pubspec.yaml").exists():
            candidates.append(child)
        if child.name in {"packages", "pkg", "pkgs", "modules"}:
            for nested in sorted(child.iterdir()):
                if nested.is_dir() and (nested / "pubspec.yaml").exists():
                    candidates.append(nested)
    return candidates


def package_eligibility(skill_name: str, package_root: Path, package_pubspec: dict[str, Any]) -> dict[str, Any]:
    scan: dict[str, Any] = scan_project(package_root, package_pubspec)
    dependency_names: set[str] = set(scan["dependency_names"])
    reasons: list[str] = []
    if skill_name == "migrate-jaspr-to-arcane-jaspr":
        if has_flutter_sdk(package_pubspec) or any(starts_with_any(item, FLUTTER_ONLY_IMPORT_PREFIXES) for item in scan["imports"]):
            reasons.append("depends on Flutter or Arcane Flutter surfaces")
        if dependency_names & NATIVE_FLUTTER_PACKAGES:
            reasons.append(f"depends on native Flutter plugins: {', '.join(sorted(dependency_names & NATIVE_FLUTTER_PACKAGES))}")
    if skill_name == "migrate-arcane-jaspr-to-arcane-flutter":
        if any(starts_with_any(item, JASPR_ONLY_IMPORT_PREFIXES + WEB_ONLY_IMPORT_PREFIXES) for item in scan["imports"]):
            reasons.append("depends on Jaspr or web-only runtime surfaces")
        if "jaspr" in dependency_names or "arcane_jaspr" in dependency_names:
            reasons.append("depends on Jaspr packages")
    if skill_name == "migrate-arcane-flutter-to-arcane-jaspr":
        if has_flutter_sdk(package_pubspec) or any(starts_with_any(item, FLUTTER_ONLY_IMPORT_PREFIXES) for item in scan["imports"]):
            reasons.append("depends on Flutter or Arcane Flutter surfaces")
        if dependency_names & NATIVE_FLUTTER_PACKAGES:
            reasons.append(f"depends on native Flutter plugins: {', '.join(sorted(dependency_names & NATIVE_FLUTTER_PACKAGES))}")
    return {"eligible": not reasons, "reasons": unique_strings(reasons)}


def build_blockers(
    skill_name: str,
    profile: dict[str, str],
    scan: dict[str, Any],
    package_records: list[dict[str, Any]],
    selected_template: str,
) -> list[str]:
    blockers: list[str] = []
    if skill_name == "migrate-jaspr-to-arcane-jaspr":
        if profile["platform"] != "jaspr":
            blockers.append("Source must be raw Jaspr. If it already uses arcane_jaspr or Flutter, use the matching migration skill.")
        if selected_template == "arcane_jaspr_docs" and profile["shape"] != "docs":
            blockers.append("The docs target template requires a docs or static-content source shape.")
    if skill_name == "migrate-arcane-jaspr-to-arcane-flutter":
        if profile["platform"] != "arcane_jaspr":
            blockers.append("Source must already be an Arcane Jaspr app or docs site.")
        if profile["shape"] == "docs":
            blockers.append("Arcane Jaspr docs/static sites must not be migrated to Arcane Flutter.")
        if scan["web_only_items"]:
            blockers.append(f"Source uses web-only escape hatches without 1:1 Arcane Flutter parity: {', '.join(scan['web_only_items'])}")
    if skill_name == "migrate-arcane-flutter-to-arcane-jaspr":
        if profile["platform"] != "arcane_flutter":
            blockers.append("Source must already be an Arcane Flutter app.")
        if profile["shape"] == "dock":
            blockers.append("Dock or tray window behavior cannot migrate 1:1 to Arcane Jaspr.")
        if scan["native_dependency_names"]:
            blockers.append(f"Source depends on native Flutter plugins without Jaspr parity: {', '.join(scan['native_dependency_names'])}")
        native_import_blockers: list[str] = [item for item in scan["imports"] if item in {"dart:io", "dart:ffi", "dart:ui"}]
        if native_import_blockers:
            blockers.append(f"Source imports native-only Dart libraries without Jaspr parity: {', '.join(sorted(native_import_blockers))}")
    for record in package_records:
        if record["required"] and not record["eligible"]:
            blockers.append(f"Required local package {record['name']} is not eligible for direct migration: {', '.join(record['reasons'])}")
    return unique_strings(blockers)


def stage_docs_dependencies(project_root: Path, workspace_root: Path, oracular_root: Path) -> list[str]:
    deps_root: Path = project_root / ".oracular_deps"
    deps_root.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []
    for package_name, aliases in {"arcane_jaspr": ["arcane_jaspr"], "arcane_lexicon": ["arcane_lexicon", "arcane_inkwell"]}.items():
        dependency_source: Path | None = find_local_dependency(workspace_root, oracular_root, package_name, aliases)
        if dependency_source is None:
            blockers.append(f"Unable to locate local dependency repository for {package_name}.")
            continue
        copy_tree(dependency_source, deps_root / package_name)
    return blockers


def find_local_dependency(workspace_root: Path, oracular_root: Path, package_name: str, aliases: list[str]) -> Path | None:
    candidates: list[Path] = []
    for root in {workspace_root, workspace_root.parent, oracular_root.parent, Path.cwd()}:
        for alias in aliases:
            candidates.append(root / alias)
    seen: set[str] = set()
    for candidate in candidates:
        key: str = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        pubspec_path: Path = candidate / "pubspec.yaml"
        if not pubspec_path.exists():
            continue
        pubspec: dict[str, Any] = load_yaml(pubspec_path)
        if str(pubspec.get("name") or "") == package_name:
            return candidate
    return None


def apply_template_replacements(app_root: Path, target_package_name: str, target_title: str, target_domain: str) -> None:
    content_replacements: list[tuple[str, str]] = [
        ("package:arcane_jaspr_docs/", f"package:{target_package_name}/"),
        ("package:arcane_jaspr_app/", f"package:{target_package_name}/"),
        ("package:arcane_beamer_app/", f"package:{target_package_name}/"),
        ("package:arcane_dock_app/", f"package:{target_package_name}/"),
        ("package:arcane_cli_app/", f"package:{target_package_name}/"),
        ("package:arcane_app/", f"package:{target_package_name}/"),
        ("art.arcane.template", target_domain),
        ("ORG_DOMAIN", target_domain),
    ]
    for template_name in TEMPLATE_PACKAGE_NAMES:
        content_replacements.append((template_name, target_package_name))
    for display_name in DISPLAY_NAME_REPLACEMENTS:
        content_replacements.append((display_name, target_title))
    for file_path in sorted(app_root.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        content: str = read_text(file_path)
        new_content: str = replace_many(content, content_replacements)
        if new_content != content:
            write_text(file_path, new_content)
    rename_tree_entries(app_root, [(template_name, target_package_name) for template_name in TEMPLATE_PACKAGE_NAMES])


def rename_tree_entries(root: Path, replacements: list[tuple[str, str]]) -> None:
    all_paths: list[Path] = sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True)
    for path in all_paths:
        new_name: str = replace_many(path.name, replacements)
        if new_name == path.name:
            continue
        path.rename(path.with_name(new_name))


def update_target_pubspec(
    pubspec_path: Path,
    target_package_name: str,
    source_dependency_refs: dict[str, dict[str, str]],
    copied_packages: list[dict[str, Any]],
    app_root: Path,
    project_root: Path,
) -> None:
    payload: dict[str, Any] = load_yaml(pubspec_path)
    payload["name"] = target_package_name
    copied_names: set[str] = {record["name"] for record in copied_packages}
    for dependency_name, ref in source_dependency_refs.items():
        if dependency_name not in copied_names:
            continue
        section_name: str = ref["section"] or "dependencies"
        section: dict[str, Any] = payload.get(section_name) or {}
        if not isinstance(section, dict):
            section = {}
        section[dependency_name] = {"path": relative_posix(app_root, project_root / "packages" / dependency_name)}
        payload[section_name] = section
    write_yaml(pubspec_path, payload)


def rewire_copied_package_pubspec(pubspec_path: Path, copied_packages: list[dict[str, Any]], current_package_name: str) -> None:
    if not pubspec_path.exists():
        return
    payload: dict[str, Any] = load_yaml(pubspec_path)
    copied_names: set[str] = {record["name"] for record in copied_packages}
    package_root: Path = pubspec_path.parent
    for section_name in ("dependencies", "dev_dependencies", "dependency_overrides"):
        section: dict[str, Any] = payload.get(section_name) or {}
        if not isinstance(section, dict):
            continue
        for package_name in copied_names:
            if package_name == current_package_name or package_name not in section:
                continue
            section[package_name] = {"path": relative_posix(package_root, package_root.parent / package_name)}
        payload[section_name] = section
    write_yaml(pubspec_path, payload)


def write_manual_checklist(
    checklist_path: Path,
    source_name: str,
    selected_template: str,
    profile: dict[str, str],
    scan: dict[str, Any],
    package_records: list[dict[str, Any]],
    copied_packages: list[dict[str, Any]],
) -> None:
    copied_package_names: list[str] = [record["name"] for record in copied_packages]
    required_package_names: list[str] = [record["name"] for record in package_records if record["required"]]
    lines: list[str] = [
        "# Manual Parity Checklist",
        "",
        f"- Source package: `{source_name}`",
        f"- Selected template: `{selected_template}`",
        f"- Source profile: `{profile['platform']}` / `{profile['shape']}`",
        "",
        "## Required Checks",
        "- [ ] App shell migrated into the staged target package",
        "- [ ] Routes and page entrypoints preserved 1:1",
        "- [ ] Hooks and state lifecycle preserved 1:1",
        "- [ ] Services, repositories, and connections preserved 1:1",
        "- [ ] Async flows, loading states, and errors preserved 1:1",
        "- [ ] Forms and validation semantics preserved 1:1",
        "- [ ] Assets and static content preserved 1:1",
        "- [ ] Theme and styling behavior preserved 1:1",
        "- [ ] Local package boundaries preserved and rewired correctly",
        "- [ ] No wrapper shims or compatibility adapters were introduced",
        "",
        "## Detected Signals",
        f"- Route score: `{scan['route_score']}`",
        f"- Hook score: `{scan['hook_score']}`",
        f"- Service score: `{scan['service_score']}`",
        f"- Form score: `{scan['form_score']}`",
        f"- Async score: `{scan['async_score']}`",
        f"- Assets: `{', '.join(scan['asset_entries']) or 'none'}`",
        f"- Required local packages: `{', '.join(required_package_names) or 'none'}`",
        f"- Copied eligible local packages: `{', '.join(copied_package_names) or 'none'}`",
    ]
    write_text(checklist_path, "\n".join(lines) + "\n")


def build_inventory(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_name": session["skill_name"],
        "oracular_reference_url": session["oracular_reference_url"],
        "oracular_root": session["oracular_root"],
        "source_root": session["source_root"],
        "workspace_root": session["workspace_root"],
        "destination_root": session["destination_root"],
        "stage_root": session["stage_root"],
        "selected_template": session["selected_template"],
        "source_package_name": session["source_package_name"],
        "target_package_name": session["target_package_name"],
        "profile": session["profile"],
        "scan": session["scan"],
        "packages": session["packages"],
        "copied_packages": session["copied_packages"],
        "blockers": session["blockers"],
    }


def write_prepare_audit(audit_path: Path, markdown_path: Path, session: dict[str, Any], checklist_path: Path) -> None:
    status: str = "blocked" if session["blockers"] else "pending-manual-parity"
    audit: dict[str, Any] = {
        "status": status,
        "source_root": session["source_root"],
        "stage_root": session["stage_root"],
        "selected_template": session["selected_template"],
        "blockers": session["blockers"],
        "dynamic_blockers": [],
        "unchecked_items": unchecked_checklist_items(checklist_path),
        "oracular_reference_url": session["oracular_reference_url"],
    }
    write_json(audit_path, audit)
    write_text(markdown_path, render_audit_markdown(audit))


def render_audit_markdown(audit: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Parity Audit",
        "",
        f"- Status: `{audit['status']}`",
        f"- Selected template: `{audit['selected_template']}`",
        f"- Oracular reference: `{audit['oracular_reference_url']}`",
        "",
        "## Blockers",
    ]
    if audit["blockers"]:
        lines.extend(f"- {item}" for item in audit["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Dynamic Blockers"])
    if audit["dynamic_blockers"]:
        lines.extend(f"- {item}" for item in audit["dynamic_blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Unchecked Manual Items"])
    if audit["unchecked_items"]:
        lines.extend(f"- {item}" for item in audit["unchecked_items"])
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def unchecked_checklist_items(checklist_path: Path) -> list[str]:
    if not checklist_path.exists():
        return [f"Missing checklist file: {checklist_path}"]
    unchecked: list[str] = []
    for line in checklist_path.read_text(encoding="utf-8").splitlines():
        match: re.Match[str] | None = re.match(r"^- \[ \] (.+)$", line.strip())
        if match:
            unchecked.append(match.group(1))
    return unchecked


def flutter_assets(pubspec: dict[str, Any]) -> list[str]:
    flutter_section: dict[str, Any] = pubspec.get("flutter") or {}
    if not isinstance(flutter_section, dict):
        return []
    assets: list[Any] = flutter_section.get("assets") or []
    if not isinstance(assets, list):
        return []
    return [str(item) for item in assets]


def all_dependency_names(pubspec: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for section_name in ("dependencies", "dev_dependencies", "dependency_overrides"):
        section: dict[str, Any] = pubspec.get(section_name) or {}
        if isinstance(section, dict):
            names.update(str(key) for key in section.keys())
    return names


def has_flutter_sdk(pubspec: dict[str, Any]) -> bool:
    for section_name in ("dependencies", "dev_dependencies"):
        section: dict[str, Any] = pubspec.get(section_name) or {}
        if not isinstance(section, dict):
            continue
        flutter_spec: Any = section.get("flutter")
        if isinstance(flutter_spec, dict) and str(flutter_spec.get("sdk") or "") == "flutter":
            return True
    return False


def starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def list_dart_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.dart"):
        if any(part in SKIP_NAMES for part in path.parts):
            continue
        files.append(path)
    return files


def count_matches(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text))


def replace_many(value: str, replacements: list[tuple[str, str]]) -> str:
    output: str = value
    for original, replacement in replacements:
        output = output.replace(original, replacement)
    return output


def unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def relative_posix(from_path: Path, to_path: Path) -> str:
    return Path(os.path.relpath(to_path, from_path)).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
