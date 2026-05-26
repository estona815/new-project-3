from __future__ import annotations

from typing import Any


def _source_bool(diagnosis: dict[str, Any], key: str) -> bool:
    rescue = diagnosis.get("rescue_decision") or {}
    flags = diagnosis.get("flags") or {}
    aliases = {
        "missing_lead": ("lead_melody_required", "no_clear_lead_melody"),
        "missing_hook": ("hook_identity_required", "no_hook_identity"),
        "weird_vocal_texture": ("vocal_texture_cleanup_required", "weird_or_random_vocal_textures"),
    }
    decision_key, flag_key = aliases[key]
    return bool(rescue.get(decision_key) or flags.get(flag_key))


def build_hook_identity_plan(
    diagnosis: dict[str, Any],
    *,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing_lead = _source_bool(diagnosis, "missing_lead")
    missing_hook = _source_bool(diagnosis, "missing_hook")
    weird_vocal = _source_bool(diagnosis, "weird_vocal_texture")
    sample_motifs = (((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates") or [])
    vocal_phrases = (vocal_to_code or {}).get("phrases") or []
    return {
        "schema_version": "hook_identity_builder.v1",
        "create_new_lead": bool(missing_lead),
        "create_hook_identity": bool(missing_hook),
        "lead_source": "new MIDI/synth motif" if missing_lead else "preserve and simplify strongest existing motif",
        "hook_source": "new lead plus sample/synth call-sign" if missing_hook else "reuse detected hook with tighter repetition",
        "usable_sample_motif_candidates": len(sample_motifs),
        "usable_vocal_phrase_candidates": len(vocal_phrases),
        "motif_rules": [
            "Use fewer stronger motifs.",
            "Repeat one main motif in every hook.",
            "Create one call-response phrase for verse or hook answer.",
            "Do not over-chop randomly.",
            "Do not copy exact melodies, samples, lyrics, drum patterns, basslines, or artist vocal identities.",
        ],
        "vocal_texture_rule": "push back or replace with synth/sample lead" if weird_vocal else "keep vocal texture below lead motif",
        "hook_qc": [
            "Hook is recognizable with drums muted.",
            "Hook appears before 15 seconds for short-form modes.",
            "Hook return clearly references the first hook.",
        ],
    }
