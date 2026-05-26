from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT
from vocal_demote_or_replace import build_vocal_texture_actions, has_separate_vocal_control, process_vocal_texture_demotion
from vocal_texture_classifier import classify_vocal_texture_candidates


def _mode_from_inputs(
    *,
    mode: str | None = None,
    rescue_diagnosis: dict[str, Any] | None = None,
    vocal_stem_path: str | Path | None = None,
) -> str:
    if mode:
        return str(mode)
    if vocal_stem_path:
        return "vocal_stem"
    diagnosis_mode = ((rescue_diagnosis or {}).get("input") or {}).get("mode")
    return str(diagnosis_mode or "unknown")


def _stereo_limitations(mode: str, has_vocal_stem: bool) -> list[str]:
    limitations = [
        "Stereo-only source cannot fully remove vocal texture.",
        "True replacement requires stems or manual Logic editing.",
        "This workflow demotes vocal-like texture and may add/plan a new lead role; it does not claim vocal removal.",
    ]
    if has_vocal_stem:
        limitations = [
            "Separate vocal/stem processing can shape that file, but final role replacement still needs arrangement decisions.",
            "True replacement of the lead identity may require manual Logic editing and a generated synth/sample lead.",
            "This workflow preserves voice identity and does not claim artist vocal imitation.",
        ]
    elif mode not in {"full_song_stereo", "unknown"}:
        limitations.append("Mode does not guarantee isolated vocal control unless a real vocal stem path is supplied.")
    return limitations


def _input_path_from_diagnosis(rescue_diagnosis: dict[str, Any] | None) -> str | None:
    return ((rescue_diagnosis or {}).get("input") or {}).get("path")


def build_vocal_texture_rescue_plan(
    *,
    input_path: str | Path | None = None,
    vocal_stem_path: str | Path | None = None,
    vocal_like_texture_candidates: list[dict[str, Any]] | None = None,
    creative_brief: dict[str, Any] | None = None,
    rescue_diagnosis: dict[str, Any] | None = None,
    mode: str | None = None,
    new_lead_available: bool = True,
) -> dict[str, Any]:
    resolved_mode = _mode_from_inputs(mode=mode, rescue_diagnosis=rescue_diagnosis, vocal_stem_path=vocal_stem_path)
    stem_control = has_separate_vocal_control(resolved_mode, vocal_stem_path)
    issues = classify_vocal_texture_candidates(
        vocal_like_texture_candidates,
        rescue_diagnosis=rescue_diagnosis,
        creative_brief=creative_brief,
        mode=resolved_mode,
    )
    actions = build_vocal_texture_actions(
        issues,
        mode=resolved_mode,
        has_vocal_stem=stem_control,
        new_lead_available=new_lead_available,
    )
    source_path = str(vocal_stem_path or input_path or _input_path_from_diagnosis(rescue_diagnosis) or "")
    return {
        "schema_version": "vocal_texture_rescue_plan.v1",
        "input": {
            "path": source_path,
            "mode": resolved_mode,
            "has_vocal_stem": stem_control,
        },
        "detected_issues": issues,
        "actions": actions,
        "processing_options": {
            "separate_vocal_stem": [
                "clip gain",
                "pitch approximation if requested",
                "de-ess",
                "tone shaping",
                "reverb/delay",
                "preserve voice identity",
            ],
            "full_stereo_only": [
                "dynamic EQ demotion",
                "mid/side attenuation if vocal texture is center-heavy",
                "no guaranteed removal",
                "add new lead motif to shift attention",
            ],
        },
        "claim_guard": {
            "vocal_removal_claimed": False,
            "stem_level_control_from_stereo_claimed": False,
            "artist_vocal_identity_imitation_claimed": False,
        },
        "limitations": _stereo_limitations(resolved_mode, stem_control),
    }


def write_vocal_texture_rescue_outputs(
    *,
    project_root: str | Path = PROJECT_ROOT,
    input_path: str | Path | None = None,
    vocal_stem_path: str | Path | None = None,
    vocal_like_texture_candidates: list[dict[str, Any]] | None = None,
    creative_brief: dict[str, Any] | None = None,
    rescue_diagnosis: dict[str, Any] | None = None,
    mode: str | None = None,
    process: bool = False,
    new_lead_available: bool = True,
) -> dict[str, Any]:
    root = Path(project_root)
    edit_dir = root / "02_EDIT_PLAN"
    processed_dir = root / "04_PROCESSED_AUDIO"
    edit_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    plan = build_vocal_texture_rescue_plan(
        input_path=input_path,
        vocal_stem_path=vocal_stem_path,
        vocal_like_texture_candidates=vocal_like_texture_candidates,
        creative_brief=creative_brief,
        rescue_diagnosis=rescue_diagnosis,
        mode=mode,
        new_lead_available=new_lead_available,
    )
    plan_path = edit_dir / "vocal_texture_rescue_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    processing_report: dict[str, Any] = {
        "created": False,
        "reason": "processing disabled; plan only",
        "claim_guard": {
            "vocal_removal_performed": False,
            "stem_level_control_from_stereo_claimed": False,
        },
    }
    source_path = vocal_stem_path or input_path or _input_path_from_diagnosis(rescue_diagnosis)
    if process:
        if source_path and plan["detected_issues"]:
            output_path = processed_dir / "vocal_texture_rescued.wav"
            processing_report = process_vocal_texture_demotion(
                source_path,
                output_path,
                plan["detected_issues"],
                mode=plan["input"]["mode"],
            )
        else:
            processing_report = {
                "created": False,
                "reason": "processing requested but no source audio or detected vocal texture issue was available",
                "claim_guard": {
                    "vocal_removal_performed": False,
                    "stem_level_control_from_stereo_claimed": False,
                },
            }

    return {
        "vocal_texture_rescue_plan": plan,
        "paths": {
            "vocal_texture_rescue_plan": plan_path,
            "vocal_texture_rescued": processed_dir / "vocal_texture_rescued.wav",
        },
        "processing": processing_report,
    }
