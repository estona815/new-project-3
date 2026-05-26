from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arrangement_templates import normalize_genre_mode
from hook_motif_generator import build_hook_identity_plan, generate_hook_motif
from paths import PROJECT_ROOT
from simple_synth_renderer import render_lead_plan_to_wav


NOTE_TO_PC = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "BB": 10,
    "B": 11,
}
PC_TO_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
MINOR_PENTATONIC = (0, 3, 5, 7, 10)
MAJOR_PENTATONIC = (0, 2, 4, 7, 9)


def _duration_to_beats(value: str) -> float:
    return {
        "1/16": 0.25,
        "1/8": 0.5,
        "1/4": 1.0,
        "1/2": 2.0,
        "1": 4.0,
    }.get(str(value), 0.5)


def _parse_key_label(key_label: str | None) -> tuple[str, str] | None:
    if not key_label:
        return None
    cleaned = str(key_label).strip().replace("♯", "#").replace("♭", "b")
    parts = cleaned.split()
    if not parts:
        return None
    root_raw = parts[0]
    if len(root_raw) >= 2 and root_raw[1] == "b":
        root = root_raw[0].upper() + "b"
    elif len(root_raw) >= 2 and root_raw[1] == "#":
        root = root_raw[0].upper() + "#"
    else:
        root = root_raw[0].upper()
    if root not in NOTE_TO_PC:
        return None
    mode = "minor" if any(part.lower().startswith("min") for part in parts[1:]) else "major" if any(part.lower().startswith("maj") for part in parts[1:]) else "minor"
    return root, mode


