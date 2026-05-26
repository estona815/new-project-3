from __future__ import annotations

from typing import Any


def generate_bass_808_midi_pattern_guide(arrangement_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = arrangement_plan or {}
    chord = plan.get("chord_progression_guide") or {}
    key = chord.get("estimated_key") or "confirm_by_ear"
    root_note = _root_note_from_key(key)
    sections = (plan.get("section_progression_guide") or {}).get("sections", [])
    notes = []
    for section in sections[:8]:
        if section.get("energy_target", 3) < 3:
            continue
        start_bar = _seconds_to_bar(float(section.get("start", 0.0)))
        notes.extend(
            [
                {"bar": start_bar, "beat": 1, "note": root_note, "duration": "1/2", "glide": False},
                {"bar": start_bar, "beat": 3, "note": root_note, "duration": "1/4", "glide": True},
            ]
        )
    if not notes:
        notes = [{"bar": 1, "beat": 1, "note": root_note, "duration": "1/2", "glide": False}]
    return {
        "schema_version": "bass_808_midi_guide.v1",
        "key_reference": key,
        "notes": notes,
        "sub_mono": True,
        "manual_logic_required": True,
        "claim_guard": {
            "midi_file_written": False,
            "midi_imported_into_logic": False,
            "true_808_rewrite_performed": False,
        },
        "limitations": ["Bass/808 guide is note guidance only; confirm root notes by ear before programming."],
    }


def _root_note_from_key(key: str) -> str:
    if not key or key == "confirm_by_ear":
        return "C1"
    tonic = key.split()[0]
    return f"{tonic}1"


def _seconds_to_bar(seconds: float, bpm: float = 148.0) -> int:
    bar_seconds = 4.0 * 60.0 / bpm
    return max(1, int(seconds / bar_seconds) + 1)
