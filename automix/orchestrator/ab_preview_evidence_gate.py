from __future__ import annotations

import json
import math
import wave
from pathlib import Path
from typing import Any

from automix.export.audio_export_utils import wav_info
from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json


AB_PREVIEW_EVIDENCE_SCHEMA = "automix-ab-preview-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/ab_preview_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/ab_preview_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/ab_preview_review_manifest_template.json")
REQUEST_REL_PATH = Path("review/ab_preview_review_request.md")
DEFAULT_MANIFEST_REL_PATH = Path("eval_reports/final_ab_preview_manifest.json")

LOUDNESS_TOLERANCE_DB = 0.25


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
    except (wave.Error, EOFError, OSError) as exc:
        return {
            "label": label,
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size if path.is_file() else 0,
            "valid_wav": False,
            "failures": [f"{label}_wav_info_unavailable:{exc}"],
        }
    failures: list[str] = []
    if int(info.get("size_bytes", 0) or 0) <= 0:
        failures.append(f"{label}_file_empty")
    if float(info.get("duration_seconds", 0.0) or 0.0) <= 0.0:
        failures.append(f"{label}_duration_missing")
    info["label"] = label
    info["path"] = str(path)
    info["valid_wav"] = not failures
    info["failures"] = failures
    return info


def _db_ratio(value: float, reference: float) -> float | None:
    if value <= 1.0e-12 or reference <= 1.0e-12:
        return None
    return 20.0 * math.log10(value / reference)


