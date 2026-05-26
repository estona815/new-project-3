from __future__ import annotations

from typing import Any


def _note_key(note: dict[str, Any]) -> tuple[int, float]:
    return int(note.get("bar", 1)), float(note.get("beat", 1.0))


def _pitchless(note: dict[str, Any]) -> tuple[float, str]:
    return float(note.get("beat", 0.0)), str(note.get("duration", "1/8"))


def motif_repetition_report(motifs: list[dict[str, Any]]) -> dict[str, Any]:
    lead = next((motif for motif in motifs if motif.get("motif_id") == "lead_A"), motifs[0] if motifs else {})
    notes = sorted(list(lead.get("notes", [])), key=_note_key)
    first_half = [note for note in notes if int(note.get("bar", 1)) <= 2]
    second_half = [note for note in notes if int(note.get("bar", 1)) >= 3]
    first_shape = [_pitchless(note) for note in first_half]
    second_shape = [(float(note.get("beat", 0.0)), str(note.get("duration", "1/8"))) for note in second_half]
    repeated_positions = len(set(first_shape) & set(second_shape))
    variation_notes = sum(1 for left, right in zip(first_half, second_half) if left.get("note") != right.get("note"))
    has_repetition = repeated_positions >= max(2, len(first_shape) // 3)
    has_variation = variation_notes >= 1
    return {
        "has_repetition": bool(has_repetition),
        "has_variation": bool(has_variation),
        "repeated_rhythm_positions": repeated_positions,
        "variation_notes": variation_notes,
        "note_count": len(notes),
    }


def generate_hook_motif(
    *,
    motifs: list[dict[str, Any]],
    section_plan: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sections = (section_plan or {}).get("sections") or []
    hook_sections = [section for section in sections if "hook" in str(section.get("name", "")).lower()]
    sample_candidates = (((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates") or [])
    vocal_phrases = (vocal_to_code or {}).get("phrases") or []
    repetition = motif_repetition_report(motifs)
    return {
        "schema_version": "hook_motif_generator.v1",
        "status": "HOOK_MOTIF_READY",
        "primary_motif_id": "lead_A",
        "response_motif_id": "response_B" if any(motif.get("motif_id") == "response_B" for motif in motifs) else None,
        "hook_sections": [
            {
                "name": section.get("name"),
                "start_time": section.get("start_time", section.get("start")),
                "duration": section.get("duration"),
            }
            for section in hook_sections
        ],
        "sample_motif_candidates_used_as_rhythm_hints": len(sample_candidates),
        "vocal_phrase_rhythm_hints": len(vocal_phrases),
        "repetition": repetition,
        "identity_rules": [
            "Repeat lead_A in every hook.",
            "Use response_B in verse gaps or hook second half.",
            "Keep rhythm recognizable; vary only landing notes or octave.",
            "Avoid random note soup and excessive chops.",
        ],
        "safety": {
            "exact_reference_melody_copy": False,
            "artist_melody_imitation_claimed": False,
            "generated_from_style_traits_only": True,
        },
    }


def build_hook_identity_plan(
    *,
    lead_plan: dict[str, Any],
    section_plan: dict[str, Any] | None = None,
    style_cluster: str | None = None,
) -> dict[str, Any]:
    motif = generate_hook_motif(
        motifs=lead_plan.get("motifs", []),
        section_plan=section_plan,
    )
    return {
        "schema_version": "hook_identity_plan.v1",
        "status": "HOOK_IDENTITY_PLAN_READY",
        "style_cluster": style_cluster or "custom",
        "main_hook_motif_id": motif["primary_motif_id"],
        "call_response_motif_id": motif["response_motif_id"],
        "hook_return_strategy": "repeat lead_A with a small variation, then answer with response_B",
        "motif_repetition_quality": "structured_repeat_with_variation" if motif["repetition"]["has_repetition"] and motif["repetition"]["has_variation"] else "needs_revision",
        "hook_motif": motif,
        "arrangement_rules": [
            "Lead motif must be audible before mix/master.",
            "Core melody stays centered; width belongs to support layers.",
            "Do not claim artist melody imitation.",
        ],
    }
