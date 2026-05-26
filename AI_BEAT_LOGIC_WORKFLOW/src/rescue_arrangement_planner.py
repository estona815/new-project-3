from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arrangement_templates import normalize_length_mode
from energy_curve_designer import design_energy_curve
from hook_identity_builder import build_hook_identity_plan
from paths import PROJECT_ROOT
from section_rebuilder import rebuild_sections


STYLE_SAFETY_NOTE = "exact copying prohibited"


def _read_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    resolved = Path(path)
    if not resolved.exists():
        return None
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _source_problem(diagnosis: dict[str, Any]) -> dict[str, bool]:
    rescue = diagnosis.get("rescue_decision") or {}
    flags = diagnosis.get("flags") or {}
    return {
        "mix_only_not_enough": bool(rescue.get("mix_only_not_enough") or diagnosis.get("MIX_ONLY_NOT_ENOUGH")),
        "missing_lead": bool(rescue.get("lead_melody_required") or flags.get("no_clear_lead_melody")),
        "missing_hook": bool(rescue.get("hook_identity_required") or flags.get("no_hook_identity")),
        "weak_arrangement": bool(rescue.get("arrangement_rebuild_required") or flags.get("no_arrangement_structure")),
        "weird_vocal_texture": bool(rescue.get("vocal_texture_cleanup_required") or flags.get("weird_or_random_vocal_textures")),
    }


def _style_text(creative_brief: dict[str, Any] | None, style_cluster: str | None) -> str:
    brief = creative_brief or {}
    return " ".join(
        str(item or "")
        for item in (
            style_cluster,
            brief.get("style_cluster"),
            brief.get("style_cluster_text"),
            brief.get("creative_target_text"),
            brief.get("raw_full_korean_request"),
            brief.get("rough_request"),
        )
    ).lower()


def _target_style(creative_brief: dict[str, Any] | None, style_cluster: str | None) -> dict[str, Any]:
    text = _style_text(creative_brief, style_cluster)
    family: list[str] = []
    if "digicore" in text or "디지코어" in text:
        family.append("digicore")
    if "hyperpop" in text or "하이퍼팝" in text:
        family.append("hyperpop")
    if "internet" in text or "underground" in text or "언더" in text:
        family.append("internet_underground")
    if not family:
        family = ["digicore", "hyperpop", "internet_underground"]
    notes = ["broad ycs/SYSTEM SEOUL-adjacent texture", STYLE_SAFETY_NOTE]
    if "system" in text or "시스템" in text:
        notes.insert(0, "SYSTEM SEOUL-adjacent reference is high-level texture only")
    return {"genre_family": list(dict.fromkeys(family)), "style_notes": list(dict.fromkeys(notes))}


def _length_mode(creative_brief: dict[str, Any] | None, requested: str | None = None) -> str:
    if requested:
        return normalize_length_mode(requested)
    brief = creative_brief or {}
    length = brief.get("length")
    if isinstance(length, dict) and length.get("mode"):
        return normalize_length_mode(str(length["mode"]))
    for key in ("length_mode", "final_length", "target_length"):
        if brief.get(key):
            return normalize_length_mode(str(brief[key]))
    text = _style_text(creative_brief, None)
    if "15" in text or "릴스" in text or "reels" in text:
        return "reels_15sec"
    if "30" in text or "short" in text:
        return "short_30sec"
    return "under_2min"


def _remove_or_reduce(source_problem: dict[str, bool], diagnosis: dict[str, Any]) -> list[str]:
    items = ["long weak intro", "random glitch fills", "unmotivated vocal textures", "repeated AI loop blocks", "dead outro"]
    if not source_problem.get("weird_vocal_texture"):
        items.remove("unmotivated vocal textures")
    if not source_problem.get("weak_arrangement"):
        items.append("overextended sections")
    randomness = diagnosis.get("ai_randomness") or {}
    if randomness.get("randomness_risk") == "low":
        items = [item for item in items if item != "random glitch fills"] + ["decorative fills that do not support hook"]
    return list(dict.fromkeys(items))


def _add_or_create(source_problem: dict[str, bool]) -> list[str]:
    items = ["hook return", "call-response phrase", "4-8 bar variation", "clean transition", "final hook lift"]
    if source_problem.get("missing_lead"):
        items.insert(0, "new lead motif")
    if source_problem.get("missing_hook"):
        items.insert(1 if source_problem.get("missing_lead") else 0, "new hook identity")
    return list(dict.fromkeys(items))


