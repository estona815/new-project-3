from __future__ import annotations

import re
from typing import Any

from reference_intent_parser import parse_reference_intent
from zero_clarification_defaults import apply_zero_clarification_defaults, zero_clarification_requested


SUPPORTED_RELEASE_WORKFLOWS = {
    "bad_ai_song_rescue",
    "song_to_release",
    "sample_to_release",
    "vocal_to_release",
    "stems_to_release",
    "plan_only",
}

TARGET_DELIVERABLES = {"demo", "final_master", "release_package"}
RELEASE_PROFILES = {"commercial_digicore", "hip_hop", "hyperpop", "internet_underground", "system_seoul_adjacent", "custom"}


def _has(text: str, *items: str) -> bool:
    return any(item in text for item in items)


def _compact(text: str) -> str:
    return re.sub(r"[\s._/-]+", "", text.lower())


def infer_release_workflow(*, workflow: str | None, mode: str | None, text: str, target_deliverable: str) -> str:
    if workflow in SUPPORTED_RELEASE_WORKFLOWS:
        return str(workflow)
    if workflow == "bad_ai_song_rescue":
        return "bad_ai_song_rescue"
    if workflow == "song_to_mix_master":
        return "song_to_release"
    if workflow == "sample_to_arrangement":
        return "sample_to_release"
    if workflow == "vocal_to_code":
        return "vocal_to_release"
    if workflow == "stems_to_production":
        return "stems_to_release"
    if mode == "stems":
        return "stems_to_release"
    if mode == "vocal_plus_beat":
        return "vocal_to_release"
    normalized = text.lower()
    compacted = _compact(text)
    if _has(normalized, "샘플", "sample"):
        return "sample_to_release" if target_deliverable != "demo" else "plan_only"
    if _has(normalized, "보컬", "vocal", "목소리") and not _has(normalized, "비트", "beat", "song"):
        return "vocal_to_release"
    if _has(normalized, "stem", "stems") or "스템" in compacted:
        return "stems_to_release"
    if target_deliverable in {"final_master", "release_package"} or _has(normalized, "믹마", "마스터", "master", "발매", "릴리즈", "상업"):
        return "song_to_release"
    return "plan_only"


def infer_style_cluster(text: str, release_profile: str | None = None) -> str:
    if release_profile and release_profile != "custom":
        return release_profile
    normalized = text.lower()
    compacted = _compact(text)
    if _has(normalized, "system seoul") or "시스템서울" in compacted:
        return "system_seoul_adjacent"
    if _has(normalized, "hyperpop") or "하이퍼팝" in compacted:
        return "hyperpop"
    if _has(normalized, "digicore") or "디지코어" in compacted:
        return "commercial_digicore"
    if _has(normalized, "internet underground") or "인터넷언더" in compacted:
        return "internet_underground"
    if _has(normalized, "hip hop", "hiphop", "rap") or _has(text, "힙합", "랩"):
        return "hip_hop"
    return "commercial_digicore" if _has(text, "상업") else "custom"


def infer_final_length(text: str) -> str:
    normalized = text.lower()
    if _has(normalized, "15", "15초", "릴스", "reels"):
        return "15sec_reels"
    if _has(normalized, "30", "30초", "short"):
        return "30sec_short_form"
    if _has(normalized, "원곡", "keep original"):
        return "keep_original"
    return "under_2min"


def infer_priority(text: str, parsed: dict[str, Any]) -> str:
    normalized = text.lower()
    if _has(normalized, "훅", "hook", "릴스", "reels"):
        return "hook"
    if _has(normalized, "보컬", "vocal", "목소리"):
        return "vocal"
    if _has(normalized, "멜로디", "melody"):
        return "melody"
    if _has(normalized, "드럼", "drum", "킥", "kick"):
        return "drums"
    if _has(normalized, "808", "베이스", "bass", "서브"):
        return "808"
    if _has(normalized, "신스", "신디", "wide", "넓", "스테레오"):
        return "synth width"
    if _has(normalized, "마스터", "믹마", "master"):
        return "master"
    targets = parsed.get("target_elements", [])
    if "arrangement" in targets:
        return "hook"
    if "vocal" in targets:
        return "vocal"
    if "bass_808" in targets:
        return "808"
    return "hook"


