from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


GITHUB_UPLOAD_READINESS_SCHEMA = "automix-github-upload-readiness-v1"

JSON_REL_PATH = Path("eval_reports/github_upload_readiness.json")
MD_REL_PATH = Path("eval_reports/github_upload_readiness.md")

REQUIRED_PATHS = [
    "README.md",
    "QUICKSTART.md",
    "AGENTS.md",
    "MIXMASTER_SPEC.md",
    "PLUGIN_POLICY.md",
    "QC_TARGETS.md",
    "TESTING_AND_HARNESS.md",
    "docs/automix_runbook.md",
    "docs/github_integration_pipeline.md",
    "docs/github_upload_readiness.md",
    "prompts/new_computer_codex_bootstrap.md",
    "configs/mix_profile.yaml",
    "configs/plugin_allowlist.yaml",
    "configs/qc_targets.yaml",
    "configs/render_targets.yaml",
    "requirements.txt",
    "requirements-harness.txt",
    "scripts/run_github_integration_smoke.py",
    "scripts/run_github_upload_readiness.py",
    "scripts/run_local_device_qc.py",
    "tools/detect_environment.py",
    "tools/build_asset_manifest.py",
    "tools/install_reaper_jsfx.py",
    "tools/run_reaper_pipeline.py",
    "tools/qc_audio.py",
    "tools/package_delivery.py",
    "delivery/.gitkeep",
    "input/reference/.gitkeep",
    "input/stems/.gitkeep",
    "input/target/.gitkeep",
    "work/assets/.gitkeep",
    "work/logs/.gitkeep",
    "work/qc/.gitkeep",
    "work/reaper_project/.gitkeep",
    "work/renders/.gitkeep",
    "work/traces/.gitkeep",
]

REQUIRED_GLOBS = {
    "automix_python_modules": "automix/**/*.py",
    "reaper_lua_scripts": "automix/**/*.lua",
    "tests": "tests/test_*.py",
}

REQUIRED_ANY_GLOBS = {
    "codex_jsfx": [
        "VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/*.jsfx",
        "reaper/jsfx/*",
    ],
}

REQUIRED_IGNORE_PATTERNS = [
    "*.wav",
    "*.mp3",
    "*.mp4",
    "*.zip",
    "*.rpp",
    "*.RPP",
    "*.jpg",
    "*.png",
    "*.ass",
    "audio_work/",
    "deliverables/",
    "delivery/*",
    "drive_handoff/",
    "input/stems/*",
    "input/reference/*",
    "input/target/*",
    "output/",
    "processed_audio/",
    "renders/",
    "tmp/",
    "tools/bin/",
    "hwp_extract/",
    "*.odt",
    "work/assets/*",
    "work/logs/*",
    "work/qc/*",
    "work/renders/*",
    "work/reaper_project/*",
    "work/traces/*",
]

SENSITIVE_SUFFIXES = {
    ".aac",
    ".aif",
    ".aiff",
    ".ass",
    ".docx",
    ".flac",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".odt",
    ".pdf",
    ".png",
    ".rpp",
    ".wav",
    ".wave",
    ".webp",
    ".zip",
}

SENSITIVE_DIR_PREFIXES = (
    "audio_work/",
    "deliverables/",
    "delivery/",
    "drive_handoff/",
    "input/reference/",
    "input/stems/",
    "input/target/",
    "output/",
    "processed_audio/",
    "renders/",
    "tmp/",
    "tools/bin/",
    "hwp_extract/",
    "work/assets/",
    "work/logs/",
    "work/qc/",
    "work/renders/",
    "work/reaper_project/",
    "work/traces/",
)

GIT_SAMPLE_LIMIT = 25


def _rel(path: Path, root: Path) -> str:
    try:
        value = path.relative_to(root)
    except ValueError:
        value = path
    return value.as_posix()


def _normalise_git_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _is_sensitive_path(path: str) -> bool:
    lower = _normalise_git_path(path).lower()
    if lower.endswith(".rpp-bak"):
        return True
    if any(lower.startswith(prefix) for prefix in SENSITIVE_DIR_PREFIXES):
        return not lower.endswith("/.gitkeep")
    return Path(lower).suffix in SENSITIVE_SUFFIXES


