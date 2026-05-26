from __future__ import annotations

from typing import Any


def reference_plain_language(profile: dict[str, Any]) -> str:
    text = profile.get("source", {}).get("reference_text", "")
    style = profile.get("style_targets", {})
    genres = ", ".join(style.get("genre_family", [])) or "modern hip-hop"
    if "love blur" in text.lower():
        return (
            "Reference-inspired energetic digital underground drum feel: fast hook lift, punchy controlled drums, "
            "bright digicore-compatible energy, and a non-generic trap bounce."
        )
    return (
        f"Reference-inspired {genres} direction with energy {style.get('energy', 3)}/5, "
        f"brightness {style.get('brightness', 3)}/5, and low-end weight {style.get('low_end_weight', 3)}/5."
    )


def autopilot_completion_integrity_note(status: str | None, completion_gate_complete: bool) -> str:
    if status == "PLAN_PASS" and not completion_gate_complete:
        return "PLAN_PASS means arrangement/mix guidance is ready; it is not COMPLETE and does not claim final WAV completion."
    if status == "FINAL_PASS" and completion_gate_complete:
        return "FINAL_PASS is supported by verified final WAV, QC artifacts, and completion gate."
    return "COMPLETE remains blocked unless completion_gate complete is true."


def _score(value: int) -> int:
    return max(1, min(5, int(value)))


def _has_vocal_context(options: dict[str, Any] | None, vocal_mode: str | None) -> bool:
    opts = options or {}
    mode = opts.get("project_mode") or opts.get("mode")
    return bool(mode in {"vocal_plus_beat", "full_song_stereo", "stems"} or (vocal_mode and vocal_mode not in {"none", "suppress"}))


def _source_mode(options: dict[str, Any] | None) -> str:
    opts = options or {}
    brief = opts.get("creative_brief") or {}
    return str(brief.get("mode") or opts.get("project_mode") or opts.get("mode") or "instrumental_beat")


def _has_direct_sources(options: dict[str, Any] | None, source_type: str) -> bool:
    opts = options or {}
    brief = opts.get("creative_brief") or {}
    files = brief.get("input_files", {})
    if _source_mode(opts) == "stems" or files.get("stems_folder"):
        return True
    if files.get("lead_vocal_file") and (files.get("beat_file") or files.get("main_input")):
        return True
    if opts.get("lead_vocal_file") and (opts.get("beat_file") or opts.get("input")):
        return True
    return source_type in {"logic_export", "final_mix_master"} and _source_mode(opts) in {"vocal_plus_beat", "stems"}


def _target_elements(profile: dict[str, Any] | None) -> set[str]:
    parsed = (profile or {}).get("parsed_intent", {})
    traits = (profile or {}).get("reference_traits", {})
    targets = {str(item) for item in parsed.get("target_elements", [])}
    targets.update(str(item) for item in traits.get("target_elements", []))
    if len(targets) > 1:
        targets.discard("whole_song")
    return targets or {"whole_song"}


def _reference_needs_manual_edit(profile: dict[str, Any] | None) -> bool:
    return bool(_target_elements(profile) & {"bass", "808", "drums", "kick", "snare", "hats"})


def _verification_passed(verification: dict[str, Any]) -> bool:
    return bool(verification.get("passed", verification.get("ok", False)))


def _evidence_mode(profile: dict[str, Any]) -> str:
    traits = profile.get("reference_traits", {})
    safety = traits.get("safety", {})
    if safety.get("evidence_mode"):
        return str(safety["evidence_mode"])
    source = profile.get("source", {})
    web = profile.get("web_reference_research", {})
    if source.get("reference_audio_path"):
        return "audio_informed"
    if web.get("trait_inference_allowed"):
        return "web_informed"
    return "text_only"


