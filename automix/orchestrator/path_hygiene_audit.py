from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


PATH_HYGIENE_SCHEMA = "automix-path-hygiene-audit-v1"

AUDIT_REL_PATH = Path("eval_reports/path_hygiene_audit.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/path_hygiene_audit.md")

USER_HOME_PREFIX = "/" + "Users" + "/"
VOLUME_PREFIX = "/" + "Volumes" + "/"
FILE_URI_PREFIX = "file" + "://"
TILDE_HOME_PREFIX = "~" + "/"
ABSOLUTE_PATH_RE = re.compile(
    rf"({re.escape(USER_HOME_PREFIX)}[^\s\"'`]+|{re.escape(VOLUME_PREFIX)}[^\s\"'`]+|{re.escape(FILE_URI_PREFIX)}[^\s\"'`]+|{re.escape(TILDE_HOME_PREFIX)}[^\s\"'`]+)"
)

SOURCE_PATTERNS = [
    "automix/**/*.py",
    "scripts/*.py",
]

FIXTURE_PATTERNS = [
    "tests/automix_validation/fixtures/**/*.json",
]

RUNTIME_REPORT_PATTERNS = [
    "automix/analysis_reports/**/*.json",
    "automix/eval_reports/**/*.json",
    "automix/export/**/*.json",
    "automix/orchestrator/**/*.json",
    "automix/review/**/*.json",
    "automix/rollback/**/*.json",
]

EXCLUDED_SOURCE_PARTS = {
    "__pycache__",
}

GENERATED_REPORT_NAMES_TO_SKIP = {
    "path_hygiene_audit.json",
    "path_hygiene_audit.md",
}


def _matches(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return sorted(set(match.group(0) for match in ABSOLUTE_PATH_RE.finditer(text)))


def _files(root: Path, patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(paths))


def _source_files(root: Path) -> list[Path]:
    return [
        path
        for path in _files(root, SOURCE_PATTERNS)
        if not any(part in EXCLUDED_SOURCE_PARTS for part in path.parts)
    ]


def _finding(*, severity: str, category: str, path: Path, root: Path, matches: list[str]) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        "matches": matches,
        "count": len(matches),
    }


def build_path_hygiene_audit(
    *,
    project_name: str,
    output_dir: Path,
    workspace_root: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(workspace_root or Path.cwd())
    output_dir = Path(output_dir)
    findings: list[dict[str, Any]] = []
    source_files = _source_files(root)
    fixture_files = _files(root, FIXTURE_PATTERNS)
    runtime_report_files = [
        path
        for path in _files(root, RUNTIME_REPORT_PATTERNS)
        if path.name not in GENERATED_REPORT_NAMES_TO_SKIP
    ]
    for path in source_files:
        matches = _matches(path)
        if matches:
            findings.append(_finding(severity="blocker", category="source_code", path=path, root=root, matches=matches))
    for path in fixture_files:
        matches = _matches(path)
        if matches:
            findings.append(_finding(severity="warning", category="fixture_manifest", path=path, root=root, matches=matches))
    for path in runtime_report_files:
        matches = _matches(path)
        if matches:
            findings.append(_finding(severity="info", category="runtime_report", path=path, root=root, matches=matches))

    blockers = [
        f"source_code_contains_absolute_local_path:{finding['relative_path']}"
        for finding in findings
        if finding.get("severity") == "blocker"
    ]
    warnings = [
        f"fixture_manifest_contains_absolute_local_path:{finding['relative_path']}"
        for finding in findings
        if finding.get("severity") == "warning"
    ]
    audit = {
        "schema": PATH_HYGIENE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "workspace_root": str(root),
        "output_dir": str(output_dir),
        "source_files_scanned": len(source_files),
        "fixture_files_scanned": len(fixture_files),
        "runtime_report_files_scanned": len(runtime_report_files),
        "findings": findings,
        "finding_counts": {
            "blocker": sum(1 for item in findings if item.get("severity") == "blocker"),
            "warning": sum(1 for item in findings if item.get("severity") == "warning"),
            "info": sum(1 for item in findings if item.get("severity") == "info"),
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "passed": not blockers,
        "limits": [
            "Runtime reports may contain local evidence paths; this audit treats those as informational unless they appear in source code.",
            "Before external handoff, generated reports should be reviewed for raw audio/reference path exposure.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_path_hygiene_report(audit, output_dir)
    return audit


def write_path_hygiene_report(audit: dict[str, Any], output_dir: Path) -> Path:
    counts = audit.get("finding_counts", {})
    lines = [
        "# Path Hygiene Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Passed: `{audit.get('passed')}`",
        f"- Source files scanned: `{audit.get('source_files_scanned')}`",
        f"- Fixture files scanned: `{audit.get('fixture_files_scanned')}`",
        f"- Runtime report files scanned: `{audit.get('runtime_report_files_scanned')}`",
        f"- Blockers: `{counts.get('blocker', 0)}`",
        f"- Warnings: `{counts.get('warning', 0)}`",
        f"- Info findings: `{counts.get('info', 0)}`",
        "",
        "This audit checks path portability. It does not move files, delete evidence, or prove audio quality.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Findings", ""])
    for finding in audit.get("findings", [])[:80]:
        sample = ", ".join(finding.get("matches", [])[:3])
        lines.append(f"- `{finding.get('severity')}` `{finding.get('category')}` `{finding.get('relative_path')}` matches `{sample}`")
    if len(audit.get("findings", [])) > 80:
        lines.append(f"- plus `{len(audit.get('findings', [])) - 80}` more findings")
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
