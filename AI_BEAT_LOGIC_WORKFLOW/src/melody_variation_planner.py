from __future__ import annotations

from typing import Any


def generate_melody_variation_guide(
    *,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    song_structure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    motifs = ((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates", [])
    phrases = (vocal_to_code or {}).get("phrases", [])
    buried = (song_structure or {}).get("melody_buried_candidates") or []
    return {
        "schema_version": "melody_variation_guide.v1",
        "preserve_original_emotional_motif": True,
        "motif_sources": {
            "sample_motif_candidates": motifs[:6],
            "vocal_phrase_count": len(phrases),
            "melody_buried_candidates": buried[:6],
        },
        "variation_moves": [
            "filter movement across intro/pre sections",
            "reverb or delay send throws at phrase ends",
            "mute melody for one or two beats before hook impact",
            "808 pauses to reveal hook/motif",
            "octave or counterline only after the main motif is clear",
        ],
        "avoid": [
            "vocal chop lead unless requested",
            "random AI glitch",
            "constant top-line density that hides the hook",
        ],
        "limitations": ["Melody variation is a manual production guide; no exact melody transcription or rewrite is claimed."],
    }