def _ownership_status(profile: dict[str, Any], options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    copying = profile.get("copying_policy", {})
    if copying.get("exact_copy_allowed"):
        return "owned/cleared source confirmed"
    if brief.get("owned_reference_sample") or brief.get("owned_reference_stems"):
        return "ownership flag present, local source must be verified"
    if copying.get("requires_user_owned_source"):
        return "owned/cleared source required but not confirmed"
    return "not required"


def korean_request_interpretation_qc(
    profile: dict[str, Any] | None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = profile or {}
    options = options or {}
    parsed = profile.get("parsed_intent", {})
    traits = profile.get("reference_traits", {})
    safety = traits.get("safety", {})
    copying = profile.get("copying_policy", {})
    source = profile.get("source", {})
    brief = options.get("creative_brief") or {}
    raw_request = (
        brief.get("raw_full_korean_request")
        or parsed.get("raw_text")
        or source.get("reference_text")
        or options.get("reference_text")
        or options.get("creative_target")
        or "not provided"
    )
    exact_allowed = bool(copying.get("exact_copy_allowed", safety.get("exact_copy_allowed", False)))
    copying_risk = str(copying.get("copying_risk") or safety.get("copying_risk") or parsed.get("copying_risk", "none"))
    return {
        "raw_request": raw_request,
        "parsed_targets": sorted(_target_elements(profile)),
        "copying_risk": copying_risk,
        "exact_copy_allowed": exact_allowed,
        "exact_copy_status": "allowed with owned/cleared source" if exact_allowed else "blocked",
        "ownership_sample_status": _ownership_status(profile, options),
        "evidence_mode": _evidence_mode(profile),
        "confidence": str(source.get("confidence") or safety.get("confidence") or "low"),
        "copying_policy_note": copying.get("report_note", "No exact copying is performed or claimed."),
    }


def target_match_scores(
    profile: dict[str, Any] | None,
    *,
    verification: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    source_type: str = "fallback_processed",
    completion_gate_complete: bool = False,
    qc_report_exists: bool = True,
    master_qc_report_exists: bool = True,
) -> list[dict[str, Any]]:
    profile = profile or {}
    verification = verification or {}
    options = options or {}
    traits = profile.get("reference_traits", {})
    style = profile.get("style_targets", {})
    parsed = profile.get("parsed_intent", {})
    copying = profile.get("copying_policy", {})
    target_elements = _target_elements(profile)
    stereo_only = source_type == "fallback_processed" or _source_mode(options) == "full_song_stereo"
    direct_sources = _has_direct_sources(options, source_type)
    exact_copy_requested = bool(copying.get("copying_requested") or parsed.get("copying_risk") == "high")
    exact_copy_allowed = bool(copying.get("exact_copy_allowed"))
    evidence = _evidence_mode(profile)
    vocal = traits.get("vocal", {})
    synth = traits.get("synth_width", {})
    arrangement = traits.get("arrangement", {})
    avoid = profile.get("avoid", [])
    verification_ok = _verification_passed(verification)
    format_ok = bool(verification.get("format_verified", verification_ok))
    clipping = int(verification.get("clipping_count", 0) or 0)
    severe_clipping = clipping > 0

    copy_note = "exact sample copy was not performed; trait matching may still be acceptable" if exact_copy_requested and not exact_copy_allowed else "high-level trait match only"
    plugin_requested = bool(vocal.get("requested_plugin") == "Soundtoys Decapitator" or "decapitator" in str(parsed.get("raw_text", "")).lower() or "디카페이터" in str(parsed.get("raw_text", "")))
    plugin_applied = bool(options.get("decapitator_applied") or options.get("plugin_application_verified"))
    pitch_requested = vocal.get("pitch_correction") not in {None, "none"}
    pitch_available = bool(options.get("pitch_tool_available") or options.get("pitch_available"))

    kick_score = 4 if target_elements & {"kick", "drums"} else 3
    bass_score = _score(style.get("low_end_weight", 3))
    if stereo_only and target_elements & {"kick", "drums", "bass", "808", "bass_808"}:
        kick_score = min(kick_score, 3)
        bass_score = min(bass_score, 3)
    if exact_copy_requested and not exact_copy_allowed:
        kick_note = f"{evidence}; {copy_note}."
        bass_note = f"{evidence}; {copy_note}."
    else:
        kick_note = f"{evidence}; kick direction scored as broad production trait."
        bass_note = f"{evidence}; bass/808 direction scored as broad production trait."

    if plugin_requested and not plugin_applied:
        vocal_score = 3
        vocal_note = "Decapitator request not scored as plugin-applied; generic saturation approximation and manual Logic insert recommended."
    elif pitch_requested and not pitch_available:
        vocal_score = 3
        vocal_note = "Pitch correction requested but tool availability is not verified; manual Logic/AutoTune required."
    else:
        vocal_score = _score(style.get("vocal_forwardness", 3))
        vocal_note = "Vocal FX scored only from verified/generic-safe processing and plan evidence."

    autopilot = profile.get("commercial_digicore_autopilot") or traits.get("commercial_digicore_autopilot", {})
    style_cluster_active = any(token in str(parsed.get("raw_text", "")).lower() for token in ("2hollis", "ycs", "system seoul", "투홀리스", "시스템서울", "와이씨에스", "slayr", "jane remover", "슬레이어", "제인"))
    style_cluster_score = 4 if style_cluster_active else 3
    synth_score = _score(synth.get("stereo_width", 2 if "synth_width" not in target_elements else 4))
    if stereo_only and "synth_width" in target_elements:
        synth_score = min(synth_score, 3)
    melody_score = 4 if traits.get("melody", {}).get("preserve") else 3
    avoid_score = 4 if avoid else 3
    if any("cheap rage clipping" in str(item) or "random AI glitch" in str(item) for item in avoid):
        avoid_score = 4
    limitation_score = 2 if stereo_only and _reference_needs_manual_edit(profile) else 4 if stereo_only else 5
    technical_score = 5 if verification_ok and format_ok and not severe_clipping else 1
    integrity_score = 5 if verification_ok and qc_report_exists and master_qc_report_exists and completion_gate_complete and not severe_clipping else 1 if not verification_ok or severe_clipping else 3

    scores = [
        {"id": 1, "name": "Kick reference direction match", "score": kick_score, "note": kick_note},
        {"id": 2, "name": "Bass/808 reference direction match", "score": bass_score, "note": bass_note},
        {"id": 3, "name": "Vocal FX request match / Vocal reference direction match", "score": vocal_score, "note": vocal_note},
        {"id": 4, "name": "Style cluster match: 2hollis/ycs/SYSTEM SEOUL/etc.", "score": style_cluster_score, "note": "Scored as broad style cluster only; no exact artist/song copying."},
        {"id": 5, "name": "Synth width/panning request match", "score": synth_score, "note": "Sub/kick/808 fundamental must remain mono; stereo-only widening is limited."},
        {"id": 6, "name": "Melody preservation / Melody/vibe preservation", "score": melody_score, "note": "Melody preservation is scored separately from reference copying."},
        {"id": 7, "name": "Avoid-list compliance", "score": avoid_score, "note": "Avoid-list compliance is heuristic until a listening pass confirms it."},
        {"id": 8, "name": "Stereo-only limitation impact", "score": limitation_score, "note": "Stereo-only source pushes stem-level rewrite targets toward manual Logic edit; stereo-only processing cannot prove stem-level drum/bass edits." if stereo_only else "Direct sources/stems reduce stereo-only limitation."},
        {"id": 9, "name": "Final WAV technical verification", "score": technical_score, "note": "PASS is blocked by failed verification, severe clipping, or wrong bit depth/sample rate."},
        {"id": 10, "name": "Artifact/completion integrity", "score": integrity_score, "note": "COMPLETE is allowed only through completion_gate after required QC artifacts exist."},
    ]
    if autopilot.get("active"):
        readiness = 4
        notes = ["Commercial readiness means technical readiness, mix clarity, arrangement intentionality, and QC discipline."]
        if autopilot.get("stem_limit_requested") and stereo_only:
            readiness = 3
            notes.append("Stem-level commercial moves require manual Logic/stems; fallback stays stereo-only.")
        if verification and not verification_ok:
            readiness = 1
            notes.append("Commercial readiness is blocked by failed final verification.")
        scores.append(
            {
                "id": 11,
                "name": "Commercial digicore autopilot readiness",
                "score": readiness,
                "note": " ".join(notes),
            }
        )
    return scores


def reference_match_qc(
    profile: dict[str, Any] | None,
    *,
    verification: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    source_type: str = "fallback_processed",
    completion_gate_complete: bool = False,
    qc_report_exists: bool = True,
    master_qc_report_exists: bool = True,
    vocal_mode: str | None = None,
    enforce_completion: bool = True,
) -> dict[str, Any]:
    profile = profile or {}
    verification = verification or {}
    options = options or {}
    style = profile.get("style_targets", {})
    avoid = profile.get("avoid", [])
    parsed = profile.get("parsed_intent", {})
    source = profile.get("source", {})
    confidence = source.get("confidence", source.get("reference_confidence", "low"))
    reference_audio = bool(source.get("reference_audio_path"))
    web = profile.get("web_reference_research", {})
    web_informed = bool(web.get("sources") and web.get("trait_inference_allowed"))
    web_metadata_only = bool(web.get("sources") and not web.get("trait_inference_allowed"))
    text_only = bool(source.get("reference_text")) and not reference_audio
    stereo_only = source_type == "fallback_processed" or _source_mode(options) == "full_song_stereo"
    direct_sources = _has_direct_sources(options, source_type)
    vocal_context = _has_vocal_context(options, vocal_mode or options.get("vocal_mode"))
    target_elements = _target_elements(profile)
    verification_ok = _verification_passed(verification)
    clipping = int(verification.get("clipping_count", 0) or 0)
    severe_clipping = clipping > 0
    format_verified = bool(verification.get("format_verified", verification_ok))

    score_note = (
        "audio-informed heuristic"
        if reference_audio
        else "web-informed broad descriptors"
        if web_informed
        else "web-metadata-only/no sonic inference"
        if web_metadata_only
        else "heuristic/text-only"
        if text_only
        else "heuristic/no reference"
    )
    source_limit = "limited: stereo-only processing cannot prove stem-level drum/bass edits" if stereo_only else "direct scoring allowed when stems/separate sources were provided" if direct_sources else "manual listening still required"

    scores = target_match_scores(
        profile,
        verification=verification,
        options=options,
        source_type=source_type,
        completion_gate_complete=completion_gate_complete,
        qc_report_exists=qc_report_exists,
        master_qc_report_exists=master_qc_report_exists,
    )
    average = round(sum(item["score"] for item in scores) / len(scores), 2)
    blocking: list[str] = []
    manual_limitations: list[str] = []
    if enforce_completion:
        if not completion_gate_complete:
            blocking.append("completion gate did not pass")
        if not verification_ok:
            blocking.append("final WAV verification failed")
        if not format_verified:
            blocking.append("wrong sample rate/bit depth or unverified final format")
        if severe_clipping:
            blocking.append("severe clipping detected")
        if not qc_report_exists:
            blocking.append("qc_report.md missing")
        if not master_qc_report_exists:
            blocking.append("master_qc_report.md missing")
    if stereo_only and _reference_needs_manual_edit(profile):
        manual_limitations.append("reference requested bass/drum pattern or tone changes, but only stereo-level processing is available")
    if vocal_context and not direct_sources and target_elements & {"vocal"}:
        manual_limitations.append("vocal reference target requires separate vocal/beat or manual Logic edits")
    if blocking or average < 3.0:
        result = "FAIL_REPROCESS"
    elif manual_limitations or 3.0 <= average < 4.0:
        result = "NEEDS_MANUAL_LOGIC_EDIT"
    else:
        result = "PASS"
    return {
        "scores": scores,
        "average": average,
        "overall": average,
        "result": result,
        "blocking_reasons": blocking,
        "manual_limitations": manual_limitations,
        "scale": "1-5 honest reference-direction score; 5 is closest to the high-level production target",
        "limitation": source_limit,
        "target_elements": sorted(target_elements),
        "confidence": confidence,
        "text_only": text_only,
        "web_informed": web_informed,
        "web_metadata_only": web_metadata_only,
        "reference_audio_provided": reference_audio,
        "stereo_only": stereo_only,
        "exact_match_claimed": False,
        "korean_request_interpretation": korean_request_interpretation_qc(profile, options),
    }


def style_match_scores(profile: dict[str, Any], stereo_only: bool = True, vocal_mode: str | None = None) -> dict[str, Any]:
    source_type = "fallback_processed" if stereo_only else "logic_export"
    return reference_match_qc(
        profile,
        source_type=source_type,
        completion_gate_complete=True,
        qc_report_exists=True,
        master_qc_report_exists=True,
        vocal_mode=vocal_mode,
        enforce_completion=False,
    )


def expanded_qc_rubric(
    analysis: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    source_type: str = "fallback_processed",
    qc_report_exists: bool = True,
    master_qc_report_exists: bool = True,
    final_wav_exists: bool = True,
    completion_gate_complete: bool | None = None,
) -> dict[str, Any]:
    analysis = analysis or {}
    verification = verification or {}
    options = options or {}
    stereo_only = source_type == "fallback_processed"
    vocal_mode = options.get("vocal_mode", "suppress")
    vocal_context = _has_vocal_context(options, vocal_mode)
    low_end = analysis.get("low_end_excess_candidates", [])
    vocal_texture = analysis.get("vocal_like_texture_candidates", [])
    arrangement = analysis.get("arrangement_candidates", {})
    glitches = arrangement.get("ai_random_transition_or_glitch_candidates", [])
    repeated = arrangement.get("repeated_loop_blocks", [])
    warnings = verification.get("warnings", [])
    clipping = int(verification.get("clipping_count", 0) or 0)
    verification_passed = _verification_passed(verification)
    gate_complete = bool(completion_gate_complete) if completion_gate_complete is not None else verification_passed and qc_report_exists and master_qc_report_exists and final_wav_exists
    reference_style = (reference_profile or {}).get("style_targets", {})
    avoid = (reference_profile or {}).get("avoid", [])

    scores: list[dict[str, Any]] = [
        {"id": 1, "name": "Melody centrality", "score": 4 if not analysis.get("melody_buried_candidates") else 3, "note": "Heuristic melody-burial analysis."},
        {"id": 2, "name": "Original vibe preservation", "score": 4, "note": "Conservative processing is intended to preserve source vibe."},
        {"id": 3, "name": "Vocal texture control", "score": 3 if vocal_texture else 4, "note": "Stereo vocal-like texture control remains heuristic."},
        {"id": 4, "name": "Drum/808 balance", "score": 3 if low_end else 4, "note": "Low-end warning count drives this score."},
        {"id": 5, "name": "AI transition cleanup", "score": 3 if glitches else 4, "note": "Transition cleanup requires listening and manual edits."},
        {"id": 6, "name": "Arrangement intentionality", "score": 3 if repeated else 4, "note": "Repeated-loop and section heuristics drive this score."},
        {"id": 7, "name": "Mix headroom", "score": 5 if verification.get("peak_dbfs", 0.0) <= -1.0 and clipping == 0 else 2, "note": "Headroom score is based on peak and clipping."},
        {"id": 8, "name": "Reels/edit usefulness", "score": 4 if options.get("length_mode") in {"15sec_reels", "30sec_short_form", "under_2min"} else 3, "note": "Edit usefulness is based on length/edit mode."},
    ]
    if vocal_context:
        vocal_limit = "heuristic and limited from stereo-only processing" if stereo_only else "evaluated from separate vocal/beat context when available"
        scores.extend(
            [
                {"id": 9, "name": "Lead vocal intelligibility", "score": 2 if stereo_only else 3, "note": vocal_limit},
                {"id": 10, "name": "Vocal tone control", "score": 2 if stereo_only else 3, "note": vocal_limit},
                {"id": 11, "name": "Vocal/beat blend", "score": 2 if stereo_only else 3, "note": vocal_limit},
                {"id": 12, "name": "Adlib/backing control", "score": 2 if stereo_only else 3, "note": vocal_limit},
            ]
        )
    if reference_profile:
        ref_qc = reference_match_qc(
            reference_profile,
            verification=verification,
            options=options,
            source_type=source_type,
            completion_gate_complete=gate_complete,
            qc_report_exists=qc_report_exists,
            master_qc_report_exists=master_qc_report_exists,
            vocal_mode=vocal_mode,
        )
        for item in ref_qc["scores"]:
            scores.append({"id": 12 + item["id"], "name": item["name"], "score": item["score"], "note": item["note"]})
    average = round(sum(item["score"] for item in scores) / len(scores), 2)
    blocking: list[str] = []
    if not final_wav_exists:
        blocking.append("missing final WAV")
    if not qc_report_exists:
        blocking.append("missing QC report")
    if not master_qc_report_exists:
        blocking.append("missing master QC report")
    if not verification_passed:
        blocking.append("final WAV verification failed")
    if clipping > 0:
        blocking.append("critical clipping detected")
    if any("sample rate mismatch" in str(warning).lower() for warning in warnings):
        blocking.append("wrong export format or sample rate")
    if blocking or average < 3.0:
        result = "FAIL_REPROCESS"
    elif average < 4.0 or (stereo_only and reference_profile and _reference_needs_manual_edit(reference_profile)):
        result = "NEEDS_MANUAL_LOGIC_EDIT"
    else:
        result = "PASS"
    return {
        "scores": scores,
        "average": average,
        "result": result,
        "blocking_reasons": blocking,
        "stereo_only": stereo_only,
        "vocal_context": vocal_context,
        "scale": "1-5 honest heuristic score; stereo-only processing limits vocal/reference precision.",
    }


def render_expanded_qc_rubric(rubric: dict[str, Any]) -> str:
    lines = [
        "## Expanded QC Rubric",
        "",
        f"- scale: {rubric['scale']}",
        f"- average score: {rubric['average']}/5",
        f"- overall result: {rubric['result']}",
    ]
    if rubric["blocking_reasons"]:
        lines.append(f"- blocking reasons: {'; '.join(rubric['blocking_reasons'])}")
    if rubric["stereo_only"]:
        lines.append("- stereo-only note: vocal/reference scores are heuristic and limited.")
    for item in rubric["scores"]:
        lines.append(f"- {item['id']}. {item['name']}: {item['score']}/5 ({item['note']})")
    return "\n".join(lines) + "\n"


def render_style_match_qc(
    profile: dict[str, Any],
    stereo_only: bool = True,
    vocal_mode: str | None = None,
    verification: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    source_type: str | None = None,
    completion_gate_complete: bool = False,
    qc_report_exists: bool = True,
    master_qc_report_exists: bool = True,
    enforce_completion: bool = False,
) -> str:
    qc = reference_match_qc(
        profile,
        verification=verification,
        options=options,
        source_type=source_type or ("fallback_processed" if stereo_only else "logic_export"),
        completion_gate_complete=completion_gate_complete,
        qc_report_exists=qc_report_exists,
        master_qc_report_exists=master_qc_report_exists,
        vocal_mode=vocal_mode,
        enforce_completion=enforce_completion,
    )
    lines = [
        "## Reference Match QC",
        "",
        f"- scoring note: {qc['scale']}",
        f"- processing limitation: {qc['limitation']}",
        f"- confidence: {qc.get('confidence', 'low')}",
        f"- target support: {'audio-informed' if qc.get('reference_audio_provided') else 'web-informed' if qc.get('web_informed') else 'web-metadata-only' if qc.get('web_metadata_only') else 'heuristic/text-only' if qc.get('text_only') else 'not provided'}",
        f"- parsed target elements: {', '.join(qc.get('target_elements', [])) or 'not provided'}",
        f"- overall result: {qc['result']}",
    ]
    if qc["blocking_reasons"]:
        lines.append(f"- blocking reasons: {'; '.join(qc['blocking_reasons'])}")
    if qc["manual_limitations"]:
        lines.append(f"- manual limitations: {'; '.join(qc['manual_limitations'])}")
    interp = qc.get("korean_request_interpretation", {})
    if interp:
        lines.extend(
            [
                "",
                "## Korean Request Interpretation QC",
                f"- Raw request: {interp.get('raw_request', 'not provided')}",
                f"- Parsed targets: {', '.join(interp.get('parsed_targets', [])) or 'not provided'}",
                f"- Copying risk: {interp.get('copying_risk', 'none')}",
                f"- Exact-copy blocked or allowed: {interp.get('exact_copy_status', 'blocked')}",
                f"- Ownership/sample status: {interp.get('ownership_sample_status', 'not required')}",
                f"- Reference evidence mode: {interp.get('evidence_mode', 'text_only')}",
                f"- Confidence level: {interp.get('confidence', 'low')}",
                f"- Policy note: {interp.get('copying_policy_note', 'No exact copying is performed or claimed.')}",
                "",
                "## Target Match Scores",
            ]
        )
    for item in qc["scores"]:
        lines.append(f"- {item['id']}. {item['name']}: {item['score']}/5 ({item['note']})")
    lines.append("- legacy score alias: Drum reference direction match maps to Kick reference direction match for older reports.")
    lines.append(f"- overall reference match: {qc['overall']}/5")
    lines.append("- exact reference song match: not claimed")
    if qc.get("stereo_only"):
        lines.append("- Reference match is limited because only broad stereo processing was used.")
    lines.extend(["", "## Style Match QC", "", "- legacy label: see Reference Match QC above for the authoritative reference scoring."])
    return "\n".join(lines) + "\n"
