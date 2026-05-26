from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_artifact_detector import detect_over_compressed_sections, detect_repeated_ai_loops
from audio_analysis import mono_mix, read_wav_float
from hook_detector import detect_hook_candidates
from melody_focus_detection import detect_low_end_excess_and_melody_burial
from paths import PROJECT_ROOT
from section_detector import detect_sections, frame_energy_features
from transition_detector import detect_abrupt_transitions
from vocal_texture_detection import detect_vocal_like_textures
from bad_song_diagnosis import build_bad_song_diagnosis as build_core_bad_song_diagnosis
from bad_song_diagnosis import render_bad_song_diagnosis_markdown as render_core_bad_song_diagnosis_markdown


PLAN_STATUS = "RESCUE_PLAN_READY"
MIX_ONLY_NOT_ENOUGH = "MIX_ONLY_NOT_ENOUGH"
ARRANGEMENT_REBUILD_REQUIRED = "ARRANGEMENT_REBUILD_REQUIRED"
LEAD_MELODY_REQUIRED = "LEAD_MELODY_REQUIRED"
HOOK_IDENTITY_REQUIRED = "HOOK_IDENTITY_REQUIRED"
VOCAL_TEXTURE_CLEANUP_REQUIRED = "VOCAL_TEXTURE_CLEANUP_REQUIRED"
SAMPLE_MOTIF_REBUILD_REQUIRED = "SAMPLE_MOTIF_REBUILD_REQUIRED"

STYLE_SAFETY_NOTE = (
    "Reference artist/song prompts are broad production targets only; do not copy exact melodies, samples, "
    "lyrics, drum patterns, basslines, recordings, or artist vocal identities."
)


def _ratio(count: int, total: int) -> float:
    return float(count) / max(1.0, float(total))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _read_context(path: str | Path) -> dict[str, Any]:
    song_path = Path(path).expanduser()
    metadata, channels = read_wav_float(song_path)
    mono = mono_mix(channels)
    sample_rate = int(metadata["sample_rate"])
    duration = float(metadata["duration_seconds"])
    features = frame_energy_features(mono, sample_rate)
    return {
        "metadata": metadata,
        "channels": channels,
        "mono": mono,
        "sample_rate": sample_rate,
        "duration_seconds": duration,
        "features": features,
        "sections": detect_sections(features, duration),
        "hook_candidates": detect_hook_candidates(features, duration),
        "repeated_ai_loop_candidates": detect_repeated_ai_loops(features),
        "abrupt_transition_candidates": detect_abrupt_transitions(features),
        "over_compressed_sections": detect_over_compressed_sections(features),
        "low_end_and_melody": detect_low_end_excess_and_melody_burial(mono, sample_rate),
        "vocal_like_texture_candidates": detect_vocal_like_textures(channels, sample_rate),
    }


def _energy_contrast(features: list[dict[str, Any]]) -> float:
    if not features:
        return 0.0
    energies = [float(frame.get("energy", 0.0)) for frame in features]
    high = max(energies)
    low = min(energies)
    if high <= 1e-12:
        return 0.0
    return _clamp((high - low) / high)


def _section_variety(sections: list[dict[str, Any]]) -> float:
    if not sections:
        return 0.0
    labels = [str(section.get("name", "unknown")) for section in sections]
    return _clamp(len(set(labels)) / 4.0)


def _longest_section_ratio(sections: list[dict[str, Any]], duration: float) -> float:
    if duration <= 0 or not sections:
        return 1.0
    longest = max(float(section.get("end", 0.0)) - float(section.get("start", 0.0)) for section in sections)
    return _clamp(longest / duration)


def _hook_identity_score(hooks: list[dict[str, Any]], repeated_count: int, section_contrast: float) -> float:
    if not hooks:
        return 0.0
    top = max(float(hook.get("score", 0.0)) for hook in hooks)
    confidence_bonus = 0.12 if any(hook.get("confidence") == "high" for hook in hooks) else 0.0
    repetition_penalty = min(0.50, repeated_count * 0.05)
    flat_penalty = 0.30 if section_contrast < 0.18 else 0.0
    return _clamp(top + confidence_bonus - repetition_penalty - flat_penalty)


