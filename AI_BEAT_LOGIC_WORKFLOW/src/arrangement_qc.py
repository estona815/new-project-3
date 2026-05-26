from __future__ import annotations

from typing import Any


ARRANGEMENT_CATEGORIES = [
    "Hook impact",
    "Arrangement intentionality",
    "Sample/motif usability",
    "Vocal phrase usability",
    "Drum/808 guide strength",
    "Melody/vibe preservation",
    "Synth width/space plan",
    "Logic manual clarity",
]


def score_arrangement_plan(
    arrangement_plan: dict[str, Any] | None,
    *,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    song_structure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = arrangement_plan or {}
    section = plan.get("section_progression_guide") or {}
    sample = plan.get("sample_chop_guide") or {}
    melody = plan.get("melody_variation_guide") or {}
    drum = plan.get("drum_programming_guide") or {}
    bass = plan.get("bass_808_midi_guide") or {}
    hooks = (song_structure or {}).get("hook_candidates") or []
    phrases = (vocal_to_code or {}).get("phrases") or []
    motifs = ((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates") or sample.get("motif_candidates", [])
    sections = section.get("sections") or []
    scores = [
        _item("Hook impact", 5 if hooks or any("hook" in str(s.get("name", "")) for s in sections[:2]) else 3, "Hook/drop appears early or has a detected candidate."),
        _item("Arrangement intentionality", 5 if len(sections) >= 4 else 3, "Section plan uses named purposes and energy targets."),
        _item("Sample/motif usability", 4 if motifs or sample.get("chop_candidates") or sample.get("loop_candidates") else 2, "Motif/loop evidence improves chop confidence."),
        _item("Vocal phrase usability", 4 if phrases else 3 if plan.get("input_mode") != "vocal_plus_beat" else 2, "Vocal phrase guide is useful only when phrase evidence exists."),
        _item("Drum/808 guide strength", 4 if drum and bass else 2, "Drum and 808 plans should include manual MIDI/Logic constraints."),
        _item("Melody/vibe preservation", 4 if melody.get("preserve_original_emotional_motif") else 3, "Preserve emotional motif while varying texture."),
        _item("Synth width/space plan", 4 if plan.get("synth_width_plan") or melody.get("variation_moves") else 3, "Width must stay high-passed with mono low-end."),
        _item("Logic manual clarity", 4 if plan.get("logic_manual_plan") else 2, "Manual Logic steps are required for real production moves."),
    ]
    average = round(sum(item["score"] for item in scores) / len(scores), 2)
    needs_more_input = _needs_more_input(sample_analysis, vocal_to_code, song_structure)
    return {
        "schema_version": "arrangement_qc.v1",
        "categories": scores,
        "average_score": average,
        "plan_pass": average >= 4.0 and not needs_more_input,
        "needs_more_input": needs_more_input,
        "manual_logic_required": True,
        "limitations": ["PLAN_PASS is not COMPLETE; it means the arrangement plan is useful enough for manual production."],
    }


def _item(name: str, score: int, note: str) -> dict[str, Any]:
    return {"name": name, "score": max(1, min(5, int(score))), "note": note}


def _needs_more_input(sample_analysis: dict[str, Any] | None, vocal_to_code: dict[str, Any] | None, song_structure: dict[str, Any] | None) -> bool:
    timing = (sample_analysis or {}).get("timing") or {}
    tonal = (sample_analysis or {}).get("tonal") or {}
    phrases = (vocal_to_code or {}).get("phrases") or []
    hooks = (song_structure or {}).get("hook_candidates") or []
    unreliable_bpm_key = timing.get("confidence") == "low" and tonal.get("confidence") == "low"
    low_vocal = vocal_to_code is not None and not phrases
    no_hook = song_structure is not None and not hooks
    return bool(unreliable_bpm_key or low_vocal or no_hook)


def render_arrangement_qc_report(qc: dict[str, Any]) -> str:
    lines = [
        "# Arrangement QC Report",
        "",
        f"- average score: {qc['average_score']}",
        f"- plan pass: {str(bool(qc['plan_pass'])).lower()}",
        f"- needs more input: {str(bool(qc['needs_more_input'])).lower()}",
        f"- manual Logic required: {str(bool(qc['manual_logic_required'])).lower()}",
        "",
        "## Categories",
    ]
    lines.extend(f"- {item['name']}: {item['score']}/5 - {item['note']}" for item in qc["categories"])
    lines.extend(["", "## Limitations", *[f"- {item}" for item in qc.get("limitations", [])]])
    return "\n".join(lines).rstrip() + "\n"
