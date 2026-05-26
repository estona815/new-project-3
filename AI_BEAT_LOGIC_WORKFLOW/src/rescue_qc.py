from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT


QC_CATEGORIES = (
    "lead_melody_clarity",
    "hook_identity",
    "arrangement_structure",
    "section_contrast",
    "call_response_quality",
    "vocal_texture_control",
    "sample_motif_usefulness",
    "ai_randomness_reduction",
    "mix_balance",
    "low_end_control",
    "stereo_width_mono_safety",
    "master_technical_verification",
    "manual_logic_honesty",
    "commercial_readiness",
)

UNSAFE_CLAIM_KEYS = {
    "stem_level_remix_claimed",
    "stem_level_control_from_stereo_claimed",
    "vocal_removal_claimed",
    "vocal_removal_performed",
    "kick_replacement_claimed",
    "drum_rewrite_claimed",
    "plugin_insertion_claimed",
    "logic_automation_success_claimed",
}


def _score(value: float) -> int:
    return max(1, min(5, int(round(value))))


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _gate_complete(completion_gate: Any | None) -> bool:
    if completion_gate is None:
        return False
    if isinstance(completion_gate, dict):
        return _bool(completion_gate.get("complete"))
    return _bool(getattr(completion_gate, "complete", False))


def _gate_blocking(completion_gate: Any | None) -> list[str]:
    if completion_gate is None:
        return []
    if isinstance(completion_gate, dict):
        return [str(item) for item in completion_gate.get("blocking_reasons", [])]
    return [str(item) for item in getattr(completion_gate, "blocking_reasons", [])]


def _path_exists(path: str | Path | None) -> bool:
    return bool(path and Path(path).expanduser().exists())


def _clip_count(verification: dict[str, Any] | None) -> int:
    if not verification:
        return 0
    try:
        return int(verification.get("clipping_count") or 0)
    except (TypeError, ValueError):
        return 0


def _format_ok(verification: dict[str, Any] | None) -> bool:
    return bool(
        verification
        and verification.get("ok")
        and verification.get("format_verified")
        and int(verification.get("sample_rate") or 0) == 48_000
        and int(verification.get("bit_depth") or 0) == 24
        and _clip_count(verification) == 0
    )


def _demo_ok(verification: dict[str, Any] | None) -> bool:
    return bool(verification and verification.get("exists", True) and _clip_count(verification) == 0)


def _nested_claims(payload: Any) -> list[str]:
    claims: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in UNSAFE_CLAIM_KEYS and _bool(value):
                claims.append(key)
            claims.extend(_nested_claims(value))
    elif isinstance(payload, list):
        for item in payload:
            claims.extend(_nested_claims(item))
    return claims


def unsafe_claims(*payloads: Any) -> list[str]:
    claims: list[str] = []
    for payload in payloads:
        claims.extend(_nested_claims(payload))
    return list(dict.fromkeys(claims))


def _hook_appears_by(arrangement_plan: dict[str, Any] | None) -> float | None:
    if not arrangement_plan:
        return None
    value = arrangement_plan.get("hook_appears_by_seconds")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    hook_starts: list[float] = []
    for section in arrangement_plan.get("sections", []):
        if "hook" in str(section.get("name", section.get("section", ""))).lower():
            try:
                hook_starts.append(float(section.get("start_time", section.get("start", 999.0))))
            except (TypeError, ValueError):
                pass
    return min(hook_starts) if hook_starts else None


def _energy_values(arrangement_plan: dict[str, Any] | None) -> list[int]:
    values: list[int] = []
    for section in (arrangement_plan or {}).get("sections", []):
        try:
            values.append(int(section.get("energy", 3)))
        except (TypeError, ValueError):
            values.append(3)
    return values


def _lead_repetition(lead_plan: dict[str, Any] | None) -> dict[str, Any]:
    summary = (lead_plan or {}).get("hook_motif_summary") or {}
    return summary.get("repetition") or {}


def _has_response_motif(lead_plan: dict[str, Any] | None, sample_plan: dict[str, Any] | None) -> bool:
    motifs = (lead_plan or {}).get("motifs") or []
    if any(motif.get("motif_id") == "response_B" and motif.get("notes") for motif in motifs):
        return True
    selected = (sample_plan or {}).get("selected_samples") or []
    return any(item.get("role") == "response_motif" for item in selected)


