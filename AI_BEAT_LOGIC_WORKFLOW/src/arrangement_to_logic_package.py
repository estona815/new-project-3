from __future__ import annotations

from typing import Any


def stems_available_from_context(arrangement_plan: dict[str, Any], creative_brief: dict[str, Any] | None = None) -> bool:
    brief = creative_brief or {}
    input_files = brief.get("input_files") or {}
    if brief.get("mode") == "stems" or input_files.get("stems_folder"):
        return True
    if arrangement_plan.get("genre_mode") == "stems":
        return True
    return False


def stereo_only_from_context(arrangement_plan: dict[str, Any], creative_brief: dict[str, Any] | None = None) -> bool:
    if stems_available_from_context(arrangement_plan, creative_brief):
        return False
    brief = creative_brief or {}
    input_files = brief.get("input_files") or {}
    provided = [value for value in input_files.values() if value]
    return bool((brief.get("mode") in {"full_song_stereo", "instrumental_beat", None}) or len(provided) <= 1)


def build_synth_width_panning_guide(arrangement_plan: dict[str, Any]) -> dict[str, Any]:
    genre = arrangement_plan.get("genre_mode") or arrangement_plan.get("style_target") or "commercial_digicore_hyperpop"
    width = "wide_high_layers" if genre in {"commercial_digicore_hyperpop", "hyperpop", "system_seoul_adjacent", "digicore"} else "moderate_width"
    return {
        "schema_version": "synth_width_panning_guide.v1",
        "status": "PRODUCTION_PACKAGE_READY",
        "width_target": width,
        "sub_mono_required": True,
        "low_frequency_mono_cutoff_hz": 120,
        "instructions": [
            "Keep kick, sub, and 808 centered.",
            "Widen high-passed synth layers, pads, adlibs, or upper bass harmonics only.",
            "Check mono compatibility before final export.",
        ],
        "claim_guard": {"panning_applied": False, "logic_project_modified": False},
    }


def build_vocal_production_guide(vocal_to_code: dict[str, Any] | None = None, arrangement_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    phrases = (vocal_to_code or {}).get("phrases", [])
    pitch = (vocal_to_code or {}).get("pitch_correction_guide") or {}
    return {
        "schema_version": "vocal_production_guide.v1",
        "status": "PRODUCTION_PACKAGE_READY",
        "phrase_count": len(phrases),
        "pitch_guide": pitch,
        "instructions": [
            "Keep lead vocal/melody forward when present.",
            "Use pitch guide as recommendation only; no AutoTune or pitch correction is claimed.",
            "Manual plugin insertion is required unless verified automation proves otherwise.",
        ],
        "claim_guard": {
            "auto_tune_applied": False,
            "voice_clone": False,
            "exact_transcription": False,
            "plugins_inserted": False,
        },
    }


def build_mix_prep_checklist(package: dict[str, Any]) -> list[str]:
    stereo_only = bool((package.get("capabilities") or {}).get("stereo_only"))
    checklist = [
        "Confirm session sample rate/export format before production work.",
        "Gain-stage imported audio before adding processing.",
        "Confirm BPM/key by ear before committing MIDI notes.",
        "Check sample ownership before direct chop/layer use.",
        "Keep sub/kick/808 mono-centered.",
        "Leave headroom for final master and no clipping in pre-master.",
        "Export pre-master only after manual arrangement and mix review.",
    ]
    if stereo_only:
        checklist.append("Stereo-only source: mark drum/808/vocal replacement tasks as manual/stems required.")
    else:
        checklist.append("Stems available: direct balancing is allowed, but plugin/render success still requires verification.")
    return checklist


def render_mix_prep_checklist(package: dict[str, Any]) -> str:
    checklist = package.get("mix_prep_checklist") or build_mix_prep_checklist(package)
    return "\n".join(["# Mix Prep Checklist", "", *[f"- {item}" for item in checklist]]) + "\n"


def convert_arrangement_to_logic_package(
    arrangement_plan: dict[str, Any],
    *,
    midi_region_guide: dict[str, Any],
    automation_guide: dict[str, Any],
    creative_brief: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    master_target: str = "streaming_safe",
) -> dict[str, Any]:
    section_plan = arrangement_plan.get("section_progression_guide") or {}
    sample_chop = arrangement_plan.get("sample_chop_guide") or {}
    chord = arrangement_plan.get("chord_progression_guide") or {}
    drum = arrangement_plan.get("drum_programming_guide") or {}
    bass = arrangement_plan.get("bass_808_midi_guide") or {}
    stems = stems_available_from_context(arrangement_plan, creative_brief)
    stereo_only = stereo_only_from_context(arrangement_plan, creative_brief)
    synth_width = build_synth_width_panning_guide(arrangement_plan)
    vocal = build_vocal_production_guide(vocal_to_code, arrangement_plan)
    manual_logic = [
        "Logic arrangement, MIDI import, plugin insertion, automation, and bounce require manual or verified execution.",
        "No false Logic automation success is claimed by this package.",
    ]
    if stereo_only:
        manual_logic.append("Stereo-only source: stem-level drum/808/vocal moves require stems, MIDI, or manual layers.")
    if not sample_chop.get("direct_sample_use_allowed"):
        manual_logic.append("Sample ownership unknown or unconfirmed: direct sample use is blocked.")
    return {
        "schema_version": "arrangement_to_logic_package.v1",
        "status": "PRODUCTION_PACKAGE_READY",
        "complete": False,
        "song_structure": {
            "length_mode": arrangement_plan.get("length_mode"),
            "genre_mode": arrangement_plan.get("genre_mode"),
            "request_text": arrangement_plan.get("request_text"),
        },
        "section_plan": section_plan,
        "chord_progression_guide": chord,
        "sample_chop_guide": sample_chop,
        "drum_programming_guide": drum,
        "bass_808_midi_guide": bass,
        "synth_width_panning_guide": synth_width,
        "vocal_guide": vocal,
        "midi_region_guide": midi_region_guide,
        "automation_guide": automation_guide,
        "master_target": master_target,
        "capabilities": {
            "stems_available": stems,
            "stereo_only": stereo_only,
            "direct_stem_balancing_allowed": stems,
            "stem_level_tasks_require_stems": stereo_only,
        },
        "plugin_requirements": [
            "Manual plugin insert required unless plugin availability and insertion are verified.",
            "Vocal tuning/saturation plugin references are style instructions, not applied-plugin claims.",
        ],
        "manual_logic_requirements": manual_logic,
        "claim_guard": {
            "logic_automation_success": False,
            "midi_imported_into_logic": False,
            "plugins_inserted": False,
            "final_wav_exported": False,
        },
    }
