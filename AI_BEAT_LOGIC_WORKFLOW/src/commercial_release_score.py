from __future__ import annotations

from typing import Any


SCORE_CATEGORIES = (
    "final_audio_verification",
    "mix_master_readiness",
    "arrangement_readiness",
    "style_target_fit",
    "deliverable_completeness",
    "rights_safety_readiness",
    "completion_integrity",
)


def clamp_score(value: int | float) -> int:
    return max(1, min(5, int(round(value))))


def _has_metrics(final_audio: dict[str, Any]) -> bool:
    return all(final_audio.get(key) is not None for key in ("peak_dbfs", "rms_dbfs", "clipping_count"))


def score_final_audio_verification(final_audio: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not final_audio.get("path"):
        issues.append("final WAV path missing")
    if final_audio.get("exists") is False:
        issues.append("final WAV missing")
    if not final_audio.get("duration_seconds") and final_audio.get("duration_seconds") != 0:
        issues.append("duration is not readable")
    if final_audio.get("sample_rate") != final_audio.get("expected_sample_rate", final_audio.get("requested_sample_rate", final_audio.get("sample_rate"))):
        issues.append("requested sample rate was not verified")
    if final_audio.get("bit_depth") != final_audio.get("expected_bit_depth", final_audio.get("requested_bit_depth", final_audio.get("bit_depth"))):
        issues.append("requested bit depth was not verified")
    if final_audio.get("format_verified") is False:
        issues.append("codec/format was not verified")
    if not _has_metrics(final_audio):
        issues.append("peak/RMS/clipping metrics are incomplete")
    if int(final_audio.get("clipping_count") or 0) > 0:
        issues.append("clipping detected")
    if not bool(final_audio.get("verified") or final_audio.get("ok") or final_audio.get("passed")):
        issues.append("final WAV verification failed")
    return {
        "category": "final_audio_verification",
        "score": 5 if not issues else 1,
        "blocking_issues": list(dict.fromkeys(issues)),
    }


def score_mix_master_readiness(mix_master: dict[str, Any] | None = None, final_audio: dict[str, Any] | None = None) -> dict[str, Any]:
    mix = mix_master or {}
    audio = final_audio or {}
    issues: list[str] = []
    warnings = " ".join(str(item).lower() for item in mix.get("warnings", []) + mix.get("limitations", []))
    priorities = set(mix.get("mix_priorities", []))
    if "vocal_forwardness" not in priorities and "melody_forward" not in priorities and not mix.get("vocal_melody_clarity", True):
        issues.append("vocal/melody clarity is not confirmed")
    if "controlled_808" not in priorities and not mix.get("low_end_control", True):
        issues.append("low-end control is not confirmed")
    if mix.get("mono_compatibility") is False:
        issues.append("stereo width/mono compatibility risk remains")
    if mix.get("harshness_sibilance_risk") in {True, "high"} or "harsh" in warnings or "sibilance" in warnings:
        issues.append("harshness/sibilance risk remains")
    if mix.get("overcompression_risk") in {True, "high"}:
        issues.append("overcompression risk remains")
    peak = audio.get("peak_dbfs")
    if peak is not None and float(peak) > -0.1:
        issues.append("headroom target is not met")
    score = 5 if not issues else 3 if len(issues) <= 2 else 2
    return {"category": "mix_master_readiness", "score": score, "blocking_issues": issues}


def score_arrangement_readiness(arrangement: dict[str, Any] | None = None) -> dict[str, Any]:
    arrangement = arrangement or {}
    by_name = {item.get("name"): item.get("score") for item in arrangement.get("categories", []) if isinstance(item, dict)}
    values = [
        by_name.get("Hook impact", arrangement.get("hook_impact_score", 3)),
        by_name.get("Arrangement intentionality", arrangement.get("section_intentionality_score", 3)),
        by_name.get("Drum/808 guide strength", arrangement.get("variation_score", 3)),
        by_name.get("AI artifact cleanup", arrangement.get("ai_artifact_cleanup_score", 3)),
        by_name.get("Outro/cut cleanliness", arrangement.get("outro_cut_cleanliness_score", 3)),
    ]
    score = clamp_score(sum(int(value or 3) for value in values) / len(values))
    issues = []
    if score < 4:
        issues.append("arrangement still needs stronger hook, section intent, variation, cleanup, or outro/cut polish")
    return {"category": "arrangement_readiness", "score": score, "blocking_issues": issues}


def score_style_target_fit(reference_profile: dict[str, Any] | None = None, mix_master: dict[str, Any] | None = None) -> dict[str, Any]:
    reference = reference_profile or {}
    mix = mix_master or {}
    safety = reference.get("copying_policy") or {}
    style_target = str(mix.get("style_target") or reference.get("style_cluster") or reference.get("target_style") or "").lower()
    issues: list[str] = []
    if safety.get("claim_exact_copy") or safety.get("exact_copy_claim"):
        issues.append("exact-copy reference claim exists")
    if not safety.get("exact_copy_allowed", False) and safety.get("copying_requested") and safety.get("claim_exact_copy"):
        issues.append("reference safety compliance failed")
    if not any(token in style_target for token in ("hip", "hyperpop", "digicore", "internet", "system_seoul", "underground")):
        issues.append("style target fit is only broadly documented")
    return {"category": "style_target_fit", "score": 5 if not issues else 3 if len(issues) == 1 else 1, "blocking_issues": issues}


def score_deliverable_completeness(
    deliverable_manifest: dict[str, Any] | None = None,
    *,
    requested_deliverables: list[str] | None = None,
    metadata_complete: bool = False,
    rights_checklist_exists: bool = False,
    release_manifest_exists: bool = False,
) -> dict[str, Any]:
    manifest = deliverable_manifest or {}
    requested = set(requested_deliverables or [])
    by_type = {item.get("type"): item for item in manifest.get("deliverables", []) if isinstance(item, dict)}
    issues: list[str] = []
    if not by_type.get("final_master", {}).get("available"):
        issues.append("final master deliverable missing")
    optional_map = {
        "preview": "mp3_preview",
        "mp3_preview": "mp3_preview",
        "reels_15sec": "reels_15sec",
        "short_30sec": "short_30sec",
        "instrumental": "instrumental",
        "acapella": "acapella",
        "stems": "stems",
    }
    for requested_name, deliverable_type in optional_map.items():
        if requested_name in requested and not by_type.get(deliverable_type, {}).get("available"):
            issues.append(f"requested {requested_name} deliverable missing")
    if not metadata_complete:
        issues.append("metadata sheet incomplete")
    if not rights_checklist_exists:
        issues.append("rights checklist missing")
    if not release_manifest_exists:
        issues.append("release manifest missing")
    score = 5 if not issues else 3 if all("metadata" in issue for issue in issues) else 2
    return {"category": "deliverable_completeness", "score": score, "blocking_issues": issues}


def score_rights_safety_readiness(rights: dict[str, Any] | None = None, false_claim_risk: dict[str, Any] | None = None) -> dict[str, Any]:
    rights = rights or {}
    false_claim = false_claim_risk or {}
    issues: list[str] = []
    if rights.get("contains_samples") and rights.get("all_samples_owned_or_cleared") is not True:
        issues.append("sample ownership/clearance unresolved")
    if rights.get("web_audio_downloaded"):
        issues.append("web audio download is present")
    if rights.get("voice_clone_used"):
        issues.append("voice clone claim/use is present")
    if rights.get("exact_copy_claim"):
        issues.append("exact-copy claim is present")
    risky = set(false_claim.get("risky_flags", []))
    if risky.intersection({"plugin_processing_verified", "stem_level_remix_claimed", "stem_generation_claimed"}):
        issues.append("plugin or stem false-claim risk remains")
    return {"category": "rights_safety_readiness", "score": 5 if not issues else 1, "blocking_issues": issues}


def score_completion_integrity(
    completion_gate: dict[str, Any] | None = None,
    *,
    qc_report_exists: bool = False,
    master_qc_report_exists: bool = False,
    release_qc_report_exists: bool = False,
) -> dict[str, Any]:
    gate = completion_gate or {}
    issues: list[str] = []
    if not gate.get("complete"):
        issues.append("completion_gate has not passed")
    if not qc_report_exists:
        issues.append("qc_report.md missing")
    if not master_qc_report_exists:
        issues.append("master_qc_report.md missing")
    if not release_qc_report_exists:
        issues.append("release_qc_report.md missing")
    if gate.get("unsafe_complete_path"):
        issues.append("unsafe COMPLETE path detected")
    return {"category": "completion_integrity", "score": 5 if not issues else 2, "blocking_issues": issues}


def build_commercial_release_score(
    *,
    final_audio: dict[str, Any],
    mix_master: dict[str, Any] | None = None,
    arrangement: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    deliverable_manifest: dict[str, Any] | None = None,
    requested_deliverables: list[str] | None = None,
    metadata_complete: bool = False,
    rights: dict[str, Any] | None = None,
    rights_checklist_exists: bool = False,
    release_manifest_exists: bool = False,
    false_claim_risk: dict[str, Any] | None = None,
    completion_gate: dict[str, Any] | None = None,
    qc_report_exists: bool = False,
    master_qc_report_exists: bool = False,
    release_qc_report_exists: bool = False,
) -> dict[str, Any]:
    categories = [
        score_final_audio_verification(final_audio),
        score_mix_master_readiness(mix_master, final_audio),
        score_arrangement_readiness(arrangement),
        score_style_target_fit(reference_profile, mix_master),
        score_deliverable_completeness(
            deliverable_manifest,
            requested_deliverables=requested_deliverables,
            metadata_complete=metadata_complete,
            rights_checklist_exists=rights_checklist_exists,
            release_manifest_exists=release_manifest_exists,
        ),
        score_rights_safety_readiness(rights, false_claim_risk),
        score_completion_integrity(
            completion_gate,
            qc_report_exists=qc_report_exists,
            master_qc_report_exists=master_qc_report_exists,
            release_qc_report_exists=release_qc_report_exists,
        ),
    ]
    average = round(sum(item["score"] for item in categories) / len(categories), 2)
    blocking = [issue for item in categories for issue in item.get("blocking_issues", [])]
    high_safety = [issue for item in categories if item["category"] == "rights_safety_readiness" for issue in item.get("blocking_issues", [])]
    return {
        "schema_version": "commercial_release_score.v1",
        "average_score": average,
        "categories": categories,
        "blocking_issues": list(dict.fromkeys(blocking)),
        "high_safety_issues": list(dict.fromkeys(high_safety)),
        "release_ready_score_pass": average >= 4.0,
        "commercial_success_claimed": False,
        "note": "Scores estimate local release-package readiness only; they do not claim commercial success or distributor approval.",
    }
