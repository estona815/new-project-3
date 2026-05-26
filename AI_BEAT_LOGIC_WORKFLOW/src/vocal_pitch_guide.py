from __future__ import annotations

import math
from statistics import mean
from typing import Any

from vocal_phrase_segmenter import rms


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_from_frequency(frequency: float | None) -> float | None:
    if not frequency or frequency <= 0:
        return None
    return 69 + 12 * math.log2(frequency / 440.0)


def note_name(midi: float | None) -> str | None:
    if midi is None:
        return None
    rounded = int(round(midi))
    return f"{NOTE_NAMES[rounded % 12]}{rounded // 12 - 1}"


def _dominant_frequency(frame: list[float], sample_rate: int) -> tuple[float | None, float]:
    if sample_rate <= 0 or len(frame) < 64 or rms(frame) < 0.001:
        return None, 0.0
    min_lag = max(1, int(sample_rate / 900.0))
    max_lag = min(len(frame) - 2, int(sample_rate / 70.0))
    if max_lag <= min_lag:
        return None, 0.0
    energy = sum(sample * sample for sample in frame) or 1.0
    best_lag = 0
    best_score = 0.0
    for lag in range(min_lag, max_lag + 1, 2):
        score = sum(frame[index] * frame[index + lag] for index in range(len(frame) - lag)) / energy
        if score > best_score:
            best_score = score
            best_lag = lag
    if best_lag <= 0 or best_score < 0.16:
        return None, best_score
    return sample_rate / best_lag, best_score


def pitch_frames(samples: list[float], sample_rate: int, frame_seconds: float = 0.08, hop_seconds: float = 0.08) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    frame_size = max(64, int(sample_rate * frame_seconds))
    hop = max(1, int(sample_rate * hop_seconds))
    frames: list[dict[str, Any]] = []
    for start in range(0, max(1, len(samples) - frame_size + 1), hop):
        frame = samples[start : start + frame_size]
        frequency, confidence = _dominant_frequency(frame, sample_rate)
        midi = midi_from_frequency(frequency)
        frames.append(
            {
                "start": round(start / sample_rate, 3),
                "end": round((start + len(frame)) / sample_rate, 3),
                "frequency_hz": round(frequency, 2) if frequency else None,
                "midi": int(round(midi)) if midi is not None else None,
                "midi_float": round(midi, 2) if midi is not None else None,
                "note": note_name(midi),
                "confidence": "medium" if confidence >= 0.28 else "low",
                "confidence_score": round(confidence, 3),
            }
        )
    return frames


def notes_for_phrase(phrase: dict[str, Any], pitch: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    start = float(phrase["start"])
    end = float(phrase["end"])
    for frame in pitch:
        if frame["start"] < start or frame["start"] > end or not frame.get("note"):
            continue
        confidence = frame["confidence"]
        if mode == "full_song_stereo":
            confidence = "low"
        notes.append(
            {
                "note": frame["note"],
                "start": frame["start"],
                "end": frame["end"],
                "midi": frame["midi"],
                "frequency_hz": frame["frequency_hz"],
                "confidence": confidence,
            }
        )
    return notes[:64]


def pitch_contour(notes: list[dict[str, Any]]) -> dict[str, Any]:
    midis = [int(note["midi"]) for note in notes if note.get("midi") is not None]
    if not midis:
        return {"shape": "unstable", "average_note": None, "range_semitones": None, "stability": "low"}
    range_semitones = max(midis) - min(midis)
    delta = midis[-1] - midis[0] if len(midis) > 1 else 0
    if range_semitones <= 1:
        shape = "flat"
    elif delta > 2:
        shape = "rising"
    elif delta < -2:
        shape = "falling"
    elif max(midis) > midis[0] and max(midis) > midis[-1]:
        shape = "arched"
    else:
        shape = "unstable"
    stability = "high" if range_semitones <= 2 else "medium" if range_semitones <= 7 else "low"
    return {
        "shape": shape,
        "average_note": note_name(mean(midis)),
        "range_semitones": range_semitones,
        "stability": stability,
    }


def build_pitch_correction_guide(phrases: list[dict[str, Any]], request_mode: str = "subtle", estimated_key: str | None = None) -> dict[str, Any]:
    confident_notes = sum(
        1
        for phrase in phrases
        for note in phrase.get("estimated_notes", [])
        if note.get("confidence") in {"medium", "high"}
    )
    scale_confidence = "medium" if estimated_key and confident_notes >= 4 else "low"
    recommended = request_mode if request_mode in {"none", "subtle", "medium", "hard_effect"} else "subtle"
    return {
        "recommended_mode": recommended,
        "scale_lock": estimated_key,
        "scale_confidence": scale_confidence,
        "manual_logic_required": True,
        "plugin_required": "AutoTune/Melodyne/Flex Pitch or equivalent",
        "claim_language": "recommended, not applied",
    }
