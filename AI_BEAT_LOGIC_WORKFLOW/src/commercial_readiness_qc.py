from __future__ import annotations

from typing import Any

from commercial_release_score import build_commercial_release_score


QC_CATEGORIES = [
    "Hook impact",
    "Arrangement intentionality",
    "Sample/motif usability",
    "Vocal phrase usability",
    "Vocal commercial readiness",
    "Drum/808 guide strength",
    "Kick/bass commercial impact",
    "Melody/vibe preservation",
    "Synth width/space plan",
    "Digicore/hyperpop/internet underground style fit",
    "AI artifact cleanup",
    "Reference safety compliance",
    "Stereo/stem limitation honesty",
    "Technical delivery",
    "Logic manual clarity",
    "Completion integrity",
]


def evaluate_commercial_readiness(
    *,
    arrangement_qc: dict[str, Any] | None = None,
    mix_master_plan: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    completion_gate: dict[str, Any] | None = None,
    render_manifest: dict[str, Any] | None = None,
    input_mode: str = "instrumental_beat",
) -> dict[str, Any]:
    gate = completion_gate or {}
    manifest = render_manifest or {}
    mix = mix_master_plan or {}
    arrangement = arrangement_qc or {}
    safety = _safety(reference_profile, mix)
    false_claim_risk = _false_claim_risk(mix)
    final_verified = bool((manifest.get("final_wav") or {}).get("verified"))
    gate_complete = bool(gate.get("complete"))
    technical_score = 5 if final_verified and gate_complete else 3 if arrangement.get("plan_pass") else 1
    scores = _base_scores(arrangement, mix, safety, technical_score, input_mode)
    average = round(sum(item["score"] for item in scores) / len(scores), 2)
    final_audio = manifest.get("final_wav") or manifest.get("final_master") or {}
    release_score = build_commercial_release_score(
        final_audio={
            **final_audio,
            "verified": final_verified,
            "format_verified": final_audio.get("format_verified", final_verified),
        },
        mix_master=mix,
        arrangement=arrangement,
        reference_profile=reference_profile,
        deliverable_manifest={"deliverables": [{"type": "final_master", "available": bool(final_audio.get("exists") or final_verified)}]},
        metadata_complete=False,
        rights={},
        rights_checklist_exists=False,
        release_manifest_exists=False,
        false_claim_risk=false_claim_risk,
        completion_gate=gate,
        qc_report_exists=gate_complete,
        master_qc_report_exists=gate_complete,
        release_qc_report_exists=False,
    )
    status = determine_commercial_status(
        average_score=average,
        arrangement_qc=arrangement,
        safety=safety,
        false_claim_risk=false_claim_risk,
        completion_gate=gate,
        render_manifest=manifest,
        input_mode=input_mode,
    )
    return {
        "schema_version": "commercial_readiness_qc.v1",
        "status": status,
        "average_score": average,
        "categories": scores,
        "safety": safety,
        "false_claim_risk": false_claim_risk,
        "commercial_release_score": release_score,
        "completion_gate_complete": gate_complete,
        "final_wav_verified": final_verified,
        "capability_statement": _capability_statement(status),
    }


def determine_commercial_status(
    *,
    average_score: float,
    arrangement_qc: dict[str, Any],
    safety: dict[str, Any],
    false_claim_risk: dict[str, Any],
    completion_gate: dict[str, Any],
    render_manifest: dict[str, Any],
    input_mode: str,
) -> str:
    gate_complete = bool(completion_gate.get("complete"))
    final_verified = bool((render_manifest.get("final_wav") or {}).get("verified"))
    final_exists = bool((render_manifest.get("final_wav") or {}).get("exists"))
    if safety.get("unsafe_exact_copy_claim") or safety.get("voice_clone_claim") or false_claim_risk.get("high"):
        return "FAIL_REPROCESS"
    if final_exists and (not final_verified or not gate_complete):
        return "FAIL_REPROCESS"
    if gate_complete and final_verified:
        return "FINAL_PASS"
    if arrangement_qc.get("needs_more_input") or safety.get("requires_owned_source") or (input_mode != "stems" and _requires_stems(safety)):
        return "NEEDS_MORE_INPUT"
    if arrangement_qc.get("plan_pass") and average_score >= 4.0:
        return "PLAN_PASS"
    if arrangement_qc:
        return "NEEDS_LOGIC_PRODUCTION"
    return "NEEDS_MORE_INPUT"


