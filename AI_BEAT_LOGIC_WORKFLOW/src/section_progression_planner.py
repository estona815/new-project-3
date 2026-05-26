from __future__ import annotations

from typing import Any

from arrangement_templates import arrangement_template, normalize_genre_mode, normalize_length_mode


def _hook_hint(song_structure: dict[str, Any] | None) -> dict[str, Any] | None:
    hooks = (song_structure or {}).get("hook_candidates") or []
    if hooks:
        first = hooks[0]
        return {"start": first.get("start"), "end": first.get("end"), "confidence": first.get("confidence", "low")}
    reels = (song_structure or {}).get("reels_hook_region")
    return reels if isinstance(reels, dict) else None


def plan_section_progression(
    *,
    length_mode: str = "under_2min",
    genre_mode: str = "digicore",
    song_structure: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
) -> dict[str, Any]:
    length = normalize_length_mode(length_mode)
    genre = normalize_genre_mode(genre_mode)
    template = arrangement_template(length, genre)
    hook_hint = _hook_hint(song_structure)
    phrase_count = len((vocal_to_code or {}).get("phrases", []))
    motif_count = len(((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates", []))
    planned_sections: list[dict[str, Any]] = []
    for index, section in enumerate(template["sections"], start=1):
        instruction = section["purpose"]
        if index == 1 and length in {"reels_15sec", "short_30sec"}:
            instruction += "; place the strongest motif immediately"
        if "hook" in section["name"] and hook_hint:
            instruction += f"; adapt detected hook candidate {hook_hint.get('start')}s-{hook_hint.get('end')}s by ear"
        planned_sections.append(
            {
                "section_id": f"section_{index:02d}",
                "name": section["name"],
                "start": section["start"],
                "end": section["end"],
                "duration": round(float(section["end"]) - float(section["start"]), 3),
                "energy_target": _energy_target(section["name"], genre),
                "arrangement_instruction": instruction,
                "confidence": "medium" if hook_hint or motif_count or phrase_count else "low",
            }
        )
    return {
        "schema_version": "section_progression_guide.v1",
        "length_mode": length,
        "genre_mode": genre,
        "sections": planned_sections,
        "hook_hint": hook_hint,
        "source_summary": {
            "sample_motif_candidates": motif_count,
            "vocal_phrase_count": phrase_count,
            "song_sections_detected": len((song_structure or {}).get("sections", [])),
        },
        "rules": template["global_rules"],
        "limitations": ["Section progression is a production plan, not a rendered arrangement."],
    }


def _energy_target(name: str, genre_mode: str) -> int:
    if "hook" in name or "drop" in name:
        return 5 if genre_mode in {"hyperpop", "digicore", "commercial_digicore_hyperpop"} else 4
    if name in {"intro", "outro", "cut_or_loop"}:
        return 2
    if name in {"bridge", "contrast", "pre"}:
        return 3
    return 4
