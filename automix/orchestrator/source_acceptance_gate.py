from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

from automix.export.audio_export_utils import wav_info
from automix.plugins.plugin_adapter_schema import now_utc, write_json


SOURCE_ACCEPTANCE_SCHEMA = "automix-source-acceptance-gate-v1"

AUDIT_REL_PATH = Path("eval_reports/source_acceptance_gate.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/source_acceptance_gate.md")
TEMPLATE_REL_PATH = Path("review/source_acceptance_manifest_template.json")
REQUEST_REL_PATH = Path("review/source_acceptance_request.md")

VALID_FINAL_EXPORT_STAGES = {
    "accepted_premaster_draft",
    "accepted_vocal_placement_draft",
    "accepted_pitch_recovery_integrated_draft",
    "accepted_recovery_draft",
    "original_mix_explicitly_approved",
}

FINAL_EXPORT_INTENT = "final_export_source"
STEM_INTENT = "isolated_stem"

FULL_MIX_CLASSIFICATIONS = {"full_mix", "full_mix_reference", "reference", "reference_mix"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _candidate_from_args(
    *,
    source_audio: Path | None,
    source_stage: str,
    source_role: str,
    source_classification: str,
    intended_use: str,
    human_accepted: bool,
    notes: str,
) -> dict[str, Any] | None:
    if not source_audio:
        return None
    return {
        "label": source_audio.stem,
        "source_path": str(source_audio),
        "source_stage": source_stage,
        "source_role": source_role,
        "source_classification": source_classification,
        "intended_use": intended_use,
        "human_accepted": bool(human_accepted),
        "notes": notes,
    }


def _manifest_candidates(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = manifest.get("candidate_sources", [])
    if isinstance(candidates, list):
        return [item for item in candidates if isinstance(item, dict)]
    if manifest.get("source_path"):
        return [manifest]
    return []


def _audio_status(path_text: str) -> dict[str, Any]:
    if not path_text:
        return {"path": "", "exists": False, "valid_wav": False, "failures": ["source_path_missing"]}
    path = Path(path_text)
    if not path.exists():
        return {"path": str(path), "exists": False, "valid_wav": False, "failures": ["source_file_missing"]}
    if path.suffix.lower() != ".wav":
        return {"path": str(path), "exists": True, "size_bytes": path.stat().st_size, "valid_wav": False, "failures": ["source_file_not_wav"]}
    try:
        info = wav_info(path)
    except (wave.Error, EOFError, OSError) as exc:
        return {"path": str(path), "exists": True, "size_bytes": path.stat().st_size, "valid_wav": False, "failures": [f"wav_info_unavailable:{exc}"]}
    failures: list[str] = []
    if int(info.get("size_bytes", 0) or 0) <= 0:
        failures.append("source_file_empty")
    if float(info.get("duration_seconds", 0.0) or 0.0) <= 0.0:
        failures.append("source_duration_missing")
    info["path"] = str(path)
    info["valid_wav"] = not failures
    info["failures"] = failures
    return info


def _candidate_result(candidate: dict[str, Any]) -> dict[str, Any]:
    intended_use = str(candidate.get("intended_use", FINAL_EXPORT_INTENT) or FINAL_EXPORT_INTENT)
    stage = str(candidate.get("source_stage", "") or "")
    role = str(candidate.get("source_role", "") or "")
    classification = str(candidate.get("source_classification", "") or "")
    human_accepted = bool(candidate.get("human_accepted", False))
    audio = _audio_status(str(candidate.get("source_path", "") or ""))
    blockers: list[str] = []
    warnings: list[str] = []

    if not audio.get("valid_wav", False):
        blockers.extend(str(item) for item in audio.get("failures", []) or ["source_audio_invalid"])
    if not human_accepted:
        blockers.append("explicit_source_acceptance_missing")
    if intended_use not in {FINAL_EXPORT_INTENT, STEM_INTENT}:
        blockers.append(f"unknown_intended_use:{intended_use}")
    if intended_use == FINAL_EXPORT_INTENT:
        if stage not in VALID_FINAL_EXPORT_STAGES:
            blockers.append("accepted_export_stage_missing_or_invalid")
        if classification in FULL_MIX_CLASSIFICATIONS and stage != "original_mix_explicitly_approved":
            blockers.append("full_mix_source_cannot_be_accepted_for_automatic_processing")
        if role in {"full_mix_reference", "reference"} and stage != "original_mix_explicitly_approved":
            blockers.append("reference_role_cannot_be_final_export_source")
    if intended_use == STEM_INTENT:
        if classification in FULL_MIX_CLASSIFICATIONS or role in {"full_mix_reference", "reference"}:
            blockers.append("full_mix_reference_cannot_satisfy_isolated_stem_request")
        if not role:
            blockers.append("stem_role_missing")
        if stage and stage in VALID_FINAL_EXPORT_STAGES:
            warnings.append("stem_candidate_uses_final_export_stage_label")
    if audio.get("sample_rate") and int(audio.get("sample_rate")) != 48000:
        warnings.append("source_sample_rate_not_48k_document_equivalent_required")
    if audio.get("bit_depth") and int(audio.get("bit_depth")) not in {24, 32}:
        warnings.append("source_bit_depth_not_24_or_32_document_equivalent_required")

    accepted = not blockers
    return {
        "label": candidate.get("label", Path(str(candidate.get("source_path", ""))).stem),
        "source_path": str(candidate.get("source_path", "") or ""),
        "source_stage": stage,
        "source_role": role,
        "source_classification": classification,
        "intended_use": intended_use,
        "human_accepted": human_accepted,
        "audio": audio,
        "accepted": accepted,
        "allowed_for_final_export": accepted and intended_use == FINAL_EXPORT_INTENT,
        "allowed_as_isolated_stem": accepted and intended_use == STEM_INTENT,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "notes": candidate.get("notes", ""),
    }


def _template_from_source_handoff(source_handoff: dict[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for request in source_handoff.get("stem_requests", []) or []:
        if not isinstance(request, dict):
            continue
        for item in request.get("requested_files", []) or []:
            candidates.append(
                {
                    "label": item.get("label", "requested_stem"),
                    "source_path": "",
                    "source_stage": "",
                    "source_role": request.get("role", ""),
                    "source_classification": "isolated_stem",
                    "intended_use": STEM_INTENT,
                    "human_accepted": False,
                    "notes": item.get("notes", ""),
                }
            )
    if not candidates:
        candidates.append(
            {
                "label": "accepted_premaster_or_reviewed_draft",
                "source_path": "",
                "source_stage": "accepted_premaster_draft",
                "source_role": "premaster",
                "source_classification": "accepted_premaster_render",
                "intended_use": FINAL_EXPORT_INTENT,
                "human_accepted": False,
                "notes": "Fill with a reviewed WAV path only after human listening acceptance.",
            }
        )
    return {
        "schema": "automix-source-acceptance-manifest-template-v1",
        "candidate_sources": candidates,
        "limits": [
            "Do not mark human_accepted true without actual user listening acceptance.",
            "Full-mix/reference tracks cannot satisfy isolated stem requests.",
            "This template is not final export approval.",
        ],
    }


def build_source_acceptance_gate(
    *,
    project_name: str,
    output_dir: Path,
    manifest_path: Path | None = None,
    source_audio: Path | None = None,
    source_stage: str = "",
    source_role: str = "",
    source_classification: str = "",
    intended_use: str = FINAL_EXPORT_INTENT,
    human_accepted: bool = False,
    notes: str = "",
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    manifest = _load_json(Path(manifest_path)) if manifest_path else {}
    inline_candidate = _candidate_from_args(
        source_audio=source_audio,
        source_stage=source_stage,
        source_role=source_role,
        source_classification=source_classification,
        intended_use=intended_use,
        human_accepted=human_accepted,
        notes=notes,
    )
    candidates = _manifest_candidates(manifest)
    if inline_candidate:
        candidates.append(inline_candidate)
    results = [_candidate_result(candidate) for candidate in candidates]
    accepted_final = [item for item in results if item.get("allowed_for_final_export")]
    accepted_stems = [item for item in results if item.get("allowed_as_isolated_stem")]
    rejected = [item for item in results if not item.get("accepted")]

    blockers = sorted({blocker for item in results for blocker in item.get("blockers", [])})
    warnings = sorted({warning for item in results for warning in item.get("warnings", [])})
    if not candidates:
        blockers.append("source_acceptance_candidates_missing")
    if not accepted_final:
        warnings.append("accepted_final_export_source_not_recorded")

    source_handoff = _load_json(output_dir / "eval_reports/source_handoff_readiness.json")
    template = _template_from_source_handoff(source_handoff)
    write_json(output_dir / TEMPLATE_REL_PATH, template)

    gate = {
        "schema": SOURCE_ACCEPTANCE_SCHEMA,
        "project_name": project_name or manifest.get("project_name", ""),
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path or ""),
        "accepted_export_source_ready": bool(accepted_final),
        "accepted_stem_sources_total": len(accepted_stems),
        "candidate_sources_total": len(results),
        "rejected_candidate_sources_total": len(rejected),
        "candidate_results": results,
        "accepted_final_export_sources": accepted_final,
        "accepted_isolated_stems": accepted_stems,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "template_path": str(output_dir / TEMPLATE_REL_PATH),
        "limits": [
            "This gate does not modify final_export_state or project_state_manifest.",
            "It records whether candidate source evidence is acceptable before final export packaging.",
            "It does not listen to audio or replace user A/B approval.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, gate)
    write_source_acceptance_report(gate, output_dir)
    write_source_acceptance_request(gate, output_dir)
    return gate


def write_source_acceptance_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Source Acceptance Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Accepted final export source ready: `{gate.get('accepted_export_source_ready')}`",
        f"- Accepted isolated stems: `{gate.get('accepted_stem_sources_total')}`",
        f"- Candidate sources: `{gate.get('candidate_sources_total')}`",
        "",
        "This gate checks source acceptance evidence only. It does not approve a final export.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Candidates", ""])
    if not gate.get("candidate_results"):
        lines.append("- none")
    for item in gate.get("candidate_results", []):
        audio = item.get("audio", {})
        lines.extend(
            [
                f"### {item.get('label')}",
                "",
                f"- Source path: `{item.get('source_path')}`",
                f"- Intended use: `{item.get('intended_use')}`",
                f"- Stage: `{item.get('source_stage')}`",
                f"- Role: `{item.get('source_role')}`",
                f"- Classification: `{item.get('source_classification')}`",
                f"- Human accepted: `{item.get('human_accepted')}`",
                f"- Valid WAV: `{audio.get('valid_wav')}`",
                f"- Sample rate: `{audio.get('sample_rate', '')}`",
                f"- Bit depth: `{audio.get('bit_depth', '')}`",
                f"- Accepted: `{item.get('accepted')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_source_acceptance_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Source Acceptance Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
        "Fill the template with user-owned WAV candidates after listening review.",
        "",
        "Required before a source can be used for final export:",
        "",
        "- WAV source exists and is readable.",
        "- `human_accepted` is true only after explicit user listening acceptance.",
        "- Final export stage is one of the accepted final export stages.",
        "- Full-mix/reference material is not used as automatic processing input.",
        "",
        "Current blockers:",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
