from __future__ import annotations

from typing import Any

from humanization_rubric import autopilot_completion_integrity_note, expanded_qc_rubric, korean_request_interpretation_qc, reference_match_qc


def score_style_match(
    profile: dict[str, Any],
    analysis: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    source_type: str = "fallback_processed",
) -> dict[str, Any]:
    avoid = profile.get("avoid", [])
    parsed = profile.get("parsed_intent", {})
    source = profile.get("source", {})
    confidence = source.get("confidence", source.get("reference_confidence", "low"))
    notes = [
        "Style match is a high-level production target QC only.",
        "No exact reference track copying is measured or claimed.",
        f"Parsed target elements: {', '.join(parsed.get('target_elements', [])) or 'not provided'}.",
        f"Reference confidence: {confidence}.",
    ]
    score = 0.65 if confidence == "low" else 0.75 if confidence == "medium" else 0.85
    if "generic trap loop" in avoid:
        score += 0.05
    if source_type == "fallback_processed":
        score -= 0.1
        notes.append("Fallback stereo processing limits reference-match precision.")
    natural_qc = korean_request_interpretation_qc(profile, options or {})
    notes.extend(
        [
            f"Korean request evidence mode: {natural_qc['evidence_mode']}.",
            f"Korean request copying risk: {natural_qc['copying_risk']}; exact copy {natural_qc['exact_copy_status']}.",
            autopilot_completion_integrity_note((options or {}).get("autopilot_qc_status"), bool((verification or {}).get("passed", (verification or {}).get("ok", False)))),
        ]
    )
    rubric = reference_match_qc(
        profile,
        verification=verification,
        options=options or {},
        source_type=source_type,
        completion_gate_complete=bool((verification or {}).get("passed", (verification or {}).get("ok", False))),
        qc_report_exists=True,
        master_qc_report_exists=True,
        vocal_mode=(options or {}).get("vocal_mode"),
        enforce_completion=bool(verification),
    )
    expanded = expanded_qc_rubric(
        analysis=analysis,
        verification=verification,
        reference_profile=profile,
        options=options or {},
        source_type=source_type,
        qc_report_exists=True,
        final_wav_exists=bool((verification or {}).get("path")),
    )
    return {
        "score": min(1.0, score),
        "notes": notes,
        "rubric": rubric,
        "expanded_rubric": expanded,
        "natural_request_qc": natural_qc,
    }