def _lead_melody_score(
    *,
    hook_score: float,
    melody_buried_count: int,
    low_end_count: int,
    vocal_texture_count: int,
    section_contrast: float,
) -> float:
    score = 0.45 * hook_score + 0.30 * section_contrast + 0.25
    score -= min(0.30, melody_buried_count * 0.08)
    score -= min(0.18, low_end_count * 0.04)
    score -= min(0.15, vocal_texture_count * 0.025)
    return _clamp(score)


def _arrangement_structure_score(sections: list[dict[str, Any]], features: list[dict[str, Any]], duration: float) -> float:
    contrast = _energy_contrast(features)
    variety = _section_variety(sections)
    longest_penalty = max(0.0, _longest_section_ratio(sections, duration) - 0.45)
    count_bonus = _clamp(len(sections) / 5.0) * 0.25
    return _clamp(0.42 * contrast + 0.33 * variety + count_bonus - longest_penalty)


def _sample_folder_audio_files(sample_folder: str | Path | None, limit: int = 12) -> list[str]:
    if not sample_folder:
        return []
    folder = Path(sample_folder).expanduser()
    if not folder.exists() or not folder.is_dir():
        return []
    allowed = {".wav", ".mp3", ".aiff", ".aif", ".flac", ".m4a"}
    return [str(path) for path in sorted(folder.iterdir()) if path.is_file() and path.suffix.lower() in allowed][:limit]


