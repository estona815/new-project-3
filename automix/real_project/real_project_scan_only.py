from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import analyze_source, read_wav
from automix.mastering.premaster_safety_analyzer import analyze_premaster_safety
from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator
from automix.pitch.pitch_safety_gate import evaluate_pitch_safety, input_from_reports
from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json
from automix.plugins.plugin_inventory_audit import audit_plugin_inventory, write_plugin_capability_report
from automix.real_project.read_only_project_guard import (
    build_read_only_guard_report,
    snapshot_project_state,
)
from automix.reference.reference_intake import build_reference_manifest
from automix.vocal_placement.vocal_placement_analyzer import analyze_vocal_placement
from automix.vocal_recovery.vocal_recovery_analyzer import analyze_vocal_recovery


ALLOWED_NEXT_MODES = {
    "run_prompt41_validation",
    "validate_plugin_mappings",
    "provide_isolated_stems",
    "scan_only_again",
    "safe_draft_recovery_only",
    "safe_draft_no_pitch",
    "safe_draft_full_pipeline",
    "manual_mix_required",
}

FINAL_RECOMMENDATIONS = {
    "safe_draft_recovery_only": "safe_to_run_recovery_draft_only",
    "safe_draft_no_pitch": "safe_to_run_safe_draft_no_pitch",
    "safe_draft_full_pipeline": "safe_to_run_safe_draft_full_pipeline",
    "provide_isolated_stems": "provide_stems_first",
    "validate_plugin_mappings": "validate_plugin_mappings_first",
    "run_prompt41_validation": "run_prompt41_first",
    "manual_mix_required": "manual_mix_required",
    "scan_only_again": "manual_mix_required",
}

STAGE_REQUIRED_PLUGINS = {
    "vocal_recovery": ["validated EQ/dynamic EQ or JSFX artifact guard adapter"],
    "pitch_correction": ["validated pitch correction adapter"],
    "vocal_placement": ["validated EQ/dynamics/utility adapter"],
    "reference_matching": ["validated EQ/dynamics/utility adapter"],
    "premaster": ["validated EQ/dynamics/limiter adapter"],
    "final_export": [],
}


def _fx_name(fx: Any) -> str:
    if isinstance(fx, dict):
        return str(fx.get("name") or fx.get("detected_name") or fx.get("display_name") or "")
    text = str(fx or "").strip()
    if '"' in text:
        parts = text.split('"')
        if len(parts) >= 2:
            return parts[1]
    return text


def _project_inventory_from_context(context: dict[str, Any]) -> dict[str, Any]:
    tracks = []
    detected: dict[str, dict[str, Any]] = {}
    for track in context.get("track_list", []) or []:
        fx_entries = []
        for fx in track.get("fx", []) or []:
            name = _fx_name(fx)
            if not name:
                continue
            entry = {"name": name, "confidence": 0.90, "existing_on_track": True}
            fx_entries.append(entry)
            detected.setdefault(name.lower(), {"name": name, "confidence": 0.90, "existing_on_track": True})
        tracks.append({"track_index": track.get("track_index"), "name": track.get("name"), "fx": fx_entries})
    return {
        "schema": "automix-real-project-derived-plugin-inventory-v1",
        "scan_date_utc": now_utc(),
        "reaper": {"version": context.get("reaper_version", "unknown"), "project_name": context.get("project_name", "project")},
        "tracks": tracks,
        "detected_plugins": list(detected.values()),
        "insertable_plugins": [],
        "missing_recommended_plugins": [],
        "warnings": ["derived_from_project_fx_chain_read_only"],
    }


def _num(value: Any, default: float = 0.0) -> float:
    return safe_float(value, default)


def _clamp01(value: Any) -> float:
    return max(0.0, min(1.0, _num(value)))


def _tokens(track: dict[str, Any]) -> str:
    return f"{track.get('name', '')} {track.get('role', '')}".lower().replace("_", " ")


def infer_track_role(track: dict[str, Any]) -> tuple[str, float]:
    text = _tokens(track)
    role = str(track.get("role", "")).lower()
    if role in {
        "lead_vocal",
        "backing_vocal",
        "vocal_double",
        "adlib",
        "vocal_bus",
        "instrumental_bus",
        "drum_bus",
        "bass",
        "guitar",
        "piano",
        "synth",
        "fx",
        "reverb_send",
        "delay_send",
        "full_mix_reference",
        "master_related",
        "unknown",
    }:
        return role, 0.88
    if "master" in text or "premaster" in text:
        return "master_related", 0.85
    if "full mix" in text or "reference" in text or "ref " in text or text.startswith("ref"):
        return "full_mix_reference", 0.86
    if "lead" in text and ("vocal" in text or "vox" in text):
        return "lead_vocal", 0.86
    if ("back" in text or "background" in text) and ("vocal" in text or "vox" in text or "double" in text or "support" in text):
        return "backing_vocal", 0.82
    if "double" in text and ("vocal" in text or "vox" in text or "support" in text):
        return "vocal_double", 0.80
    if "adlib" in text or "ad lib" in text:
        return "adlib", 0.80
    if "vocal bus" in text or "vox bus" in text:
        return "vocal_bus", 0.82
    if "instrumental" in text or "music bus" in text or "beat" in text:
        return "instrumental_bus", 0.80
    if "drum" in text or "kick" in text or "snare" in text:
        return "drum_bus", 0.75
    if "bass" in text or "808" in text:
        return "bass", 0.74
    if "guitar" in text:
        return "guitar", 0.74
    if "piano" in text or "keys" in text:
        return "piano", 0.72
    if "synth" in text or "pad" in text or "melody" in text:
        return "synth", 0.70
    if "reverb" in text:
        return "reverb_send", 0.76
    if "delay" in text:
        return "delay_send", 0.76
    if "fx" in text or "sfx" in text:
        return "fx", 0.68
    if "vocal" in text or "vox" in text:
        return "lead_vocal", 0.62
    return "unknown", 0.35


