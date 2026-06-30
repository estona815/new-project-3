from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automix.analyze_ai_pitch_source import analyze_source, read_wav, safe_filename, write_json
from automix.pitch.conservative_pitch_profiles import resolve_pitch_profile
from automix.pitch.pitch_safety_gate import evaluate_pitch_safety, input_from_reports
from automix.vocal_recovery.recovery_iteration_engine import build_recovery_iteration_history
from automix.vocal_recovery.vocal_recovery_analyzer import analyze_vocal_recovery, missing_recovery_eval_metrics
from automix.vocal_recovery.vocal_recovery_policy import (
    build_recovery_chain_plan,
    evaluate_recovery_policy,
    write_recovery_artifacts,
)
from automix.vocal_placement.placement_iteration_engine import build_placement_iteration_history
from automix.vocal_placement.vocal_placement_analyzer import analyze_vocal_placement, missing_placement_eval_metrics
from automix.vocal_placement.vocal_placement_policy import (
    build_placement_chain_plan,
    evaluate_placement_policy,
    write_placement_artifacts,
)


TRACK_ROLES = {
    "lead_vocal",
    "backing_vocal",
    "vocal_double",
    "adlib",
    "vocal_bus",
    "instrumental_bus",
    "drums",
    "bass",
    "guitar",
    "piano",
    "synth",
    "fx",
    "full_mix_reference",
    "master",
    "unknown",
}

BATCH_MODES = {
    "conservative_scan_only",
    "conservative_apply_drafts",
    "report_only",
    "no_pitch_correction",
    "force_review_all_vocals",
    "experimental_full_mix_drafts",
}

NEVER_PITCH_ROLES = {
    "master",
    "instrumental_bus",
    "drums",
    "bass",
    "guitar",
    "piano",
    "synth",
    "fx",
    "full_mix_reference",
}

VOCAL_LIKE_ROLES = {"lead_vocal", "backing_vocal", "vocal_double", "adlib", "vocal_bus"}

ROLE_CORRECTION_MULTIPLIERS = {
    "lead_vocal": 1.0,
    "backing_vocal": 0.70,
    "vocal_double": 0.60,
    "adlib": 0.50,
    "vocal_bus": 0.0,
    "unknown": 0.0,
}

ACTION_COUNTS = {
    "skip",
    "micro_draft",
    "light_draft",
    "manual_tuning",
    "stem_required",
    "full_mix_unsafe",
    "plugin_mapping_required",
    "needs_human_review",
}


@dataclass
class TrackCandidate:
    track_name: str
    track_guid: str = ""
    media_item_names: list[str] = field(default_factory=list)
    source_audio_path: str | None = None
    existing_fx: list[str] = field(default_factory=list)
    routing: dict[str, Any] = field(default_factory=dict)
    folder_depth: int = 0
    source_classification: dict[str, Any] | None = None
    pitch_analysis: dict[str, Any] | None = None


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_adapter_status(path: Path | None) -> dict[str, Any]:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "plugin_name": None,
        "available": False,
        "mapping_confidence": 0.0,
        "semantic_controls": {},
        "reason": "No high-confidence adapter mapping supplied for batch triage.",
    }


def parse_reaper_project(project_path: Path) -> list[TrackCandidate]:
    if not project_path or not project_path.exists():
        return []
    text = project_path.read_text(encoding="utf-8", errors="ignore")
    chunks = re.split(r"\n(?=<TRACK\b)", text)
    tracks: list[TrackCandidate] = []
    for idx, chunk in enumerate(chunks):
        if "<TRACK" not in chunk:
            continue
        name_match = re.search(r'^\s*NAME\s+"([^"]*)"', chunk, re.MULTILINE)
        guid_match = re.search(r'^\s*TRACKID\s+(\{[^}]+\})', chunk, re.MULTILINE)
        if not guid_match:
            guid_match = re.search(r'(\{[A-Fa-f0-9-]{20,}\})', chunk)
        file_names = re.findall(r'^\s*FILE\s+"([^"]+)"', chunk, re.MULTILINE)
        item_names = re.findall(r'^\s*NAME\s+"([^"]*)"', chunk, re.MULTILINE)
        track_name = name_match.group(1) if name_match else f"Track {idx + 1}"
        tracks.append(
            TrackCandidate(
                track_name=track_name,
                track_guid=guid_match.group(1) if guid_match else f"rpp-track-{idx + 1}",
                media_item_names=[name for name in item_names if name != track_name] + file_names,
                source_audio_path=file_names[0] if file_names else None,
            )
        )
    return tracks