def build_bad_song_diagnosis(
    path: str | Path,
    *,
    mode: str = "full_song_stereo",
    request_text: str = "",
    song_structure_analysis: dict[str, Any] | None = None,
    general_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    song_path = Path(path).expanduser()
    try:
        context = _read_context(song_path)
    except Exception as error:  # noqa: BLE001 - rescue diagnosis must fail closed.
        return {
            "schema_version": "bad_song_diagnosis.v1",
            "status": PLAN_STATUS,
            "complete": False,
            "input": {"path": str(song_path), "mode": mode},
            "MIX_ONLY_NOT_ENOUGH": True,
            "required_routes": [
                ARRANGEMENT_REBUILD_REQUIRED,
                LEAD_MELODY_REQUIRED,
                HOOK_IDENTITY_REQUIRED,
                VOCAL_TEXTURE_CLEANUP_REQUIRED,
                SAMPLE_MOTIF_REBUILD_REQUIRED,
            ],
            "flags": {"audio_read_failed": True},
            "scores": {},
            "limitations": [f"Audio could not be read: {error}", "No mix/master completion is claimed."],
        }

    duration = float(context["duration_seconds"])
    sections = song_structure_analysis.get("sections", context["sections"]) if song_structure_analysis else context["sections"]
    hooks = song_structure_analysis.get("hook_candidates", context["hook_candidates"]) if song_structure_analysis else context["hook_candidates"]
    repeated = song_structure_analysis.get("repeated_ai_loop_candidates", context["repeated_ai_loop_candidates"]) if song_structure_analysis else context["repeated_ai_loop_candidates"]
    abrupt = song_structure_analysis.get("abrupt_transition_candidates", context["abrupt_transition_candidates"]) if song_structure_analysis else context["abrupt_transition_candidates"]
    vocal_textures = (
        song_structure_analysis.get("vocal_like_texture_candidates", context["vocal_like_texture_candidates"])
        if song_structure_analysis
        else context["vocal_like_texture_candidates"]
    )
    low_end, melody_buried = context["low_end_and_melody"]
    if song_structure_analysis:
        low_end = song_structure_analysis.get("low_end_excess_candidates", low_end)
        melody_buried = song_structure_analysis.get("melody_buried_candidates", melody_buried)

    level = (general_analysis or {}).get("level_analysis", {})
    rms_dbfs = level.get("rms_dbfs")
    peak_dbfs = level.get("peak_dbfs")

    features = context["features"]
    contrast = _energy_contrast(features)
    hook_score = _hook_identity_score(hooks, len(repeated), contrast)
    lead_score = _lead_melody_score(
        hook_score=hook_score,
        melody_buried_count=len(melody_buried),
        low_end_count=len(low_end),
        vocal_texture_count=len(vocal_textures),
        section_contrast=contrast,
    )
    arrangement_score = _arrangement_structure_score(sections, features, duration)
    vocal_score = _clamp(1.0 - len(vocal_textures) * 0.12)
    motif_score = _clamp(0.55 * hook_score + 0.45 * lead_score)
    drum_support_score = _clamp(1.0 - len(low_end) * 0.08 - len(melody_buried) * 0.10)
    ai_artifact_risk = _clamp(max(_ratio(len(repeated), len(features)), len(abrupt) * 0.10, len(context["over_compressed_sections"]) * 0.07))

    flags = {
        "no_clear_lead_melody": lead_score < 0.48,
        "no_hook_identity": hook_score < 0.50,
        "no_arrangement_structure": arrangement_score < 0.46 or _longest_section_ratio(sections, duration) > 0.62,
        "weird_or_random_vocal_textures": len(vocal_textures) >= 3,
        "sections_repeat_without_intention": len(repeated) >= max(3, len(features) // 5),
        "drums_808_do_not_support_melody": drum_support_score < 0.58,
        "song_too_long": duration > 125.0,
        "loud_but_musically_weak": bool(rms_dbfs is not None and float(rms_dbfs) > -10.0 and max(hook_score, lead_score) < 0.55),
        "ai_glitches_transitions_dominate": len(abrupt) >= 3 or ai_artifact_risk > 0.42,
    }
    flags["generated_audio_feel"] = sum(1 for value in flags.values() if value) >= 3

    identity_failures = sum(
        1
        for key in ("no_clear_lead_melody", "no_hook_identity", "no_arrangement_structure")
        if flags[key]
    )
    mix_only_not_enough = bool(identity_failures >= 2 or (flags["generated_audio_feel"] and max(hook_score, lead_score) < 0.58))
    required_routes = []
    if mix_only_not_enough or flags["no_arrangement_structure"]:
        required_routes.append(ARRANGEMENT_REBUILD_REQUIRED)
    if mix_only_not_enough or flags["no_clear_lead_melody"]:
        required_routes.append(LEAD_MELODY_REQUIRED)
    if mix_only_not_enough or flags["no_hook_identity"]:
        required_routes.append(HOOK_IDENTITY_REQUIRED)
    if mix_only_not_enough or flags["weird_or_random_vocal_textures"]:
        required_routes.append(VOCAL_TEXTURE_CLEANUP_REQUIRED)
    if mix_only_not_enough or motif_score < 0.58:
        required_routes.append(SAMPLE_MOTIF_REBUILD_REQUIRED)

    return {
        "schema_version": "bad_song_diagnosis.v1",
        "status": PLAN_STATUS,
        "complete": False,
        "input": {"path": str(song_path), "mode": mode},
        "request_text": request_text,
        "duration_seconds": duration,
        "MIX_ONLY_NOT_ENOUGH": mix_only_not_enough,
        "decision": "ARRANGEMENT_REBUILD_REQUIRED" if mix_only_not_enough else "MIX_REPAIR_CAN_FOLLOW_RESCUE_PLAN",
        "required_routes": list(dict.fromkeys(required_routes)),
        "scores": {
            "lead_melody_score": round(lead_score, 4),
            "hook_identity_score": round(hook_score, 4),
            "arrangement_structure_score": round(arrangement_score, 4),
            "vocal_texture_cleanliness_score": round(vocal_score, 4),
            "sample_synth_motif_score": round(motif_score, 4),
            "drum_808_support_score": round(drum_support_score, 4),
            "ai_artifact_risk_score": round(ai_artifact_risk, 4),
            "section_energy_contrast": round(contrast, 4),
        },
        "flags": flags,
        "analysis_basis": {
            "sections_count": len(sections),
            "hook_candidates_count": len(hooks),
            "repeated_ai_loop_candidates_count": len(repeated),
            "abrupt_transition_candidates_count": len(abrupt),
            "vocal_like_texture_candidates_count": len(vocal_textures),
            "melody_buried_candidates_count": len(melody_buried),
            "low_end_excess_candidates_count": len(low_end),
            "rms_dbfs": rms_dbfs,
            "peak_dbfs": peak_dbfs,
        },
        "stereo_claim_guard": {
            "stem_level_remix_claimed": False,
            "vocal_removal_claimed": False,
            "kick_replacement_claimed": False,
            "drum_rewrite_claimed": False,
            "plugin_insertion_claimed": False,
            "logic_automation_success_claimed": False,
        },
        "limitations": [
            "Diagnosis is heuristic and should be confirmed by listening.",
            "Stereo-only input cannot prove or perform stem-level remixing.",
            "EQ/mastering is not treated as sufficient when musical identity is missing.",
            STYLE_SAFETY_NOTE,
        ],
    }


def _target_structure(duration: float) -> list[dict[str, Any]]:
    target_bpm = 160.0
    bar = 60.0 / target_bpm * 4.0
    structure = [
        ("intro_hook_tease", 0, 4, "tease the hook motif with no full vocal layer"),
        ("hook_1_identity", 4, 8, "present the main sample/synth motif clearly"),
        ("verse_vocal_answer", 12, 12, "lower density and place only intentional vocal answers"),
        ("pre_hook_lift", 24, 4, "remove clutter and rebuild tension into the hook"),
        ("hook_2_identity", 28, 12, "repeat and vary the exact hook identity, not random new material"),
        ("bridge_texture_reset", 40, 8, "short glitch/vocal cleanup bridge with strict edits"),
        ("final_hook", 48, 12, "strongest hook, supported by drums/808"),
        ("outro_hook_decay", 60, 4, "decay the hook motif quickly"),
    ]
    return [
        {
            "section": name,
            "start_bar": start_bar,
            "bars": bars,
            "start_seconds": round(start_bar * bar, 3),
            "end_seconds": round((start_bar + bars) * bar, 3),
            "instruction": instruction,
        }
        for name, start_bar, bars, instruction in structure
    ]


def build_rescue_arrangement_plan(diagnosis: dict[str, Any], *, request_text: str = "") -> dict[str, Any]:
    return {
        "schema_version": "rescue_arrangement_plan.v1",
        "status": PLAN_STATUS,
        "complete": False,
        "MIX_ONLY_NOT_ENOUGH": bool(diagnosis.get("MIX_ONLY_NOT_ENOUGH")),
        "decision": diagnosis.get("decision"),
        "required_routes": diagnosis.get("required_routes", []),
        "request_text": request_text or diagnosis.get("request_text", ""),
        "target": {
            "length_seconds": 96.0,
            "bpm": 160.0,
            "song_form": "intro -> hook -> verse -> pre-hook -> hook -> bridge -> final hook -> outro",
            "arrangement_priority": "hook identity before mix/master",
        },
        "sections": _target_structure(float(diagnosis.get("duration_seconds") or 96.0)),
        "rebuild_rules": [
            "Pick one lead motif and repeat it in every hook.",
            "Use the verse to answer the hook, not to introduce unrelated AI material.",
            "Cut or mute transitions that do not announce a section change.",
            "Keep drums/808 subordinate to the lead motif until the hook is recognizable.",
            "Move to mix/master only after the hook, lead, and section map are approved.",
        ],
        "status_policy": {
            "final_wav_required_for_complete": True,
            "completion_gate_required": True,
            "complete_may_print": False,
            "plan_status": PLAN_STATUS,
        },
        "safety": {
            "style_safety_note": STYLE_SAFETY_NOTE,
            "stem_level_remix_claimed": False,
            "logic_automation_success_claimed": False,
        },
    }


def build_lead_melody_plan(diagnosis: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "lead_melody_plan.v1",
        "status": PLAN_STATUS,
        "lead_melody_required": LEAD_MELODY_REQUIRED in diagnosis.get("required_routes", []),
        "composition_method": "new motif blueprint; do not transcribe or copy a reference melody",
        "motif_grid": [
            {"beat": 0.0, "degree": "1", "role": "anchor", "duration_beats": 0.5},
            {"beat": 0.5, "degree": "5", "role": "lift", "duration_beats": 0.25},
            {"beat": 0.75, "degree": "b7", "role": "digital color", "duration_beats": 0.25},
            {"beat": 1.25, "degree": "high 1", "role": "hook peak", "duration_beats": 0.5},
            {"beat": 2.0, "degree": "b7", "role": "answer", "duration_beats": 0.5},
            {"beat": 2.5, "degree": "5", "role": "fall", "duration_beats": 0.25},
            {"beat": 2.75, "degree": "4", "role": "tension", "duration_beats": 0.25},
            {"beat": 3.25, "degree": "5", "role": "loop-back", "duration_beats": 0.5},
        ],
        "sound_design": [
            "bright square/saw digital lead with controlled bit edge",
            "mono-compatible center lead plus short stereo throw delays",
            "filter automation only as section support, not as random motion",
        ],
        "approval_test": "The hook should still be identifiable when drums and vocals are muted.",
    }


def build_hook_identity_plan(diagnosis: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "hook_identity_plan.v1",
        "status": PLAN_STATUS,
        "hook_identity_required": HOOK_IDENTITY_REQUIRED in diagnosis.get("required_routes", []),
        "hook_pillars": [
            "one-bar lead motif repeated across all hooks",
            "one sample/synth call-sign on beats 1 and 3",
            "808 answer that follows motif roots instead of masking them",
            "same hook entrance every time with one controlled variation in final hook",
        ],
        "hook_fail_conditions": [
            "new riser or glitch appears without section purpose",
            "vocal texture replaces the lead motif",
            "drums become louder but hook motif is not memorable",
        ],
        "qc_questions": [
            "Can the listener hum or recognize the motif after one hook?",
            "Does hook 2 clearly relate to hook 1?",
            "Does the final hook feel like payoff, not another generated continuation?",
        ],
    }


def build_vocal_texture_rescue_plan(diagnosis: dict[str, Any], *, vocal_files: list[str]) -> dict[str, Any]:
    stems_available = bool(vocal_files)
    return {
        "schema_version": "vocal_texture_rescue_plan.v1",
        "status": PLAN_STATUS,
        "vocal_texture_cleanup_required": VOCAL_TEXTURE_CLEANUP_REQUIRED in diagnosis.get("required_routes", []),
        "stems_available": stems_available,
        "vocal_files": vocal_files,
        "stereo_only_limits": [] if stems_available else [
            "No vocal removal is claimed from a stereo-only file.",
            "Use mute/gain/EQ edits around detected vocal-like texture regions rather than claiming separation.",
        ],
        "cleanup_moves": [
            "keep lead vocal phrases only where they answer the section",
            "remove random adlib-like textures from hook unless they reinforce the motif",
            "band-limit weird AI vocal smears and push them behind the lead/synth motif",
            "use short throws on last words only; avoid continuous washed delay",
        ],
        "claims": {
            "vocal_removal_performed": False,
            "stem_level_vocal_mix_performed": False,
            "autotune_applied": False,
        },
    }


def build_sample_motif_rebuild_plan(
    diagnosis: dict[str, Any],
    *,
    sample_folder: str | Path | None = None,
    owned_samples: bool = False,
) -> dict[str, Any]:
    candidates = _sample_folder_audio_files(sample_folder)
    return {
        "schema_version": "sample_motif_rebuild_plan.v1",
        "status": PLAN_STATUS,
        "sample_motif_rebuild_required": SAMPLE_MOTIF_REBUILD_REQUIRED in diagnosis.get("required_routes", []),
        "sample_folder": str(sample_folder) if sample_folder else None,
        "candidate_audio_files": candidates,
        "direct_sample_use_allowed": bool(owned_samples),
        "ownership_note": "Direct sample use allowed only because the user marked samples owned/cleared." if owned_samples else "Treat samples as inspiration or manual candidates until ownership/clearance is confirmed.",
        "motif_roles": [
            {"role": "call-sign", "placement": "hook beats 1 and 3", "rule": "same rhythm every hook"},
            {"role": "counter-chop", "placement": "verse bar endings", "rule": "short answer, not new melody clutter"},
            {"role": "transition tag", "placement": "last half-bar before hook", "rule": "one recognizable tag only"},
        ],
        "copying_policy": STYLE_SAFETY_NOTE,
    }


def render_bad_song_diagnosis_markdown(diagnosis: dict[str, Any]) -> str:
    flags = diagnosis.get("flags", {})
    scores = diagnosis.get("scores", {})
    routes = diagnosis.get("required_routes", [])
    return "\n".join(
        [
            "# Bad AI Song Diagnosis",
            "",
            f"- status: {diagnosis.get('status')}",
            f"- complete: {str(bool(diagnosis.get('complete'))).lower()}",
            f"- input: {diagnosis.get('input', {}).get('path')}",
            f"- duration: {float(diagnosis.get('duration_seconds') or 0):.3f}s",
            f"- MIX_ONLY_NOT_ENOUGH: {str(bool(diagnosis.get('MIX_ONLY_NOT_ENOUGH'))).lower()}",
            f"- decision: {diagnosis.get('decision')}",
            "",
            "## Scores",
            *[f"- {key}: {value}" for key, value in scores.items()],
            "",
            "## Flags",
            *[f"- {key}: {str(bool(value)).lower()}" for key, value in flags.items()],
            "",
            "## Required Routes",
            *[f"- {item}" for item in routes],
            "",
            "## Limits",
            *[f"- {item}" for item in diagnosis.get("limitations", [])],
            "",
        ]
    )


def render_rescue_arrangement_markdown(plan: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Rescue Arrangement Plan",
            "",
            f"- status: {plan['status']}",
            f"- complete: {str(bool(plan['complete'])).lower()}",
            f"- MIX_ONLY_NOT_ENOUGH: {str(bool(plan['MIX_ONLY_NOT_ENOUGH'])).lower()}",
            f"- decision: {plan['decision']}",
            "",
            "## Target Form",
            f"- length: {plan['target']['length_seconds']}s",
            f"- bpm: {plan['target']['bpm']}",
            f"- form: {plan['target']['song_form']}",
            "",
            "## Sections",
            *[
                f"- {section['section']} {section['start_seconds']:.1f}-{section['end_seconds']:.1f}s: {section['instruction']}"
                for section in plan["sections"]
            ],
            "",
            "## Rebuild Rules",
            *[f"- {item}" for item in plan["rebuild_rules"]],
            "",
            "## Safety",
            f"- {plan['safety']['style_safety_note']}",
            "- No Logic automation success, plugin insertion, stem remix, vocal removal, drum rewrite, or final master is claimed by this plan.",
            "",
        ]
    )


def render_logic_rescue_plan_markdown(
    *,
    arrangement_plan: dict[str, Any],
    lead_melody_plan: dict[str, Any],
    hook_identity_plan: dict[str, Any],
    vocal_texture_plan: dict[str, Any],
    sample_motif_plan: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Logic Rescue Plan",
            "",
            f"- status: {PLAN_STATUS}",
            "- execution: manual Logic Pro plan only",
            "- verified Logic automation success: false",
            "",
            "## Marker Pass",
            *[
                f"- create marker `{section['section']}` at {section['start_seconds']:.1f}s; end {section['end_seconds']:.1f}s"
                for section in arrangement_plan["sections"]
            ],
            "",
            "## Lead / Hook Pass",
            f"- lead approval: {lead_melody_plan['approval_test']}",
            *[f"- hook pillar: {item}" for item in hook_identity_plan["hook_pillars"]],
            "",
            "## Vocal Cleanup Pass",
            *[f"- {item}" for item in vocal_texture_plan["cleanup_moves"]],
            "",
            "## Sample / Synth Motif Pass",
            *[f"- {item['role']}: {item['placement']} / {item['rule']}" for item in sample_motif_plan["motif_roles"]],
            "",
            "## Mix Handoff",
            "- Start mix/master only after the hook motif is approved in mute tests.",
            "- Keep stereo-only limitations visible; do not label edits as true stem processing.",
            "",
        ]
    )