def _media_paths(track: dict[str, Any], project_path: Path) -> list[Path]:
    paths = []
    for raw in track.get("media_paths", []) or []:
        path = Path(str(raw).strip().strip('"')).expanduser()
        if not path.is_absolute() and project_path:
            path = project_path.parent / path
        paths.append(path)
    return paths


def _first_audio(track: dict[str, Any], project_path: Path) -> tuple[Any | None, str, list[str]]:
    warnings: list[str] = []
    for path in _media_paths(track, project_path):
        if path.exists() and path.suffix.lower() == ".wav":
            try:
                return read_wav(path, max_seconds=30.0), str(path), warnings
            except Exception as exc:  # pragma: no cover - defensive real-project boundary
                warnings.append(f"audio_read_failed:{path.name}:{type(exc).__name__}")
                return None, str(path), warnings
        if path.suffix.lower() == ".wav":
            warnings.append(f"audio_file_missing:{path}")
    return None, "", warnings


def _heuristic_source(track: dict[str, Any], role: str) -> tuple[dict[str, Any], dict[str, Any]]:
    text = _tokens(track)
    source = "unknown"
    confidence = 0.35
    full_mix = 0.10
    vocal = 0.20
    source_sep = 0.0
    already_mixed = 0.0
    already_tuned = 0.0
    ai_artifact = 0.0
    baked_reverb = 0.0

    if role in {"full_mix_reference", "instrumental_bus"} or "full mix" in text or "reference" in text:
        source = "full_mix"
        confidence = 0.78
        full_mix = 0.82
        already_mixed = 0.70
        vocal = 0.10 if role == "instrumental_bus" else 0.25
    elif role in {"lead_vocal", "backing_vocal", "vocal_double", "adlib", "vocal_bus"}:
        source = "raw_vocal"
        confidence = 0.52
        vocal = 0.72
        if any(word in text for word in ("ai", "suno", "tuned", "autotune", "auto tune", "processed", "cleaned")):
            source = "ai_vocal_stem"
            confidence = 0.68
            already_tuned = 0.78 if "tuned" in text or "autotune" in text else 0.55
            already_mixed = 0.58
            ai_artifact = 0.58
        if any(word in text for word in ("separated", "split", "uvr", "demucs", "rx", "watery")):
            source = "source_separated_vocal"
            confidence = 0.70
            source_sep = 0.72
            ai_artifact = max(ai_artifact, 0.55)
    elif role in {"drum_bus", "bass", "guitar", "piano", "synth", "fx", "reverb_send", "delay_send", "master_related"}:
        source = "unknown"
        confidence = 0.45
        full_mix = 0.30 if role == "master_related" else 0.18

    risk = "unsafe"
    if source == "raw_vocal":
        risk = "low"
    elif source in {"ai_vocal_stem", "source_separated_vocal"}:
        risk = "high"
    elif source == "full_mix":
        risk = "unsafe"

    classification = {
        "schema": "automix-source-classification-v1",
        "scan_date_utc": now_utc(),
        "track_name": track.get("name", ""),
        "classification": source,
        "confidence": confidence,
        "full_mix_likelihood": full_mix,
        "vocal_stem_likelihood": vocal,
        "source_separated_likelihood": source_sep,
        "already_mixed_score": already_mixed,
        "already_tuned_score": already_tuned,
        "baked_reverb_score": baked_reverb,
        "compression_limited_score": already_mixed,
        "ai_artifact_score": ai_artifact,
        "pitch_correction_risk": risk,
        "recommendation": "provide_isolated_vocal_stem" if source == "full_mix" else "scan_only_review",
        "metrics": {"source": "track_name_heuristic_no_audio"},
    }
    pitch = {
        "schema": "automix-pitch-analysis-v1",
        "scan_date_utc": classification["scan_date_utc"],
        "track_name": track.get("name", ""),
        "source_classification": source,
        "monophonic_pitch_confidence": 0.72 if source == "raw_vocal" else 0.30,
        "key_confidence": 0.50 if source == "raw_vocal" else 0.25,
        "scale_confidence": 0.50 if source == "raw_vocal" else 0.25,
        "scale_key_confidence": 0.50 if source == "raw_vocal" else 0.25,
        "polyphonic_contamination_score": full_mix,
        "already_tuned_score": already_tuned,
        "pitch_issue_benefit": 0.35,
        "pitch_correction_risk": risk,
    }
    return classification, pitch


def _analyze_source_for_track(track: dict[str, Any], role: str, project_path: Path) -> tuple[dict[str, Any], dict[str, Any], Any | None, str, list[str]]:
    audio, audio_path, warnings = _first_audio(track, project_path)
    if audio is not None:
        try:
            classification, pitch = analyze_source(audio, str(track.get("name", "")))
            return classification, pitch, audio, audio_path, warnings
        except Exception as exc:  # pragma: no cover - defensive real-project boundary
            warnings.append(f"source_analysis_failed:{type(exc).__name__}")
    classification, pitch = _heuristic_source(track, role)
    return classification, pitch, audio, audio_path, warnings


def _pitch_gate(classification: dict[str, Any], pitch: dict[str, Any], plugin_mapping_confidence: float) -> dict[str, Any]:
    gate_input = input_from_reports(
        classification,
        pitch,
        {"mapping_confidence": plugin_mapping_confidence},
        available_semantic_controls={},
        user_goal="default_conservative",
    )
    return evaluate_pitch_safety(gate_input)


