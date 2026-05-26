from __future__ import annotations

from pathlib import Path
from typing import Any

from arrangement_autopilot import build_arrangement_autopilot_plan
from reference_copying_policy import evaluate_copying_request
from reference_intent_parser import parse_reference_intent
from sample_arrangement_analyzer import analyze_sample_for_arrangement
from vocal_analysis import analyze_full_stereo_song
from vocal_phrase_coder import code_vocal_phrases


def _existing_path(value: str | Path | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.exists() and path.is_file() else None


def _existing_stems(stems: dict[str, str | Path | None] | None) -> dict[str, str]:
    existing: dict[str, str] = {}
    for label, value in (stems or {}).items():
        path = _existing_path(value)
        if path:
            existing[label] = str(path)
    return existing


def _workflow_type(
    *,
    sample_path: Path | None,
    vocal_path: Path | None,
    song_path: Path | None,
    stems: dict[str, str],
) -> str:
    if stems:
        return "stems_to_production"
    if sample_path and vocal_path:
        return "sample_vocal_to_arrangement"
    if sample_path:
        return "sample_to_arrangement_progression"
    if vocal_path:
        return "vocal_to_code"
    if song_path:
        return "song_to_arrangement_mix_master"
    return "planning_only"


def _logic_scope(workflow: str, stereo_only: bool, stems: dict[str, str]) -> list[str]:
    if workflow == "stems_to_production":
        return [
            "Use provided stems for more direct balance, section mutes, arrangement notes, and mix planning.",
            "Program or edit drums, 808, synths, vocals, adlibs, and backing vocals only inside the provided-source/manual Logic scope.",
            "Verify any rendered Logic export before claiming success.",
        ]
    if stereo_only:
        return [
            "Use broad stereo EQ, gain, fade, width, saturation, and mastering polish only.",
            "Mark kick/bass replacement, drum rewrite, vocal removal, and stem-level remix as manual Logic or stems required.",
            "Do not claim Logic Pro automation succeeded unless the project/export exists and is verified.",
        ]
    return [
        "Create a Logic session from the available local sources.",
        "Use analysis cues as arrangement and MIDI guide data, not as verified transcription.",
        "Render and verify any final WAV before completion.",
    ]


def _midi_region_guide(arrangement_plan: dict[str, Any] | None, workflow: str) -> dict[str, Any]:
    sections = []
    if arrangement_plan:
        legacy_items = arrangement_plan.get("arrangement_structure", [])
        section_items = arrangement_plan.get("section_progression_guide", {}).get("sections", [])
        for item in legacy_items:
            sections.append(
                {
                    "section": item.get("section"),
                    "region_type": "logic_manual_region",
                    "instruction": item.get("instruction"),
                }
            )
        for item in section_items:
            sections.append(
                {
                    "section": item.get("name"),
                    "region_type": "logic_manual_region",
                    "instruction": item.get("arrangement_instruction"),
                    "start": item.get("start"),
                    "end": item.get("end"),
                }
            )
    return {
        "format": "region_and_midi_guide_v1",
        "workflow": workflow,
        "guide_only": True,
        "regions": sections,
        "midi_notes": [
            "Use vocal phrase events as rough MIDI rhythm/note candidates only; verify by ear.",
            "Use sample motif and loop candidates as section anchors only when the source is owned/cleared.",
            "808/chord/drum programming must be created from scratch or from owned/provided stems/MIDI.",
        ],
    }


def build_producer_brain_plan(
    *,
    song_path: str | Path | None = None,
    sample_path: str | Path | None = None,
    vocal_path: str | Path | None = None,
    stems: dict[str, str | Path | None] | None = None,
    request_text: str | None = None,
    genre: str = "digicore",
    ownership_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_sample = _existing_path(sample_path)
    resolved_vocal = _existing_path(vocal_path)
    resolved_song = _existing_path(song_path)
    resolved_stems = _existing_stems(stems)
    workflow = _workflow_type(
        sample_path=resolved_sample,
        vocal_path=resolved_vocal,
        song_path=resolved_song,
        stems=resolved_stems,
    )
    stereo_only = bool(workflow == "song_to_arrangement_mix_master" and not resolved_stems)

    parsed_intent = parse_reference_intent(request_text or "")
    provided_files = {
        "song": str(resolved_song) if resolved_song else None,
        "sample": str(resolved_sample) if resolved_sample else None,
        "vocal": str(resolved_vocal) if resolved_vocal else None,
        "stems": resolved_stems,
    }
    copying_policy = evaluate_copying_request(parsed_intent, provided_files, ownership_flags or {})

    sample_analysis = analyze_sample_for_arrangement(resolved_sample, genre=genre) if resolved_sample else None
    vocal_code = code_vocal_phrases(resolved_vocal) if resolved_vocal else None
    song_analysis = analyze_full_stereo_song(resolved_song) if resolved_song and not resolved_stems else None
    arrangement_plan = build_arrangement_autopilot_plan(
        sample_analysis=sample_analysis,
        vocal_code=vocal_code,
        genre=genre,
        request_text=request_text,
    )
    arrangement_plan["active"] = workflow != "planning_only"
    if workflow == "planning_only":
        arrangement_plan["active"] = False

    return {
        "schema_version": 1,
        "brain_type": "local_ai_producer_brain",
        "workflow_type": workflow,
        "request_text": request_text or "",
        "inputs": {
            "song_path": str(resolved_song) if resolved_song else None,
            "sample_path": str(resolved_sample) if resolved_sample else None,
            "vocal_path": str(resolved_vocal) if resolved_vocal else None,
            "stems": resolved_stems,
        },
        "analysis": {
            "sample": sample_analysis,
            "vocal_code": vocal_code,
            "full_song": song_analysis,
            "stems": {
                "available": bool(resolved_stems),
                "labels": sorted(resolved_stems),
                "note": "Stem-level plans are limited to provided local files; no stem separation is claimed.",
            },
        },
        "arrangement_plan": arrangement_plan,
        "midi_region_guide": _midi_region_guide(arrangement_plan, workflow),
        "logic_production_instructions": _logic_scope(workflow, stereo_only, resolved_stems),
        "mix_master_plan": {
            "target": "technical readiness, mix clarity, arrangement control, and verified export discipline",
            "stereo_only": stereo_only,
            "fallback_scope": "broad stereo polish only" if stereo_only else "source-aware planning; rendered processing must still be verified",
            "commercial_promise_limit": "No commercial success, chart success, exact reference match, or model-level song generation is promised.",
        },
        "safety": {
            "reference_policy": "high_level_production_targets_only",
            "copying_policy": copying_policy,
            "living_artist_voice_clone_allowed": False,
            "downloads_copyrighted_web_audio": False,
            "scrapes_lyrics": False,
            "logic_success_faked": False,
            "completion_claim_allowed_here": False,
            "auto_tune_applied": False,
            "decapitator_applied": False,
        },
        "qc_checklist": [
            "Confirm stereo-only claims remain heuristic unless stems are provided.",
            "Confirm exact copy requests are blocked without owned/cleared local sources.",
            "Confirm no AutoTune, plugin insertion, stem separation, or Logic export is claimed without verification.",
            "Confirm final WAV completion remains gated by completion_gate from main.py only.",
        ],
        "limitations": [
            "This brain generates analysis-backed plans and guide data, not text-to-song generation.",
            "MIDI/region guides are production cues and must be verified by listening.",
            "Commercial quality means technical readiness and QC discipline, not guaranteed market success.",
        ],
    }
