from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


SOURCE_HANDOFF_SCHEMA = "automix-source-handoff-readiness-v1"

AUDIT_REL_PATH = Path("eval_reports/source_handoff_readiness.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/source_handoff_readiness.md")
HANDOFF_REQUEST_REL_PATH = Path("review/source_stem_handoff_request.md")


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _first_media_path(track: dict[str, Any]) -> str:
    for path in track.get("media_paths", []):
        if str(path).strip():
            return str(path)
    return str(track.get("analysis_audio_path", "") or "")


def _file_status(path_text: str) -> dict[str, Any]:
    if not path_text:
        return {"path": "", "exists": False, "size_bytes": 0}
    path = Path(path_text)
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }


def _stem_request(track: dict[str, Any]) -> dict[str, Any]:
    path = _first_media_path(track)
    return {
        "track_name": track.get("track_name", ""),
        "track_index": track.get("index"),
        "role": track.get("role", ""),
        "source_classification": track.get("source_classification", ""),
        "stem_category": track.get("stem_category", "isolated_stem_required"),
        "recommended_next_action": track.get("recommended_next_action", "provide_isolated_stems"),
        "current_source": _file_status(path),
        "current_source_is_processing_target": False,
        "requested_files": _requested_files_for_track(track),
        "why_required": [
            "Current source is not accepted for automatic vocal/pitch/recovery processing.",
            "Full-mix or reference-like sources require isolated stems or manual review.",
        ],
        "acceptance_criteria": [
            "provided as WAV 24-bit/48 kHz or documented equivalent",
            "track role and processing level are labeled",
            "source is reviewed before any safe-draft processing",
            "reference/full-mix material remains reference-only unless explicitly accepted as a draft source",
        ],
    }


def _requested_files_for_track(track: dict[str, Any]) -> list[dict[str, Any]]:
    category = str(track.get("stem_category", "isolated_stem_required"))
    role = str(track.get("role", ""))
    if "instrumental" in category or role == "instrumental_bus":
        return [
            {
                "label": "instrumental_or_music_bus_stem",
                "preferred_processing": "dry or lightly processed",
                "notes": "Needed to evaluate vocal-seat carving without treating a full mix as a vocal source.",
            },
            {
                "label": "separate_lead_vocal_stem_if_available",
                "preferred_processing": "dry preferred",
                "notes": "Useful for level-matched A/B and vocal-first balance validation.",
            },
        ]
    return [
        {
            "label": "isolated_lead_vocal_stem",
            "preferred_processing": "dry preferred",
            "notes": "Needed before vocal recovery, pitch, or artifact-suppression drafts.",
        },
        {
            "label": "separate_backing_or_adlib_stems_if_available",
            "preferred_processing": "dry preferred",
            "notes": "Support layers must not replace the male lead by default.",
        },
    ]


def _manual_review_item(track: dict[str, Any]) -> dict[str, Any]:
    path = _first_media_path(track)
    return {
        "track_name": track.get("track_name", ""),
        "track_index": track.get("index"),
        "role": track.get("role", ""),
        "source_classification": track.get("source_classification", "unknown"),
        "recommended_next_action": track.get("recommended_next_action", "analyze_manually"),
        "current_source": _file_status(path),
        "automatic_processing_allowed": False,
        "review_reason": track.get("warnings", []) or ["unknown_source_skipped"],
    }


def _accepted_source_summary(final_export_state: dict[str, Any], project_state: dict[str, Any]) -> dict[str, Any]:
    selected = str(final_export_state.get("selected_export_source", "") or "")
    accepted_sources = [str(item) for item in project_state.get("accepted_sources", []) if str(item).strip()]
    selected_status = _file_status(selected)
    return {
        "safe_to_export": bool(final_export_state.get("safe_to_export", False)),
        "selected_export_source": selected_status,
        "selected_export_stage": final_export_state.get("selected_export_stage", ""),
        "accepted_sources": [_file_status(item) for item in accepted_sources],
        "blocked_reasons": final_export_state.get("blocked_reasons", []),
        "accepted_export_source_present": bool(selected and selected_status.get("exists")),
    }


