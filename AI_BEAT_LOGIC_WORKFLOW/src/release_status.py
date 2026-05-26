from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


REQUEST_PARSED = "REQUEST_PARSED"
COMPOSITION_GUIDE_READY = "COMPOSITION_GUIDE_READY"
ARRANGEMENT_PLAN_READY = "ARRANGEMENT_PLAN_READY"
MIDI_GUIDE_READY = "MIDI_GUIDE_READY"
LOGIC_MANUAL_REQUIRED = "LOGIC_MANUAL_REQUIRED"
MIX_MASTER_PLAN_READY = "MIX_MASTER_PLAN_READY"
RESCUE_PLAN_READY = "RESCUE_PLAN_READY"
DEMO_RENDERED_UNVERIFIED = "DEMO_RENDERED_UNVERIFIED"
DEMO_RENDERED_VERIFIED = "DEMO_RENDERED_VERIFIED"
FINAL_MASTER_EXPORTED_UNVERIFIED = "FINAL_MASTER_EXPORTED_UNVERIFIED"
FINAL_MASTER_EXPORTED_VERIFIED = "FINAL_MASTER_EXPORTED_VERIFIED"
RELEASE_PACKAGE_READY = "RELEASE_PACKAGE_READY"
COMPLETE = "COMPLETE"
FAILED = "FAILED"

PLAN_ONLY_STATUSES = {
    REQUEST_PARSED,
    COMPOSITION_GUIDE_READY,
    ARRANGEMENT_PLAN_READY,
    MIDI_GUIDE_READY,
    LOGIC_MANUAL_REQUIRED,
    MIX_MASTER_PLAN_READY,
    RESCUE_PLAN_READY,
}

VALID_STATUSES = PLAN_ONLY_STATUSES | {
    DEMO_RENDERED_UNVERIFIED,
    DEMO_RENDERED_VERIFIED,
    FINAL_MASTER_EXPORTED_UNVERIFIED,
    FINAL_MASTER_EXPORTED_VERIFIED,
    RELEASE_PACKAGE_READY,
    COMPLETE,
    FAILED,
}

WORKFLOW_ALIASES = {
    "song_to_mix_master": "song_to_release",
    "sample_to_arrangement": "sample_to_release",
    "vocal_to_code": "vocal_to_release",
    "stems_to_production": "stems_to_release",
}

RELEASE_READY_LIMITATION = (
    "Release package readiness does not guarantee distribution approval, rights clearance, playlist placement, "
    "sales, charting, or commercial success."
)


def normalize_release_workflow(workflow: str | None, mode: str | None = None) -> str:
    if workflow in WORKFLOW_ALIASES:
        return WORKFLOW_ALIASES[workflow]
    if mode == "stems":
        return "stems_to_release"
    if mode == "vocal_plus_beat":
        return "vocal_to_release"
    return "plan_only" if not workflow else str(workflow)


def _gate_dict(completion_gate: Any) -> dict[str, Any]:
    if completion_gate is None:
        return {"complete": False, "blocking_reasons": ["completion gate was not run"]}
    if isinstance(completion_gate, dict):
        return {
            "complete": bool(completion_gate.get("complete")),
            "blocking_reasons": list(completion_gate.get("blocking_reasons", [])),
        }
    if is_dataclass(completion_gate):
        payload = asdict(completion_gate)
        return {"complete": bool(payload.get("complete")), "blocking_reasons": list(payload.get("blocking_reasons", []))}
    return {"complete": False, "blocking_reasons": ["completion gate status could not be parsed"]}


def _exists(path: str | Path | None) -> bool:
    return bool(path) and Path(path).exists() and Path(path).stat().st_size > 0


def _path_list(project_root: str | Path, relative_paths: list[str]) -> list[str]:
    root = Path(project_root)
    return [str(root / item) for item in relative_paths if (root / item).exists()]


def _release_manifest_ready(path: Path) -> bool:
    if not _exists(path):
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(payload.get("release_ready"))


