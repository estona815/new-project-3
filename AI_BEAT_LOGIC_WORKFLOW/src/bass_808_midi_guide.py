from __future__ import annotations

from typing import Any


def generate_bass_808_midi_guide(
    *,
    chord_guide: dict[str, Any] | None = None,
    song_structure: dict[str, Any] | None = None,
    stems_available: bool = False,
    genre_mode: str = "digicore",
) -> dict[str, Any]:
    low_end_flags = (song_structure or {}).get("low_end_excess_candidates") or []
    movement = "busy_hook_support" if genre_mode in {"hyperpop", "digicore", "commercial_digicore_hyperpop"} else "pocket_sparse"
    return {
        "schema_version": "bass_808_midi_guide.v1",
        "sub_mono": True,
        "controlled_saturation": "medium" if genre_mode != "hip_hop" else "light",
        "glide_amount": "medium" if genre_mode in {"digicore", "commercial_digicore_hyperpop"} else "low",
        "movement_density": movement,
        "sidechain_recommended": bool(low_end_flags),
        "root_source": "chord_guide" if (chord_guide or {}).get("progression_allowed") else "confirm_by_ear",
        "midi_pattern_rules": [
            "Anchor sub to confirmed root notes.",
            "Use short rests before hook/drop impacts.",
            "Keep octave jumps above sub range or layer upper harmonics only.",
            "Do not copy exact basslines from references.",
        ],
        "true_rewrite_status": "manual_logic_or_midi_required" if not stems_available else "stems_available_but_manual_verification_required",
        "limitations": [
            "True 808 rewrite requires MIDI, stems, or manual Logic programming.",
            "Stereo-only input cannot provide guaranteed kick/bass replacement.",
        ],
    }