def load_track_manifest(path: Path | None) -> list[TrackCandidate]:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("tracks", data if isinstance(data, list) else [])
    tracks = []
    for idx, item in enumerate(items):
        tracks.append(
            TrackCandidate(
                track_name=item.get("track_name") or item.get("name") or f"Track {idx + 1}",
                track_guid=item.get("track_guid") or item.get("guid") or f"manifest-track-{idx + 1}",
                media_item_names=item.get("media_item_names", []),
                source_audio_path=item.get("source_audio_path"),
                existing_fx=item.get("existing_fx", []),
                routing=item.get("routing", {}),
                folder_depth=int(item.get("folder_depth", 0)),
                source_classification=item.get("source_classification"),
                pitch_analysis=item.get("pitch_analysis"),
            )
        )
    return tracks


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def detect_track_role(track: TrackCandidate) -> dict[str, Any]:
    haystack = normalize(" ".join([track.track_name, *track.media_item_names, *track.existing_fx]))
    warnings: list[str] = []
    role = "unknown"
    confidence = 0.35

    def has(*tokens: str) -> bool:
        return any(token in haystack for token in tokens)

    if has("master", "premaster", "pre master"):
        role, confidence = "master", 0.95
    elif has("full mix", "fullmix", "2track", "2 track", "reference", "ref mix", "mix ref"):
        role, confidence = "full_mix_reference", 0.92
    elif has("drum", "kick", "snare", "perc", "hi hat", "hihat"):
        role, confidence = "drums", 0.86
    elif has("bass", "808", "sub"):
        role, confidence = "bass", 0.84
    elif has("guitar", "gtr"):
        role, confidence = "guitar", 0.82
    elif has("piano", "keys", "key "):
        role, confidence = "piano", 0.80
    elif has("synth", "pad", "lead synth", "arp"):
        role, confidence = "synth", 0.78
    elif has("reverb", "delay", "fx", "sfx", "riser"):
        role, confidence = "fx", 0.78
    elif has("inst bus", "instrumental bus", "music bus", "beat bus", "instrument bus"):
        role, confidence = "instrumental_bus", 0.88
    elif has("vocal bus", "vox bus", "voc bus", "all vocals"):
        role, confidence = "vocal_bus", 0.86
        warnings.append("vocal bus may contain layered or polyphonic vocals")
    elif has("adlib", "ad lib", "shout"):
        role, confidence = "adlib", 0.86
    elif has("double", "dbl", "stack"):
        role, confidence = "vocal_double", 0.84
    elif has("backing", "bgv", "harmony", "harmonies", "chorus vox"):
        role, confidence = "backing_vocal", 0.84
    elif has("lead vocal", "main vocal", "lead vox", "main vox", "vocal", "vox", "voice"):
        role, confidence = "lead_vocal", 0.82

    vocal_likelihood = {
        "lead_vocal": 0.92,
        "backing_vocal": 0.86,
        "vocal_double": 0.82,
        "adlib": 0.78,
        "vocal_bus": 0.65,
    }.get(role, 0.12 if role in NEVER_PITCH_ROLES else 0.35)
    instrumental_likelihood = 0.90 if role in NEVER_PITCH_ROLES - {"full_mix_reference", "master"} else 0.18
    full_mix_likelihood = 0.90 if role == "full_mix_reference" else 0.20
    pitch_eligible = role in {"lead_vocal", "backing_vocal", "vocal_double", "adlib"}
    if role in NEVER_PITCH_ROLES:
        pitch_eligible = False
    if role == "unknown":
        pitch_eligible = False
        warnings.append("unknown role is skipped unless explicitly approved")

    return {
        "track_name": track.track_name,
        "track_guid": track.track_guid,
        "role": role,
        "role_confidence": confidence,
        "vocal_likelihood": vocal_likelihood,
        "full_mix_likelihood": full_mix_likelihood,
        "instrumental_likelihood": instrumental_likelihood,
        "source_classification": None,
        "pitch_triage_eligible": pitch_eligible,
        "warnings": warnings,
    }