def build_source_handoff_readiness(
    *,
    project_name: str,
    output_dir: Path,
    source_safety_path: Path | None = None,
    final_export_state_path: Path | None = None,
    project_state_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    source_safety_path = Path(source_safety_path or output_dir / "eval_reports" / "real_project_source_safety_map.json")
    final_export_state_path = Path(final_export_state_path or output_dir / "export" / "final_export_state.json")
    project_state_path = Path(project_state_path or output_dir / "export" / "project_state_manifest.json")
    source_map = _load_json(source_safety_path) or {}
    final_export_state = _load_json(final_export_state_path) or {}
    project_state = _load_json(project_state_path) or {}

    stem_requests = [_stem_request(track) for track in source_map.get("stem_required_tracks", [])]
    manual_review_items = [_manual_review_item(track) for track in source_map.get("unknown_tracks", [])]
    safe_candidates = [_manual_review_item(track) for track in source_map.get("safe_vocal_candidates", [])]
    accepted = _accepted_source_summary(final_export_state, project_state)
    source_files_present = sum(1 for item in stem_requests + manual_review_items + safe_candidates if item.get("current_source", {}).get("exists"))
    source_files_total = len(stem_requests) + len(manual_review_items) + len(safe_candidates)

    blockers: list[str] = []
    if stem_requests:
        blockers.append(f"stem_requests_open:{len(stem_requests)}")
    if source_map.get("summary", {}).get("full_mix_unsafe_tracks", 0):
        blockers.append(f"full_mix_unsafe_tracks:{source_map.get('summary', {}).get('full_mix_unsafe_tracks', 0)}")
    if not accepted.get("accepted_export_source_present"):
        blockers.append("accepted_export_source_missing")
    missing_current_sources = [item["track_name"] for item in stem_requests + manual_review_items + safe_candidates if not item.get("current_source", {}).get("exists")]
    blockers.extend(f"current_source_file_missing:{name}" for name in missing_current_sources)

    warnings: list[str] = []
    if manual_review_items:
        warnings.append(f"manual_review_required_tracks:{len(manual_review_items)}")
    if source_files_present:
        warnings.append("current_source_file_presence_is_not_acceptance")

    readiness = {
        "schema": SOURCE_HANDOFF_SCHEMA,
        "project_name": project_name or source_map.get("project_name", ""),
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_safety_path": str(source_safety_path),
        "final_export_state_path": str(final_export_state_path),
        "project_state_path": str(project_state_path),
        "source_summary": source_map.get("summary", {}),
        "accepted_source_summary": accepted,
        "stem_requests": stem_requests,
        "manual_review_items": manual_review_items,
        "safe_vocal_candidates": safe_candidates,
        "summary": {
            "stem_requests_total": len(stem_requests),
            "manual_review_tracks_total": len(manual_review_items),
            "safe_vocal_candidates_total": len(safe_candidates),
            "source_files_present_total": source_files_present,
            "source_files_total": source_files_total,
            "accepted_export_source_present": bool(accepted.get("accepted_export_source_present")),
            "automatic_processing_ready": False,
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This report does not analyze, render, modify, or approve audio.",
            "Current source files being present does not make them accepted export sources.",
            "Full-mix/reference material stays reference-only until a human review explicitly accepts a draft source.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, readiness)
    write_source_handoff_readiness_report(readiness, output_dir)
    write_source_stem_handoff_request(readiness, output_dir)
    return readiness


def write_source_handoff_readiness_report(readiness: dict[str, Any], output_dir: Path) -> Path:
    summary = readiness.get("summary", {})
    lines = [
        "# Source Handoff Readiness",
        "",
        f"- Project: `{readiness.get('project_name')}`",
        f"- Created UTC: `{readiness.get('created_at')}`",
        f"- Stem requests: `{summary.get('stem_requests_total', 0)}`",
        f"- Manual review tracks: `{summary.get('manual_review_tracks_total', 0)}`",
        f"- Source files present: `{summary.get('source_files_present_total', 0)}/{summary.get('source_files_total', 0)}`",
        f"- Accepted export source present: `{summary.get('accepted_export_source_present', False)}`",
        f"- Automatic processing ready: `{summary.get('automatic_processing_ready', False)}`",
        "",
        "This is a handoff/readiness report only. It does not approve or process audio.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in readiness.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in readiness.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Stem Requests", ""])
    if not readiness.get("stem_requests"):
        lines.append("- none")
    for item in readiness.get("stem_requests", []):
        source = item.get("current_source", {})
        lines.extend(
            [
                f"### {item.get('track_name')}",
                "",
                f"- Role: `{item.get('role')}`",
                f"- Source classification: `{item.get('source_classification')}`",
                f"- Stem category: `{item.get('stem_category')}`",
                f"- Current source exists: `{source.get('exists')}`",
                f"- Current source path: `{source.get('path')}`",
                "- Requested files:",
            ]
        )
        for request in item.get("requested_files", []):
            lines.append(f"  - `{request.get('label')}`: {request.get('notes')}")
        lines.append("")
    lines.extend(["", "## Manual Review Tracks", ""])
    if not readiness.get("manual_review_items"):
        lines.append("- none")
    for item in readiness.get("manual_review_items", []):
        source = item.get("current_source", {})
        lines.append(f"- `{item.get('track_name')}` role=`{item.get('role')}` source=`{item.get('source_classification')}` exists=`{source.get('exists')}`")
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_source_stem_handoff_request(readiness: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Source And Stem Handoff Request",
        "",
        f"- Project: `{readiness.get('project_name')}`",
        "- Preferred format: `WAV 24-bit/48 kHz`",
        "- Preferred processing: `dry or lightly processed; wet copies are reference-only`",
        "",
        "This request does not approve current audio for final delivery.",
        "",
    ]
    if not readiness.get("stem_requests"):
        lines.append("No mandatory stem requests are open.")
    for item in readiness.get("stem_requests", []):
        lines.extend([f"## {item.get('track_name')}", ""])
        lines.append(f"- Current source classification: `{item.get('source_classification')}`")
        lines.append(f"- Requested stem category: `{item.get('stem_category')}`")
        for request in item.get("requested_files", []):
            lines.append(f"- Requested file: `{request.get('label')}`")
            lines.append(f"  Preferred processing: `{request.get('preferred_processing')}`")
            lines.append(f"  Notes: {request.get('notes')}")
        lines.append("")
    if readiness.get("manual_review_items"):
        lines.extend(["## Manual Review", ""])
        for item in readiness.get("manual_review_items", []):
            lines.append(f"- `{item.get('track_name')}` should stay skipped until role/source is reviewed.")
    path = Path(output_dir) / HANDOFF_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
