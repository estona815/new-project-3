from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from .severity import Finding, add_finding, findings_to_dicts, has_warn_plus, max_severity
except ImportError:  # pragma: no cover
    from severity import Finding, add_finding, findings_to_dicts, has_warn_plus, max_severity


DEAI_TOKENS = ("suno", "deai", "de-ai", "de_ai", "artifact", "ai vocal", "vocal noise")
IGNORE_DIRS = {".git", "__pycache__", ".venv", ".venv_handoff", "build", "external_models"}


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    results: list[Path] = []
    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            results.append(path)
    return sorted(results)


def _smoke_jsfx(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "file": str(path),
        "has_desc": bool(re.search(r"(?im)^\s*desc\s*:", text)),
        "has_slider_or_code": bool(re.search(r"(?im)^\s*(slider\d+|@init|@sample|@block|@gfx)\b", text)),
        "has_null_bytes": "\x00" in text,
        "line_count": text.count("\n") + 1,
    }


def _extract_jsfx_references_from_rpp(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return re.findall(r'(?m)^\s*<JS\s+"([^"]+)"', text)


def _looks_deai(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in DEAI_TOKENS)


def audit_plugins(
    project_root: str | Path,
    findings: list[Finding] | None = None,
    *,
    mode: str = "auto",
    project_files: list[str | Path] | None = None,
) -> dict[str, Any]:
    findings = findings if findings is not None else []
    root = Path(project_root)
    jsfx_files = _iter_files(root, (".jsfx",))
    fxchain_files = _iter_files(root, (".rfxchain",))
    plugin_map = root / "config" / "plugin_map.yaml"
    project_paths = [Path(path) for path in project_files] if project_files else _iter_files(root, (".rpp",))
    referenced_jsfx: list[str] = []
    for project_path in project_paths:
        try:
            referenced_jsfx.extend(_extract_jsfx_references_from_rpp(project_path))
        except OSError:
            continue

    smoke_results = []
    for jsfx in jsfx_files:
        result = _smoke_jsfx(jsfx)
        smoke_results.append(result)
        if result["has_null_bytes"] or not result["has_desc"]:
            add_finding(
                "WARN",
                "JSFX_SMOKE_WARN",
                "Custom JSFX smoke check found a suspicious file.",
                json.dumps(result, sort_keys=True),
                "Open the JSFX in REAPER or fix desc/code structure, then rerun plugin audit.",
                findings,
                affected_file=str(jsfx),
                failed_assumption="Custom JSFX can be safely inserted.",
                command_to_rerun=f"python3 -m harness.plugin_audit --project-root {root} --json",
            )

    jsfx_lookup = {path.stem.lower(): path for path in jsfx_files}
    missing_references = []
    for reference in referenced_jsfx:
        normalized = Path(reference).stem.lower().replace("js: ", "")
        if normalized and normalized not in jsfx_lookup and _looks_deai(reference):
            missing_references.append(reference)
    if missing_references:
        severity = "BLOCKER" if mode in {"vocal_repair", "fullmix_rescue"} else "WARN"
        add_finding(
            severity,
            "REFERENCED_CUSTOM_DEAI_JSFX_MISSING",
            "A referenced custom Suno/DeAI JSFX was not found in the repository.",
            ", ".join(sorted(set(missing_references))),
            "Add the missing JSFX under reaper/jsfx or remove/downgrade the DeAI claim.",
            findings,
            affected_file=str(root),
            failed_assumption="Required custom DeAI plugin is available.",
            command_to_rerun=f"python3 -m harness.plugin_audit --project-root {root} --mode {mode} --json",
            human_listening_required=True,
        )

    if mode == "vocal_repair" and not any(_looks_deai(path.name) for path in jsfx_files):
        add_finding(
            "WARN",
            "NO_CUSTOM_DEAI_JSFX_DISCOVERED",
            "No custom Suno/DeAI JSFX was discovered for a vocal repair mode.",
            f"jsfx_count={len(jsfx_files)}",
            "Use stock cleanup only and do not claim DeAI, or add/smoke-test the custom DeAI JSFX.",
            findings,
            affected_file=str(root),
            failed_assumption="Vocal repair includes verified Suno artifact reduction.",
            command_to_rerun=f"python3 -m harness.plugin_audit --project-root {root} --mode vocal_repair --json",
            human_listening_required=True,
        )

    if not plugin_map.exists():
        add_finding(
            "WARN",
            "PLUGIN_MAP_MISSING",
            "Plugin role map is missing.",
            "config/plugin_map.yaml not found.",
            "Create/update config/plugin_map.yaml or log every fallback in the REAPER project report.",
            findings,
            affected_file=str(plugin_map),
            failed_assumption="Plugin availability is mapped before FX insertion.",
        )
    else:
        add_finding(
            "PASS",
            "PLUGIN_MAP_PRESENT",
            "Plugin role map exists.",
            str(plugin_map),
            "Keep plugin map and REAPER FX-chain logs in sync.",
            findings,
            affected_file=str(plugin_map),
        )

    return {
        "project_root": str(root),
        "jsfx_files": [str(path) for path in jsfx_files],
        "fxchain_files": [str(path) for path in fxchain_files],
        "plugin_map": str(plugin_map) if plugin_map.exists() else None,
        "referenced_jsfx": sorted(set(referenced_jsfx)),
        "missing_referenced_custom_deai_jsfx": sorted(set(missing_references)),
        "jsfx_smoke": smoke_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit REAPER plugin, JSFX, and FXChain availability.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", default="auto")
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    audit = audit_plugins(args.project_root, findings, mode=args.mode, project_files=args.project)
    payload = {"audit": audit, "max_severity": max_severity(findings), "findings": findings_to_dicts(findings)}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"max_severity={payload['max_severity']} jsfx={len(audit['jsfx_files'])} fxchains={len(audit['fxchain_files'])}")
    return 2 if has_warn_plus(findings) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

