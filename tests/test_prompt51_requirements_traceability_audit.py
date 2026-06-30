from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.requirements_traceability_audit import REQUIREMENTS, build_requirements_traceability_audit


def test_requirements_traceability_passes_against_current_repo_static_evidence(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    assert audit["passed"] is True
    assert audit["requirements_satisfied"] == len(REQUIREMENTS)
    assert audit["incomplete_requirement_ids"] == []
    assert (out / "eval_reports/requirements_traceability_audit.json").exists()
    md = (out / "eval_reports/requirements_traceability_audit.md").read_text(encoding="utf-8")
    assert "Requirements Traceability Audit" in md
    assert "does not prove audio quality" in md


def test_requirements_traceability_blocks_empty_workspace(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    workspace = tmp_path / "empty_workspace"
    workspace.mkdir()
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=workspace)
    assert audit["passed"] is False
    assert audit["requirements_incomplete"] == len(REQUIREMENTS)
    assert any("required_file_missing:PIPELINE_ARCHITECTURE.md" in blocker for blocker in audit["blockers"])


def test_requirements_traceability_cli_returns_nonzero_for_missing_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "empty_workspace"
    workspace.mkdir()
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_requirements_traceability_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--workspace-root",
            str(workspace),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert data["requirements_satisfied"] == 0
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_report_index_groups_requirements_traceability_audit(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "validation harness" and item["summary"] == "requirements_traceability_audit.json"
        for item in index["reports"]
    )


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            with tempfile.TemporaryDirectory() as directory:
                fn(Path(directory))
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt51 direct tests passed")