def _score_item(score: int, reason: str) -> dict[str, Any]:
    return {"score": _score(score), "reason": reason}


def score_categories(
    *,
    diagnosis: dict[str, Any] | None = None,
    arrangement_plan: dict[str, Any] | None = None,
    lead_plan: dict[str, Any] | None = None,
    hook_plan: dict[str, Any] | None = None,
    vocal_texture_plan: dict[str, Any] | None = None,
    sample_motif_plan: dict[str, Any] | None = None,
    mix_report: dict[str, Any] | None = None,
    demo_verification: dict[str, Any] | None = None,
    final_verification: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    repetition = _lead_repetition(lead_plan)
    lead_rendered = bool(((mix_report or {}).get("bus_reports") or {}).get("generated_lead_bus", {}).get("new_lead_hook_rendered"))
    lead_score = 5 if lead_rendered and repetition.get("has_repetition") and repetition.get("has_variation") else 4 if lead_rendered else 3 if lead_plan and (lead_plan.get("motifs") or []) else 1

    hook_quality = (hook_plan or {}).get("motif_repetition_quality")
    hook_by = _hook_appears_by(arrangement_plan)
    hook_score = 5 if hook_quality == "structured_repeat_with_variation" and hook_by is not None and hook_by <= 8.0 else 4 if hook_quality == "structured_repeat_with_variation" and hook_by is not None and hook_by <= 15.0 else 3 if hook_plan else 1

    sections = (arrangement_plan or {}).get("sections") or []
    source_restructured = bool(((mix_report or {}).get("bus_reports") or {}).get("source_music_bus", {}).get("restructure_applied"))
    target_duration = float((arrangement_plan or {}).get("target_duration_seconds") or 999.0)
    arrangement_score = 5 if source_restructured and len(sections) >= 5 and target_duration <= 120.0 else 4 if len(sections) >= 4 and target_duration <= 120.0 else 2 if sections else 1

    energy = _energy_values(arrangement_plan)
    contrast = max(energy) - min(energy) if energy else 0
    section_contrast_score = 5 if contrast >= 4 and len(set(energy)) >= 3 else 4 if contrast >= 3 else 3 if contrast >= 2 else 1

    call_response_score = 5 if _has_response_motif(lead_plan, sample_motif_plan) and lead_rendered else 4 if _has_response_motif(lead_plan, sample_motif_plan) else 2

    detected_vocal_issues = (vocal_texture_plan or {}).get("detected_issues") or []
    vocal_demoted = bool(((mix_report or {}).get("bus_reports") or {}).get("vocal_texture_bus", {}).get("created"))
    vocal_actions = [action.get("type") for action in (vocal_texture_plan or {}).get("actions", [])]
    vocal_score = 5 if detected_vocal_issues and vocal_demoted else 4 if not detected_vocal_issues else 3 if "demote_texture" in vocal_actions else 2

    sample_quality = (sample_motif_plan or {}).get("quality_gates") or {}
    sample_bus = bool(((mix_report or {}).get("bus_reports") or {}).get("sample_motif_bus", {}).get("created"))
    if sample_motif_plan:
        sample_score = 5 if sample_quality.get("main_motif_returns_in_hook") and sample_bus else 4 if sample_quality.get("main_motif_returns_in_hook") else 2
    else:
        sample_score = 3

    ai_randomness_score = 5 if source_restructured and arrangement_score >= 4 else 4 if sections and ((arrangement_plan or {}).get("remove_or_reduce") or []) else 2

    metrics = (mix_report or {}).get("metrics") or {}
    clipping = int(metrics.get("clipping_count") or _clip_count(demo_verification) or _clip_count(final_verification))
    peak = metrics.get("peak_dbfs")
    try:
        peak_value = float(peak)
    except (TypeError, ValueError):
        peak_value = None
    mix_score = 5 if clipping == 0 and peak_value is not None and peak_value <= -1.0 else 4 if clipping == 0 and demo_verification else 2 if clipping else 1

    low_end_created = bool(((mix_report or {}).get("bus_reports") or {}).get("mid_side", {}).get("created"))
    low_score = 5 if low_end_created and clipping == 0 else 3 if low_end_created else 2

    try:
        width = float(metrics.get("side_mid_db"))
    except (TypeError, ValueError):
        width = -18.0
    stereo_score = 5 if low_end_created and -32.0 <= width <= -6.0 else 4 if low_end_created else 2

    if _format_ok(final_verification):
        master_score = 5
    elif _demo_ok(demo_verification):
        master_score = 3
    else:
        master_score = 1

    claims = unsafe_claims(diagnosis, vocal_texture_plan, sample_motif_plan, mix_report)
    manual_items = (arrangement_plan or {}).get("manual_logic_required") or []
    manual_score = 5 if not claims and manual_items else 4 if not claims else 1

    commercial_score = 5 if _format_ok(final_verification) and lead_score >= 4 and hook_score >= 4 and arrangement_score >= 4 and manual_score >= 4 else 4 if lead_score >= 4 and hook_score >= 4 and arrangement_score >= 4 else 2

    return {
        "lead_melody_clarity": _score_item(lead_score, "generated lead motif is rendered and/or planned with repeated variation"),
        "hook_identity": _score_item(hook_score, "hook motif quality and early hook arrival"),
        "arrangement_structure": _score_item(arrangement_score, "rescue sections and source restructure"),
        "section_contrast": _score_item(section_contrast_score, "energy curve contrast across sections"),
        "call_response_quality": _score_item(call_response_score, "response motif or sample response supports call-response"),
        "vocal_texture_control": _score_item(vocal_score, "weird vocal texture is demoted or not detected"),
        "sample_motif_usefulness": _score_item(sample_score, "sample motif role assignment and hook return"),
        "ai_randomness_reduction": _score_item(ai_randomness_score, "random AI sections/chops are reduced by arrangement"),
        "mix_balance": _score_item(mix_score, "mix headroom and clipping status"),
        "low_end_control": _score_item(low_score, "sub mono and low-end safety processing"),
        "stereo_width_mono_safety": _score_item(stereo_score, "stereo width remains controlled"),
        "master_technical_verification": _score_item(master_score, "demo/final WAV technical verification"),
        "manual_logic_honesty": _score_item(manual_score, "manual Logic limitations and no unsafe claims"),
        "commercial_readiness": _score_item(commercial_score, "musical identity plus technical readiness"),
    }


def _answer_checks(
    scores: dict[str, dict[str, Any]],
    *,
    arrangement_plan: dict[str, Any] | None,
    vocal_texture_plan: dict[str, Any] | None,
    sample_motif_plan: dict[str, Any] | None,
    final_verification: dict[str, Any] | None,
    demo_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    hook_by = _hook_appears_by(arrangement_plan)
    sample_quality = (sample_motif_plan or {}).get("quality_gates") or {}
    manual = list((arrangement_plan or {}).get("manual_logic_required") or [])
    manual.extend((vocal_texture_plan or {}).get("limitations") or [])
    return {
        "did_result_gain_clear_lead": scores["lead_melody_clarity"]["score"] >= 4,
        "did_hook_appear_early": bool(hook_by is not None and hook_by <= 15.0),
        "did_sections_become_intentional": scores["arrangement_structure"]["score"] >= 4 and scores["section_contrast"]["score"] >= 3,
        "did_weird_vocal_texture_stop_dominating": scores["vocal_texture_control"]["score"] >= 4,
        "did_sample_motif_feel_like_hook_not_random_chop": bool(sample_quality.get("main_motif_returns_in_hook")) if sample_motif_plan else None,
        "did_mix_master_pass_technical_checks": bool(_format_ok(final_verification) or _demo_ok(demo_verification)),
        "what_remains_manual": list(dict.fromkeys(str(item) for item in manual)) or ["Manual listening check of lead/hook balance and transitions."],
    }


def _verdict(
    scores: dict[str, dict[str, Any]],
    *,
    plan_exists: bool,
    demo_exists: bool,
    final_exists: bool,
    qc_report_exists: bool,
    final_verification: dict[str, Any] | None,
    completion_gate: Any | None,
    unsafe: list[str],
    stereo_manual_block: bool,
) -> tuple[str, list[str], bool]:
    blocking: list[str] = []
    if unsafe:
        blocking.append(f"unsafe claims present: {', '.join(unsafe)}")
    if _clip_count(final_verification) > 0:
        blocking.append("final WAV has clipping")
    if final_exists and not _format_ok(final_verification):
        blocking.append("final WAV is wrong format or failed verification")
    if unsafe or _clip_count(final_verification) > 0 or (final_exists and not _format_ok(final_verification)):
        return "FAIL_REPROCESS", blocking, False

    if scores["lead_melody_clarity"]["score"] <= 2 or scores["hook_identity"]["score"] <= 2:
        blocking.append("lead/hook still weak")
    if scores["arrangement_structure"]["score"] < 3:
        blocking.append("arrangement score below 3")
    if blocking:
        return "NEEDS_RECOMPOSITION", blocking, False

    if stereo_manual_block:
        blocking.append("stereo-only source prevents needed rewrite")
        return "NEEDS_MANUAL_LOGIC", blocking, False

    if final_exists and _format_ok(final_verification) and qc_report_exists and _gate_complete(completion_gate):
        return "FINAL_RESCUE_PASS", [], True
    if final_exists and not _gate_complete(completion_gate):
        blocking.extend(_gate_blocking(completion_gate) or ["completion gate did not pass"])
        return "FAIL_REPROCESS", blocking, False
    if demo_exists:
        return "RESCUE_DEMO_READY", ["demo WAV exists but final WAV is not verified"], False
    if plan_exists:
        return "RESCUE_PLAN_READY", ["plan exists but no final WAV was verified"], False
    return "NEEDS_RECOMPOSITION", ["no rescue plan or useful musical identity"], False


def build_rescue_qc(
    *,
    diagnosis: dict[str, Any] | None = None,
    arrangement_plan: dict[str, Any] | None = None,
    lead_plan: dict[str, Any] | None = None,
    hook_plan: dict[str, Any] | None = None,
    vocal_texture_plan: dict[str, Any] | None = None,
    sample_motif_plan: dict[str, Any] | None = None,
    mix_report: dict[str, Any] | None = None,
    demo_verification: dict[str, Any] | None = None,
    final_verification: dict[str, Any] | None = None,
    completion_gate: Any | None = None,
    qc_report_exists: bool = False,
    demo_wav_path: str | Path | None = None,
    final_wav_path: str | Path | None = None,
) -> dict[str, Any]:
    scores = score_categories(
        diagnosis=diagnosis,
        arrangement_plan=arrangement_plan,
        lead_plan=lead_plan,
        hook_plan=hook_plan,
        vocal_texture_plan=vocal_texture_plan,
        sample_motif_plan=sample_motif_plan,
        mix_report=mix_report,
        demo_verification=demo_verification,
        final_verification=final_verification,
    )
    unsafe = unsafe_claims(diagnosis, vocal_texture_plan, sample_motif_plan, mix_report)
    rescue = (diagnosis or {}).get("rescue_decision") or {}
    stereo_only = ((diagnosis or {}).get("input") or {}).get("mode") in {"full_song_stereo", "unknown", None}
    stereo_manual_block = bool(
        stereo_only
        and (rescue.get("vocal_texture_cleanup_required") or rescue.get("arrangement_rebuild_required"))
        and scores["vocal_texture_control"]["score"] <= 2
    )
    plan_exists = bool(arrangement_plan and lead_plan and hook_plan)
    demo_exists = bool(_demo_ok(demo_verification) or _path_exists(demo_wav_path))
    final_exists = bool((final_verification or {}).get("exists") or _path_exists(final_wav_path))
    verdict, blocking, complete_allowed = _verdict(
        scores,
        plan_exists=plan_exists,
        demo_exists=demo_exists,
        final_exists=final_exists,
        qc_report_exists=qc_report_exists,
        final_verification=final_verification,
        completion_gate=completion_gate,
        unsafe=unsafe,
        stereo_manual_block=stereo_manual_block,
    )
    overall = round(sum(item["score"] for item in scores.values()) / len(scores), 2)
    answers = _answer_checks(
        scores,
        arrangement_plan=arrangement_plan,
        vocal_texture_plan=vocal_texture_plan,
        sample_motif_plan=sample_motif_plan,
        final_verification=final_verification,
        demo_verification=demo_verification,
    )
    return {
        "schema_version": "rescue_qc.v1",
        "verdict": verdict,
        "complete_allowed": bool(complete_allowed),
        "overall_score": overall,
        "scores": scores,
        "blocking_reasons": blocking,
        "unsafe_claims": unsafe,
        "answer_checks": answers,
        "technical": {
            "demo_verified": _demo_ok(demo_verification),
            "final_verified": _format_ok(final_verification),
            "qc_report_exists": bool(qc_report_exists),
            "completion_gate_complete": _gate_complete(completion_gate),
        },
    }


def render_rescue_qc_markdown(qc: dict[str, Any], *, rendered_files: list[str] | None = None) -> str:
    answers = qc.get("answer_checks") or {}
    technical = qc.get("technical") or {}
    rendered = rendered_files or []
    blocking_lines = [f"- {item}" for item in qc.get("blocking_reasons", [])] if qc.get("blocking_reasons") else ["- none"]
    lines = [
        "# Rescue QC Report",
        "",
        f"- verdict: {qc.get('verdict')}",
        f"- complete_allowed: {str(bool(qc.get('complete_allowed'))).lower()}",
        f"- overall_score: {qc.get('overall_score')}",
        "",
        "## Scores",
    ]
    for key in QC_CATEGORIES:
        item = (qc.get("scores") or {}).get(key, {})
        lines.append(f"- {key}: {item.get('score', 'n/a')}/5 - {item.get('reason', '')}")
    lines.extend(
        [
            "",
            "## Required Checks",
            f"- Did the result gain a clear lead? {str(bool(answers.get('did_result_gain_clear_lead'))).lower()}",
            f"- Did the hook appear early? {str(bool(answers.get('did_hook_appear_early'))).lower()}",
            f"- Did sections become intentional? {str(bool(answers.get('did_sections_become_intentional'))).lower()}",
            f"- Did weird vocal texture stop dominating? {str(bool(answers.get('did_weird_vocal_texture_stop_dominating'))).lower()}",
            f"- Did sample motif feel like a hook rather than random chop? {answers.get('did_sample_motif_feel_like_hook_not_random_chop')}",
            f"- Did mix/master pass technical checks? {str(bool(answers.get('did_mix_master_pass_technical_checks'))).lower()}",
            "",
            "## Technical Status",
            f"- demo verified: {str(bool(technical.get('demo_verified'))).lower()}",
            f"- final verified: {str(bool(technical.get('final_verified'))).lower()}",
            f"- QC exists: {str(bool(technical.get('qc_report_exists'))).lower()}",
            f"- completion gate complete: {str(bool(technical.get('completion_gate_complete'))).lower()}",
            "",
            "## What Was Actually Rendered",
        ]
    )
    lines.extend([f"- {path}" for path in rendered] if rendered else ["- no audio was rendered; plan only"])
    lines.extend(
        [
            "",
            "## What Remains Manual",
            *[f"- {item}" for item in answers.get("what_remains_manual", [])],
            "",
            "## Blocking Reasons",
            *blocking_lines,
            "",
            "## Claim Guard",
            f"- unsafe claims: {', '.join(qc.get('unsafe_claims', [])) or 'none'}",
            "- stereo-only source cannot fully isolate stems.",
            "- no vocal removal, stem-level remix, plugin insertion, or Logic automation success is claimed without verification.",
            "",
        ]
    )
    return "\n".join(lines)


def write_rescue_qc_report(
    *,
    project_root: str | Path = PROJECT_ROOT,
    diagnosis: dict[str, Any] | None = None,
    arrangement_plan: dict[str, Any] | None = None,
    lead_plan: dict[str, Any] | None = None,
    hook_plan: dict[str, Any] | None = None,
    vocal_texture_plan: dict[str, Any] | None = None,
    sample_motif_plan: dict[str, Any] | None = None,
    mix_report: dict[str, Any] | None = None,
    demo_verification: dict[str, Any] | None = None,
    final_verification: dict[str, Any] | None = None,
    completion_gate: Any | None = None,
    rendered_files: list[str] | None = None,
    demo_wav_path: str | Path | None = None,
    final_wav_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    report_path = root / "06_QC_REPORT" / "rescue_qc_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    qc = build_rescue_qc(
        diagnosis=diagnosis,
        arrangement_plan=arrangement_plan,
        lead_plan=lead_plan,
        hook_plan=hook_plan,
        vocal_texture_plan=vocal_texture_plan,
        sample_motif_plan=sample_motif_plan,
        mix_report=mix_report,
        demo_verification=demo_verification,
        final_verification=final_verification,
        completion_gate=completion_gate,
        qc_report_exists=True,
        demo_wav_path=demo_wav_path,
        final_wav_path=final_wav_path,
    )
    report_path.write_text(render_rescue_qc_markdown(qc, rendered_files=rendered_files), encoding="utf-8")
    json_path = root / "06_QC_REPORT" / "rescue_qc_score.json"
    json_path.write_text(json.dumps(qc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"qc": qc, "report_path": report_path, "json_path": json_path}