def render_rescue_qc_report(
    *,
    diagnosis: dict[str, Any],
    arrangement_plan: dict[str, Any],
    demo_path: str | None = None,
    final_wav_path: str | None = None,
) -> str:
    return "\n".join(
        [
            "# Rescue QC Report",
            "",
            f"- status: {PLAN_STATUS}",
            f"- MIX_ONLY_NOT_ENOUGH: {str(bool(diagnosis.get('MIX_ONLY_NOT_ENOUGH'))).lower()}",
            f"- arrangement rebuild required: {str(ARRANGEMENT_REBUILD_REQUIRED in diagnosis.get('required_routes', [])).lower()}",
            f"- lead melody required: {str(LEAD_MELODY_REQUIRED in diagnosis.get('required_routes', [])).lower()}",
            f"- hook identity required: {str(HOOK_IDENTITY_REQUIRED in diagnosis.get('required_routes', [])).lower()}",
            f"- vocal texture cleanup required: {str(VOCAL_TEXTURE_CLEANUP_REQUIRED in diagnosis.get('required_routes', [])).lower()}",
            f"- sample motif rebuild required: {str(SAMPLE_MOTIF_REBUILD_REQUIRED in diagnosis.get('required_routes', [])).lower()}",
            f"- rescue demo rendered: {str(bool(demo_path)).lower()}",
            f"- final WAV rendered: {str(bool(final_wav_path)).lower()}",
            "- final WAV verified: false",
            "- completion gate passed: false",
            "",
            "## Plan Checks",
            f"- sections planned: {len(arrangement_plan.get('sections', []))}",
            "- lead melody plan written: true",
            "- hook identity plan written: true",
            "- vocal cleanup plan written: true",
            "- sample motif rebuild plan written: true",
            "",
            "## Blocking Notes",
            "- This rescue run is plan-ready only; no final master completion is claimed.",
            "- Mix/master is intentionally blocked until musical identity is rebuilt.",
            f"- {STYLE_SAFETY_NOTE}",
            "",
        ]
    )