def release_status_allows_complete(status: str, completion_gate: Any = None) -> bool:
    gate = _gate_dict(completion_gate)
    return status == COMPLETE and bool(gate.get("complete"))


def build_release_status(
    *,
    workflow: str = "plan_only",
    status: str,
    completion_gate: Any = None,
    final_audio_verified: bool = False,
    release_package_ready: bool = False,
    blocking_reasons: list[str] | None = None,
    generated_deliverables: list[str] | None = None,
    manual_logic_required: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    selected = status if status in VALID_STATUSES else FAILED
    gate = _gate_dict(completion_gate)
    blocking = list(blocking_reasons or [])
    if selected == FAILED and not blocking:
        blocking.append("release status failed")
    if selected in PLAN_ONLY_STATUSES:
        blocking.append(f"{selected} is not COMPLETE")
    if selected == DEMO_RENDERED_VERIFIED:
        blocking.append("DEMO_RENDERED_VERIFIED is not COMPLETE unless explicitly selected as final and final QC passes")
    if selected == FINAL_MASTER_EXPORTED_VERIFIED and not release_package_ready:
        blocking.append("FINAL_MASTER_EXPORTED_VERIFIED is not COMPLETE until required QC and release reports exist")
    if selected == RELEASE_PACKAGE_READY:
        blocking.append("RELEASE_PACKAGE_READY is separate from COMPLETE")
    blocking = list(dict.fromkeys(blocking))
    return {
        "schema_version": "release_status.v1",
        "workflow": workflow,
        "status": selected,
        "complete_allowed": release_status_allows_complete(selected, gate),
        "final_audio_verified": bool(final_audio_verified),
        "release_package_ready": bool(release_package_ready),
        "blocking_reasons": blocking if selected != COMPLETE else list(gate.get("blocking_reasons", [])),
        "generated_deliverables": list(generated_deliverables or []),
        "manual_logic_required": list(manual_logic_required or []),
        "limitations": list(dict.fromkeys([*(limitations or []), RELEASE_READY_LIMITATION])),
    }


def infer_release_status_from_artifacts(
    *,
    project_root: str | Path,
    workflow: str = "plan_only",
    completion_gate: Any = None,
    final_audio_verified: bool = False,
    release_package_manifest_path: str | Path | None = None,
    release_qc_report_path: str | Path | None = None,
    final_selected: bool = True,
) -> dict[str, Any]:
    root = Path(project_root)
    gate = _gate_dict(completion_gate)
    has_intent = _exists(root / "02_EDIT_PLAN" / "production_intent.json") or _exists(root / "02_EDIT_PLAN" / "creative_brief.json")
    has_composition = (
        _exists(root / "02_EDIT_PLAN" / "composition_guide.json")
        or _exists(root / "02_EDIT_PLAN" / "chord_progression_guide.json")
        or _exists(root / "02_EDIT_PLAN" / "melody_variation_guide.json")
    )
    has_arrangement = _exists(root / "02_EDIT_PLAN" / "arrangement_plan.json")
    has_rescue = _exists(root / "02_EDIT_PLAN" / "rescue_arrangement_plan.json")
    has_midi = _exists(root / "02_EDIT_PLAN" / "midi_region_guide.json")
    has_logic = _exists(root / "02_EDIT_PLAN" / "logic_arrangement_plan.md")
    has_mix = _exists(root / "09_MIX_MASTER" / "mix_master_plan.json")
    demo_path = root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
    final_wavs = sorted((root / "05_FINAL_WAV").glob("*.wav")) if (root / "05_FINAL_WAV").exists() else []
    manifest_path = Path(release_package_manifest_path) if release_package_manifest_path else root / "06_QC_REPORT" / "release_package_manifest.json"
    release_qc_path = Path(release_qc_report_path) if release_qc_report_path else root / "06_QC_REPORT" / "release_qc_report.md"
    release_package_ready = _release_manifest_ready(manifest_path) and _exists(release_qc_path)
    final_exists = bool(final_wavs)

    if gate.get("complete") and final_audio_verified and release_package_ready:
        selected = COMPLETE
    elif release_package_ready and final_audio_verified:
        selected = RELEASE_PACKAGE_READY
    elif final_exists and final_audio_verified:
        selected = FINAL_MASTER_EXPORTED_VERIFIED
    elif final_exists:
        selected = FINAL_MASTER_EXPORTED_UNVERIFIED
    elif _exists(demo_path):
        selected = DEMO_RENDERED_VERIFIED if final_selected and final_audio_verified else DEMO_RENDERED_UNVERIFIED
    elif has_mix:
        selected = MIX_MASTER_PLAN_READY
    elif has_logic:
        selected = LOGIC_MANUAL_REQUIRED
    elif has_midi:
        selected = MIDI_GUIDE_READY
    elif has_rescue:
        selected = RESCUE_PLAN_READY
    elif has_arrangement:
        selected = ARRANGEMENT_PLAN_READY
    elif has_composition:
        selected = COMPOSITION_GUIDE_READY
    elif has_intent:
        selected = REQUEST_PARSED
    else:
        selected = FAILED

    deliverables = _path_list(
        root,
        [
            "02_EDIT_PLAN/production_intent.json",
            "02_EDIT_PLAN/composition_guide.json",
            "02_EDIT_PLAN/arrangement_plan.json",
            "01_ANALYSIS/bad_song_diagnosis.json",
            "01_ANALYSIS/bad_song_diagnosis.md",
            "02_EDIT_PLAN/rescue_arrangement_plan.json",
            "02_EDIT_PLAN/rescue_arrangement_plan.md",
            "02_EDIT_PLAN/lead_melody_plan.json",
            "02_EDIT_PLAN/hook_identity_plan.json",
            "02_EDIT_PLAN/vocal_texture_rescue_plan.json",
            "02_EDIT_PLAN/sample_motif_rebuild_plan.json",
            "02_EDIT_PLAN/logic_rescue_plan.md",
            "02_EDIT_PLAN/midi_region_guide.json",
            "02_EDIT_PLAN/logic_arrangement_plan.md",
            "09_MIX_MASTER/mix_master_plan.json",
            "04_PROCESSED_AUDIO/fallback_processed.wav",
            "06_QC_REPORT/qc_report.md",
            "06_QC_REPORT/rescue_qc_report.md",
            "06_QC_REPORT/master_qc_report.md",
            "09_MIX_MASTER/master_qc_report.md",
            "06_QC_REPORT/release_package_manifest.json",
            "06_QC_REPORT/release_qc_report.md",
        ],
    )
    deliverables.extend(str(path) for path in final_wavs)

    blocking = list(gate.get("blocking_reasons", []))
    if selected == FINAL_MASTER_EXPORTED_VERIFIED and not release_package_ready:
        if not _exists(manifest_path):
            blocking.append(f"release package manifest missing: {manifest_path}")
        if not _exists(release_qc_path):
            blocking.append(f"release QC report missing: {release_qc_path}")
    if selected == FAILED and not blocking:
        blocking.append("no release workflow artifacts were found")

    manual_logic = []
    if has_logic or selected in {LOGIC_MANUAL_REQUIRED, MIX_MASTER_PLAN_READY, DEMO_RENDERED_UNVERIFIED, DEMO_RENDERED_VERIFIED}:
        manual_logic.append("Logic production/export remains manual unless verified artifacts exist")

    limitations = [
        "Plan-ready statuses are not COMPLETE.",
        "Demo renders are not final masters unless explicitly selected and verified through final QC.",
        "Release package readiness is separate from COMPLETE.",
    ]
    return build_release_status(
        workflow=workflow,
        status=selected,
        completion_gate=gate,
        final_audio_verified=final_audio_verified,
        release_package_ready=release_package_ready,
        blocking_reasons=blocking,
        generated_deliverables=deliverables,
        manual_logic_required=manual_logic,
        limitations=limitations,
    )


def write_release_status(path: str | Path, payload: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
