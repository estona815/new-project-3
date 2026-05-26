from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from audio_analysis import mono_mix, read_wav_float
from loudness_estimation import rms_db
from paths import PROJECT_ROOT
from tempo_key_estimation import estimate_key
from vocal_phrase_segmenter import segment_vocal_phrases, vocal_activity_frames
from vocal_pitch_guide import build_pitch_correction_guide, notes_for_phrase, pitch_contour, pitch_frames
from vocal_rhythm_grid import estimate_vocal_bpm, rhythm_grid_for_phrase, timing_for_phrase


VALID_MODES = {"separate_vocal", "vocal_plus_beat", "full_song_stereo"}


def _mode(value: str | None) -> str:
    if value in VALID_MODES:
        return str(value)
    if value == "stems":
        return "vocal_plus_beat"
    return "separate_vocal"


def _mix_notes(phrase_frames: list[dict[str, Any]]) -> dict[str, Any]:
    bright = [frame for frame in phrase_frames if frame.get("brightness_ratio", 0.0) > 1.35]
    loud_low = [frame for frame in phrase_frames if frame.get("peak", 0.0) > 0.55 and frame.get("brightness_ratio", 0.0) < 0.35]
    needs_clip = any(frame.get("peak", 0.0) > 0.75 for frame in phrase_frames)
    sibilance = "high" if len(bright) >= 3 else "medium" if bright else "low"
    plosive = "high" if len(loud_low) >= 2 else "medium" if loud_low else "low"
    return {
        "sibilance_risk": sibilance,
        "plosive_risk": plosive,
        "needs_deess": sibilance in {"medium", "high"},
        "needs_clip_gain": needs_clip or plosive in {"medium", "high"},
    }


def _compact_note_sequence(notes: list[dict[str, Any]]) -> list[str]:
    sequence: list[str] = []
    for note in notes:
        name = note.get("note")
        if name and (not sequence or sequence[-1] != name):
            sequence.append(str(name))
        if len(sequence) >= 16:
            break
    return sequence


def _global_key(mono: list[float], sample_rate: int, duration: float, mode: str) -> dict[str, Any]:
    key = estimate_key(mono, sample_rate, duration)
    if mode == "full_song_stereo" and key["confidence"] == "high":
        key["confidence"] = "medium"
    return key


def analyze_vocal_to_code(
    path: str | Path,
    *,
    mode: str = "separate_vocal",
    requested_pitch_mode: str = "subtle",
) -> dict[str, Any]:
    analysis_mode = _mode(mode)
    vocal_path = Path(path).expanduser()
    metadata, channels = read_wav_float(vocal_path)
    mono = mono_mix(channels)
    duration = float(metadata["duration_seconds"])
    sample_rate = int(metadata["sample_rate"])
    activity = vocal_activity_frames(mono, sample_rate)
    base_phrases = segment_vocal_phrases(activity, mode=analysis_mode)
    pitch = pitch_frames(mono, sample_rate)
    bpm = estimate_vocal_bpm(base_phrases, duration)
    key = _global_key(mono, sample_rate, duration, analysis_mode)

    phrases: list[dict[str, Any]] = []
    for phrase in base_phrases:
        notes = notes_for_phrase(phrase, pitch, analysis_mode)
        compact = _compact_note_sequence(notes)
        phrase_frames = phrase.pop("frames", [])
        phrase_limitations = list(phrase.get("limitations", []))
        if not notes:
            phrase_limitations.append("No stable pitch was detected; useful timing cues may still remain.")
        if analysis_mode == "full_song_stereo":
            phrase_limitations.append("Pitch and phrase labels come from a full stereo mix and are not isolated vocal transcription.")
        phrases.append(
            {
                **phrase,
                "estimated_notes": notes,
                "note_sequence_compact": compact,
                "rhythm_grid": rhythm_grid_for_phrase(phrase, bpm.get("estimated_bpm")),
                "pitch_contour": pitch_contour(notes),
                "timing": timing_for_phrase(phrase, bpm.get("estimated_bpm")),
                "mix_notes": _mix_notes(phrase_frames),
                "limitations": list(dict.fromkeys(phrase_limitations)),
            }
        )

    isolated = analysis_mode in {"separate_vocal", "vocal_plus_beat"}
    return {
        "schema_version": "vocal_to_code.v1",
        "input": {
            "path": str(vocal_path),
            "mode": analysis_mode,
            "analysis_isolated": isolated,
        },
        "global": {
            "duration_seconds": duration,
            "estimated_bpm": bpm.get("estimated_bpm"),
            "bpm_confidence": bpm.get("bpm_confidence", "low"),
            "estimated_key": key.get("estimated_key"),
            "key_confidence": key.get("confidence", "low"),
            "rms_dbfs": rms_db([sample for channel in channels for sample in channel]),
        },
        "phrases": phrases,
        "pitch_correction_guide": build_pitch_correction_guide(phrases, requested_pitch_mode, key.get("estimated_key")),
        "false_claim_guard": {
            "auto_tune_applied": False,
            "pitch_correction_performed": False,
            "note_transcription_is_exact": False,
            "description": "Estimated pitch/timing guide only. It does not mean AutoTune or pitch correction was applied.",
        },
        "limitations": [
            "Never claim verified score transcription from this analysis.",
            "Never claim AutoTune or pitch correction was applied unless a verified pitch process occurred.",
            "Artist-style vocal requests are production traits only; no voice cloning is performed.",
        ]
        + (["Full stereo mode is heuristic and not isolated vocal analysis."] if not isolated else []),
    }


def render_vocal_to_code_summary(payload: dict[str, Any]) -> str:
    guard = payload["false_claim_guard"]
    guide = payload["pitch_correction_guide"]
    return "\n".join(
        [
            "# Vocal To Code Summary",
            "",
            f"- path: {payload['input']['path']}",
            f"- mode: {payload['input']['mode']}",
            f"- isolated analysis: {str(bool(payload['input']['analysis_isolated'])).lower()}",
            f"- duration: {payload['global']['duration_seconds']:.3f}s",
            f"- estimated BPM: {payload['global']['estimated_bpm']} ({payload['global']['bpm_confidence']})",
            f"- estimated key: {payload['global']['estimated_key'] or 'unknown'} ({payload['global']['key_confidence']})",
            f"- phrase count: {len(payload['phrases'])}",
            f"- pitch guide: {guide['recommended_mode']} ({guide['claim_language']})",
            f"- AutoTune applied: {str(bool(guard['auto_tune_applied'])).lower()}",
            f"- exact transcription: {str(bool(guard['note_transcription_is_exact'])).lower()}",
            "",
            "## Limitations",
            *[f"- {item}" for item in payload.get("limitations", [])],
            "",
        ]
    )


def write_vocal_to_code(
    path: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    mode: str = "separate_vocal",
    requested_pitch_mode: str = "subtle",
) -> dict[str, Path]:
    payload = analyze_vocal_to_code(path, mode=mode, requested_pitch_mode=requested_pitch_mode)
    analysis_dir = project_root / "01_ANALYSIS"
    edit_dir = project_root / "02_EDIT_PLAN"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    edit_dir.mkdir(parents=True, exist_ok=True)
    json_path = analysis_dir / "vocal_to_code.json"
    summary_path = analysis_dir / "vocal_to_code_summary.md"
    pitch_path = edit_dir / "vocal_pitch_guide.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(render_vocal_to_code_summary(payload), encoding="utf-8")
    pitch_path.write_text(json.dumps(payload["pitch_correction_guide"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"json": json_path, "summary": summary_path, "pitch_guide": pitch_path}
