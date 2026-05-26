from __future__ import annotations

from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT
from release_status import (
    infer_release_status_from_artifacts,
    normalize_release_workflow,
    write_release_status,
)


def build_release_workflow_status(
    *,
    project_root: str | Path = PROJECT_ROOT,
    workflow: str | None = None,
    mode: str | None = None,
    completion_gate: Any = None,
    final_audio_verified: bool = False,
    release_package_manifest_path: str | Path | None = None,
    release_qc_report_path: str | Path | None = None,
    final_selected: bool = True,
) -> dict[str, Any]:
    release_workflow = normalize_release_workflow(workflow, mode)
    return infer_release_status_from_artifacts(
        project_root=project_root,
        workflow=release_workflow,
        completion_gate=completion_gate,
        final_audio_verified=final_audio_verified,
        release_package_manifest_path=release_package_manifest_path,
        release_qc_report_path=release_qc_report_path,
        final_selected=final_selected,
    )


def write_release_workflow_status(
    *,
    project_root: str | Path = PROJECT_ROOT,
    workflow: str | None = None,
    mode: str | None = None,
    completion_gate: Any = None,
    final_audio_verified: bool = False,
    release_package_manifest_path: str | Path | None = None,
    release_qc_report_path: str | Path | None = None,
    final_selected: bool = True,
) -> dict[str, Any]:
    root = Path(project_root)
    status = build_release_workflow_status(
        project_root=root,
        workflow=workflow,
        mode=mode,
        completion_gate=completion_gate,
        final_audio_verified=final_audio_verified,
        release_package_manifest_path=release_package_manifest_path,
        release_qc_report_path=release_qc_report_path,
        final_selected=final_selected,
    )
    path = root / "06_QC_REPORT" / "release_status.json"
    write_release_status(path, status)
    return {"status": status, "path": path}
