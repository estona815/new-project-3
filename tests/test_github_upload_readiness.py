from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.github_upload_readiness import REQUIRED_IGNORE_PATTERNS, REQUIRED_PATHS, build_github_upload_readiness
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def write_text(path: Path, text: str = "fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_minimal_workspace(
    root: Path,
    *,
    ignore_patterns: list[str] | None = None,
    jsfx_layout: str = "vocal_clarity_bundle",
) -> None:
    for rel in REQUIRED_PATHS:
        path = root / rel
        if rel.endswith(".gitkeep"):
            write_text(path, "")
        elif rel.endswith(".py"):
            write_text(path, "# fixture\n")
        elif rel.endswith(".lua"):
            write_text(path, "-- fixture\n")
        elif rel.endswith(".yaml"):
            write_text(path, "{}\n")
        else:
            write_text(path, "fixture\n")
    write_text(root / "automix/harness/fixture_module.py", "# fixture\n")
    write_text(root / "automix/scan_reaper_plugin_inventory.lua", "-- fixture\n")
    if jsfx_layout == "vocal_clarity_bundle":
        write_text(root / "VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx", "desc: fixture\n")
    elif jsfx_layout == "legacy_reaper_bundle":
        write_text(root / "reaper/jsfx/Codex Vocal AI Artifact Split Tamer", "desc: fixture\n")
    else:
        raise ValueError(f"Unsupported jsfx_layout: {jsfx_layout}")
    write_text(root / "tests/test_fixture.py", "def test_fixture():\n    assert True\n")
    write_text(root / ".gitignore", "\n".join(ignore_patterns if ignore_patterns is not None else REQUIRED_IGNORE_PATTERNS) + "\n")


def init_git(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)


def test_github_upload_readiness_passes_when_local_media_is_ignored(tmp_path: Path) -> None:
    make_minimal_workspace(tmp_path)
    init_git(tmp_path)
    write_text(tmp_path / "renders/final.wav", "RIFF")
    write_text(tmp_path / "session.rpp", "<REAPER_PROJECT>\n")

    audit = build_github_upload_readiness(project_name="unit", output_dir=tmp_path / "automix", workspace_root=tmp_path)

    assert audit["passed"] is True
    assert audit["status"] == "github_upload_source_ready"
    assert audit["readiness"]["source_handoff_ready"] is True
    assert audit["readiness"]["safe_to_git_add_all"] is True
    assert audit["readiness"]["clean_public_upload_ready"] is True
    assert audit["blockers"] == []
    assert (tmp_path / "automix/eval_reports/github_upload_readiness.json").exists()
    assert (tmp_path / "automix/eval_reports/github_upload_readiness.md").exists()


def test_github_upload_readiness_accepts_legacy_reaper_jsfx_layout(tmp_path: Path) -> None:
    make_minimal_workspace(tmp_path, jsfx_layout="legacy_reaper_bundle")
    init_git(tmp_path)

    audit = build_github_upload_readiness(project_name="unit", output_dir=tmp_path / "automix", workspace_root=tmp_path)

    assert audit["passed"] is True
    assert audit["readiness"]["source_handoff_ready"] is True
    assert audit["missing_required_any_globs"] == []


def test_github_upload_readiness_blocks_unignored_sensitive_candidates(tmp_path: Path) -> None:
    ignore_patterns = [pattern for pattern in REQUIRED_IGNORE_PATTERNS if pattern not in {"*.rpp", "*.RPP"}]
    make_minimal_workspace(tmp_path, ignore_patterns=ignore_patterns)
    init_git(tmp_path)
    write_text(tmp_path / "session.rpp", "<REAPER_PROJECT>\n")

    audit = build_github_upload_readiness(project_name="unit", output_dir=tmp_path / "automix", workspace_root=tmp_path)

    assert audit["passed"] is False
    assert "gitignore_missing_pattern:*.rpp" in audit["blockers"]
    assert "gitignore_missing_pattern:*.RPP" in audit["blockers"]
    assert "untracked_sensitive_files_not_ignored" in audit["blockers"]
    assert audit["readiness"]["safe_to_git_add_all"] is False


def test_github_upload_readiness_warns_about_already_tracked_sensitive_files(tmp_path: Path) -> None:
    make_minimal_workspace(tmp_path)
    init_git(tmp_path)
    write_text(tmp_path / "legacy.wav", "RIFF")
    write_text(tmp_path / "reaper/legacy_project.rpp", "<REAPER_PROJECT>\n")
    subprocess.run(["git", "add", "-f", "legacy.wav", "reaper/legacy_project.rpp"], cwd=tmp_path, check=True, capture_output=True)

    audit = build_github_upload_readiness(project_name="unit", output_dir=tmp_path / "automix", workspace_root=tmp_path)

    assert audit["passed"] is True
    assert audit["readiness"]["source_handoff_ready"] is True
    assert audit["readiness"]["clean_public_upload_ready"] is False
    assert audit["readiness"]["requires_manual_staging_review"] is True
    assert audit["git"]["tracked_sensitive_total"] == 2
    assert "tracked_sensitive_files_present_manual_history_cleanup_recommended" in audit["warnings"]


def test_github_upload_readiness_cli_writes_reports(tmp_path: Path) -> None:
    make_minimal_workspace(tmp_path)
    init_git(tmp_path)
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_github_upload_readiness.py"),
            "--project-name",
            "unit",
            "--workspace-root",
            str(tmp_path),
            "--output-dir",
            str(out),
            "--require-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["status"] == "github_upload_source_ready"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_report_index_groups_github_upload_readiness(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/github_upload_readiness.json", {"schema": "automix-github-upload-readiness-v1"})

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(item["stage"] == "handoff evidence" and item["summary"] == "github_upload_readiness.json" for item in index["reports"])