def _segment_status(manifest: dict[str, Any]) -> dict[str, Any]:
    raw_segments = manifest.get("segments", [])
    segments = [item for item in raw_segments if isinstance(item, dict)] if isinstance(raw_segments, list) else []
    labels = [str(item.get("label", "")) for item in segments]
    blockers: list[str] = []
    warnings: list[str] = []
    if not segments:
        blockers.append("ab_preview_segments_missing")
    if "original_mix" not in labels:
        blockers.append("ab_preview_original_segment_missing")
    if "final_processed" not in labels:
        blockers.append("ab_preview_final_segment_missing")
    if len(segments) < 2:
        blockers.append("ab_preview_too_few_segments")
    if segments and any(safe_float(item.get("duration_seconds"), 0.0) <= 0.0 for item in segments):
        warnings.append("ab_preview_segment_duration_missing_or_zero")
    return {
        "segments_total": len(segments),
        "labels": labels,
        "has_original_segment": "original_mix" in labels,
        "has_final_segment": "final_processed" in labels,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def _loudness_status(manifest: dict[str, Any], *, allow_legacy_loudness_flag: bool) -> dict[str, Any]:
    match = manifest.get("loudness_match", {})
    flag = bool(manifest.get("loudness_matched", False))
    blockers: list[str] = []
    warnings: list[str] = []
    if not flag:
        blockers.append("ab_preview_not_loudness_matched")
    if not isinstance(match, dict) or not match:
        if flag and allow_legacy_loudness_flag:
            warnings.append("ab_preview_loudness_match_metrics_missing_legacy_flag_used")
            return {
                "metrics_present": False,
                "matched": True,
                "loudness_matched_flag": flag,
                "method": "legacy_boolean",
                "delta_db_after_match": None,
                "tolerance_db": LOUDNESS_TOLERANCE_DB,
                "blockers": sorted(set(blockers)),
                "warnings": sorted(set(warnings)),
            }
        blockers.append("ab_preview_loudness_match_metrics_missing")
        return {
            "metrics_present": False,
            "matched": False,
            "loudness_matched_flag": flag,
            "method": "",
            "delta_db_after_match": None,
            "tolerance_db": LOUDNESS_TOLERANCE_DB,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
        }

    target_rms = safe_float(match.get("target_rms"), 0.0)
    after_rms = safe_float(match.get("final_rms_after_match"), 0.0)
    delta_db = match.get("delta_db_after_match")
    if delta_db is None:
        ratio_db = _db_ratio(after_rms, target_rms)
        delta_db = abs(ratio_db) if ratio_db is not None else None
    else:
        delta_db = abs(safe_float(delta_db, 999.0))

    if target_rms <= 1.0e-9:
        blockers.append("ab_preview_loudness_target_rms_missing")
    if after_rms <= 1.0e-9:
        blockers.append("ab_preview_loudness_after_match_rms_missing")
    if delta_db is None:
        blockers.append("ab_preview_loudness_delta_unavailable")
    elif delta_db > LOUDNESS_TOLERANCE_DB:
        blockers.append("ab_preview_loudness_delta_exceeds_tolerance")
    if match.get("matched") is False:
        blockers.append("ab_preview_loudness_match_reported_false")

    return {
        "metrics_present": True,
        "matched": bool(flag and not blockers),
        "loudness_matched_flag": flag,
        "method": str(match.get("method", "")),
        "original_rms": safe_float(match.get("original_rms"), 0.0),
        "final_rms_before_match": safe_float(match.get("final_rms_before_match"), 0.0),
        "final_rms_after_match": after_rms,
        "target_rms": target_rms,
        "applied_gain_db": safe_float(match.get("applied_gain_db"), 0.0),
        "delta_db_after_match": delta_db,
        "tolerance_db": LOUDNESS_TOLERANCE_DB,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def _render_manifest_paths(output_dir: Path) -> set[str]:
    manifest = _load_json(output_dir / "export/final_render_manifest.json")
    paths: set[str] = set()
    for item in manifest.get("renders", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("format") == "wav" and item.get("created"):
            path = str(item.get("path", ""))
            if path:
                paths.add(str(_resolve_path(path, output_dir)))
    return paths


def _template(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "automix-ab-preview-review-manifest-template-v1",
        "source_original": manifest.get("source_original", ""),
        "source_final": manifest.get("source_final", ""),
        "preview_output_path": manifest.get("output_path", ""),
        "loudness_matched_reviewed": False,
        "human_reviewed": False,
        "review_decision": "pending",
        "reviewer": "",
        "notes": "",
        "limits": [
            "Do not mark human_reviewed true without actual matched-loudness listening.",
            "This review is not final export approval.",
            "If the preview sounds worse at matched loudness, keep the export blocked.",
        ],
    }


def build_ab_preview_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    manifest_path: Path | None = None,
    allow_legacy_loudness_flag: bool = False,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    manifest_file = Path(manifest_path) if manifest_path else output_dir / DEFAULT_MANIFEST_REL_PATH
    manifest = _load_json(manifest_file)
    blockers: list[str] = []
    warnings: list[str] = []

    if not manifest_file.exists() or not manifest:
        blockers.append("final_ab_preview_manifest_missing_or_invalid")
    elif manifest.get("schema") != "automix-final-ab-preview-v1":
        blockers.append("final_ab_preview_manifest_schema_invalid")

    if not bool(manifest.get("created", False)):
        blockers.append("ab_preview_not_created")
    manifest_warnings = [str(item) for item in manifest.get("warnings", []) or []]
    if manifest_warnings:
        blockers.append("ab_preview_manifest_has_warnings")
        warnings.extend(f"manifest:{item}" for item in manifest_warnings)

    original = _wav_status(str(manifest.get("source_original", "") or ""), output_dir, "source_original")
    final = _wav_status(str(manifest.get("source_final", "") or ""), output_dir, "source_final")
    preview = _wav_status(str(manifest.get("output_path", "") or ""), output_dir, "preview_output")
    for status in (original, final, preview):
        if not status.get("valid_wav", False):
            blockers.extend(str(item) for item in status.get("failures", []))

    if original.get("path") and final.get("path") and original.get("path") == final.get("path"):
        blockers.append("ab_preview_original_and_final_sources_match")

    render_paths = _render_manifest_paths(output_dir)
    if render_paths:
        if final.get("path") not in render_paths:
            blockers.append("ab_preview_final_not_in_render_manifest")
    else:
        warnings.append("final_render_manifest_missing_ab_link_unverified")

    segment_status = _segment_status(manifest)
    loudness_status = _loudness_status(manifest, allow_legacy_loudness_flag=allow_legacy_loudness_flag)
    blockers.extend(segment_status.get("blockers", []))
    blockers.extend(loudness_status.get("blockers", []))
    warnings.extend(segment_status.get("warnings", []))
    warnings.extend(loudness_status.get("warnings", []))

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    ready = not blockers
    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template(manifest))
    gate = {
        "schema": AB_PREVIEW_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_file),
        "ready_for_human_ab_review": ready,
        "ready_for_final_approval_request": ready,
        "human_ab_review_recorded": False,
        "manifest_summary": {
            "created": bool(manifest.get("created", False)),
            "loudness_matched": bool(manifest.get("loudness_matched", False)),
            "source_original": manifest.get("source_original", ""),
            "source_final": manifest.get("source_final", ""),
            "output_path": manifest.get("output_path", ""),
            "warnings": manifest_warnings,
        },
        "audio_status": {
            "source_original": original,
            "source_final": final,
            "preview_output": preview,
        },
        "segment_status": segment_status,
        "loudness_match_status": loudness_status,
        "render_manifest_link": {
            "render_manifest_wav_paths_total": len(render_paths),
            "source_final_in_render_manifest": bool(render_paths and final.get("path") in render_paths),
        },
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates A/B preview evidence only; it does not approve audio.",
            "Loudness-match evidence must include measured RMS match data unless legacy mode is explicitly allowed.",
            "Human listening review and final approval remain separate gates.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_ab_preview_evidence_report(gate, output_dir)
    write_ab_preview_review_request(gate, output_dir)
    return gate


def write_ab_preview_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    loudness = gate.get("loudness_match_status", {})
    render = gate.get("render_manifest_link", {})
    lines = [
        "# A/B Preview Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for human A/B review: `{gate.get('ready_for_human_ab_review')}`",
        f"- Ready for final approval request: `{gate.get('ready_for_final_approval_request')}`",
        f"- Human A/B review recorded: `{gate.get('human_ab_review_recorded')}`",
        f"- Loudness metrics present: `{loudness.get('metrics_present')}`",
        f"- Loudness delta after match: `{loudness.get('delta_db_after_match')}`",
        f"- Tolerance dB: `{loudness.get('tolerance_db')}`",
        f"- Final source linked to render manifest: `{render.get('source_final_in_render_manifest')}`",
        "",
        "This gate does not approve audio. It only checks that the A/B preview evidence is reviewable.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Audio Files", ""])
    for name, item in gate.get("audio_status", {}).items():
        lines.append(f"- `{name}` path=`{item.get('path')}` valid_wav=`{item.get('valid_wav')}` failures=`{item.get('failures', [])}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_ab_preview_review_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# A/B Preview Review Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
    ]
    if gate.get("ready_for_human_ab_review"):
        lines.extend(
            [
                "The preview evidence is technically reviewable. Human listening is still required.",
                "",
                "Required operator check:",
                "",
                "- Listen to the original/final A/B preview at matched loudness.",
                "- Confirm the final source is better or acceptable at equal loudness.",
                "- Record the decision before final approval.",
            ]
        )
    else:
        lines.extend(["The A/B preview is not ready for review. Resolve these blockers first:", ""])
        lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