def _run_git(workspace_root: Path, args: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=workspace_root,
            check=False,
            capture_output=True,
            text=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    raw = result.stdout
    if b"\0" in raw:
        return [item.decode("utf-8", errors="replace") for item in raw.split(b"\0") if item]
    return [line.decode("utf-8", errors="replace") for line in raw.splitlines() if line]


def _git_available(workspace_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git_counts(workspace_root: Path) -> dict[str, Any]:
    if not _git_available(workspace_root):
        return {
            "git_available": False,
            "tracked_sensitive_files": [],
            "tracked_sensitive_total": 0,
            "untracked_unignored_sensitive_files": [],
            "untracked_unignored_sensitive_total": 0,
            "deleted_tracked_files": [],
            "deleted_tracked_total": 0,
            "modified_or_deleted_short_status_total": 0,
        }

    tracked = [_normalise_git_path(item) for item in _run_git(workspace_root, ["ls-files", "-z"])]
    untracked = [_normalise_git_path(item) for item in _run_git(workspace_root, ["ls-files", "--others", "--exclude-standard", "-z"])]
    deleted = [_normalise_git_path(item) for item in _run_git(workspace_root, ["ls-files", "--deleted", "-z"])]
    short = _run_git(workspace_root, ["status", "--short", "--untracked-files=no"])
    tracked_sensitive = sorted(path for path in tracked if _is_sensitive_path(path))
    untracked_sensitive = sorted(path for path in untracked if _is_sensitive_path(path))
    return {
        "git_available": True,
        "tracked_sensitive_files": tracked_sensitive[:GIT_SAMPLE_LIMIT],
        "tracked_sensitive_total": len(tracked_sensitive),
        "untracked_unignored_sensitive_files": untracked_sensitive[:GIT_SAMPLE_LIMIT],
        "untracked_unignored_sensitive_total": len(untracked_sensitive),
        "deleted_tracked_files": sorted(deleted)[:GIT_SAMPLE_LIMIT],
        "deleted_tracked_total": len(deleted),
        "modified_or_deleted_short_status_total": len(short),
    }


def _ignore_lines(workspace_root: Path) -> set[str]:
    path = workspace_root / ".gitignore"
    if not path.is_file():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")}


def _path_record(workspace_root: Path, rel_path: str) -> dict[str, Any]:
    path = workspace_root / rel_path
    return {
        "path": rel_path,
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def _glob_record(workspace_root: Path, name: str, pattern: str) -> dict[str, Any]:
    matches = sorted(path for path in workspace_root.glob(pattern) if path.is_file())
    return {
        "name": name,
        "pattern": pattern,
        "count": len(matches),
        "examples": [_rel(path, workspace_root) for path in matches[:GIT_SAMPLE_LIMIT]],
    }


def _glob_group_record(workspace_root: Path, name: str, patterns: list[str]) -> dict[str, Any]:
    pattern_records = [_glob_record(workspace_root, name, pattern) for pattern in patterns]
    total_count = sum(item["count"] for item in pattern_records)
    examples: list[str] = []
    for item in pattern_records:
        for example in item["examples"]:
            if example not in examples:
                examples.append(example)
            if len(examples) >= GIT_SAMPLE_LIMIT:
                break
        if len(examples) >= GIT_SAMPLE_LIMIT:
            break
    return {
        "name": name,
        "patterns": patterns,
        "pattern_results": pattern_records,
        "count": total_count,
        "examples": examples,
    }


def build_github_upload_readiness(
    *,
    project_name: str,
    output_dir: Path,
    workspace_root: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root or Path.cwd())
    output_dir = Path(output_dir)

    required_paths = [_path_record(workspace_root, path) for path in REQUIRED_PATHS]
    required_globs = [_glob_record(workspace_root, name, pattern) for name, pattern in REQUIRED_GLOBS.items()]
    required_any_globs = [
        _glob_group_record(workspace_root, name, patterns)
        for name, patterns in REQUIRED_ANY_GLOBS.items()
    ]
    ignore_lines = _ignore_lines(workspace_root)
    missing_ignore_patterns = [pattern for pattern in REQUIRED_IGNORE_PATTERNS if pattern not in ignore_lines]
    missing_required_paths = [item["path"] for item in required_paths if not item["exists"]]
    missing_required_globs = [item["name"] for item in required_globs if item["count"] == 0]
    missing_required_any_globs = [item["name"] for item in required_any_globs if item["count"] == 0]
    git_counts = _git_counts(workspace_root)

    blockers: list[str] = []
    warnings: list[str] = []
    blockers.extend(f"required_path_missing:{path}" for path in missing_required_paths)
    blockers.extend(f"required_glob_empty:{name}" for name in missing_required_globs)
    blockers.extend(f"required_glob_empty:{name}" for name in missing_required_any_globs)
    blockers.extend(f"gitignore_missing_pattern:{pattern}" for pattern in missing_ignore_patterns)
    if git_counts["untracked_unignored_sensitive_total"]:
        blockers.append("untracked_sensitive_files_not_ignored")
    if git_counts["tracked_sensitive_total"]:
        warnings.append("tracked_sensitive_files_present_manual_history_cleanup_recommended")
    if git_counts["deleted_tracked_total"]:
        warnings.append("deleted_tracked_files_present_stage_or_review_before_upload")
    if not git_counts["git_available"]:
        warnings.append("git_not_available_or_not_a_worktree")

    source_handoff_ready = not blockers
    safe_to_git_add_all = bool(source_handoff_ready and not git_counts["untracked_unignored_sensitive_total"])
    clean_public_upload_ready = bool(
        source_handoff_ready
        and safe_to_git_add_all
        and git_counts["tracked_sensitive_total"] == 0
        and git_counts["deleted_tracked_total"] == 0
    )

    readiness = {
        "source_handoff_ready": source_handoff_ready,
        "safe_to_git_add_all": safe_to_git_add_all,
        "clean_public_upload_ready": clean_public_upload_ready,
        "requires_manual_staging_review": bool(git_counts["tracked_sensitive_total"] or git_counts["deleted_tracked_total"]),
        "opens_reaper": False,
        "renders_audio": False,
        "writes_parameters": False,
        "report_only": True,
    }
    audit = {
        "schema": GITHUB_UPLOAD_READINESS_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "workspace_root": str(workspace_root),
        "output_dir": str(output_dir),
        "readiness": readiness,
        "required_paths": required_paths,
        "required_globs": required_globs,
        "required_any_globs": required_any_globs,
        "missing_required_paths": missing_required_paths,
        "missing_required_globs": missing_required_globs,
        "missing_required_any_globs": missing_required_any_globs,
        "required_ignore_patterns": REQUIRED_IGNORE_PATTERNS,
        "missing_ignore_patterns": missing_ignore_patterns,
        "git": git_counts,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "status": "github_upload_source_ready" if source_handoff_ready else "github_upload_review_required",
        "passed": source_handoff_ready and safe_to_git_add_all,
        "limits": [
            "This audit is report-only and does not open REAPER, render audio, write plugin parameters, stage files, commit, or push.",
            "A clean public upload still requires manual review of already tracked legacy media or REAPER project files.",
            "Git ignore coverage protects future untracked files only; it does not remove files that are already tracked.",
        ],
    }
    target = output_path or output_dir / JSON_REL_PATH
    write_json(target, audit)
    write_github_upload_readiness_report(audit, output_dir)
    return audit


def write_github_upload_readiness_report(audit: dict[str, Any], output_dir: Path) -> Path:
    readiness = audit.get("readiness", {})
    git = audit.get("git", {})
    lines = [
        "# GitHub Upload Readiness",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Status: `{audit.get('status')}`",
        f"- Source handoff ready: `{readiness.get('source_handoff_ready')}`",
        f"- Safe to run `git add .`: `{readiness.get('safe_to_git_add_all')}`",
        f"- Clean public upload ready: `{readiness.get('clean_public_upload_ready')}`",
        f"- Requires manual staging review: `{readiness.get('requires_manual_staging_review')}`",
        "",
        "This audit is report-only. It does not open REAPER, render audio, stage files, commit, or push.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(
        [
            "",
            "## Git Summary",
            "",
            f"- Git available: `{git.get('git_available')}`",
            f"- Tracked sensitive files: `{git.get('tracked_sensitive_total')}`",
            f"- Untracked sensitive files not ignored: `{git.get('untracked_unignored_sensitive_total')}`",
            f"- Deleted tracked files: `{git.get('deleted_tracked_total')}`",
            f"- Modified/deleted tracked status entries: `{git.get('modified_or_deleted_short_status_total')}`",
            "",
            "## Tracked Sensitive Samples",
            "",
        ]
    )
    lines.extend([f"- `{item}`" for item in git.get("tracked_sensitive_files", [])] or ["- none"])
    lines.extend(["", "## Untracked Sensitive Not Ignored Samples", ""])
    lines.extend([f"- `{item}`" for item in git.get("untracked_unignored_sensitive_files", [])] or ["- none"])
    lines.extend(["", "## Deleted Tracked Samples", ""])
    lines.extend([f"- `{item}`" for item in git.get("deleted_tracked_files", [])] or ["- none"])
    lines.extend(["", "## Missing Required Paths", ""])
    lines.extend([f"- `{item}`" for item in audit.get("missing_required_paths", [])] or ["- none"])
    lines.extend(["", "## Missing Required Globs", ""])
    lines.extend([f"- `{item}`" for item in audit.get("missing_required_globs", [])] or ["- none"])
    lines.extend(["", "## Missing Required Either-Or Globs", ""])
    lines.extend([f"- `{item}`" for item in audit.get("missing_required_any_globs", [])] or ["- none"])
    lines.extend(["", "## Missing Ignore Patterns", ""])
    lines.extend([f"- `{item}`" for item in audit.get("missing_ignore_patterns", [])] or ["- none"])
    path = Path(output_dir) / MD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
