from __future__ import annotations

from typing import Any


def generate_drum_midi_guide(arrangement_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = arrangement_plan or {}
    length_mode = plan.get("length_mode", "under_2min")
    sections = (plan.get("section_progression_guide") or {}).get("sections", [])
    patterns = []
    for section in sections[:8]:
        name = section.get("name", "section")
        start_bar = _seconds_to_bar(float(section.get("start", 0.0)))
        length_bars = max(1, _seconds_to_bar(float(section.get("duration", 8.0))))
        density = "high" if "hook" in name or "drop" in name else "medium" if name not in {"intro", "outro"} else "low"
        patterns.append(
            {
                "region_name": f"drums_{name}",
                "start_bar": start_bar,
                "length_bars": length_bars,
                "kick": "beats 1 and selected anticipations",
                "snare_clap": "beats 2 and 4",
                "hat": "1/8 to 1/16 depending on section density",
                "fill": "last half bar only when entering a new section",
                "density": density,
                "manual_logic_required": True,
            }
        )
    if not patterns:
        patterns.append(
            {
                "region_name": "drums_hook_pattern",
                "start_bar": 1,
                "length_bars": 8 if length_mode != "reels_15sec" else 4,
                "kick": "beats 1 and selected anticipations",
                "snare_clap": "beats 2 and 4",
                "hat": "1/8 to 1/16 controlled hats",
                "fill": "one intentional transition fill",
                "density": "medium",
                "manual_logic_required": True,
            }
        )
    return {
        "schema_version": "drum_midi_guide.v1",
        "patterns": patterns,
        "claim_guard": {
            "midi_file_written": False,
            "midi_imported_into_logic": False,
            "drums_rewritten": False,
        },
        "limitations": ["Guide only; no MIDI file import or true drum rewrite is claimed."],
    }


def _seconds_to_bar(seconds: float, bpm: float = 148.0) -> int:
    bar_seconds = 4.0 * 60.0 / bpm
    return max(1, int(seconds / bar_seconds) + 1)