def build_rescue_arrangement_plan(
    *,
    bad_song_diagnosis: dict[str, Any],
    song_structure_analysis: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    creative_brief: dict[str, Any] | None = None,
    style_cluster: str | None = None,
    length_mode: str | None = None,
) -> dict[str, Any]:
    source_problem = _source_problem(bad_song_diagnosis)
    selected_length = _length_mode(creative_brief, length_mode)
    target_style = _target_style(creative_brief, style_cluster)
    hook_plan = build_hook_identity_plan(
        bad_song_diagnosis,
        sample_analysis=sample_analysis,
        vocal_to_code=vocal_to_code,
    )
    sections = rebuild_sections(length_mode=selected_length, source_problem=source_problem, hook_plan=hook_plan)
    energy_curve = design_energy_curve(selected_length)
    return {
        "schema_version": "rescue_arrangement_plan.v1",
        "status": "RESCUE_PLAN_READY",
        "complete": False,
        "source_problem": source_problem,
        "target_style": target_style,
        "length_mode": selected_length,
        "target_duration_seconds": energy_curve["target_duration_seconds"],
        "hook_appears_by_seconds": min(section["start_time"] for section in sections if "hook" in section["name"]),
        "hook_within_first_15_seconds": bool(energy_curve["hook_within_first_15_seconds"]),
        "sections": sections,
        "hook_identity_plan": hook_plan,
        "remove_or_reduce": _remove_or_reduce(source_problem, bad_song_diagnosis),
        "add_or_create": _add_or_create(source_problem),
        "manual_logic_required": [
            "True stem-level rewrite requires stems or manual Logic editing.",
            "New lead MIDI/synth may need manual confirmation.",
            "Stereo-only rescue cannot claim vocal removal, kick replacement, 808 rewrite, or drum rewrite.",
        ],
        "input_context": {
            "song_structure_available": bool(song_structure_analysis),
            "sample_analysis_available": bool(sample_analysis),
            "vocal_to_code_available": bool(vocal_to_code),
            "creative_brief_available": bool(creative_brief),
            "detected_song_sections": len((song_structure_analysis or {}).get("sections", [])),
            "sample_motif_candidates": len((((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates") or [])),
            "vocal_phrase_candidates": len((vocal_to_code or {}).get("phrases", [])),
        },
        "rules": [
            "Do not keep 3-minute weak AI structure by default.",
            "If no lead exists, plan a new lead.",
            "If vocal texture is weird, push it back or replace with synth/sample lead.",
            "Do not over-chop randomly.",
            "Use fewer stronger motifs.",
            "Reference style is broad production direction only.",
        ],
    }


def render_rescue_arrangement_plan_markdown(plan: dict[str, Any]) -> str:
    source = plan["source_problem"]
    lines = [
        "# Rescue Arrangement Plan",
        "",
        f"- status: {plan.get('status', 'RESCUE_PLAN_READY')}",
        f"- length mode: {plan['length_mode']}",
        f"- target duration: {plan['target_duration_seconds']}s",
        f"- hook appears by: {plan['hook_appears_by_seconds']}s",
        f"- mix only not enough: {str(bool(source['mix_only_not_enough'])).lower()}",
        "",
        "## Source Problem",
        *[f"- {key}: {str(bool(value)).lower()}" for key, value in source.items()],
        "",
        "## Sections",
    ]
    for section in plan["sections"]:
        lines.append(f"- {section['name']} {section['start_time']:.1f}s +{section['duration']:.1f}s energy {section['energy']}")
        for instruction in section["instructions"]:
            lines.append(f"  - {instruction}")
    lines.extend(
        [
            "",
            "## Remove Or Reduce",
            *[f"- {item}" for item in plan["remove_or_reduce"]],
            "",
            "## Add Or Create",
            *[f"- {item}" for item in plan["add_or_create"]],
            "",
            "## Manual Logic Required",
            *[f"- {item}" for item in plan["manual_logic_required"]],
            "",
        ]
    )
    return "\n".join(lines)


def write_rescue_arrangement_plan(
    *,
    project_root: str | Path = PROJECT_ROOT,
    bad_song_diagnosis_path: str | Path | None = None,
    song_structure_analysis_path: str | Path | None = None,
    sample_analysis_path: str | Path | None = None,
    vocal_to_code_path: str | Path | None = None,
    creative_brief_path: str | Path | None = None,
    style_cluster: str | None = None,
    length_mode: str | None = None,
) -> dict[str, Path]:
    root = Path(project_root)
    diagnosis = _read_json(bad_song_diagnosis_path or root / "01_ANALYSIS" / "bad_song_diagnosis.json")
    if not diagnosis:
        raise FileNotFoundError("bad_song_diagnosis.json is required for rescue arrangement planning")
    song_structure = _read_json(song_structure_analysis_path or root / "01_ANALYSIS" / "song_structure_analysis.json")
    sample_analysis = _read_json(sample_analysis_path or root / "01_ANALYSIS" / "sample_analysis.json")
    vocal_to_code = _read_json(vocal_to_code_path or root / "01_ANALYSIS" / "vocal_to_code.json")
    creative_brief = _read_json(creative_brief_path or root / "02_EDIT_PLAN" / "creative_brief.json")
    plan = build_rescue_arrangement_plan(
        bad_song_diagnosis=diagnosis,
        song_structure_analysis=song_structure,
        sample_analysis=sample_analysis,
        vocal_to_code=vocal_to_code,
        creative_brief=creative_brief,
        style_cluster=style_cluster,
        length_mode=length_mode,
    )
    edit_dir = root / "02_EDIT_PLAN"
    edit_dir.mkdir(parents=True, exist_ok=True)
    json_path = edit_dir / "rescue_arrangement_plan.json"
    markdown_path = edit_dir / "rescue_arrangement_plan.md"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_rescue_arrangement_plan_markdown(plan), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
