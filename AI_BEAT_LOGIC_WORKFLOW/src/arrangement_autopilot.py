from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arrangement_templates import normalize_genre_mode, normalize_length_mode
from automation_guide import build_automation_guide
from bass_808_midi_guide import generate_bass_808_midi_guide
from bass_808_midi_pattern_export import generate_bass_808_midi_pattern_guide
from drum_midi_pattern_export import generate_drum_midi_guide
from drum_programming_guide import generate_drum_programming_guide
from logic_arrangement_plan import render_logic_arrangement_plan
from logic_status_schema import build_logic_autopilot_status
from melody_variation_planner import generate_melody_variation_guide
from midi_region_guide import build_midi_region_guide
from paths import PROJECT_ROOT
from progression_guide_generator import generate_chord_progression_guide
from production_package_builder import build_and_write_production_package
from sample_analysis import analyze_sample_audio
from sample_chop_guide import generate_sample_chop_guide
from section_progression_planner import plan_section_progression
from vocal_to_code import analyze_vocal_to_code


PLAN_STATUS = "ARRANGEMENT_PLAN_READY"
STYLE_SAFETY_NOTE = (
    "Reference prompts become high-level production targets only; no exact song, kick sample, bassline, "
    "melody, lyric, drum pattern, sound recording, or living artist vocal identity is copied."
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def load_arrangement_inputs(project_root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    root = Path(project_root)
    return {
        "creative_brief": _read_json(root / "02_EDIT_PLAN" / "creative_brief.json"),
        "reference_target_profile": _read_json(root / "08_REFERENCE_MATCH" / "reference_target_profile.json"),
        "commercial_autopilot": _read_json(root / "02_EDIT_PLAN" / "commercial_autopilot.json"),
        "sample_analysis": _read_json(root / "01_ANALYSIS" / "sample_analysis.json"),
        "vocal_to_code": _read_json(root / "01_ANALYSIS" / "vocal_to_code.json"),
        "song_structure_analysis": _read_json(root / "01_ANALYSIS" / "song_structure_analysis.json"),
        "dependency_capabilities": _read_json(root / "01_ANALYSIS" / "dependency_capabilities.json"),
        "ownership_policy": _read_json(root / "02_EDIT_PLAN" / "ownership_policy.json"),
    }


def _length_from_inputs(inputs: dict[str, Any], requested: str | None) -> str:
    if requested:
        return normalize_length_mode(requested)
    brief = inputs.get("creative_brief") or {}
    length = brief.get("length") or {}
    commercial = inputs.get("commercial_autopilot") or {}
    defaults = commercial.get("arrangement_defaults") or {}
    if defaults.get("target_hook_seconds") == 15:
        return "reels_15sec"
    if defaults.get("target_hook_seconds") == 30:
        return "short_30sec"
    return normalize_length_mode(length.get("mode"))


def _genre_from_inputs(inputs: dict[str, Any], requested: str | None) -> str:
    if requested:
        return normalize_genre_mode(requested)
    brief = inputs.get("creative_brief") or {}
    text = " ".join(
        str(value or "")
        for value in (
            brief.get("creative_target_text"),
            brief.get("style_cluster_text"),
            brief.get("raw_full_korean_request"),
            ((inputs.get("reference_target_profile") or {}).get("style_cluster") or {}).get("primary"),
        )
    ).lower()
    if "commercial" in text and ("digicore" in text or "hyperpop" in text):
        return "commercial_digicore_hyperpop"
    if "system seoul" in text or "시스템" in text:
        return "system_seoul_adjacent"
    if "hyperpop" in text or "하이퍼" in text:
        return "hyperpop"
    if "internet" in text or "언더" in text:
        return "internet_underground"
    if "hip" in text or "rap" in text:
        return "hip_hop"
    return "digicore"


def _request_text(inputs: dict[str, Any], fallback: str | None = None) -> str:
    brief = inputs.get("creative_brief") or {}
    profile = inputs.get("reference_target_profile") or {}
    return (
        fallback
        or brief.get("raw_full_korean_request")
        or brief.get("creative_target_text")
        or profile.get("reference_text")
        or ""
    )


def _ownership_policy(inputs: dict[str, Any]) -> dict[str, Any]:
    policy = inputs.get("ownership_policy")
    if policy:
        return policy
    sample_safety = ((inputs.get("sample_analysis") or {}).get("sample_usage_safety") or {})
    brief = inputs.get("creative_brief") or {}
    flags = brief.get("ownership_flags") or {}
    direct = bool(sample_safety.get("direct_sample_use_allowed") or flags.get("user_confirms_owned_or_licensed"))
    return {
        "ownership_status": sample_safety.get("ownership_status", "unknown"),
        "direct_sample_use_allowed": direct,
        "exact_copy_allowed": False,
        "report_note": sample_safety.get("policy_note", "Ownership is unknown unless explicitly confirmed."),
    }


def _stems_available(inputs: dict[str, Any]) -> bool:
    brief = inputs.get("creative_brief") or {}
    files = brief.get("input_files") or {}
    song = inputs.get("song_structure_analysis") or {}
    return bool(brief.get("mode") == "stems" or files.get("stems_folder") or song.get("input", {}).get("mode") == "stems")


def build_arrangement_autopilot_plan(
    *,
    creative_brief: dict[str, Any] | None = None,
    reference_target_profile: dict[str, Any] | None = None,
    commercial_autopilot: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    song_structure_analysis: dict[str, Any] | None = None,
    dependency_capabilities: dict[str, Any] | None = None,
    ownership_policy: dict[str, Any] | None = None,
    length_mode: str | None = None,
    genre: str | None = None,
    request_text: str | None = None,
    vocal_code: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inputs = {
        "creative_brief": creative_brief,
        "reference_target_profile": reference_target_profile,
        "commercial_autopilot": commercial_autopilot,
        "sample_analysis": sample_analysis,
        "vocal_to_code": vocal_to_code or vocal_code,
        "song_structure_analysis": song_structure_analysis,
        "dependency_capabilities": dependency_capabilities,
        "ownership_policy": ownership_policy,
    }
    selected_length = _length_from_inputs(inputs, length_mode)
    selected_genre = _genre_from_inputs(inputs, genre)
    owned_policy = _ownership_policy(inputs)
    stems_available = _stems_available(inputs)

    section_guide = plan_section_progression(
        length_mode=selected_length,
        genre_mode=selected_genre,
        song_structure=song_structure_analysis,
        sample_analysis=sample_analysis,
        vocal_to_code=inputs["vocal_to_code"],
    )
    chord_guide = generate_chord_progression_guide(sample_analysis, genre_mode=selected_genre)
    drum_guide = generate_drum_programming_guide(
        genre_mode=selected_genre,
        length_mode=selected_length,
        sample_analysis=sample_analysis,
        reference_profile=reference_target_profile,
    )
    bass_guide = generate_bass_808_midi_guide(
        chord_guide=chord_guide,
        song_structure=song_structure_analysis,
        stems_available=stems_available,
        genre_mode=selected_genre,
    )
    sample_chop = generate_sample_chop_guide(sample_analysis, owned_policy)
    melody_variation = generate_melody_variation_guide(
        sample_analysis=sample_analysis,
        vocal_to_code=inputs["vocal_to_code"],
        song_structure=song_structure_analysis,
    )

    return {
        "schema_version": "arrangement_plan.v1",
        "status": PLAN_STATUS,
        "complete": False,
        "no_complete_reason": "Plan/guides generated only; final WAV export and completion gate were not run.",
        "length_mode": selected_length,
        "genre_mode": selected_genre,
        "request_text": _request_text(inputs, request_text),
        "inputs_available": {key: bool(value) for key, value in inputs.items()},
        "analysis_context": {
            "sample_timing": (sample_analysis or {}).get("timing", {}),
            "sample_tonal": (sample_analysis or {}).get("tonal", {}),
            "vocal_phrase_count": len((inputs["vocal_to_code"] or {}).get("phrases", [])),
        },
        "section_progression_guide": section_guide,
        "chord_progression_guide": chord_guide,
        "bass_808_midi_guide": bass_guide,
        "drum_programming_guide": drum_guide,
        "sample_chop_guide": sample_chop,
        "melody_variation_guide": melody_variation,
        "logic_manual_plan": [
            "Create markers from section_progression_guide in Logic.",
            "Program drums and 808 manually or from MIDI guide; do not claim true rewrite from stereo-only audio.",
            "Apply sample chops only when ownership policy permits direct use.",
            "Use plugin settings as manual instructions unless a verified automation/render artifact exists.",
        ],
        "status_policy": {
            "plan_only_status": PLAN_STATUS,
            "final_wav_required_for_complete": True,
            "complete_may_print": False,
            "complete_rule": "Only the final completion gate path may emit the completion token after all checks pass.",
        },
        "safety": {
            "style_safety_note": STYLE_SAFETY_NOTE,
            "direct_sample_use_allowed": bool(sample_chop["direct_sample_use_allowed"]),
            "stem_level_rewrite_claimed": False,
            "plugin_applied_claimed": False,
            "logic_automation_success_claimed": False,
            "reference_copying_allowed": False,
        },
        "limitations": [
            "Arrangement autopilot produces plan files and guide JSON only.",
            "Final WAV is not required for ARRANGEMENT_PLAN_READY, and the completion token must not be emitted.",
            "Stereo-only inputs cannot support true stem-level remixing, guaranteed vocal removal, kick/bass replacement, drum rewrite, or plugin insertion claims.",
        ],
    }


def render_arrangement_plan_markdown(plan: dict[str, Any]) -> str:
    sections = plan["section_progression_guide"]["sections"]
    lines = [
        "# Arrangement Autopilot Plan",
        "",
        f"- status: {plan['status']}",
        f"- complete: {str(bool(plan['complete'])).lower()}",
        f"- length mode: {plan['length_mode']}",
        f"- genre mode: {plan['genre_mode']}",
        f"- request: {plan.get('request_text') or 'not provided'}",
        "",
        "## Section Progression",
        *[
            f"- {item['section_id']} {item['name']} {item['start']:.1f}-{item['end']:.1f}s: {item['arrangement_instruction']}"
            for item in sections
        ],
        "",
        "## Drum Guide",
        f"- kick: {plan['drum_programming_guide']['kick_character']}",
        f"- snare/clap: {plan['drum_programming_guide']['snare_clap_character']}",
        f"- hats: {plan['drum_programming_guide']['hat_density']}",
        "",
        "## Bass / 808 Guide",
        f"- sub mono: {str(bool(plan['bass_808_midi_guide']['sub_mono'])).lower()}",
        f"- movement: {plan['bass_808_midi_guide']['movement_density']}",
        f"- true rewrite status: {plan['bass_808_midi_guide']['true_rewrite_status']}",
        "",
        "## Sample Safety",
        f"- direct sample use allowed: {str(bool(plan['sample_chop_guide']['direct_sample_use_allowed'])).lower()}",
        f"- ownership: {plan['sample_chop_guide']['ownership_status']}",
        "",
        "## Safety / Limitations",
        f"- {plan['safety']['style_safety_note']}",
        *[f"- {item}" for item in plan.get("limitations", [])],
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_arrangement_plan(project_root: str | Path, plan: dict[str, Any]) -> dict[str, Path]:
    root = Path(project_root)
    edit_dir = root / "02_EDIT_PLAN"
    edit_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "json": edit_dir / "arrangement_plan.json",
        "markdown": edit_dir / "arrangement_plan.md",
        "section_progression_guide": edit_dir / "section_progression_guide.json",
        "chord_progression_guide": edit_dir / "chord_progression_guide.json",
        "bass_808_midi_guide": edit_dir / "bass_808_midi_guide.json",
        "drum_programming_guide": edit_dir / "drum_programming_guide.json",
        "sample_chop_guide": edit_dir / "sample_chop_guide.json",
        "melody_variation_guide": edit_dir / "melody_variation_guide.json",
        "midi_region_guide": edit_dir / "midi_region_guide.json",
        "automation_guide": edit_dir / "automation_guide.json",
        "drum_midi_guide": edit_dir / "drum_midi_guide.json",
        "logic_arrangement_plan": edit_dir / "logic_arrangement_plan.md",
        "logic_autopilot_status": root / "03_LOGIC_PROJECT" / "logic_autopilot_status.json",
        "production_package_manifest": edit_dir / "production_package_manifest.json",
        "production_todo": edit_dir / "production_todo.md",
        "mix_prep_checklist": edit_dir / "mix_prep_checklist.md",
    }
    drum_midi = generate_drum_midi_guide(plan)
    bass_midi = generate_bass_808_midi_pattern_guide(plan)
    midi_regions = build_midi_region_guide(plan, drum_midi_guide=drum_midi, bass_808_midi_guide=bass_midi)
    automation = build_automation_guide(plan, midi_regions)
    logic_status = build_logic_autopilot_status()
    logic_manual = render_logic_arrangement_plan(plan, midi_regions, automation, logic_status)
    outputs["json"].write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["markdown"].write_text(render_arrangement_plan_markdown(plan), encoding="utf-8")
    for key in (
        "section_progression_guide",
        "chord_progression_guide",
        "bass_808_midi_guide",
        "drum_programming_guide",
        "sample_chop_guide",
        "melody_variation_guide",
    ):
        outputs[key].write_text(json.dumps(plan[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["midi_region_guide"].write_text(json.dumps(midi_regions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["automation_guide"].write_text(json.dumps(automation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["drum_midi_guide"].write_text(json.dumps(drum_midi, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["bass_808_midi_guide"].write_text(json.dumps(bass_midi, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["logic_autopilot_status"].parent.mkdir(parents=True, exist_ok=True)
    outputs["logic_autopilot_status"].write_text(json.dumps(logic_status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs["logic_arrangement_plan"].write_text(logic_manual, encoding="utf-8")
    production_package = build_and_write_production_package(
        root,
        plan,
        midi_region_guide=midi_regions,
        automation_guide=automation,
        creative_brief=_read_json(root / "02_EDIT_PLAN" / "creative_brief.json"),
        vocal_to_code=_read_json(root / "01_ANALYSIS" / "vocal_to_code.json"),
        master_target="streaming_safe",
    )
    outputs.update(production_package["paths"])
    return outputs


def run_arrangement_autopilot(
    *,
    project_root: str | Path,
    sample_path: str | Path | None = None,
    vocal_path: str | Path | None = None,
    genre: str = "digicore",
    request_text: str | None = None,
    length_mode: str | None = None,
) -> dict[str, Any]:
    inputs = load_arrangement_inputs(project_root)
    if sample_path and not inputs.get("sample_analysis"):
        inputs["sample_analysis"] = analyze_sample_audio(sample_path, ownership_status="unknown")
    if vocal_path and not inputs.get("vocal_to_code"):
        inputs["vocal_to_code"] = analyze_vocal_to_code(vocal_path, mode="separate_vocal")
    if not any(inputs.get(key) for key in ("creative_brief", "sample_analysis", "vocal_to_code", "song_structure_analysis", "reference_target_profile")):
        raise ValueError("arrangement autopilot requires at least one brief or analysis input")
    plan = build_arrangement_autopilot_plan(
        creative_brief=inputs.get("creative_brief"),
        reference_target_profile=inputs.get("reference_target_profile"),
        commercial_autopilot=inputs.get("commercial_autopilot"),
        sample_analysis=inputs.get("sample_analysis"),
        vocal_to_code=inputs.get("vocal_to_code"),
        song_structure_analysis=inputs.get("song_structure_analysis"),
        dependency_capabilities=inputs.get("dependency_capabilities"),
        ownership_policy=inputs.get("ownership_policy"),
        length_mode=length_mode,
        genre=genre,
        request_text=request_text,
    )
    paths = write_arrangement_plan(project_root, plan)
    if inputs.get("vocal_to_code") and (inputs["vocal_to_code"] or {}).get("pitch_correction_guide"):
        pitch_path = Path(project_root) / "02_EDIT_PLAN" / "vocal_pitch_guide.json"
        pitch_path.write_text(
            json.dumps(inputs["vocal_to_code"]["pitch_correction_guide"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        paths["vocal_pitch_guide"] = pitch_path
    return {
        "plan": plan,
        "paths": paths,
        "json_path": str(paths["json"]),
        "markdown_path": str(paths["markdown"]),
    }


def render_arrangement_autopilot_markdown(plan: dict[str, Any]) -> str:
    return render_arrangement_plan_markdown(plan)
