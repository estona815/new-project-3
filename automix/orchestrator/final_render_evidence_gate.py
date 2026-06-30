from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import read_wav, rms
from automix.export.audio_export_utils import wav_info
from automix.plugins.plugin_adapter_schema import now_utc, write_json


FINAL_RENDER_EVIDENCE_SCHEMA = "automix-final-render-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/final_render_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/final_render_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/final_render_evidence_manifest_template.json")
REQUEST_REL_PATH = Path("review/final_render_evidence_request.md")

RENDER_MANIFEST_REL_PATH = Path("export/final_render_manifest.json")
FINAL_EXPORT_STATE_REL_PATH = Path("export/final_export_state.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_path(path_text: str, output_dir: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    candidates = [path, output_dir / path, output_dir.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def _wav_status(path_text: str, output_dir: Path, label: str) -> dict[str, Any]:
    if not path_text:
        return {
            "label": label,
            "path": "",
            "exists": False,
            "valid_wav": False,
            "failures": [f"{label}_path_missing"],
        }
    path = _resolve_path(path_text, output_dir)
    if not path.exists():
        return {
            "label": label,
            "path": str(path),
            "exists": False,
            "valid_wav": False,
            "failures": [f"{label}_file_missing"],
        }
    if path.suffix.lower() != ".wav":
        return {
            "label": label,
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size if path.is_file() else 0,
            "valid_wav": False,
            "failures": [f"{label}_file_not_wav"],
        }
    try:
        info = wav_info(path)
        audio = read_wav(path, max_seconds=None)
    except (wave.Error, EOFError, OSError, ValueError) as exc:
        return {
            "label": label,
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size if path.is_file() else 0,
            "valid_wav": False,
            "failures": [f"{label}_wav_unreadable:{exc}"],
        }
    mono_rms = rms(audio.mono)
    failures: list[str] = []
    if int(info.get("size_bytes", 0) or 0) <= 0:
        failures.append(f"{label}_file_empty")
    if float(info.get("duration_seconds", 0.0) or 0.0) <= 0.0:
        failures.append(f"{label}_duration_missing")
    if mono_rms <= 1.0e-6:
        failures.append(f"{label}_digital_black_detected")
    info["label"] = label
    info["path"] = str(path)
    info["mono_rms"] = mono_rms
    info["valid_wav"] = not failures
    info["failures"] = failures
    return info


def _is_report_only_manifest(manifest: dict[str, Any]) -> bool:
    warnings = " ".join(str(item).lower() for item in manifest.get("warnings", []) or [])
    return bool("diagnostic/report-only" in warnings or manifest.get("diagnostic_only") is True or manifest.get("report_only") is True)


def _render_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = manifest.get("renders", [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _primary_wav(items: list[dict[str, Any]]) -> dict[str, Any]:
    wavs = [item for item in items if item.get("format") == "wav" and item.get("created")]
    for item in wavs:
        if item.get("role") == "primary_wav" or int(item.get("bit_depth", 0) or 0) == 24:
            return item
    return wavs[0] if wavs else {}


def _source_status(export_state: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    selected = str(export_state.get("selected_export_source", "") or "")
    status = _wav_status(selected, output_dir, "selected_export_source") if selected else {
        "label": "selected_export_source",
        "path": "",
        "exists": False,
        "valid_wav": False,
        "failures": ["selected_export_source_path_missing"],
    }
    return {
        "safe_to_export": bool(export_state.get("safe_to_export", False)),
        "selected_export_source": selected,
        "selected_export_stage": export_state.get("selected_export_stage", ""),
        "blocked_reasons": export_state.get("blocked_reasons", []) or [],
        "audio": status,
    }


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-final-render-evidence-manifest-template-v1",
        "expected_reports": [
            "automix/export/final_export_state.json",
            "automix/export/final_render_manifest.json",
            "automix/eval_reports/final_render_evidence_gate.json",
        ],
        "manual_checks": [
            "Confirm the selected source is the intended accepted source.",
            "Confirm the primary WAV path is a newly rendered deliverable, not the original source path.",
            "Confirm no hidden limiter, normalization, or diagnostic/report-only state is present.",
        ],
        "limits": [
            "This template is not final approval.",
            "Measured final QC and matched-loudness A/B review are still required.",
            "Do not mark diagnostic/report-only renders as delivery evidence.",
        ],
    }


def build_final_render_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    render_manifest_path: Path | None = None,
    final_export_state_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    render_path = Path(render_manifest_path) if render_manifest_path else output_dir / RENDER_MANIFEST_REL_PATH
    state_path = Path(final_export_state_path) if final_export_state_path else output_dir / FINAL_EXPORT_STATE_REL_PATH
    manifest = _load_json(render_path)
    export_state = _load_json(state_path)
    blockers: list[str] = []
    warnings: list[str] = []

    if not render_path.exists() or not manifest:
        blockers.append("final_render_manifest_missing_or_invalid")
    elif manifest.get("schema") != "automix-final-render-manifest-v1":
        blockers.append("final_render_manifest_schema_invalid")
    if not state_path.exists() or not export_state:
        blockers.append("final_export_state_missing_or_invalid")
    elif export_state.get("schema") != "automix-final-export-state-v1":
        blockers.append("final_export_state_schema_invalid")

    failures = [str(item) for item in manifest.get("failures", []) or []]
    if failures:
        blockers.append("final_render_manifest_has_failures")
    manifest_warnings = [str(item) for item in manifest.get("warnings", []) or []]
    if _is_report_only_manifest(manifest):
        blockers.append("final_render_manifest_diagnostic_or_report_only")
    warnings.extend(f"manifest:{item}" for item in manifest_warnings if "diagnostic/report-only" not in item.lower())

    source = _source_status(export_state, output_dir)
    if not source.get("safe_to_export", False):
        blockers.append("final_export_state_not_safe")
    source_audio = source.get("audio", {})
    if not source_audio.get("valid_wav", False):
        blockers.extend(str(item) for item in source_audio.get("failures", []))

    items = _render_items(manifest)
    primary = _primary_wav(items)
    if not primary:
        blockers.append("primary_wav_render_missing")
        primary_status = {
            "label": "primary_wav",
            "path": "",
            "exists": False,
            "valid_wav": False,
            "failures": ["primary_wav_render_missing"],
        }
    else:
        primary_status = _wav_status(str(primary.get("path", "") or ""), output_dir, "primary_wav")
        if not primary_status.get("valid_wav", False):
            blockers.extend(str(item) for item in primary_status.get("failures", []))
        if int(primary.get("size_bytes", 0) or 0) <= 0:
            blockers.append("primary_wav_manifest_size_missing")
        elif primary_status.get("size_bytes") and int(primary.get("size_bytes", 0) or 0) != int(primary_status.get("size_bytes", 0) or 0):
            blockers.append("primary_wav_manifest_size_mismatch")
        if int(primary.get("sample_rate", primary_status.get("sample_rate", 0)) or 0) != int(primary_status.get("sample_rate", 0) or 0):
            blockers.append("primary_wav_manifest_sample_rate_mismatch")
        if int(primary.get("bit_depth", primary_status.get("bit_depth", 0)) or 0) != int(primary_status.get("bit_depth", 0) or 0):
            blockers.append("primary_wav_manifest_bit_depth_mismatch")
        if primary.get("hidden_limiter_added") is True:
            blockers.append("primary_wav_hidden_limiter_added")
        if primary.get("normalization_applied") is True:
            blockers.append("primary_wav_normalization_applied")

    render_settings = manifest.get("render_settings", {}) if isinstance(manifest.get("render_settings", {}), dict) else {}
    if render_settings.get("hidden_limiter") is True:
        blockers.append("render_settings_hidden_limiter_enabled")
    if render_settings.get("normalization") is True:
        blockers.append("render_settings_normalization_enabled")
    if render_settings and render_settings.get("source_must_come_from_resolver") is False:
        blockers.append("render_settings_source_resolver_not_required")

    manifest_stage = str(manifest.get("source_stage", "") or "")
    selected_stage = str(source.get("selected_export_stage", "") or "")
    if manifest_stage and selected_stage and manifest_stage != selected_stage:
        blockers.append("final_render_source_stage_mismatch")
    if primary_status.get("path") and source_audio.get("path") and primary_status.get("path") == source_audio.get("path"):
        blockers.append("primary_wav_path_matches_selected_export_source")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    ready = not blockers
    gate = {
        "schema": FINAL_RENDER_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "render_manifest_path": str(render_path),
        "final_export_state_path": str(state_path),
        "ready_for_final_qc": ready,
        "ready_for_approval_readiness": ready,
        "primary_wav_path": primary_status.get("path", ""),
        "source_summary": source,
        "render_summary": {
            "render_count": len(items),
            "failures": failures,
            "warnings": manifest_warnings,
            "diagnostic_or_report_only": _is_report_only_manifest(manifest),
            "source_stage": manifest_stage,
            "export_profile": manifest.get("export_profile", ""),
        },
        "primary_wav_manifest": primary,
        "primary_wav_status": primary_status,
        "render_settings": render_settings,
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates render evidence only; it does not approve audio.",
            "Final QC, loudness-matched A/B, source acceptance, rollback, and human approval remain required.",
            "Diagnostic/report-only renders cannot be used as delivery evidence.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_final_render_evidence_report(gate, output_dir)
    write_final_render_evidence_request(gate, output_dir)
    return gate


def write_final_render_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    primary = gate.get("primary_wav_status", {})
    source = gate.get("source_summary", {})
    render = gate.get("render_summary", {})
    lines = [
        "# Final Render Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for final QC: `{gate.get('ready_for_final_qc')}`",
        f"- Ready for approval readiness: `{gate.get('ready_for_approval_readiness')}`",
        f"- Primary WAV: `{gate.get('primary_wav_path')}`",
        f"- Primary WAV valid: `{primary.get('valid_wav')}`",
        f"- Source safe to export: `{source.get('safe_to_export')}`",
        f"- Render count: `{render.get('render_count')}`",
        f"- Diagnostic/report-only: `{render.get('diagnostic_or_report_only')}`",
        "",
        "This gate does not approve audio or claim quality. It only checks render evidence.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Primary WAV", ""])
    lines.append(f"- Path: `{primary.get('path', '')}`")
    lines.append(f"- Duration seconds: `{primary.get('duration_seconds', '')}`")
    lines.append(f"- Sample rate: `{primary.get('sample_rate', '')}`")
    lines.append(f"- Bit depth: `{primary.get('bit_depth', '')}`")
    lines.append(f"- RMS: `{primary.get('mono_rms', '')}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_final_render_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Final Render Evidence Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
    ]
    if gate.get("ready_for_final_qc"):
        lines.extend(
            [
                "The primary final WAV evidence is ready for measured QC. This is not delivery approval.",
                "",
                "Next checks:",
                "",
                "- Run final QC on the primary WAV.",
                "- Build a measured loudness-matched A/B preview.",
                "- Request human listening approval only after all delivery gates are ready.",
            ]
        )
    else:
        lines.extend(["The final render is not ready for QC or approval readiness. Resolve these blockers first:", ""])
        lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