def infer_target_deliverable(text: str, requested: str | None, release_ready: bool) -> str:
    if requested in TARGET_DELIVERABLES:
        return str(requested)
    normalized = text.lower()
    if release_ready or _has(normalized, "발매", "릴리즈", "release", "metadata", "체크리스트"):
        return "release_package"
    if _has(normalized, "믹마", "마스터", "master", "final"):
        return "final_master"
    return "demo"


def infer_requested_deliverables(target_deliverable: str, workflow: str) -> list[str]:
    deliverables = ["production_intent", "creative_brief", "safety_notes"]
    if workflow == "bad_ai_song_rescue":
        deliverables.extend(
            [
                "bad_song_diagnosis",
                "rescue_arrangement_plan",
                "lead_melody_plan",
                "hook_identity_plan",
                "vocal_texture_rescue_plan",
                "sample_motif_rebuild_plan",
                "logic_rescue_plan",
                "rescue_qc_report",
            ]
        )
        return list(dict.fromkeys(deliverables))
    if workflow != "plan_only":
        deliverables.extend(["analysis", "arrangement_plan", "logic_manual_plan", "mix_master_plan"])
    if target_deliverable in {"demo", "final_master", "release_package"}:
        deliverables.append("demo_render_if_available")
    if target_deliverable in {"final_master", "release_package"}:
        deliverables.extend(["verified_final_wav", "qc_report", "master_qc_report"])
    if target_deliverable == "release_package":
        deliverables.extend(["release_metadata", "rights_safety_checklist", "release_qc_report", "release_status"])
    return list(dict.fromkeys(deliverables))


def infer_mix_master_target(text: str) -> str:
    normalized = text.lower()
    if _has(normalized, "headroom", "헤드룸"):
        return "master_ready_headroom"
    if _has(normalized, "loud demo", "라우드", "크게"):
        return "loud_demo"
    return "streaming_safe"


def build_safety_blocks(parsed: dict[str, Any]) -> list[str]:
    blocks = [
        "no exact-copy of songs, samples, kick sounds, basslines, melodies, lyrics, drum patterns, or recordings",
        "no living artist vocal identity cloning",
        "no false Logic/plugin/stem-processing claims",
    ]
    if parsed.get("requires_user_owned_source_for_sampling") or parsed.get("copying_risk") == "high":
        blocks.append("copying-risk phrases require an owned/licensed/cleared local sample or stem")
    return blocks


def build_release_intent(
    *,
    rough_request: str | None,
    workflow: str | None = None,
    mode: str | None = None,
    release_ready: bool | None = None,
    zero_clarification: bool | None = None,
    target_deliverable: str | None = None,
    release_profile: str | None = None,
    reference_audio_available: bool = False,
) -> dict[str, Any]:
    text = (rough_request or "").strip()
    parsed = parse_reference_intent(text, reference_audio_available=reference_audio_available)
    release_flag = bool(release_ready or _has(text.lower(), "발매", "릴리즈", "release", "상업"))
    target = infer_target_deliverable(text, target_deliverable, release_flag)
    resolved_workflow = infer_release_workflow(workflow=workflow, mode=mode, text=text, target_deliverable=target)
    resolved_profile = infer_style_cluster(text, release_profile)
    resolved_zero = bool(zero_clarification if zero_clarification is not None else zero_clarification_requested(text))
    intent = {
        "schema_version": "release_intent.v1",
        "rough_request": text,
        "workflow": resolved_workflow,
        "style_cluster": resolved_profile,
        "final_length": infer_final_length(text),
        "priority": infer_priority(text, parsed),
        "target_deliverable": target,
        "release_ready": release_flag or target == "release_package",
        "zero_clarification": resolved_zero,
        "deliverables_requested": infer_requested_deliverables(target, resolved_workflow),
        "mix_master_target": infer_mix_master_target(text),
        "safety_blocks": build_safety_blocks(parsed),
        "manual_logic_required": [
            "Logic arrangement, plugin insertion, automation, and final bounce require manual or verified execution",
        ],
        "assumptions": [],
        "parsed_reference_intent": parsed,
    }
    if not text:
        intent["assumptions"].append("No rough request was provided; conservative plan-only defaults are used.")
    if resolved_zero:
        intent = apply_zero_clarification_defaults(intent)
    if release_flag and "release package includes metadata/checklists/QC" not in intent["assumptions"]:
        intent["assumptions"].append("release package includes metadata/checklists/QC")
    return intent