def _base_scores(arrangement: dict[str, Any], mix: dict[str, Any], safety: dict[str, Any], technical_score: int, input_mode: str) -> list[dict[str, Any]]:
    by_name = {item["name"]: item["score"] for item in arrangement.get("categories", [])}
    priorities = set(mix.get("mix_priorities", []))
    guards = mix.get("false_claim_guards", {})
    return [
        _item("Hook impact", by_name.get("Hook impact", 3)),
        _item("Arrangement intentionality", by_name.get("Arrangement intentionality", 3)),
        _item("Sample/motif usability", by_name.get("Sample/motif usability", 3)),
        _item("Vocal phrase usability", by_name.get("Vocal phrase usability", 3)),
        _item("Vocal commercial readiness", 4 if "vocal_forwardness" in priorities else 3),
        _item("Drum/808 guide strength", by_name.get("Drum/808 guide strength", 3)),
        _item("Kick/bass commercial impact", 4 if "controlled_808" in priorities else 3),
        _item("Melody/vibe preservation", by_name.get("Melody/vibe preservation", 3)),
        _item("Synth width/space plan", by_name.get("Synth width/space plan", 3)),
        _item("Digicore/hyperpop/internet underground style fit", 4 if "digicore" in str(mix.get("style_target", "")) or "hyperpop" in str(mix.get("style_target", "")) else 3),
        _item("AI artifact cleanup", 4 if "no random AI harshness" in mix.get("commercial_style_target", []) else 3),
        _item("Reference safety compliance", 5 if safety.get("safe") else 1),
        _item("Stereo/stem limitation honesty", 5 if not guards.get("stem_level_remix_claimed") else 1),
        _item("Technical delivery", technical_score),
        _item("Logic manual clarity", by_name.get("Logic manual clarity", 3)),
        _item("Completion integrity", 5 if technical_score == 5 else 3 if not guards.get("completion_claimed") else 1),
    ]


def _item(name: str, score: int) -> dict[str, Any]:
    return {"name": name, "score": max(1, min(5, int(score)))}


def _safety(reference_profile: dict[str, Any] | None, mix: dict[str, Any]) -> dict[str, Any]:
    copying = (reference_profile or {}).get("copying_policy") or {}
    traits = (reference_profile or {}).get("reference_traits") or {}
    unsafe_copy = bool(copying.get("copying_requested") and not copying.get("exact_copy_allowed") and copying.get("claim_exact_copy"))
    voice_clone = bool(traits.get("vocal", {}).get("identity_clone_allowed"))
    requires_owned = bool(copying.get("requires_user_owned_source"))
    return {
        "safe": not unsafe_copy and not voice_clone,
        "unsafe_exact_copy_claim": unsafe_copy,
        "voice_clone_claim": voice_clone,
        "requires_owned_source": requires_owned,
        "copying_requested": bool(copying.get("copying_requested")),
        "exact_copy_allowed": bool(copying.get("exact_copy_allowed")),
        "report_note": copying.get("report_note", "Exact copy not claimed; trait-match plan remains allowed."),
        "input_mode": mix.get("input_mode"),
    }


def _false_claim_risk(mix: dict[str, Any]) -> dict[str, Any]:
    guards = mix.get("false_claim_guards") or {}
    risky = [
        key
        for key in ("auto_tune_applied", "decapitator_applied", "plugin_processing_verified", "stem_level_remix_claimed", "completion_claimed")
        if bool(guards.get(key))
    ]
    return {"high": bool(risky), "risky_flags": risky}


def _requires_stems(safety: dict[str, Any]) -> bool:
    return bool(safety.get("copying_requested") and safety.get("requires_owned_source"))


def _capability_statement(status: str) -> str:
    if status == "PLAN_PASS":
        return "Plan is commercially useful, but not final audio completion. Manual Logic production is required."
    if status == "FINAL_PASS":
        return "Final WAV and QC passed through completion gate."
    if status == "FAIL_REPROCESS":
        return "Reprocess or revise before any completion claim."
    if status == "NEEDS_MORE_INPUT":
        return "More reliable audio, stems, BPM/key, hook, vocal phrase, or ownership evidence is needed."
    return "Plan is useful but actual Logic production/stems are required."


def render_commercial_readiness_report(qc: dict[str, Any]) -> str:
    lines = [
        "# Commercial Readiness QC",
        "",
        f"- status: {qc['status']}",
        f"- average score: {qc['average_score']}",
        f"- final WAV verified: {str(bool(qc['final_wav_verified'])).lower()}",
        f"- completion gate complete: {str(bool(qc['completion_gate_complete'])).lower()}",
        f"- capability statement: {qc['capability_statement']}",
        "",
        "## Categories",
    ]
    lines.extend(f"- {item['name']}: {item['score']}/5" for item in qc["categories"])
    lines.extend(
        [
            "",
            "## Safety",
            f"- safe: {str(bool(qc['safety']['safe'])).lower()}",
            f"- exact copy allowed: {str(bool(qc['safety']['exact_copy_allowed'])).lower()}",
            f"- note: {qc['safety']['report_note']}",
            "",
            "## Release Package Scoring",
            f"- local release score average: {qc.get('commercial_release_score', {}).get('average_score')}",
            f"- commercial success claimed: {str(bool(qc.get('commercial_release_score', {}).get('commercial_success_claimed'))).lower()}",
            "",
            "## Completion",
            "- PLAN_PASS is not COMPLETE.",
            "- COMPLETE is allowed only when completion_gate complete is true.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