def _note_name(root_pc: int, degree: int, octave: int, scale: tuple[int, ...]) -> str:
    scale_index = degree % len(scale)
    octave_offset = degree // len(scale)
    pc = (root_pc + scale[scale_index]) % 12
    actual_octave = octave + octave_offset + ((root_pc + scale[scale_index]) // 12)
    return f"{PC_TO_SHARP[pc]}{actual_octave}"


def choose_scale(key: dict[str, Any] | None = None) -> dict[str, Any]:
    key_payload = key or {}
    confidence = str(key_payload.get("confidence") or key_payload.get("key_confidence") or "low")
    label = key_payload.get("estimated_key") or key_payload.get("key") or key_payload.get("estimated_tonic_or_pitch_center")
    parsed = _parse_key_label(str(label) if label else None)
    if parsed and confidence in {"medium", "high"}:
        root, mode = parsed
        scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
        return {
            "key": f"{root} {mode}",
            "key_confidence": confidence,
            "root_pc": NOTE_TO_PC[root],
            "scale_name": "natural_minor" if mode == "minor" else "major",
            "scale_degrees": list(scale),
            "confirm_by_ear": False,
        }
    fallback = parsed[0] if parsed else "F#"
    fallback_pc = NOTE_TO_PC.get(fallback, NOTE_TO_PC.get(fallback.upper(), NOTE_TO_PC["F#"]))
    return {
        "key": f"{fallback} minor",
        "key_confidence": confidence if confidence in {"low", "medium", "high"} else "low",
        "root_pc": fallback_pc,
        "scale_name": "minor_pentatonic/natural_minor_options",
        "scale_degrees": list(MINOR_PENTATONIC),
        "alternate_scale_degrees": list(MINOR_SCALE),
        "confirm_by_ear": True,
    }


def _tempo_payload(tempo: dict[str, Any] | None = None) -> dict[str, Any]:
    data = tempo or {}
    candidates = data.get("bpm_candidates") or []
    bpm = data.get("bpm")
    if not bpm and candidates:
        first = candidates[0]
        bpm = first.get("bpm") if isinstance(first, dict) else first
    try:
        bpm_value = int(round(float(bpm)))
    except (TypeError, ValueError):
        bpm_value = 148
    confidence = str(data.get("confidence") or (candidates[0].get("confidence") if candidates and isinstance(candidates[0], dict) else "low"))
    return {"tempo_bpm": bpm_value, "tempo_confidence": confidence if confidence in {"low", "medium", "high"} else "low"}


def _style_sound_design(style_cluster: str | None) -> dict[str, Any]:
    genre = normalize_genre_mode(style_cluster)
    if genre in {"hyperpop", "digicore", "commercial_digicore_hyperpop", "system_seoul_adjacent"}:
        lead_type = "bright_square" if genre == "system_seoul_adjacent" else "digital_pluck"
        delay = "short_pingpong_optional"
    else:
        lead_type = "soft_saw"
        delay = "none"
    return {
        "lead_type": lead_type,
        "stereo_width": "medium",
        "center_priority": True,
        "reverb": "small_plate",
        "delay": delay,
        "saturation": "subtle",
    }


def _notes_from_degrees(root_pc: int, scale: tuple[int, ...], pattern: list[dict[str, Any]], *, octave: int = 4) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for item in pattern:
        note = dict(item)
        note["note"] = _note_name(root_pc, int(item["degree"]), octave, scale)
        note.pop("degree", None)
        notes.append(note)
    return notes


def _main_hook_pattern() -> list[dict[str, Any]]:
    # Two bars with rests/gaps, repeated with small variation to avoid note soup.
    return [
        {"bar": 1, "beat": 1.0, "degree": 0, "duration": "1/8"},
        {"bar": 1, "beat": 1.5, "degree": 2, "duration": "1/8"},
        {"bar": 1, "beat": 2.0, "degree": 4, "duration": "1/4"},
        {"bar": 1, "beat": 3.0, "degree": 3, "duration": "1/8"},
        {"bar": 1, "beat": 3.75, "degree": 4, "duration": "1/8"},
        {"bar": 2, "beat": 1.0, "degree": 5, "duration": "1/4"},
        {"bar": 2, "beat": 2.0, "degree": 4, "duration": "1/8"},
        {"bar": 2, "beat": 2.5, "degree": 2, "duration": "1/8"},
        {"bar": 2, "beat": 3.5, "degree": 0, "duration": "1/4"},
        {"bar": 3, "beat": 1.0, "degree": 0, "duration": "1/8"},
        {"bar": 3, "beat": 1.5, "degree": 2, "duration": "1/8"},
        {"bar": 3, "beat": 2.0, "degree": 5, "duration": "1/4"},
        {"bar": 3, "beat": 3.0, "degree": 4, "duration": "1/8"},
        {"bar": 3, "beat": 3.75, "degree": 6, "duration": "1/8"},
        {"bar": 4, "beat": 1.0, "degree": 5, "duration": "1/4"},
        {"bar": 4, "beat": 2.0, "degree": 4, "duration": "1/8"},
        {"bar": 4, "beat": 2.5, "degree": 2, "duration": "1/8"},
        {"bar": 4, "beat": 3.5, "degree": 0, "duration": "1/2"},
    ]


def _response_pattern() -> list[dict[str, Any]]:
    return [
        {"bar": 1, "beat": 1.5, "degree": 4, "duration": "1/8"},
        {"bar": 1, "beat": 2.0, "degree": 3, "duration": "1/8"},
        {"bar": 1, "beat": 3.0, "degree": 2, "duration": "1/4"},
        {"bar": 2, "beat": 1.0, "degree": 0, "duration": "1/8"},
        {"bar": 2, "beat": 2.5, "degree": 2, "duration": "1/8"},
        {"bar": 2, "beat": 3.0, "degree": 0, "duration": "1/4"},
    ]


def build_lead_melody_plan(
    *,
    tempo: dict[str, Any] | None = None,
    key: dict[str, Any] | None = None,
    style_cluster: str | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    section_plan: dict[str, Any] | None = None,
    reason: str = "source has weak or absent lead melody",
) -> dict[str, Any]:
    tempo_data = _tempo_payload(tempo)
    scale = choose_scale(key)
    scale_degrees = tuple(int(value) for value in scale["scale_degrees"])
    root_pc = int(scale["root_pc"])
    motifs = [
        {
            "motif_id": "lead_A",
            "bars": 4,
            "role": "main_hook",
            "notes": _notes_from_degrees(root_pc, scale_degrees, _main_hook_pattern(), octave=4),
            "rhythm_style": "syncopated_digicore",
            "confidence": "medium" if scale["key_confidence"] in {"medium", "high"} else "low",
        },
        {
            "motif_id": "response_B",
            "bars": 2,
            "role": "call_response",
            "notes": _notes_from_degrees(root_pc, scale_degrees, _response_pattern(), octave=4),
            "rhythm_style": "syncopated_answer",
            "confidence": "medium" if (vocal_to_code or {}).get("phrases") else "low",
        },
    ]
    hook_motif = generate_hook_motif(motifs=motifs, section_plan=section_plan, sample_analysis=sample_analysis, vocal_to_code=vocal_to_code)
    return {
        "schema_version": "lead_melody_plan.v1",
        "status": "LEAD_MELODY_PLAN_READY",
        "reason": reason,
        "tempo_bpm": tempo_data["tempo_bpm"],
        "tempo_confidence": tempo_data["tempo_confidence"],
        "key": scale["key"],
        "key_confidence": scale["key_confidence"],
        "scale": scale,
        "motifs": motifs,
        "hook_motif_summary": hook_motif,
        "sound_design": _style_sound_design(style_cluster),
        "safety": {
            "exact_reference_melody_copy": False,
            "generated_from_style_traits_only": True,
            "artist_melody_imitation_claimed": False,
        },
        "limitations": [
            "Generated lead is a proposed motif, not guaranteed final composition.",
            "Confirm key and register by ear before release production.",
        ],
    }


def write_lead_melody_outputs(
    *,
    project_root: str | Path = PROJECT_ROOT,
    tempo: dict[str, Any] | None = None,
    key: dict[str, Any] | None = None,
    style_cluster: str | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    section_plan: dict[str, Any] | None = None,
    render: bool = False,
) -> dict[str, Any]:
    root = Path(project_root)
    edit_dir = root / "02_EDIT_PLAN"
    processed_dir = root / "04_PROCESSED_AUDIO"
    edit_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    lead_plan = build_lead_melody_plan(
        tempo=tempo,
        key=key,
        style_cluster=style_cluster,
        sample_analysis=sample_analysis,
        vocal_to_code=vocal_to_code,
        section_plan=section_plan,
    )
    hook_plan = build_hook_identity_plan(lead_plan=lead_plan, section_plan=section_plan, style_cluster=style_cluster)
    lead_path = edit_dir / "lead_melody_plan.json"
    hook_path = edit_dir / "hook_identity_plan.json"
    lead_path.write_text(json.dumps(lead_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    hook_path.write_text(json.dumps(hook_plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    outputs: dict[str, Any] = {
        "lead_melody_plan": lead_plan,
        "hook_identity_plan": hook_plan,
        "paths": {"lead_melody_plan": lead_path, "hook_identity_plan": hook_path},
        "rendered": {},
    }
    if render:
        lead_wav = processed_dir / "generated_lead_motif.wav"
        hook_wav = processed_dir / "generated_hook_stem.wav"
        outputs["rendered"]["lead_motif"] = render_lead_plan_to_wav(lead_plan, lead_wav, motif_ids=["lead_A"])
        outputs["rendered"]["hook_stem"] = render_lead_plan_to_wav(lead_plan, hook_wav, motif_ids=["lead_A", "response_B"])
        outputs["paths"]["generated_lead_motif"] = lead_wav
        outputs["paths"]["generated_hook_stem"] = hook_wav
    return outputs


def duration_to_beats(value: str) -> float:
    return _duration_to_beats(value)
