from __future__ import annotations

from typing import Any


def generate_chord_progression_guide(sample_analysis: dict[str, Any] | None, *, genre_mode: str = "digicore") -> dict[str, Any]:
    tonal = (sample_analysis or {}).get("tonal") or {}
    key = tonal.get("estimated_key")
    confidence = tonal.get("confidence", "low")
    key_ok = bool(key and confidence in {"medium", "high"})
    if key_ok:
        options = _keyed_options(str(key), genre_mode)
        instruction = "Use these as broad harmonic options; confirm voicing and bass relation by ear."
    else:
        options = _low_confidence_options(genre_mode)
        instruction = "Key confidence is low; confirm by ear before committing chords or bass notes."
    return {
        "schema_version": "chord_progression_guide.v1",
        "estimated_key": key,
        "key_confidence": confidence,
        "progression_allowed": key_ok,
        "options": options,
        "instruction": instruction,
        "copying_policy": "No exact song progression copying; use broad harmonic targets only.",
        "limitations": ["Chord guide is optional and must be checked by ear, especially for polyphonic stereo material."],
    }


def _keyed_options(key: str, genre_mode: str) -> list[dict[str, Any]]:
    flavor = "bright digital tension" if genre_mode in {"hyperpop", "digicore", "commercial_digicore_hyperpop"} else "simple pocket"
    return [
        {"name": "minor lift", "key": key, "roman": ["i", "VI", "III", "VII"], "feel": flavor},
        {"name": "two-chord pressure", "key": key, "roman": ["i", "VII"], "feel": "loopable hook bed"},
        {"name": "suspended contrast", "key": key, "roman": ["i", "iv", "VI", "V"], "feel": "bridge or breakdown option"},
    ]


def _low_confidence_options(genre_mode: str) -> list[dict[str, Any]]:
    return [
        {"name": "confirm by ear A", "roman": ["i", "VI", "III", "VII"], "feel": f"{genre_mode} safe minor option"},
        {"name": "confirm by ear B", "roman": ["i", "VII"], "feel": "minimal loop option"},
        {"name": "confirm by ear C", "roman": ["i", "iv"], "feel": "darker contrast option"},
    ]