def write_bad_ai_song_rescue_outputs(
    *,
    project_root: str | Path,
    diagnosis: dict[str, Any],
    arrangement_plan: dict[str, Any],
    lead_melody_plan: dict[str, Any],
    hook_identity_plan: dict[str, Any],
    vocal_texture_plan: dict[str, Any],
    sample_motif_plan: dict[str, Any],
) -> dict[str, Path]:
    root = Path(project_root)
    analysis_dir = root / "01_ANALYSIS"
    edit_dir = root / "02_EDIT_PLAN"
    qc_dir = root / "06_QC_REPORT"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    edit_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    logic_plan = render_logic_rescue_plan_markdown(
        arrangement_plan=arrangement_plan,
        lead_melody_plan=lead_melody_plan,
        hook_identity_plan=hook_identity_plan,
        vocal_texture_plan=vocal_texture_plan,
        sample_motif_plan=sample_motif_plan,
    )
    outputs = {
        "bad_song_diagnosis_json": analysis_dir / "bad_song_diagnosis.json",
        "bad_song_diagnosis_md": analysis_dir / "bad_song_diagnosis.md",
        "rescue_arrangement_plan_json": edit_dir / "rescue_arrangement_plan.json",
        "rescue_arrangement_plan_md": edit_dir / "rescue_arrangement_plan.md",
        "lead_melody_plan": edit_dir / "lead_melody_plan.json",
        "hook_identity_plan": edit_dir / "hook_identity_plan.json",
        "vocal_texture_rescue_plan": edit_dir / "vocal_texture_rescue_plan.json",
        "sample_motif_rebuild_plan": edit_dir / "sample_motif_rebuild_plan.json",
        "logic_rescue_plan": edit_dir / "logic_rescue_plan.md",
        "rescue_qc_report": qc_dir / "rescue_qc_report.md",
    }
    outputs["bad_song_diagnosis_json"].write_text(json.dumps(diagnosis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["bad_song_diagnosis_md"].write_text(render_bad_song_diagnosis_markdown(diagnosis), encoding="utf-8")
    outputs["rescue_arrangement_plan_json"].write_text(json.dumps(arrangement_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["rescue_arrangement_plan_md"].write_text(render_rescue_arrangement_markdown(arrangement_plan), encoding="utf-8")
    outputs["lead_melody_plan"].write_text(json.dumps(lead_melody_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["hook_identity_plan"].write_text(json.dumps(hook_identity_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["vocal_texture_rescue_plan"].write_text(json.dumps(vocal_texture_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["sample_motif_rebuild_plan"].write_text(json.dumps(sample_motif_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["logic_rescue_plan"].write_text(logic_plan, encoding="utf-8")
    outputs["rescue_qc_report"].write_text(
        render_rescue_qc_report(diagnosis=diagnosis, arrangement_plan=arrangement_plan),
        encoding="utf-8",
    )
    return outputs


def run_bad_ai_song_rescue(
    *,
    project_root: str | Path = PROJECT_ROOT,
    input_path: str | Path,
    mode: str = "full_song_stereo",
    request_text: str = "",
    song_structure_analysis: dict[str, Any] | None = None,
    general_analysis: dict[str, Any] | None = None,
    vocal_files: list[str] | None = None,
    sample_folder: str | Path | None = None,
    owned_samples: bool = False,
) -> dict[str, Any]:
    core_diagnosis = build_core_bad_song_diagnosis(input_path, mode=mode)
    diagnosis = build_bad_song_diagnosis(
        input_path,
        mode=mode,
        request_text=request_text,
        song_structure_analysis=song_structure_analysis,
        general_analysis=general_analysis,
    )
    arrangement_plan = build_rescue_arrangement_plan(diagnosis, request_text=request_text)
    lead_melody_plan = build_lead_melody_plan(diagnosis)
    hook_identity_plan = build_hook_identity_plan(diagnosis)
    vocal_texture_plan = build_vocal_texture_rescue_plan(diagnosis, vocal_files=list(vocal_files or []))
    sample_motif_plan = build_sample_motif_rebuild_plan(diagnosis, sample_folder=sample_folder, owned_samples=owned_samples)
    paths = write_bad_ai_song_rescue_outputs(
        project_root=project_root,
        diagnosis=diagnosis,
        arrangement_plan=arrangement_plan,
        lead_melody_plan=lead_melody_plan,
        hook_identity_plan=hook_identity_plan,
        vocal_texture_plan=vocal_texture_plan,
        sample_motif_plan=sample_motif_plan,
    )
    paths["bad_song_diagnosis_json"].write_text(json.dumps(core_diagnosis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["bad_song_diagnosis_md"].write_text(render_core_bad_song_diagnosis_markdown(core_diagnosis), encoding="utf-8")
    return {
        "status": PLAN_STATUS,
        "diagnosis": core_diagnosis,
        "arrangement_plan": arrangement_plan,
        "lead_melody_plan": lead_melody_plan,
        "hook_identity_plan": hook_identity_plan,
        "vocal_texture_rescue_plan": vocal_texture_plan,
        "sample_motif_rebuild_plan": sample_motif_plan,
        "paths": paths,
    }
