from __future__ import annotations

from typing import Any

from arrangement_templates import normalize_length_mode
from energy_curve_designer import design_energy_curve


BASE_INSTRUCTIONS: dict[str, list[str]] = {
    "intro_hook_hint": [
        "Introduce the new lead motif immediately.",
        "Use filtered sample/synth motif.",
        "Avoid long AI intro.",
    ],
    "main_hook": [
        "Full drums/808 enter.",
        "Lead melody becomes central.",
        "Vocal texture must not dominate lead.",
        "Add wide upper synth layer, sub stays mono.",
    ],
    "verse_groove": [
        "Reduce lead density but keep motif fragments audible.",
        "Use one call-response phrase.",
        "Remove repeated AI loop blocks.",
    ],
    "hook_return": [
        "Return to the same hook identity.",
        "Add one controlled variation, not a new random idea.",
        "Keep transition clean and intentional.",
    ],
    "breakdown_filtered_lead": [
        "Filter the lead or sample motif.",
        "Push weird vocal texture behind the motif.",
        "Do not add random risers unless they announce the final hook.",
    ],
    "final_hook": [
        "Bring back full hook with final lift.",
        "Use stronger drums/808 without masking lead.",
        "Resolve sample/synth motif clearly.",
    ],
    "clean_outro_or_loop": [
        "End quickly or make a loopable ending.",
        "Avoid dead outro.",
        "Do not extend generated material.",
    ],
}


def _instructions_for(section_name: str, source_problem: dict[str, bool], hook_plan: dict[str, Any]) -> list[str]:
    instructions = list(BASE_INSTRUCTIONS.get(section_name, [f"Build intentional {section_name} section."]))
    if source_problem.get("missing_lead") and "hook" in section_name:
        instructions.append("Create and feature a new lead MIDI/synth motif.")
    if source_problem.get("missing_hook") and "hook" in section_name:
        instructions.append("Make this section the clear hook identity, not just a louder part.")
    if source_problem.get("weird_vocal_texture"):
        instructions.append("Push vocal texture back or replace it with synth/sample lead.")
    if hook_plan.get("usable_sample_motif_candidates", 0) > 0:
        instructions.append("Use the strongest sample motif only if ownership/clearance allows direct use.")
    return list(dict.fromkeys(instructions))


def rebuild_sections(
    *,
    length_mode: str = "under_2min",
    source_problem: dict[str, bool] | None = None,
    hook_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    length = normalize_length_mode(length_mode)
    source = source_problem or {}
    hook = hook_plan or {}
    curve = design_energy_curve(length)["curve"]
    sections: list[dict[str, Any]] = []
    for item in curve:
        name = str(item["name"])
        sections.append(
            {
                "name": name,
                "start_time": float(item["start_time"]),
                "duration": float(item["duration"]),
                "energy": int(item["energy"]),
                "instructions": _instructions_for(name, source, hook),
            }
        )
    return sections
