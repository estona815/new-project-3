from __future__ import annotations

import hashlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.local_device_qc import build_local_device_qc
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.plugin_validation_preflight import STOCK_PLUGIN_FILES


def make_reaper_app(root: Path) -> Path:
    app = root / "REAPER.app"
    binary = app / "Contents/MacOS/REAPER"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    info_plist = app / "Contents/Info.plist"
    with info_plist.open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleIdentifier": "com.cockos.reaper",
                "CFBundleName": "REAPER",
                "CFBundleShortVersionString": "7.99",
                "CFBundleVersion": "7990",
                "LSMinimumSystemVersion": "10.15",
            },
            handle,
        )
    fx = app / "Contents/Plugins/FX"
    fx.mkdir(parents=True, exist_ok=True)
    for filenames in STOCK_PLUGIN_FILES.values():
        (fx / filenames[0]).write_text("mock", encoding="utf-8")
    return app


def make_resource_dir(root: Path, *, include_required_jsfx: bool = True) -> Path:
    resource = root / "REAPER"
    effects = resource / "Effects"
    effects.mkdir(parents=True, exist_ok=True)
    if include_required_jsfx:
        for rel in [
            "Codex Vocal/vocal_ai_artifact_split_tamer.jsfx",
            "Vocal Clarity Repair/vocal_air_guard.jsfx",
            "Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx",
            "Vocal Clarity Repair/vocal_output_guard.jsfx",
            "Vocal Clarity Repair/vocal_presence_enhancer.jsfx",
        ]:
            path = effects / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("desc: mock\n", encoding="utf-8")
    return resource


def make_workspace(root: Path) -> Path:
    workspace = root / "workspace"
    analyzer = workspace / "automix/export/final_qc_analyzer.py"
    analyzer.parent.mkdir(parents=True, exist_ok=True)
    analyzer.write_text("# mock analyzer\n", encoding="utf-8")
    render = workspace / "renders/unit/final.wav"
    render.parent.mkdir(parents=True, exist_ok=True)
    render.write_bytes(b"RIFF")
    return workspace


def write_ready_gates(out: Path) -> None:
    write_json(out / "eval_reports/plugin_validation_preflight.json", {"summary": {"safe_to_write_parameters": True}, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/plugin_semantic_validation_gate.json", {"semantic_validation_ready": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/plugin_semantic_validation_runtime_collector_package.json", {"ready_for_reaper_runtime_collection": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/reaper_runtime_collector_safety_audit.json", {"passed": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json", {"ready_for_semantic_gate_rerun": True, "runtime_evidence_ready": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/source_acceptance_gate.json", {"accepted_export_source_ready": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/final_render_evidence_gate.json", {"ready_for_final_qc": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/final_qc_evidence_gate.json", {"ready_for_approval_readiness": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/ab_preview_evidence_gate.json", {"ready_for_human_ab_review": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/approval_export_readiness.json", {"ready_for_approval_export": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/path_hygiene_audit.json", {"passed": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/requirements_traceability_audit.json", {"passed": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/processing_policy_audit.json", {"passed": True, "blockers": [], "warnings": []})


def test_local_device_qc_reports_ready_local_machine_but_blocks_writes_without_gates(tmp_path: Path) -> None:
    reaper_app = make_reaper_app(tmp_path)
    resource = make_resource_dir(tmp_path)
    workspace = make_workspace(tmp_path)
    out = tmp_path / "automix"

    qc = build_local_device_qc(
        project_name="unit",
        output_dir=out,
        workspace_root=workspace,
        reaper_app=reaper_app,
        reaper_resource_dir=resource,
        command_overrides={"afinfo": "/usr/bin/afinfo", "ffmpeg": None, "ffprobe": None, "pytest": None, "sox": None},
    )

    assert qc["passed"] is True
    assert qc["readiness"]["local_device_qc_ready"] is True
    assert qc["readiness"]["ready_for_applied_parameter_writes"] is False
    assert qc["readiness"]["ready_for_delivery_claims"] is False
    assert qc["reaper_app_metadata"]["bundle_identifier"] == "com.cockos.reaper"
    assert qc["reaper_app_metadata"]["version"] == "7.99"
    assert qc["file_evidence"]["reaper_binary"]["sha256"] == hashlib.sha256(b"#!/bin/sh\n").hexdigest()
    assert qc["required_jsfx"][0]["file_evidence"]["sha256"] == hashlib.sha256(b"desc: mock\n").hexdigest()
    assert qc["stock_plugins"][0]["present_files"][0]["sha256"] == hashlib.sha256(b"mock").hexdigest()
    assert "ffmpeg_missing_mp3_export_or_filter_qc_limited" in qc["warnings"]
    assert (out / "eval_reports/local_device_qc.json").exists()
    assert (out / "eval_reports/local_device_qc.md").exists()


def test_local_device_qc_allows_readiness_true_only_when_evidence_gates_are_ready(tmp_path: Path) -> None:
    reaper_app = make_reaper_app(tmp_path)
    resource = make_resource_dir(tmp_path)
    workspace = make_workspace(tmp_path)
    out = tmp_path / "automix"
    write_ready_gates(out)

    qc = build_local_device_qc(
        project_name="unit",
        output_dir=out,
        workspace_root=workspace,
        reaper_app=reaper_app,
        reaper_resource_dir=resource,
        command_overrides={"afinfo": "/usr/bin/afinfo", "ffmpeg": "/usr/bin/ffmpeg", "ffprobe": "/usr/bin/ffprobe"},
    )

    assert qc["readiness"]["ready_for_reaper_runtime_collection"] is True
    assert qc["readiness"]["ready_for_applied_parameter_writes"] is True
    assert qc["readiness"]["ready_for_delivery_claims"] is True


def test_local_device_qc_blocks_missing_reaper_or_required_jsfx(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    resource = make_resource_dir(tmp_path, include_required_jsfx=False)
    qc = build_local_device_qc(
        project_name="unit",
        output_dir=tmp_path / "automix",
        workspace_root=workspace,
        reaper_app=tmp_path / "missing.app",
        reaper_resource_dir=resource,
        command_overrides={"afinfo": None, "ffprobe": None},
    )

    blockers = "\n".join(qc["blockers"])
    assert qc["passed"] is False
    assert "reaper_app_missing" in blockers
    assert "reaper_binary_missing" in blockers
    assert "required_codex_vocal_ai_artifact_split_tamer_missing" in blockers


def test_local_device_qc_cli_writes_reports(tmp_path: Path) -> None:
    reaper_app = make_reaper_app(tmp_path)
    resource = make_resource_dir(tmp_path)
    workspace = make_workspace(tmp_path)
    out = tmp_path / "automix"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_local_device_qc.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--workspace-root",
            str(workspace),
            "--reaper-app",
            str(reaper_app),
            "--reaper-resource-dir",
            str(resource),
            "--require-local-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["status"] == "local_device_qc_ready"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_report_index_groups_local_device_qc(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/local_device_qc.json", {"schema": "automix-local-device-qc-v1"})
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "local device QC" and item["summary"] == "local_device_qc.json" for item in index["reports"])