def _plugin_mapping_confidence(plugin_audit: dict[str, Any], capability_hint: str = "pitch") -> float:
    best = 0.0
    for plugin in plugin_audit.get("plugins_detected", []):
        if plugin.get("safe_for_automix"):
            caps = " ".join(plugin.get("capabilities", []) or []) + " " + str(plugin.get("family", ""))
            if capability_hint in caps.lower() or capability_hint == "any":
                best = max(best, _num(plugin.get("confidence"), 0.90))
    return best


def build_track_audit(
    *,
    project_name: str,
    project_path: Path,
    context: dict[str, Any],
    plugin_audit: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    tracks = []
    pitch_confidence = _plugin_mapping_confidence(plugin_audit, "pitch")
    for track in context.get("track_list", []):
        role, role_confidence = infer_track_role(track)
        classification, pitch, audio, audio_path, warnings = _analyze_source_for_track(track, role, project_path)
        gate = _pitch_gate(classification, pitch, pitch_confidence)
        recovery = analyze_vocal_recovery(audio, str(track.get("name", "")), str(track.get("track_guid", "")), classification)
        placement = analyze_vocal_placement(
            audio if role in {"lead_vocal", "backing_vocal", "vocal_double", "adlib", "vocal_bus"} else None,
            None,
            track_name=str(track.get("name", "")),
            track_guid=str(track.get("track_guid", "")),
            role=role,
            source_report=classification,
        )

        source_class = str(classification.get("classification", "unknown"))
        full_mix = _clamp01(classification.get("full_mix_likelihood"))
        vocal_likelihood = _clamp01(classification.get("vocal_stem_likelihood"))
        instrumental_likelihood = 0.88 if role in {"instrumental_bus", "drum_bus", "bass", "guitar", "piano", "synth"} else max(0.0, full_mix - vocal_likelihood * 0.4)
        source_sep = _clamp01(classification.get("source_separated_likelihood"))
        already_tuned = _clamp01(classification.get("already_tuned_score"))
        already_mixed = _clamp01(classification.get("already_mixed_score"))
        recommended = "analyze_manually"
        if source_class == "full_mix" or full_mix > 0.65:
            recommended = "provide_isolated_stems"
            warnings.append("full_mix_unsafe_for_pitch_correction")
        elif source_class == "unknown":
            recommended = "analyze_manually"
            warnings.append("unknown_source_skipped")
        elif source_sep > 0.55:
            recommended = "provide_isolated_stems"
            warnings.append("source_separated_vocal_high_risk")
        elif already_tuned > 0.70:
            recommended = "skip_pitch_correction_or_manual_micro_review"
            warnings.append("already_tuned_ai_style_vocal_high_risk")
        elif gate.get("decision") == "plugin_mapping_required":
            recommended = "validate_plugin_mappings_first"
            warnings.append("pitch_plugin_mapping_required")
        elif gate.get("eligible"):
            recommended = "pitch_triage_eligible"

        tracks.append(
            {
                "index": int(track.get("track_index", len(tracks) + 1)),
                "track_name": str(track.get("name", f"Track {len(tracks) + 1}")),
                "track_guid": str(track.get("track_guid", "")),
                "folder_depth": int(track.get("folder_depth", 0)),
                "role": role,
                "role_confidence": round(role_confidence, 6),
                "media_items": int(track.get("media_items", 0)),
                "media_paths": [str(path) for path in _media_paths(track, project_path)],
                "analysis_audio_path": audio_path,
                "fx_count": int(track.get("fx_count", 0)),
                "send_count": int(track.get("send_count", 0)),
                "receive_count": int(track.get("receive_count", 0)),
                "vocal_likelihood": round(vocal_likelihood, 6),
                "instrumental_likelihood": round(_clamp01(instrumental_likelihood), 6),
                "full_mix_likelihood": round(full_mix, 6),
                "source_classification": source_class,
                "source_confidence": round(_clamp01(classification.get("confidence")), 6),
                "already_mixed_score": round(already_mixed, 6),
                "already_tuned_score": round(already_tuned, 6),
                "source_separated_likelihood": round(source_sep, 6),
                "pitch_risk": str(gate.get("risk", classification.get("pitch_correction_risk", "unknown"))),
                "pitch_gate": gate,
                "recovery_risk": str(recovery.get("recovery_risk", "unknown")),
                "recovery_recommended_mode": str(recovery.get("recommended_recovery_mode", "unknown")),
                "placement_relevance": str(placement.get("recommended_placement_mode", "unknown")),
                "recommended_next_action": recommended,
                "warnings": sorted(set(warnings + list(recovery.get("warnings", [])) + list(placement.get("warnings", [])))),
            }
        )

    audit = {
        "schema": "automix-real-project-track-audit-v1",
        "project_name": project_name,
        "project_path": str(project_path),
        "scan_time": now_utc(),
        "total_tracks": len(tracks),
        "tracks": tracks,
    }
    write_json(output_dir / "analysis_reports" / "real_project_track_audit.json", audit)
    return audit


def build_source_safety_map(*, project_name: str, track_audit: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    safe_vocals = []
    high_risk = []
    stem_required = []
    unknown = []
    warnings: list[str] = []
    for track in track_audit.get("tracks", []):
        source = track.get("source_classification")
        vocal_like = track.get("vocal_likelihood", 0.0) > 0.50 or track.get("role") in {"lead_vocal", "backing_vocal", "vocal_double", "adlib", "vocal_bus"}
        full_mix = track.get("full_mix_likelihood", 0.0) > 0.65 or source == "full_mix"
        source_sep = track.get("source_separated_likelihood", 0.0) > 0.55
        tuned = track.get("already_tuned_score", 0.0) > 0.70
        if full_mix:
            high_risk.append(track)
            stem_required.append({**track, "stem_category": "isolated_lead_vocal_required" if vocal_like else "instrumental_bus_required"})
        elif source_sep:
            high_risk.append(track)
            stem_required.append({**track, "stem_category": "dry_vocal_preferred"})
        elif tuned:
            high_risk.append(track)
        elif source == "unknown":
            unknown.append(track)
        elif vocal_like:
            safe_vocals.append(track)
    if unknown:
        warnings.append("unknown_tracks_are_not_eligible_for_automatic_processing")
    source_map = {
        "schema": "automix-real-project-source-safety-map-v1",
        "project_name": project_name,
        "summary": {
            "safe_vocal_candidates": len(safe_vocals),
            "ai_or_already_processed_vocals": sum(1 for track in high_risk if track.get("already_tuned_score", 0.0) > 0.70 or track.get("source_classification") == "ai_vocal_stem"),
            "source_separated_vocals": sum(1 for track in high_risk if track.get("source_separated_likelihood", 0.0) > 0.55),
            "full_mix_unsafe_tracks": sum(1 for track in high_risk if track.get("full_mix_likelihood", 0.0) > 0.65 or track.get("source_classification") == "full_mix"),
            "stem_required_tracks": len(stem_required),
            "unknown_tracks": len(unknown),
        },
        "safe_vocal_candidates": safe_vocals,
        "high_risk_tracks": high_risk,
        "stem_required_tracks": stem_required,
        "unknown_tracks": unknown,
        "warnings": warnings,
    }
    write_json(output_dir / "eval_reports" / "real_project_source_safety_map.json", source_map)
    return source_map


def build_plugin_readiness(*, project_name: str, plugin_audit: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    detected = plugin_audit.get("plugins_detected", [])
    safe = [item for item in detected if item.get("safe_for_automix")]
    provisional = [item for item in detected if item.get("mapping_status") == "mapped_unvalidated"]
    unsafe = plugin_audit.get("unsafe_or_unmapped_plugins", [])
    commercial = [item for item in detected if item.get("kind") == "third_party"]
    stock = [item.get("name") for item in detected if item.get("kind") == "stock"]
    jsfx = [item.get("name") for item in detected if item.get("kind") == "jsfx"]
    required = sorted({plugin for plugins in STAGE_REQUIRED_PLUGINS.values() for plugin in plugins})
    missing = []
    if not safe:
        missing.extend(required)
    readiness = {
        "schema": "automix-real-project-plugin-readiness-v1",
        "project_name": project_name,
        "safe_adapters_count": len(safe),
        "provisional_adapters_count": len(provisional),
        "unsafe_unmapped_plugins_count": len(unsafe),
        "commercial_plugins_detected": [item.get("name") for item in commercial],
        "commercial_plugins_safe": [item.get("name") for item in commercial if item.get("safe_for_automix")],
        "stock_fallbacks_available": stock,
        "jsfx_fallbacks_available": jsfx,
        "required_mappings_for_next_stage": required,
        "missing_or_unsafe_mappings": sorted(set(missing + [item.get("name", "unknown") for item in unsafe])),
        "can_run_recovery_drafts_safely": bool(safe),
        "can_run_pitch_correction_safely": _plugin_mapping_confidence(plugin_audit, "pitch") >= 0.85,
        "can_run_vocal_placement_safely": bool(safe),
        "can_run_premaster_draft_safely": bool(safe),
        "third_party_plugins_detected_and_validated": bool([item for item in commercial if item.get("safe_for_automix")]),
        "stock_or_jsfx_fallbacks_enough": bool(safe and (stock or jsfx)),
        "safe_draft_plugin_ready": bool(safe),
        "warnings": ["no_validated_safe_plugin_adapters"] if not safe else [],
    }
    write_json(output_dir / "eval_reports" / "real_project_plugin_readiness.json", readiness)
    return readiness


def _proposal(track: dict[str, Any], stage: str, proposed: bool, blocked: bool, blockers: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "track_name": track.get("track_name", "__project__"),
        "track_index": track.get("index"),
        "stage": stage,
        "proposed": proposed,
        "draft_required": proposed and stage not in {"final_export", "reference_matching"},
        "would_modify_project": False,
        "selected_profile": {
            "vocal_recovery": "conservative_ai_vocal_cleanup",
            "pitch_correction": "conservative_pitch_triage_only",
            "vocal_placement": "vocal_forward_dry_run",
            "reference_matching": "target_profile_scan_only",
            "premaster": "premaster_safety_scan_only",
            "final_export": "blocked_scan_only",
        }.get(stage, "scan_only"),
        "required_plugins": STAGE_REQUIRED_PLUGINS.get(stage, []),
        "safe_plugins_available": False,
        "blocked": blocked,
        "blockers": blockers,
        "warnings": warnings or [],
    }


def build_dry_run_proposals(
    *,
    project_name: str,
    track_audit: dict[str, Any],
    source_map: dict[str, Any],
    plugin_readiness: dict[str, Any],
    target_profile: str,
    references: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []
    plugin_blocker = [] if plugin_readiness.get("safe_draft_plugin_ready") else ["validated_plugin_mapping_required"]
    for track in track_audit.get("tracks", []):
        source = track.get("source_classification")
        vocal_like = track.get("vocal_likelihood", 0.0) > 0.50 or track.get("role") in {"lead_vocal", "backing_vocal", "vocal_double", "adlib", "vocal_bus"}
        full_mix = source == "full_mix" or track.get("full_mix_likelihood", 0.0) > 0.65
        source_sep = track.get("source_separated_likelihood", 0.0) > 0.55
        already_tuned = track.get("already_tuned_score", 0.0) > 0.70
        unknown = source == "unknown"
        if vocal_like or full_mix:
            recovery_blockers = []
            if full_mix:
                recovery_blockers.append("full_mix_requires_isolated_stem")
            if unknown:
                recovery_blockers.append("unknown_source_skipped")
            recovery_blockers.extend(plugin_blocker)
            proposals.append(_proposal(track, "vocal_recovery", vocal_like and not full_mix, bool(recovery_blockers), recovery_blockers, track.get("warnings", [])))
            pitch_blockers = []
            if full_mix:
                pitch_blockers.append("full_mix_pitch_blocked")
            if source_sep:
                pitch_blockers.append("source_separated_high_risk")
            if already_tuned:
                pitch_blockers.append("already_tuned_skip_strong_correction")
            if unknown:
                pitch_blockers.append("unknown_source_skipped")
            if track.get("pitch_gate", {}).get("decision") == "plugin_mapping_required":
                pitch_blockers.append("pitch_plugin_mapping_required")
            pitch_blockers.extend(plugin_blocker)
            proposals.append(_proposal(track, "pitch_correction", vocal_like and not pitch_blockers, bool(pitch_blockers), sorted(set(pitch_blockers)), track.get("warnings", [])))
            placement_blockers = list(plugin_blocker)
            if full_mix:
                placement_blockers.append("full_mix_not_safe_for_vocal_placement_automation")
            proposals.append(_proposal(track, "vocal_placement", vocal_like and not full_mix, bool(placement_blockers), sorted(set(placement_blockers)), track.get("warnings", [])))
    project_entry = {"track_name": "__project__", "index": None}
    proposals.append(_proposal(project_entry, "reference_matching", bool(target_profile or references), bool(plugin_blocker), list(plugin_blocker), []))
    proposals.append(_proposal(project_entry, "premaster", True, bool(plugin_blocker), list(plugin_blocker), ["accepted_mix_required_before_premaster_draft"]))
    proposals.append(_proposal(project_entry, "final_export", False, True, ["scan_only_mode_blocks_final_export", "explicit_human_approval_required"], []))
    for proposal in proposals:
        if proposal["stage"] in {"vocal_recovery", "vocal_placement", "reference_matching", "premaster"}:
            proposal["safe_plugins_available"] = bool(plugin_readiness.get("safe_draft_plugin_ready"))
        elif proposal["stage"] == "pitch_correction":
            proposal["safe_plugins_available"] = bool(plugin_readiness.get("can_run_pitch_correction_safely"))
    data = {
        "schema": "automix-real-project-dry-run-chain-proposals-v1",
        "project_name": project_name,
        "proposals": proposals,
        "warnings": ["dry_run_informational_only_no_fx_inserted"],
    }
    write_json(output_dir / "chain_plans" / "real_project_dry_run_chain_proposals.json", data)
    return data


def write_stem_request_plan(*, project_name: str, source_map: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Real Project Stem Request Plan",
        "",
        f"- Project: `{project_name}`",
        "- Preferred file format: `WAV 24-bit/48 kHz`",
        "- Preferred processing level: `dry or lightly processed`",
        "",
    ]
    stem_tracks = source_map.get("stem_required_tracks", [])
    if not stem_tracks:
        lines.append("No mandatory stem requests were detected during scan-only audit.")
    for track in stem_tracks:
        category = track.get("stem_category", "isolated_lead_vocal_required")
        lines.extend(
            [
                f"## {track.get('track_name')}",
                "",
                f"- Detected issue: `{track.get('source_classification')}` / full-mix `{track.get('full_mix_likelihood')}` / source-separated `{track.get('source_separated_likelihood')}`",
                "- Why unsafe: Automatic vocal pitch correction or recovery is unsafe on this track because it appears to be a full mix, heavily source-separated vocal, or already processed AI-style stem.",
                f"- Requested stem type: `{category}`",
                "- Preferred file format: `WAV 24-bit/48 kHz`",
                "- Preferred processing level: `dry or lightly processed`",
                "- Dry or wet preferred: `dry preferred; wet acceptable for reference only`",
                "- Backing/adlibs: `separate backing vocals/adlibs if possible`",
                "- Current track as reference: `yes, reference only`",
                "",
            ]
        )
    path = output_dir / "eval_reports" / "real_project_stem_request_plan.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _prompt41_status(output_dir: Path, check: bool = True) -> dict[str, Any]:
    json_path = output_dir / "validation_reports" / "prompt41_validation_summary.json"
    md_path = output_dir / "validation_reports" / "prompt41_validation_summary.md"
    if not check:
        return {"status": "unchecked", "risk": "elevated", "json_exists": json_path.exists(), "md_exists": md_path.exists(), "warnings": ["prompt41_check_disabled"]}
    if not json_path.exists() or not md_path.exists():
        return {"status": "missing", "risk": "elevated", "json_exists": json_path.exists(), "md_exists": md_path.exists(), "warnings": ["prompt41_validation_not_found"]}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "missing", "risk": "elevated", "json_exists": True, "md_exists": md_path.exists(), "warnings": ["prompt41_validation_json_unreadable"]}
    raw = str(data.get("final_validation_status") or data.get("status") or "").upper()
    if "PASS" in raw:
        status = "PASS"
    elif "PARTIAL" in raw:
        status = "PARTIAL"
    elif "FAIL" in raw:
        status = "FAIL"
    else:
        status = "unknown"
    return {"status": status, "risk": "normal" if status in {"PASS", "PARTIAL"} else "elevated", "json_exists": True, "md_exists": md_path.exists(), "warnings": [] if status in {"PASS", "PARTIAL"} else ["prompt41_validation_not_passed"]}


def build_safe_draft_readiness(
    *,
    project_name: str,
    prompt41: dict[str, Any],
    guard_report: dict[str, Any],
    source_map: dict[str, Any],
    plugin_readiness: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    summary = source_map.get("summary", {})
    total_known = max(1, summary.get("safe_vocal_candidates", 0) + summary.get("stem_required_tracks", 0) + summary.get("unknown_tracks", 0))
    reports = [
        output_dir / "analysis_reports" / "real_project_track_audit.json",
        output_dir / "eval_reports" / "real_project_source_safety_map.json",
        output_dir / "eval_reports" / "real_project_plugin_readiness.json",
        output_dir / "chain_plans" / "real_project_dry_run_chain_proposals.json",
        output_dir / "eval_reports" / "real_project_stem_request_plan.md",
    ]
    prompt41_score = {"PASS": 1.0, "PARTIAL": 0.70, "missing": 0.25, "unchecked": 0.25, "FAIL": 0.0}.get(prompt41.get("status"), 0.35)
    plugin_score = 1.0 if plugin_readiness.get("safe_draft_plugin_ready") else 0.0
    source_score = max(0.0, 1.0 - (summary.get("full_mix_unsafe_tracks", 0) + summary.get("unknown_tracks", 0)) / total_known)
    stem_score = max(0.0, 1.0 - summary.get("stem_required_tracks", 0) / total_known)
    breakdown = {
        "prompt41_validation": round(prompt41_score, 6),
        "read_only_guard": 1.0 if guard_report.get("safe") else 0.0,
        "plugin_mapping_readiness": plugin_score,
        "source_quality_readiness": round(source_score, 6),
        "stem_availability": round(stem_score, 6),
        "report_completeness": round(sum(1 for path in reports if path.exists()) / len(reports), 6),
        "rollback_preparedness": 1.0 if (output_dir / "rollback" / "global_rollback_registry.json").exists() else 0.0,
    }
    score = round(sum(breakdown.values()) / len(breakdown), 6)
    blockers = []
    warnings = list(prompt41.get("warnings", []))
    if prompt41.get("status") in {"FAIL", "missing", "unchecked"}:
        blockers.append("prompt41_validation_required_before_safe_draft")
    if not guard_report.get("safe"):
        blockers.append("read_only_guard_failed")
    if not plugin_readiness.get("safe_draft_plugin_ready"):
        blockers.append("validated_plugin_mapping_required")
    if summary.get("stem_required_tracks", 0) > 0:
        blockers.append("isolated_stems_required")
    if summary.get("unknown_tracks", 0) > 0:
        warnings.append("unknown_tracks_skipped")

    recommended = "scan_only_again"
    if not guard_report.get("safe"):
        recommended = "scan_only_again"
    elif prompt41.get("status") in {"FAIL", "missing", "unchecked"}:
        recommended = "run_prompt41_validation"
    elif not plugin_readiness.get("safe_draft_plugin_ready"):
        recommended = "validate_plugin_mappings"
    elif summary.get("stem_required_tracks", 0) > 0:
        recommended = "provide_isolated_stems"
    elif summary.get("safe_vocal_candidates", 0) > 0 and plugin_readiness.get("can_run_pitch_correction_safely"):
        recommended = "safe_draft_full_pipeline"
    elif summary.get("safe_vocal_candidates", 0) > 0:
        recommended = "safe_draft_no_pitch"
    elif summary.get("unknown_tracks", 0) > 0:
        recommended = "manual_mix_required"

    ready = not blockers and recommended in {"safe_draft_recovery_only", "safe_draft_no_pitch", "safe_draft_full_pipeline"} and score >= 0.80
    data = {
        "schema": "automix-real-project-safe-draft-readiness-v1",
        "project_name": project_name,
        "safe_draft_readiness_score": score,
        "ready": ready,
        "readiness_breakdown": breakdown,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommended_next_mode": recommended if recommended in ALLOWED_NEXT_MODES else "scan_only_again",
    }
    write_json(output_dir / "eval_reports" / "real_project_safe_draft_readiness.json", data)
    return data


def write_real_project_report(
    *,
    project_name: str,
    prompt41: dict[str, Any],
    guard_report: dict[str, Any],
    track_audit: dict[str, Any],
    source_map: dict[str, Any],
    plugin_readiness: dict[str, Any],
    proposals: dict[str, Any],
    readiness: dict[str, Any],
    target_profile: str,
    references: list[str],
    output_dir: Path,
) -> Path:
    final_recommendation = "scan_failed_do_not_proceed" if not guard_report.get("safe") else FINAL_RECOMMENDATIONS.get(readiness.get("recommended_next_mode"), "manual_mix_required")
    summary = source_map.get("summary", {})
    pitch_eligible = [p for p in proposals.get("proposals", []) if p.get("stage") == "pitch_correction" and p.get("proposed") and not p.get("blocked")]
    pitch_skipped = [p for p in proposals.get("proposals", []) if p.get("stage") == "pitch_correction" and p.get("blocked")]
    recovery_eligible = [p for p in proposals.get("proposals", []) if p.get("stage") == "vocal_recovery" and p.get("proposed") and not p.get("blocked")]
    recovery_blocked = [p for p in proposals.get("proposals", []) if p.get("stage") == "vocal_recovery" and p.get("blocked")]
    lines = [
        "# Real Project Scan-Only Audit Report",
        "",
        "## Summary",
        "",
        f"- Project: `{project_name}`",
        "- Mode: `real_project_scan_only`",
        f"- Read-only status: `{guard_report.get('safe')}`",
        f"- Prompt 41 validation status: `{prompt41.get('status')}`",
        f"- Safe-draft readiness: `{readiness.get('ready')}`",
        f"- Recommended next mode: `{readiness.get('recommended_next_mode')}`",
        "",
        "## Read-Only Guard",
        "",
        f"- Modified: `{guard_report.get('modified')}`",
        f"- Safe: `{guard_report.get('safe')}`",
        f"- Warnings: `{', '.join(guard_report.get('warnings', [])) or 'none'}`",
        "",
        "## Track Role Map",
        "",
        "| Track | Role | Confidence | Source Type | Vocal Likelihood | Full Mix Likelihood | Risk | Recommended Next Action |",
        "|---|---|---:|---|---:|---:|---|---|",
    ]
    for track in track_audit.get("tracks", []):
        lines.append(
            f"| `{track.get('track_name')}` | `{track.get('role')}` | {track.get('role_confidence')} | `{track.get('source_classification')}` | {track.get('vocal_likelihood')} | {track.get('full_mix_likelihood')} | `{track.get('pitch_risk')}` | `{track.get('recommended_next_action')}` |"
        )
    track_warnings = [(track.get("track_name"), track.get("warnings", [])) for track in track_audit.get("tracks", []) if track.get("warnings")]
    lines.extend(["", "## Track Warnings", ""])
    if not track_warnings:
        lines.append("- none")
    for name, warnings in track_warnings:
        lines.append(f"- `{name}`: `{', '.join(warnings[:6])}`")
    lines.extend(
        [
            "",
            "## Source Safety",
            "",
            f"- Safe vocal candidates: `{summary.get('safe_vocal_candidates', 0)}`",
            f"- AI/already processed vocals: `{summary.get('ai_or_already_processed_vocals', 0)}`",
            f"- Source-separated vocals: `{summary.get('source_separated_vocals', 0)}`",
            f"- Full-mix unsafe tracks: `{summary.get('full_mix_unsafe_tracks', 0)}`",
            f"- Stem-required tracks: `{summary.get('stem_required_tracks', 0)}`",
            f"- Unknown tracks: `{summary.get('unknown_tracks', 0)}`",
            "",
            "## Plugin Readiness",
            "",
            f"- Safe adapters: `{plugin_readiness.get('safe_adapters_count', 0)}`",
            f"- Provisional adapters: `{plugin_readiness.get('provisional_adapters_count', 0)}`",
            f"- Unsafe/unmapped: `{plugin_readiness.get('unsafe_unmapped_plugins_count', 0)}`",
            f"- Stock fallbacks: `{len(plugin_readiness.get('stock_fallbacks_available', []))}`",
            f"- JSFX fallbacks: `{len(plugin_readiness.get('jsfx_fallbacks_available', []))}`",
            f"- Missing mappings: `{len(plugin_readiness.get('missing_or_unsafe_mappings', []))}`",
            "",
            "## Pitch Correction Dry-Run",
            "",
            f"- Tracks eligible: `{len(pitch_eligible)}`",
            f"- Tracks skipped: `{len(pitch_skipped)}`",
            f"- Already tuned skipped: `{summary.get('ai_or_already_processed_vocals', 0)}`",
            f"- Full mix unsafe: `{summary.get('full_mix_unsafe_tracks', 0)}`",
            f"- Source-separated high risk: `{summary.get('source_separated_vocals', 0)}`",
            f"- Plugin mapping required: `{not plugin_readiness.get('can_run_pitch_correction_safely')}`",
            "- Manual tuning required: `true if pitch plugin mapping remains unsafe`",
            "",
            "## Vocal Recovery Dry-Run",
            "",
            f"- Tracks eligible: `{len(recovery_eligible)}`",
            f"- Tracks blocked: `{len(recovery_blocked)}`",
            "- Suggested profiles: `conservative_ai_vocal_cleanup`",
            f"- Stem required: `{summary.get('stem_required_tracks', 0)}`",
            "",
            "## Vocal Placement Dry-Run",
            "",
            f"- Lead vocal candidate: `{next((t.get('track_name') for t in track_audit.get('tracks', []) if t.get('role') == 'lead_vocal'), 'none')}`",
            f"- Instrumental bus candidate: `{next((t.get('track_name') for t in track_audit.get('tracks', []) if t.get('role') == 'instrumental_bus'), 'none')}`",
            "- Masking risk: `not fully measured unless track audio was available`",
            f"- Placement readiness: `{plugin_readiness.get('can_run_vocal_placement_safely')}`",
            "",
            "## Premaster Dry-Run",
            "",
            f"- Premaster readiness: `{plugin_readiness.get('can_run_premaster_draft_safely')}`",
            "- Loudness/peak measurement availability: `scan-only; source-dependent`",
            "- Translation check readiness: `blocked until accepted mix draft exists`",
            "- Warnings: `no premaster render created`",
            "",
            "## Reference / Target Profile",
            "",
            f"- Target profile: `{target_profile or 'not configured'}`",
            f"- References found: `{len(references)}`",
            "- Reference analysis status: `manifest-only unless WAV references were supplied`",
            f"- Safe adjustment readiness: `{plugin_readiness.get('safe_draft_plugin_ready')}`",
            "",
            "## Stem Request Plan",
            "",
            "- See `automix/eval_reports/real_project_stem_request_plan.md`.",
            "",
            "## Safe-Draft Readiness",
            "",
            f"- Score: `{readiness.get('safe_draft_readiness_score')}`",
            f"- Ready: `{readiness.get('ready')}`",
            f"- Blockers: `{', '.join(readiness.get('blockers', [])) or 'none'}`",
            f"- Warnings: `{', '.join(readiness.get('warnings', [])) or 'none'}`",
            "",
            "## Next Required Actions",
            "",
        ]
    )
    for action in readiness.get("blockers", []) or ["review_scan_only_reports"]:
        lines.append(f"- `{action}`")
    lines.extend(["", "## Final Recommendation", "", f"`{final_recommendation}`", ""])
    path = output_dir / "eval_reports" / "real_project_scan_only_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_real_project_scan_only(
    *,
    project_path: str | Path | None,
    target_profile: str = "",
    references: list[str] | None = None,
    reference_roles: list[str] | None = None,
    output_dir: str | Path = "automix",
    check_prompt41: bool = True,
    strict_read_only: bool = True,
    dry_run: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    project = Path(project_path).expanduser() if project_path else Path("")
    refs = list(references or [])
    roles = list(reference_roles or [])
    prompt41 = _prompt41_status(output, check_prompt41)
    before = snapshot_project_state(project if strict_read_only else None)

    orchestrator = AutoMixOrchestrator(
        {
            "mode": "real_project_scan_only",
            "project_path": str(project) if project_path else "",
            "output_dir": str(output),
            "target_profile": target_profile,
            "references": refs,
            "reference_roles": roles,
            "dry_run": True if dry_run else True,
            "strict_read_only": True if strict_read_only else False,
            "allow_recovery_drafts": False,
            "allow_placement_drafts": False,
            "allow_reference_match_draft": False,
            "allow_premaster_draft": False,
            "allow_final_export": False,
        }
    )
    manifest = orchestrator.run()
    project_inventory = _project_inventory_from_context(orchestrator.context)
    if project_inventory.get("detected_plugins"):
        orchestrator.plugin_audit = audit_plugin_inventory(project_inventory, output_dir=output)
        write_plugin_capability_report(orchestrator.plugin_audit, output)
    after = snapshot_project_state(project if strict_read_only else None)
    guard = build_read_only_guard_report(
        project_name=orchestrator.project_name,
        output_dir=output,
        before_snapshot=before,
        after_snapshot=after,
        warnings=[] if strict_read_only else ["strict_read_only_disabled"],
    )

    reference_pairs = [(Path(path), roles[idx] if idx < len(roles) else "primary_reference") for idx, path in enumerate(refs)]
    reference_warnings: list[str] = []
    try:
        build_reference_manifest(project_name=orchestrator.project_name, references=reference_pairs, target_profile=target_profile or None, output_dir=output)
    except ValueError as exc:
        reference_warnings.append(str(exc))
    track_audit = build_track_audit(
        project_name=orchestrator.project_name,
        project_path=project,
        context=orchestrator.context,
        plugin_audit=orchestrator.plugin_audit,
        output_dir=output,
    )
    source_map = build_source_safety_map(project_name=orchestrator.project_name, track_audit=track_audit, output_dir=output)
    plugin_readiness = build_plugin_readiness(project_name=orchestrator.project_name, plugin_audit=orchestrator.plugin_audit, output_dir=output)
    proposals = build_dry_run_proposals(
        project_name=orchestrator.project_name,
        track_audit=track_audit,
        source_map=source_map,
        plugin_readiness=plugin_readiness,
        target_profile=target_profile,
        references=refs,
        output_dir=output,
    )
    stem_plan = write_stem_request_plan(project_name=orchestrator.project_name, source_map=source_map, output_dir=output)
    readiness = build_safe_draft_readiness(
        project_name=orchestrator.project_name,
        prompt41=prompt41,
        guard_report=guard,
        source_map=source_map,
        plugin_readiness=plugin_readiness,
        output_dir=output,
    )
    premaster_scan = analyze_premaster_safety(None, project_name=orchestrator.project_name, source_mix_path="", input_stage="scan_only")
    write_json(output / "analysis_reports" / "real_project_premaster_dry_run.json", premaster_scan)
    report = write_real_project_report(
        project_name=orchestrator.project_name,
        prompt41=prompt41,
        guard_report=guard,
        track_audit=track_audit,
        source_map=source_map,
        plugin_readiness=plugin_readiness,
        proposals=proposals,
        readiness=readiness,
        target_profile=target_profile,
        references=refs,
        output_dir=output,
    )

    status = "real_project_scan_only_complete"
    if not guard.get("safe"):
        status = "read_only_guard_failed"
    summary = {
        "status": status,
        "project_name": orchestrator.project_name,
        "project_path": str(project) if project_path else "",
        "mode": "real_project_scan_only",
        "dry_run": True,
        "strict_read_only": strict_read_only,
        "prompt41_validation_status": prompt41.get("status"),
        "real_project_pilot_risk": prompt41.get("risk"),
        "read_only_guard_safe": guard.get("safe"),
        "project_modified": guard.get("modified"),
        "tracks_scanned": track_audit.get("total_tracks", 0),
        "source_safety_summary": source_map.get("summary", {}),
        "plugin_readiness_summary": {
            "safe_adapters": plugin_readiness.get("safe_adapters_count", 0),
            "provisional_adapters": plugin_readiness.get("provisional_adapters_count", 0),
            "unsafe_unmapped": plugin_readiness.get("unsafe_unmapped_plugins_count", 0),
            "safe_draft_plugin_ready": plugin_readiness.get("safe_draft_plugin_ready", False),
        },
        "dry_run_proposals_created": len(proposals.get("proposals", [])),
        "stem_request_plan": str(stem_plan),
        "safe_draft_readiness_score": readiness.get("safe_draft_readiness_score"),
        "safe_draft_ready": readiness.get("ready"),
        "recommended_next_mode": readiness.get("recommended_next_mode"),
        "manifest": str(output / "orchestrator" / "automix_orchestration_manifest.json"),
        "reports": {
            "read_only_guard": str(output / "real_project" / "read_only_guard_report.json"),
            "track_audit": str(output / "analysis_reports" / "real_project_track_audit.json"),
            "source_safety_map": str(output / "eval_reports" / "real_project_source_safety_map.json"),
            "plugin_readiness": str(output / "eval_reports" / "real_project_plugin_readiness.json"),
            "dry_run_proposals": str(output / "chain_plans" / "real_project_dry_run_chain_proposals.json"),
            "readiness": str(output / "eval_reports" / "real_project_safe_draft_readiness.json"),
            "report": str(report),
        },
        "warnings": sorted(set(prompt41.get("warnings", []) + guard.get("warnings", []) + readiness.get("warnings", []) + reference_warnings)),
    }
    if verbose:
        summary["orchestrator_global_status"] = manifest.get("global_status")
        summary["next_required_actions"] = manifest.get("next_required_actions", [])
    write_json(output / "real_project" / "real_project_scan_only_summary.json", summary)
    return summary