def default_reports_for_role(track: TrackCandidate, role_entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    role = role_entry["role"]
    classification = "unknown"
    risk = "unsafe"
    if role in NEVER_PITCH_ROLES:
        classification = "full_mix" if role in {"full_mix_reference", "master", "instrumental_bus"} else "unknown"
    elif role in VOCAL_LIKE_ROLES:
        classification = "mixed_vocal_stem" if role != "lead_vocal" else "unknown"
        risk = "medium" if role != "vocal_bus" else "high"

    source = {
        "schema": "automix-source-classification-v1",
        "scan_date_utc": now_utc(),
        "track_name": track.track_name,
        "classification": classification,
        "confidence": role_entry["role_confidence"] * 0.5,
        "full_mix_likelihood": role_entry["full_mix_likelihood"],
        "vocal_stem_likelihood": role_entry["vocal_likelihood"],
        "source_separated_likelihood": 0.20,
        "already_mixed_score": 0.50 if role in VOCAL_LIKE_ROLES else 0.20,
        "already_tuned_score": 0.35,
        "baked_reverb_score": 0.30,
        "compression_limited_score": 0.30,
        "ai_artifact_score": 0.20,
        "pitch_correction_risk": risk,
        "recommendation": "needs_human_review",
        "metrics": {},
    }
    pitch = {
        "schema": "automix-pitch-analysis-v1",
        "scan_date_utc": source["scan_date_utc"],
        "track_name": track.track_name,
        "source_classification": classification,
        "voiced_frame_ratio": 0.0,
        "monophonic_pitch_confidence": 0.0,
        "pitch_stability": 0.0,
        "note_confidence": 0.0,
        "scale_key_confidence": 0.0,
        "key_confidence": 0.0,
        "scale_confidence": 0.0,
        "octave_error_suspicion": 0.0,
        "vibrato_presence": 0.0,
        "pitch_jump_density": 0.0,
        "polyphonic_contamination_score": 0.70 if role in {"vocal_bus", "full_mix_reference", "instrumental_bus"} else 0.35,
        "already_tuned_score": source["already_tuned_score"],
        "pitch_correction_risk": risk,
    }
    return source, pitch


def reports_for_track(track: TrackCandidate, role_entry: dict[str, Any], project_path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if track.source_classification and track.pitch_analysis:
        return track.source_classification, track.pitch_analysis

    if track.source_audio_path:
        candidate = Path(track.source_audio_path)
        if project_path and not candidate.is_absolute():
            candidate = project_path.parent / candidate
        if candidate.exists() and candidate.suffix.lower() == ".wav":
            audio = read_wav(candidate)
            return analyze_source(audio, track.track_name)

    return default_reports_for_role(track, role_entry)


def audio_for_track(track: TrackCandidate, project_path: Path | None = None):
    if not track.source_audio_path:
        return None
    candidate = Path(track.source_audio_path)
    if project_path and not candidate.is_absolute():
        candidate = project_path.parent / candidate
    if candidate.exists() and candidate.suffix.lower() == ".wav":
        return read_wav(candidate)
    return None


def recovery_for_track(
    track: TrackCandidate,
    role_entry: dict[str, Any],
    source_report: dict[str, Any],
    *,
    output_dir: Path,
    adapter_status: dict[str, Any],
    project_path: Path | None,
) -> dict[str, Any]:
    if role_entry["role"] not in VOCAL_LIKE_ROLES:
        return {
            "track_name": track.track_name,
            "track_guid": track.track_guid,
            "role": role_entry["role"],
            "source_classification": source_report.get("classification", "unknown"),
            "recovery_risk": "not_applicable",
            "recovery_action": "skip",
            "selected_profile": "skip_recovery",
            "draft_required": False,
            "draft_created": False,
            "evaluation_status": "not_applicable",
            "pitch_allowed_after_recovery": False,
            "report_path": None,
            "reason_codes": ["NON_VOCAL_ROLE"],
        }

    audio = audio_for_track(track, project_path)
    analysis = analyze_vocal_recovery(audio, track.track_name, track.track_guid, source_report)
    decision = evaluate_recovery_policy(analysis)
    chain_plan = build_recovery_chain_plan(analysis, decision, adapter_status)
    eval_metrics = missing_recovery_eval_metrics(track.track_name) if decision["requires_ab_evaluation"] else None
    if eval_metrics:
        write_json(output_dir / "eval_reports" / f"{safe_filename(track.track_name)}_vocal_recovery_eval_metrics.json", eval_metrics)
    iteration_history = build_recovery_iteration_history(chain_plan.get("semantic_settings", {}), [eval_metrics] if eval_metrics else [])
    paths = write_recovery_artifacts(output_dir, analysis, decision, chain_plan, eval_metrics, iteration_history)
    return {
        "track_name": track.track_name,
        "track_guid": track.track_guid,
        "role": role_entry["role"],
        "source_classification": analysis["source_classification"],
        "recovery_risk": analysis["recovery_risk"],
        "recovery_action": decision["recovery_action"],
        "selected_profile": chain_plan["selected_profile"],
        "draft_required": decision["draft_required"],
        "draft_created": False,
        "draft_track_name": decision["draft_track_name"],
        "evaluation_status": "missing_renders" if eval_metrics else "not_required",
        "pitch_allowed_after_recovery": decision["pitch_allowed_after_recovery"],
        "report_path": str(paths["report"]),
        "analysis_path": str(paths["analysis"]),
        "chain_plan_path": str(paths["chain_plan"]),
        "rollback_path": str(paths["rollback"]),
        "reason_codes": decision["reason_codes"],
        "warnings": chain_plan.get("warnings", []),
    }


def target_context_for_placement(tracks: list[TrackCandidate], role_map: list[dict[str, Any]], current_track: TrackCandidate) -> dict[str, Any]:
    instrumental = None
    backing = []
    sends = []
    for track, role_entry in zip(tracks, role_map):
        role = role_entry["role"]
        if role == "instrumental_bus" and instrumental is None:
            instrumental = track.track_name
        elif role in {"backing_vocal", "vocal_double", "adlib"} and track.track_name != current_track.track_name:
            backing.append(track.track_name)
        elif role == "fx":
            sends.append(track.track_name)
    return {
        "lead_vocal": current_track.track_name,
        "instrumental_bus": instrumental,
        "backing_vocals": backing,
        "send_tracks": sends,
    }


def placement_for_track(
    track: TrackCandidate,
    role_entry: dict[str, Any],
    source_report: dict[str, Any],
    recovery_entry: dict[str, Any],
    pitch_entry: dict[str, Any],
    *,
    output_dir: Path,
    adapter_status: dict[str, Any],
    project_path: Path | None,
    target_context: dict[str, Any],
    instrumental_track: TrackCandidate | None,
) -> dict[str, Any]:
    if role_entry["role"] not in VOCAL_LIKE_ROLES:
        return {
            "track_name": track.track_name,
            "role": role_entry["role"],
            "source_classification": source_report.get("classification", "unknown"),
            "recovery_status": "not_applicable",
            "pitch_status": pitch_entry.get("recommended_action", "not_applicable"),
            "masking_risk": "not_applicable",
            "placement_action": "skip_placement",
            "draft_created": False,
            "evaluation_status": "not_applicable",
            "report_path": None,
            "reason_codes": ["NON_VOCAL_ROLE"],
        }

    vocal_audio = audio_for_track(track, project_path)
    instrumental_audio = audio_for_track(instrumental_track, project_path) if instrumental_track else None
    recovery_status = recovery_entry.get("evaluation_status", "not_required")
    if recovery_entry.get("recovery_action") == "skip":
        recovery_status = "no_recovery_needed"
    pitch_status = pitch_entry.get("recommended_action", "unknown")
    role_context = source_report.get("placement_context", {}) if isinstance(source_report.get("placement_context", {}), dict) else {}
    analysis = analyze_vocal_placement(
        vocal_audio,
        instrumental_audio,
        track_name=track.track_name,
        track_guid=track.track_guid,
        role=role_entry["role"],
        source_report=source_report,
        recovery_status=recovery_status,
        pitch_status=pitch_status,
        role_context=role_context,
    )
    decision = evaluate_placement_policy(analysis, target_context)
    chain_plan = build_placement_chain_plan(analysis, decision, target_context, adapter_status, output_dir=output_dir)
    eval_metrics = missing_placement_eval_metrics(track.track_name) if decision["requires_ab_evaluation"] else None
    if eval_metrics:
        write_json(output_dir / "eval_reports" / f"{safe_filename(track.track_name)}_vocal_placement_eval_metrics.json", eval_metrics)
    iteration_history = build_placement_iteration_history(chain_plan.get("semantic_settings", {}), [eval_metrics] if eval_metrics else [])
    paths = write_placement_artifacts(output_dir, analysis, decision, chain_plan, eval_metrics, iteration_history)
    return {
        "track_name": track.track_name,
        "role": role_entry["role"],
        "source_classification": analysis["source_classification"],
        "recovery_status": analysis["recovery_status"],
        "pitch_status": analysis["pitch_status"],
        "masking_risk": analysis["placement_risk"],
        "placement_action": decision["placement_action"],
        "selected_profile": chain_plan["selected_profile"],
        "draft_created": False,
        "draft_required": decision["draft_required"],
        "evaluation_status": "missing_renders" if eval_metrics else "not_required",
        "report_path": str(paths["report"]),
        "analysis_path": str(paths["analysis"]),
        "chain_plan_path": str(paths["chain_plan"]),
        "routing_plan_path": str(paths["routing_plan"]),
        "rollback_path": str(paths["rollback"]),
        "reason_codes": decision["reason_codes"],
        "warnings": chain_plan.get("warnings", []),
    }


def mode_to_gate_mode(mode: str, apply_drafts: bool, allow_experimental_full_mix: bool) -> str:
    if mode == "no_pitch_correction":
        return "no_pitch_correction"
    if allow_experimental_full_mix or mode == "experimental_full_mix_drafts":
        return "allow_full_mix_pitch_experiment"
    if apply_drafts or mode == "conservative_apply_drafts":
        return "allow_light_pitch_draft"
    return "default_conservative"


def recommended_action_from_gate(role: str, source: dict[str, Any], gate: dict[str, Any]) -> str:
    decision = gate["decision"]
    reasons = set(gate.get("reason_codes", []))
    if role in NEVER_PITCH_ROLES:
        return "full_mix_unsafe" if role == "full_mix_reference" else "skip"
    if "FULL_MIX_LIKELY" in reasons:
        return "stem_required" if source.get("full_mix_likelihood", 0.0) > 0.45 else "full_mix_unsafe"
    if "SOURCE_SEPARATED_HIGH" in reasons and not gate.get("eligible"):
        return "stem_required"
    if decision == "plugin_mapping_required":
        return "plugin_mapping_required"
    if decision == "manual_review_required":
        return "needs_human_review"
    if decision == "full_mix_unsafe":
        return "full_mix_unsafe"
    if decision == "apply_micro" and gate.get("eligible"):
        return "micro_draft"
    if decision == "apply_light" and gate.get("eligible"):
        return "light_draft"
    if decision == "skip":
        if "PITCH_CONFIDENCE_LOW" in reasons and role in VOCAL_LIKE_ROLES:
            return "manual_tuning"
        return "skip"
    return "needs_human_review"


def apply_role_multiplier(role: str, profile: dict[str, Any]) -> None:
    multiplier = ROLE_CORRECTION_MULTIPLIERS.get(role, 0.0)
    settings = profile.get("settings", {})
    for key in ("correction_amount", "depth", "dry_wet"):
        if key in settings and isinstance(settings[key], (int, float)):
            settings[key] = round(settings[key] * multiplier, 6)
    for item in profile.get("semantic_controls_to_write", {}).values():
        if isinstance(item, dict) and "value" in item and isinstance(item["value"], (int, float)):
            item["value"] = round(item["value"] * multiplier, 6)


def triage_track(
    track: TrackCandidate,
    role_entry: dict[str, Any],
    adapter_status: dict[str, Any],
    *,
    mode: str,
    apply_drafts: bool,
    allow_experimental_full_mix: bool,
    project_path: Path | None,
    source_report: dict[str, Any] | None = None,
    pitch_report: dict[str, Any] | None = None,
    recovery_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source_report is not None and pitch_report is not None:
        source, pitch = source_report, pitch_report
    else:
        source, pitch = reports_for_track(track, role_entry, project_path)
    role_entry["source_classification"] = source["classification"]
    gate_mode = mode_to_gate_mode(mode, apply_drafts, allow_experimental_full_mix)
    controls = adapter_status.get("semantic_controls", {})
    gate = evaluate_pitch_safety(
        input_from_reports(source, pitch, adapter_status, available_semantic_controls=controls, user_goal=gate_mode)
    )
    profile = resolve_pitch_profile(source["classification"], gate, controls)
    apply_role_multiplier(role_entry["role"], profile)

    if mode in {"conservative_scan_only", "report_only", "force_review_all_vocals"}:
        draft_created = False
    else:
        draft_created = bool(apply_drafts and gate["eligible"] and role_entry["role"] not in NEVER_PITCH_ROLES)

    action = recommended_action_from_gate(role_entry["role"], source, gate)
    if recovery_entry and role_entry["role"] in VOCAL_LIKE_ROLES and not recovery_entry.get("pitch_allowed_after_recovery", False):
        recovery_action = recovery_entry.get("recovery_action")
        if recovery_action == "stem_required":
            action = "stem_required"
        elif recovery_action in {"unsafe_to_process"}:
            action = "needs_human_review"
        elif recovery_action in {"minimal_cleanup_draft", "conservative_ai_vocal_cleanup_draft", "source_separated_rescue_draft"}:
            action = "needs_human_review"
        else:
            action = "needs_human_review"
    if mode == "no_pitch_correction":
        action = "skip"
    if mode == "force_review_all_vocals" and role_entry["role"] in VOCAL_LIKE_ROLES and action in {"micro_draft", "light_draft"}:
        action = "needs_human_review"
    if recovery_entry and not recovery_entry.get("pitch_allowed_after_recovery", False):
        draft_created = False

    warnings = list(role_entry.get("warnings", []))
    if source["classification"] == "full_mix":
        warnings.append("full mix or reference-like source is not tuned by default")
    if role_entry["role"] == "vocal_bus":
        warnings.append("vocal bus may be layered/polyphonic; prefer separate stems")
    if recovery_entry and role_entry["role"] in VOCAL_LIKE_ROLES:
        warnings.append(f"vocal recovery before pitch: {recovery_entry.get('recovery_action')}")
        if not recovery_entry.get("pitch_allowed_after_recovery", False):
            warnings.append("pitch correction blocked until vocal recovery is accepted or manually reviewed")
    if gate["reason_codes"]:
        warnings.extend(gate["reason_codes"])

    return {
        "track_name": track.track_name,
        "track_guid": track.track_guid,
        "role": role_entry["role"],
        "source_classification": source["classification"],
        "classification_confidence": source.get("confidence", 0.0),
        "already_mixed_score": source.get("already_mixed_score", 0.0),
        "already_tuned_score": source.get("already_tuned_score", 0.0),
        "baked_reverb_score": source.get("baked_reverb_score", 0.0),
        "compression_limited_score": source.get("compression_limited_score", 0.0),
        "full_mix_likelihood": source.get("full_mix_likelihood", 0.0),
        "source_separated_likelihood": source.get("source_separated_likelihood", 0.0),
        "pitch_confidence": pitch.get("monophonic_pitch_confidence", 0.0),
        "key_confidence": pitch.get("key_confidence", pitch.get("scale_key_confidence", 0.0)),
        "scale_confidence": pitch.get("scale_confidence", pitch.get("scale_key_confidence", 0.0)),
        "polyphonic_contamination_score": pitch.get("polyphonic_contamination_score", 0.0),
        "plugin_adapter_confidence": adapter_status.get("mapping_confidence", 0.0),
        "vocal_recovery_action": recovery_entry.get("recovery_action") if recovery_entry else None,
        "vocal_recovery_report": recovery_entry.get("report_path") if recovery_entry else None,
        "pitch_allowed_after_recovery": recovery_entry.get("pitch_allowed_after_recovery", role_entry["role"] not in VOCAL_LIKE_ROLES) if recovery_entry else role_entry["role"] not in VOCAL_LIKE_ROLES,
        "safety_gate_decision": gate["decision"],
        "risk": gate["risk"],
        "reason_codes": gate["reason_codes"],
        "recommended_action": action,
        "correction_profile": profile["profile"],
        "proposed_settings": profile["settings"],
        "semantic_controls_to_write": profile["semantic_controls_to_write"],
        "semantic_controls_skipped": profile["semantic_controls_skipped"],
        "draft_required": action in {"micro_draft", "light_draft"},
        "draft_created": draft_created,
        "draft_track_name": f"{track.track_name}_PITCH_DRAFT",
        "ab_eval_required": action in {"micro_draft", "light_draft"},
        "manual_approval_required": gate.get("requires_manual_approval", True),
        "warnings": sorted(set(warnings)),
        "safety_gate": gate,
    }


def stem_required_reason(triage: dict[str, Any]) -> bool:
    return triage["recommended_action"] in {"stem_required", "full_mix_unsafe"} or (
        triage["role"] == "vocal_bus" and triage["source_separated_likelihood"] > 0.45
    )


def write_stem_report(output_dir: Path, triage: dict[str, Any]) -> Path:
    path = output_dir / "eval_reports" / f"{safe_filename(triage['track_name'])}_stem_required_report.md"
    lines = [
        "# Stem Required Report",
        "",
        f"- Track: `{triage['track_name']}`",
        f"- Role: `{triage['role']}`",
        f"- Source classification: `{triage['source_classification']}`",
        f"- Full mix likelihood: `{triage['full_mix_likelihood']}`",
        f"- Source-separated likelihood: `{triage['source_separated_likelihood']}`",
        f"- Pitch confidence: `{triage['pitch_confidence']}`",
        "",
        "Automatic vocal pitch correction is unsafe on this source because it appears to contain full-mix or source-separated material. Provide an isolated lead vocal stem, preferably dry or lightly processed, with backing vocals and adlibs separated if possible.",
        "",
        "- Preferred stem type: isolated lead vocal stem",
        "- Mono or stereo: mono preferred for lead tuning; stereo acceptable if natural ambience is essential",
        "- Dry vocal preferred: yes",
        "- Wet vocal acceptable: only if lightly processed and not source-separated",
        "- Backing vocals separated: yes",
        "- Manual tuning better than automatic tuning: yes when pitch confidence is low or artifacts are high",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_matrix(project_name: str, role_map: list[dict[str, Any]], triages: list[dict[str, Any]], report_paths: dict[str, str]) -> dict[str, Any]:
    summary = {
        "total_tracks": len(role_map),
        "vocal_like_tracks": sum(1 for item in role_map if item["role"] in VOCAL_LIKE_ROLES),
        "pitch_skipped": 0,
        "micro_draft": 0,
        "light_draft": 0,
        "manual_tuning": 0,
        "stem_required": 0,
        "full_mix_unsafe": 0,
        "plugin_mapping_required": 0,
        "needs_human_review": 0,
    }
    decisions = []
    for triage in triages:
        action = triage["recommended_action"]
        if action == "skip":
            summary["pitch_skipped"] += 1
        elif action in summary:
            summary[action] += 1
        decisions.append(
            {
                "track_name": triage["track_name"],
                "role": triage["role"],
                "decision": action,
                "reason_codes": triage["reason_codes"],
                "risk": triage["risk"],
                "draft_track_name": triage["draft_track_name"] if triage["draft_required"] else None,
                "report_path": report_paths.get(triage["track_name"]),
            }
        )
    return {"project_name": project_name, "summary": summary, "track_decisions": decisions}


def build_recovery_matrix(project_name: str, role_map: list[dict[str, Any]], recovery_entries: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total_tracks": len(role_map),
        "vocal_like_tracks": sum(1 for item in role_map if item["role"] in VOCAL_LIKE_ROLES),
        "recovery_skipped": 0,
        "minimal_cleanup_draft": 0,
        "conservative_ai_vocal_cleanup_draft": 0,
        "source_separated_rescue_draft": 0,
        "stem_required": 0,
        "manual_review_required": 0,
        "unsafe_to_process": 0,
    }
    decisions = []
    for entry in recovery_entries:
        action = entry["recovery_action"]
        if action == "skip":
            summary["recovery_skipped"] += 1
        elif action in summary:
            summary[action] += 1
        decisions.append(
            {
                "track_name": entry["track_name"],
                "role": entry["role"],
                "source_type": entry["source_classification"],
                "artifact_risk": entry["recovery_risk"],
                "recovery_decision": action,
                "draft_created": entry["draft_created"],
                "evaluation_status": entry["evaluation_status"],
                "pitch_allowed_after_recovery": entry["pitch_allowed_after_recovery"],
                "report_path": entry.get("report_path"),
                "reason_codes": entry.get("reason_codes", []),
            }
        )
    return {"project_name": project_name, "summary": summary, "track_decisions": decisions}


def build_placement_matrix(project_name: str, role_map: list[dict[str, Any]], placement_entries: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total_tracks": len(role_map),
        "lead_vocal_tracks": sum(1 for item in role_map if item["role"] == "lead_vocal"),
        "placement_skipped": 0,
        "dynamic_space_creation_draft": 0,
        "sidechain_dynamic_eq_draft": 0,
        "ms_center_cleanup_draft": 0,
        "send_cleanup_draft": 0,
        "manual_mix_required": 0,
        "stem_required": 0,
    }
    decisions = []
    for entry in placement_entries:
        action = entry["placement_action"]
        if action == "skip_placement":
            summary["placement_skipped"] += 1
        elif action in summary:
            summary[action] += 1
        decisions.append(
            {
                "track_name": entry["track_name"],
                "role": entry["role"],
                "source_type": entry["source_classification"],
                "recovery_status": entry["recovery_status"],
                "pitch_status": entry["pitch_status"],
                "masking_risk": entry["masking_risk"],
                "placement_decision": action,
                "draft_created": entry["draft_created"],
                "evaluation_status": entry["evaluation_status"],
                "report_path": entry.get("report_path"),
                "reason_codes": entry.get("reason_codes", []),
            }
        )
    return {"project_name": project_name, "summary": summary, "track_decisions": decisions}


def build_render_plan(triages: list[dict[str, Any]], mode: str, apply_drafts: bool, force_review: bool = False) -> dict[str, Any]:
    tracks_to_render = []
    skipped = []
    for triage in triages:
        if triage["draft_created"] or (force_review and triage["recommended_action"] in {"micro_draft", "light_draft"}):
            tracks_to_render.append(
                {
                    "track_name": triage["track_name"],
                    "draft_track_name": triage["draft_track_name"],
                    "render_original": True,
                    "render_processed": True,
                    "render_loudness_matched": True,
                    "render_difference": True,
                    "priority": "high",
                    "reason": "pitch correction applied" if triage["draft_created"] else "review requested",
                }
            )
        else:
            skipped.append({"track_name": triage["track_name"], "reason": f"pitch correction {triage['recommended_action']}"})
    return {"render_required": bool(tracks_to_render), "tracks_to_render": tracks_to_render, "tracks_skipped_from_render": skipped}


def build_rollback_index(project_name: str, triages: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    entries = []
    for triage in triages:
        if triage["draft_created"]:
            rollback_file = output_dir / "rollback" / f"{safe_filename(triage['track_name'])}_pitch_rollback.json"
            entries.append(
                {
                    "original_track_name": triage["track_name"],
                    "original_track_guid": triage["track_guid"],
                    "draft_track_name": triage["draft_track_name"],
                    "draft_track_guid": None,
                    "rollback_file": str(rollback_file),
                    "draft_creation_status": "pending_reaper_runtime",
                }
            )
    return {"project_name": project_name, "created_at": now_utc(), "draft_tracks": entries}


def safety_score(triages: list[dict[str, Any]], render_plan: dict[str, Any]) -> dict[str, Any]:
    risk_values = {"low": 0.15, "medium": 0.45, "high": 0.75, "unsafe": 1.0}
    unsafe_count = sum(1 for item in triages if item["risk"] == "unsafe")
    stem_count = sum(1 for item in triages if item["recommended_action"] == "stem_required")
    draft_count = sum(1 for item in triages if item["draft_created"])
    plugin_issues = sum(1 for item in triages if item["recommended_action"] == "plugin_mapping_required")
    correct_skips = sum(1 for item in triages if item["recommended_action"] in {"skip", "stem_required", "full_mix_unsafe"} and item["risk"] in {"high", "unsafe"})
    average_risk = sum(risk_values.get(item["risk"], 1.0) for item in triages) / max(1, len(triages))
    missing_eval_penalty = draft_count if render_plan["render_required"] and not render_plan["tracks_to_render"] else 0
    score = 1.0 - average_risk * 0.35 - plugin_issues * 0.05 - missing_eval_penalty * 0.10 + correct_skips * 0.03
    score = max(0.0, min(1.0, score))
    if draft_count == 0 and stem_count == 0 and plugin_issues == 0:
        recommendation = "accept_no_pitch"
    elif stem_count:
        recommendation = "stems_required"
    elif plugin_issues:
        recommendation = "plugin_mapping_required"
    elif draft_count:
        recommendation = "review_before_accept"
    else:
        recommendation = "manual_tuning_required" if any(item["recommended_action"] == "manual_tuning" for item in triages) else "accept_no_pitch"
    return {
        "project_pitch_safety_score": round(score, 4),
        "average_risk": round(average_risk, 4),
        "unsafe_track_count": unsafe_count,
        "stem_required_count": stem_count,
        "draft_created_count": draft_count,
        "evaluation_pass_count": 0,
        "evaluation_fail_count": draft_count,
        "recommendation": recommendation,
    }


def write_batch_report(
    output_dir: Path,
    matrix: dict[str, Any],
    triages: list[dict[str, Any]],
    score: dict[str, Any],
    render_plan: dict[str, Any],
    recovery_matrix: dict[str, Any] | None = None,
    placement_matrix: dict[str, Any] | None = None,
) -> Path:
    path = output_dir / "eval_reports" / "project_pitch_batch_report.md"
    summary = matrix["summary"]
    lines = [
        "# Project Pitch Triage Report",
        "",
        "## Summary",
        "",
        f"- Total tracks: `{summary['total_tracks']}`",
        f"- Vocal-like tracks: `{summary['vocal_like_tracks']}`",
        f"- Draft pitch corrections created: `{score['draft_created_count']}`",
        f"- Tracks skipped: `{summary['pitch_skipped']}`",
        f"- Tracks requiring isolated stems: `{summary['stem_required']}`",
        f"- Tracks requiring manual tuning: `{summary['manual_tuning']}`",
        f"- Full mix unsafe tracks: `{summary['full_mix_unsafe']}`",
        f"- Plugin mapping issues: `{summary['plugin_mapping_required']}`",
        "",
        "## Global Recommendation",
        "",
        f"`{score['recommendation']}`",
        "",
        "## Track Decision Table",
        "",
        "| Track | Role | Source Type | Risk | Decision | Reason Codes | Draft Created | Report |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for triage in triages:
        lines.append(
            f"| {triage['track_name']} | {triage['role']} | {triage['source_classification']} | {triage['risk']} | {triage['recommended_action']} | {', '.join(triage['reason_codes']) or 'none'} | {triage['draft_created']} | {safe_filename(triage['track_name'])}_pitch_triage.json |"
        )

    if recovery_matrix:
        lines.extend(
            [
                "",
                "## Vocal Recovery Before Pitch Correction",
                "",
                "| Track | Role | Source Type | Artifact Risk | Recovery Decision | Draft Created | Evaluation Status | Pitch Allowed After Recovery | Report |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in recovery_matrix.get("track_decisions", []):
            lines.append(
                f"| {item['track_name']} | {item['role']} | {item['source_type']} | {item['artifact_risk']} | {item['recovery_decision']} | {item['draft_created']} | {item['evaluation_status']} | {item['pitch_allowed_after_recovery']} | {item.get('report_path') or 'none'} |"
            )

    if placement_matrix:
        lines.extend(
            [
                "",
                "## Vocal Forward Placement",
                "",
                "| Track | Role | Source Type | Recovery Status | Pitch Status | Masking Risk | Placement Decision | Draft Created | Evaluation Status | Report |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in placement_matrix.get("track_decisions", []):
            lines.append(
                f"| {item['track_name']} | {item['role']} | {item['source_type']} | {item['recovery_status']} | {item['pitch_status']} | {item['masking_risk']} | {item['placement_decision']} | {item['draft_created']} | {item['evaluation_status']} | {item.get('report_path') or 'none'} |"
            )

    lines.extend(["", "## Stem Required Tracks", ""])
    stem_items = [item for item in triages if stem_required_reason(item)]
    if stem_items:
        for item in stem_items:
            lines.append(f"- `{item['track_name']}`: unsafe because `{', '.join(item['reason_codes']) or item['source_classification']}`. Requested stem type: isolated lead vocal, preferably dry/lightly processed.")
    else:
        lines.append("- none")

    lines.extend(["", "## Pitch Draft Tracks", ""])
    draft_items = [item for item in triages if item["draft_required"]]
    if draft_items:
        for item in draft_items:
            lines.append(f"- `{item['track_name']}`: `{item['correction_profile']}`, settings `{json.dumps(item['proposed_settings'])}`, evaluation required `{item['ab_eval_required']}`.")
    else:
        lines.append("- none")

    lines.extend(["", "## Skipped Tracks", ""])
    for item in triages:
        if item["recommended_action"] == "skip":
            lines.append(f"- `{item['track_name']}`: {', '.join(item['reason_codes']) or 'role not pitch eligible'}")

    lines.extend(
        [
            "",
            "## Manual Review Checklist",
            "",
            "- Compare original vs draft at equal loudness.",
            "- Check if the vocal sounds more robotic.",
            "- Check if sibilants warble.",
            "- Check if reverb tails bend.",
            "- Check if the vocal becomes thinner.",
            "- Check if consonants smear.",
            "- Check if stereo image shifts.",
            "- Reject the draft if it sounds more AI-like even when pitch is tighter.",
            "",
            "## Final Recommendation",
            "",
            f"`{score['recommendation']}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_batch_triage(
    *,
    project_path: Path | None,
    output_dir: Path,
    mode: str = "conservative_scan_only",
    track_filter: str | None = None,
    apply_drafts: bool = False,
    render_ab: bool = False,
    report_only: bool = False,
    allow_experimental_full_mix: bool = False,
    adapter_status_path: Path | None = None,
    track_manifest_path: Path | None = None,
) -> dict[str, Path]:
    if mode not in BATCH_MODES:
        raise ValueError(f"Unknown batch mode: {mode}")
    if report_only:
        mode = "report_only"
    if mode == "conservative_scan_only":
        apply_drafts = False
    if mode == "report_only":
        apply_drafts = False
    if mode == "no_pitch_correction":
        apply_drafts = False

    output_dir.mkdir(parents=True, exist_ok=True)
    tracks = load_track_manifest(track_manifest_path)
    if not tracks and project_path:
        tracks = parse_reaper_project(project_path)
    if track_filter:
        needle = normalize(track_filter)
        tracks = [track for track in tracks if needle in normalize(track.track_name)]

    adapter_status = load_adapter_status(adapter_status_path)
    project_name = project_path.name if project_path else "manifest_project"
    role_map: list[dict[str, Any]] = []
    triages: list[dict[str, Any]] = []
    recovery_entries: list[dict[str, Any]] = []
    source_reports: dict[str, dict[str, Any]] = {}
    report_paths: dict[str, str] = {}

    for track in tracks:
        role_entry = detect_track_role(track)
        source, pitch = reports_for_track(track, role_entry, project_path)
        source_reports[track.track_name] = source
        recovery_entry = recovery_for_track(
            track,
            role_entry,
            source,
            output_dir=output_dir,
            adapter_status=adapter_status,
            project_path=project_path,
        )
        triage = triage_track(
            track,
            role_entry,
            adapter_status,
            mode=mode,
            apply_drafts=apply_drafts,
            allow_experimental_full_mix=allow_experimental_full_mix,
            project_path=project_path,
            source_report=source,
            pitch_report=pitch,
            recovery_entry=recovery_entry,
        )
        role_map.append(role_entry)
        recovery_entries.append(recovery_entry)
        triages.append(triage)
        triage_path = output_dir / "analysis_reports" / f"{safe_filename(track.track_name)}_pitch_triage.json"
        write_json(triage_path, triage)
        report_paths[track.track_name] = str(triage_path)
        if stem_required_reason(triage):
            write_stem_report(output_dir, triage)

    instrumental_track = None
    for track, role_entry in zip(tracks, role_map):
        if role_entry["role"] == "instrumental_bus":
            instrumental_track = track
            break

    placement_entries: list[dict[str, Any]] = []
    for track, role_entry, recovery_entry, triage in zip(tracks, role_map, recovery_entries, triages):
        context = target_context_for_placement(tracks, role_map, track)
        placement_entry = placement_for_track(
            track,
            role_entry,
            source_reports.get(track.track_name, {}),
            recovery_entry,
            triage,
            output_dir=output_dir,
            adapter_status=adapter_status,
            project_path=project_path,
            target_context=context,
            instrumental_track=instrumental_track,
        )
        placement_entries.append(placement_entry)

    role_map_doc = {"project_name": project_name, "tracks": role_map}
    matrix = build_matrix(project_name, role_map, triages, report_paths)
    recovery_matrix = build_recovery_matrix(project_name, role_map, recovery_entries)
    placement_matrix = build_placement_matrix(project_name, role_map, placement_entries)
    render_plan = build_render_plan(triages, mode, apply_drafts, force_review=render_ab)
    rollback_index = build_rollback_index(project_name, triages, output_dir)
    score = safety_score(triages, render_plan)

    paths = {
        "role_map": output_dir / "analysis_reports" / "project_track_role_map.json",
        "matrix": output_dir / "eval_reports" / "project_pitch_triage_matrix.json",
        "recovery_matrix": output_dir / "eval_reports" / "project_vocal_recovery_matrix.json",
        "placement_matrix": output_dir / "eval_reports" / "project_vocal_placement_matrix.json",
        "render_plan": output_dir / "eval_reports" / "project_pitch_render_plan.json",
        "rollback_index": output_dir / "rollback" / "project_pitch_rollback_index.json",
        "safety_score": output_dir / "eval_reports" / "project_pitch_safety_score.json",
        "batch_report": output_dir / "eval_reports" / "project_pitch_batch_report.md",
    }
    write_json(paths["role_map"], role_map_doc)
    write_json(paths["matrix"], matrix)
    write_json(paths["recovery_matrix"], recovery_matrix)
    write_json(paths["placement_matrix"], placement_matrix)
    write_json(paths["render_plan"], render_plan)
    write_json(paths["rollback_index"], rollback_index)
    write_json(paths["safety_score"], score)
    write_batch_report(output_dir, matrix, triages, score, render_plan, recovery_matrix, placement_matrix)
    return paths
