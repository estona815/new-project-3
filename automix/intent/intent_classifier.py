from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.revision_memory import summarize_feedback_memory
from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json


INTENT_CLASSIFICATION_SCHEMA = "automix-intent-classification-v1"

INTENT_REL_PATH = Path("eval_reports/intent_classification.json")
INTENT_REPORT_REL_PATH = Path("eval_reports/intent_classification.md")

INTENTS = [
    "vocal_rescue",
    "suno_artifact_suppression",
    "conservative_cleanup",
    "stem_mix",
    "full_mix_polish",
    "master_only",
    "active_rebeat_mix",
    "reels_preview_master",
    "streaming_master",
    "aggressive_creative_enhancement",
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _clamp01(value: Any) -> float:
    return max(0.0, min(1.0, safe_float(value, 0.0)))


def _load_source_summary(output_dir: Path, provided: dict[str, Any] | None = None) -> dict[str, Any]:
    if provided:
        return dict(provided)
    source_map = _load_json(output_dir / "eval_reports/real_project_source_safety_map.json")
    if source_map:
        summary = dict(source_map.get("summary", {}))
        summary.setdefault("schema", source_map.get("schema", "automix-real-project-source-safety-map-v1"))
        return summary
    orchestration = _load_json(output_dir / "analysis_reports/orchestrator_source_classification_summary.json")
    if orchestration:
        return {
            "schema": orchestration.get("schema", "automix-orchestrator-source-classification-summary-v1"),
            "safe_vocal_candidates": orchestration.get("vocal_like_tracks", 0),
            "full_mix_unsafe_tracks": orchestration.get("full_mix_unsafe_tracks", 0),
            "stem_required_tracks": orchestration.get("stem_required_tracks", 0),
            "unknown_tracks": orchestration.get("unknown_tracks_skipped", 0),
            "ai_or_already_processed_vocals": 0,
            "source_separated_vocals": 0,
            "tracks_total": orchestration.get("tracks_total", 0),
        }
    return {
        "schema": "automix-source-summary-missing-v1",
        "safe_vocal_candidates": 0,
        "full_mix_unsafe_tracks": 0,
        "stem_required_tracks": 0,
        "unknown_tracks": 0,
        "ai_or_already_processed_vocals": 0,
        "source_separated_vocals": 0,
        "tracks_total": 0,
    }


def _plugin_readiness(output_dir: Path, plugin_audit: dict[str, Any] | None = None) -> dict[str, Any]:
    real_project = _load_json(output_dir / "eval_reports/real_project_plugin_readiness.json")
    if real_project:
        return {
            "schema": real_project.get("schema", "automix-real-project-plugin-readiness-v1"),
            "safe_draft_plugin_ready": bool(real_project.get("safe_draft_plugin_ready")),
            "can_run_pitch_correction_safely": bool(real_project.get("can_run_pitch_correction_safely")),
            "can_run_vocal_placement_safely": bool(real_project.get("can_run_vocal_placement_safely")),
            "can_run_premaster_draft_safely": bool(real_project.get("can_run_premaster_draft_safely")),
            "safe_adapters_count": int(real_project.get("safe_adapters_count", 0) or 0),
            "missing_or_unsafe_mappings": real_project.get("missing_or_unsafe_mappings", []),
            "warnings": real_project.get("warnings", []),
        }
    audit = plugin_audit or _load_json(output_dir / "analysis_reports/plugin_inventory_audit.json")
    summary = audit.get("summary", {}) if audit else {}
    safe_count = int(summary.get("validated_safe_count", 0) or 0)
    return {
        "schema": audit.get("schema", "automix-plugin-readiness-derived-v1") if audit else "automix-plugin-readiness-missing-v1",
        "safe_draft_plugin_ready": safe_count > 0,
        "can_run_pitch_correction_safely": safe_count > 0,
        "can_run_vocal_placement_safely": safe_count > 0,
        "can_run_premaster_draft_safely": safe_count > 0,
        "safe_adapters_count": safe_count,
        "missing_or_unsafe_mappings": [item.get("name", "unknown") for item in audit.get("unsafe_or_unmapped_plugins", [])] if audit else [],
        "warnings": audit.get("warnings", []) if audit else ["plugin_readiness_report_missing"],
    }


def _feedback_intent_signals(output_dir: Path) -> dict[str, Any]:
    summary = summarize_feedback_memory(output_dir)
    counts = summary.get("category_counts", {})
    return {
        "summary": summary,
        "has_feedback": summary.get("total_entries", 0) > 0,
        "unresolved": int(summary.get("pending_unresolved_count", 0) or 0),
        "vocal_feedback": sum(int(counts.get(name, 0) or 0) for name in ("vocal_clarity", "vocal_presence", "masking_balance", "female_support_layer")),
        "artifact_feedback": int(counts.get("ai_artifact", 0) or 0),
        "mastering_feedback": sum(int(counts.get(name, 0) or 0) for name in ("mastering_dynamics", "low_end", "stereo_mono")),
    }


def _target_profile_signals(target_profile: str) -> dict[str, bool]:
    text = target_profile.lower()
    return {
        "reels": "reel" in text or "short" in text,
        "streaming": "stream" in text or "professional" in text or "master" in text,
        "rebeat": "rebeat" in text or "stem" in text,
        "vocal_forward": "vocal" in text or "digicore" in text or "hyperpop" in text or "hiphop" in text,
    }


def _intent(
    *,
    name: str,
    confidence: float,
    risk: float,
    vocal_priority: float,
    artifact_focus: float,
    overprocessing: float,
    conservative_mode: bool,
    human_review: bool,
    dry_wet_limit: float,
    status: str,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    recommended_next_action: str = "review_reports",
) -> dict[str, Any]:
    return {
        "intent": name,
        "confidence": round(_clamp01(confidence), 6),
        "source_risk_score": round(_clamp01(risk), 6),
        "vocal_priority_score": round(_clamp01(vocal_priority), 6),
        "artifact_focus_score": round(_clamp01(artifact_focus), 6),
        "overprocessing_risk_score": round(_clamp01(overprocessing), 6),
        "conservative_mode": bool(conservative_mode),
        "human_review_required": bool(human_review),
        "dry_run_only": True,
        "preview_only": status != "safe_draft_allowed",
        "max_artifact_focus_dry_wet": round(_clamp01(dry_wet_limit), 6),
        "status": status,
        "blockers": sorted(set(blockers or [])),
        "warnings": sorted(set(warnings or [])),
        "recommended_next_action": recommended_next_action,
    }


def _safe_next_mode(intents: list[dict[str, Any]], source: dict[str, Any], plugin: dict[str, Any], feedback: dict[str, Any]) -> str:
    if not plugin.get("safe_draft_plugin_ready"):
        return "validate_plugin_mappings"
    if int(source.get("stem_required_tracks", 0) or 0) > 0:
        return "provide_isolated_stems"
    if int(source.get("unknown_tracks", 0) or 0) > 0 and int(source.get("safe_vocal_candidates", 0) or 0) == 0:
        return "manual_mix_required"
    if feedback.get("unresolved", 0) > 0:
        return "safe_draft_review_only_until_feedback_resolved"
    if any(item["intent"] == "vocal_rescue" and item["status"] == "safe_draft_allowed" for item in intents):
        return "safe_draft_no_pitch"
    if any(item["intent"] == "conservative_cleanup" and item["status"] == "safe_draft_allowed" for item in intents):
        return "safe_draft_recovery_only"
    return "scan_only_again"


def build_intent_classification(
    *,
    project_name: str,
    output_dir: Path,
    target_profile: str = "digicore_hyperpop_hiphop_vocal_forward",
    requested_intents: list[str] | None = None,
    source_summary: dict[str, Any] | None = None,
    plugin_audit: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    source = _load_source_summary(output_dir, source_summary)
    plugin = _plugin_readiness(output_dir, plugin_audit)
    feedback = _feedback_intent_signals(output_dir)
    profile = _target_profile_signals(target_profile)
    requested = sorted({str(item) for item in requested_intents or [] if str(item).strip()})

    safe_vocals = int(source.get("safe_vocal_candidates", 0) or 0)
    full_mix = int(source.get("full_mix_unsafe_tracks", 0) or 0)
    stems_required = int(source.get("stem_required_tracks", 0) or 0)
    unknown = int(source.get("unknown_tracks", 0) or 0)
    ai_processed = int(source.get("ai_or_already_processed_vocals", 0) or 0)
    source_sep = int(source.get("source_separated_vocals", 0) or 0)
    tracks_total = max(1, int(source.get("tracks_total", 0) or safe_vocals + full_mix + unknown + stems_required or 1))
    plugin_ready = bool(plugin.get("safe_draft_plugin_ready"))
    source_risk = _clamp01((full_mix + stems_required + unknown * 0.5 + source_sep * 0.7 + ai_processed * 0.35) / tracks_total)

    common_blockers: list[str] = []
    if not plugin_ready:
        common_blockers.append("validated_plugin_mapping_required")
    if stems_required:
        common_blockers.append("isolated_stems_required")
    if unknown and not safe_vocals:
        common_blockers.append("unknown_source_manual_review_required")

    vocal_signal = _clamp01((safe_vocals + feedback["vocal_feedback"] * 0.6) / max(1, tracks_total))
    artifact_signal = _clamp01((ai_processed + source_sep + feedback["artifact_feedback"] * 0.8) / max(1, tracks_total))
    mastering_signal = _clamp01((feedback["mastering_feedback"] * 0.6 + (1 if profile["streaming"] else 0)) / 2.0)

    intents = [
        _intent(
            name="vocal_rescue",
            confidence=max(vocal_signal, 0.35 if profile["vocal_forward"] else 0.15),
            risk=source_risk,
            vocal_priority=0.95,
            artifact_focus=max(artifact_signal, 0.25),
            overprocessing=max(0.35, source_risk),
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.35 if artifact_signal > 0.35 else 0.50,
            status="safe_draft_allowed" if plugin_ready and safe_vocals and not stems_required else "blocked_or_review_only",
            blockers=[] if plugin_ready and safe_vocals and not stems_required else common_blockers + (["no_safe_vocal_candidate"] if not safe_vocals else []),
            warnings=["male_lead_vocal_must_remain_primary"],
            recommended_next_action="run_vocal_recovery_or_placement_dry_run",
        ),
        _intent(
            name="suno_artifact_suppression",
            confidence=max(artifact_signal, 0.20),
            risk=max(source_risk, 0.55 if artifact_signal else 0.25),
            vocal_priority=0.90,
            artifact_focus=max(artifact_signal, 0.70 if feedback["artifact_feedback"] else 0.35),
            overprocessing=0.70,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.30,
            status="safe_draft_allowed" if plugin_ready and safe_vocals and artifact_signal > 0 else "blocked_or_review_only",
            blockers=[] if plugin_ready and safe_vocals and artifact_signal > 0 else common_blockers + (["artifact_signal_not_established"] if artifact_signal <= 0 else []),
            warnings=["artifact_reduction_not_total_removal", "formant_protection_required"],
            recommended_next_action="run_conservative_artifact_suppression_dry_run",
        ),
        _intent(
            name="conservative_cleanup",
            confidence=max(0.45, vocal_signal, artifact_signal),
            risk=source_risk,
            vocal_priority=0.80,
            artifact_focus=max(artifact_signal, 0.25),
            overprocessing=0.30,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.45,
            status="safe_draft_allowed" if plugin_ready and (safe_vocals or tracks_total > 0) and not stems_required else "blocked_or_review_only",
            blockers=[] if plugin_ready and (safe_vocals or tracks_total > 0) and not stems_required else common_blockers,
            warnings=["dry_run_only_until_ab_review"],
            recommended_next_action="create_conservative_cleanup_plan",
        ),
        _intent(
            name="stem_mix",
            confidence=_clamp01((safe_vocals + (1 if profile["rebeat"] else 0)) / max(2, tracks_total)),
            risk=source_risk,
            vocal_priority=0.90,
            artifact_focus=artifact_signal,
            overprocessing=0.45,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.45,
            status="safe_draft_allowed" if plugin_ready and safe_vocals and not stems_required else "blocked_or_review_only",
            blockers=[] if plugin_ready and safe_vocals and not stems_required else common_blockers + (["stems_not_ready"] if stems_required or not safe_vocals else []),
            warnings=["female_support_layers_must_not_replace_male_lead"],
            recommended_next_action="run_stem_mix_dry_run",
        ),
        _intent(
            name="full_mix_polish",
            confidence=_clamp01(full_mix / tracks_total),
            risk=max(source_risk, 0.75 if full_mix else 0.35),
            vocal_priority=0.70,
            artifact_focus=artifact_signal,
            overprocessing=0.80,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.25,
            status="manual_review_only",
            blockers=["full_mix_processing_is_high_risk", "isolated_stems_preferred"] if full_mix else ["full_mix_source_not_confirmed"],
            warnings=["do_not_fake_polish_full_mix_with_limiter"],
            recommended_next_action="request_stems_or_run_report_only_full_mix_qc",
        ),
        _intent(
            name="master_only",
            confidence=max(mastering_signal, 0.20),
            risk=max(source_risk, 0.55 if feedback["unresolved"] else 0.30),
            vocal_priority=0.65,
            artifact_focus=artifact_signal,
            overprocessing=0.65,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.20,
            status="manual_review_only" if feedback["unresolved"] or full_mix or stems_required else ("safe_draft_allowed" if plugin_ready else "blocked_or_review_only"),
            blockers=(["user_feedback_unresolved"] if feedback["unresolved"] else []) + (["mix_or_stem_issue_must_be_resolved_before_master"] if full_mix or stems_required else []) + ([] if plugin_ready else ["validated_plugin_mapping_required"]),
            warnings=["mastering_must_not_fix_mix_balance_problem"],
            recommended_next_action="run_premaster_safety_scan",
        ),
        _intent(
            name="active_rebeat_mix",
            confidence=0.60 if profile["rebeat"] else 0.15,
            risk=max(source_risk, 0.45),
            vocal_priority=0.85,
            artifact_focus=artifact_signal,
            overprocessing=0.60,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.40,
            status="blocked_or_review_only",
            blockers=["explicit_rebeat_stems_and_arrangement_review_required"] + ([] if plugin_ready else ["validated_plugin_mapping_required"]),
            warnings=["do_not_replace_existing_song_feel_without_request"],
            recommended_next_action="collect_rebeat_stems_and_manual_arrangement_intent",
        ),
        _intent(
            name="reels_preview_master",
            confidence=0.75 if profile["reels"] else 0.20,
            risk=max(source_risk, 0.50),
            vocal_priority=0.80,
            artifact_focus=artifact_signal,
            overprocessing=0.70,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.20,
            status="manual_review_only",
            blockers=["final_loud_preview_requires_ab_qc_and_approval"] + ([] if plugin_ready else ["validated_plugin_mapping_required"]),
            warnings=["reels_loudness_preview_must_not_replace_streaming_master_qc"],
            recommended_next_action="run_loud_preview_only_after_final_qc",
        ),
        _intent(
            name="streaming_master",
            confidence=0.70 if profile["streaming"] else 0.25,
            risk=max(source_risk, 0.45 if feedback["unresolved"] else 0.25),
            vocal_priority=0.80,
            artifact_focus=artifact_signal,
            overprocessing=0.50,
            conservative_mode=True,
            human_review=True,
            dry_wet_limit=0.20,
            status="safe_draft_allowed" if plugin_ready and not feedback["unresolved"] and not stems_required else "blocked_or_review_only",
            blockers=([] if plugin_ready else ["validated_plugin_mapping_required"]) + (["user_feedback_unresolved"] if feedback["unresolved"] else []) + (["stem_or_mix_issue_before_streaming_master"] if stems_required else []),
            warnings=["translation_and_true_peak_before_loudness"],
            recommended_next_action="run_conservative_streaming_premaster_scan",
        ),
        _intent(
            name="aggressive_creative_enhancement",
            confidence=1.0 if "aggressive_creative_enhancement" in requested else 0.05,
            risk=0.90,
            vocal_priority=0.30,
            artifact_focus=0.20,
            overprocessing=0.95,
            conservative_mode=False,
            human_review=True,
            dry_wet_limit=0.0,
            status="blocked",
            blockers=["aggressive_creative_enhancement_disabled_by_default", "explicit_user_approval_and_preview_required"],
            warnings=["random_vocal_chops_and_unbounded_saturation_disallowed"],
            recommended_next_action="manual_review_only",
        ),
    ]

    requested_unknown = sorted(set(requested) - set(INTENTS))
    safe_candidates = [item for item in intents if item["status"] == "safe_draft_allowed"]
    primary = max(intents, key=lambda item: (item["status"] == "safe_draft_allowed", item["confidence"], -item["source_risk_score"]))
    blockers = sorted({blocker for item in intents for blocker in item.get("blockers", []) if item["status"] in {"blocked", "blocked_or_review_only"}})
    warnings = sorted(
        set(plugin.get("warnings", []))
        | set(feedback["summary"].get("warnings", []))
        | ({f"unknown_requested_intent:{item}" for item in requested_unknown})
    )
    classification = {
        "schema": INTENT_CLASSIFICATION_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "target_profile": target_profile,
        "requested_intents": requested,
        "source_summary": source,
        "plugin_readiness": plugin,
        "feedback_summary": feedback["summary"],
        "intents": intents,
        "recommended_primary_intent": primary["intent"],
        "safe_next_mode": _safe_next_mode(intents, source, plugin, feedback),
        "safe_draft_intents": [item["intent"] for item in safe_candidates],
        "human_review_required": True,
        "dry_run_only": True,
        "preview_only_until_ab_review": True,
        "blockers": blockers,
        "warnings": warnings,
        "status": "safe_draft_intent_available" if safe_candidates else "review_required",
    }
    target = output_path or output_dir / INTENT_REL_PATH
    write_json(target, classification)
    write_intent_classification_report(classification, output_dir)
    return classification


def write_intent_classification_report(classification: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Intent Classification Report",
        "",
        f"- Project: `{classification.get('project_name')}`",
        f"- Created UTC: `{classification.get('created_at')}`",
        f"- Target profile: `{classification.get('target_profile')}`",
        f"- Status: `{classification.get('status')}`",
        f"- Recommended primary intent: `{classification.get('recommended_primary_intent')}`",
        f"- Safe next mode: `{classification.get('safe_next_mode')}`",
        "",
        "This report classifies intended work modes from available evidence. It does not apply FX, render audio, or prove a listening result.",
        "",
        "## Intent Matrix",
        "",
        "| Intent | Status | Confidence | Source risk | Vocal priority | Artifact focus | Overprocessing risk | Dry/wet cap | Next action |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in classification.get("intents", []):
        lines.append(
            f"| `{item.get('intent')}` | `{item.get('status')}` | {item.get('confidence')} | {item.get('source_risk_score')} | {item.get('vocal_priority_score')} | {item.get('artifact_focus_score')} | {item.get('overprocessing_risk_score')} | {item.get('max_artifact_focus_dry_wet')} | `{item.get('recommended_next_action')}` |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in classification.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in classification.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Safety Notes", ""])
    lines.extend(
        [
            "- `dry_run_only`: true",
            "- `preview_only_until_ab_review`: true",
            "- Aggressive creative enhancement is blocked by default.",
            "- Artifact handling is described as reduction or suppression, not total cleanup.",
            "- Mastering intent does not override unresolved mix, stem, or feedback blockers.",
        ]
    )
    path = Path(output_dir) / INTENT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
