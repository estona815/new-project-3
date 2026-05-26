from __future__ import annotations

import math
from pathlib import Path
from statistics import mean
from typing import Any

from audio_analysis import mono_mix, read_wav_float


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def _dominant_frequency(frame: list[float], sample_rate: int) -> tuple[float | None, float]:
    if sample_rate <= 0 or len(frame) < 64 or _rms(frame) < 0.001:
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


def _midi_from_frequency(frequency: float | None) -> float | None:
    if not frequency or frequency <= 0:
        return None
    return 69 + 12 * math.log2(frequency / 440.0)


def _note_name(midi: float | None) -> str | None:
    if midi is None:
        return None
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    rounded = int(round(midi))
    return f"{names[rounded % 12]}{rounded // 12 - 1}"


def _pitch_frames(samples: list[float], sample_rate: int, frame_seconds: float = 0.06, hop_seconds: float = 0.12) -> list[dict[str, Any]]:
    frame_size = max(64, int(sample_rate * frame_seconds))
    hop = max(1, int(sample_rate * hop_seconds))
    frames: list[dict[str, Any]] = []
    for start in range(0, max(1, len(samples) - frame_size + 1), hop):
        frame = samples[start : start + frame_size]
        energy = _rms(frame)
        frequency, score = _dominant_frequency(frame, sample_rate)
        midi = _midi_from_frequency(frequency)
        frames.append(
            {
                "time": round(start / sample_rate, 3),
                "end": round((start + len(frame)) / sample_rate, 3),
                "rms": energy,
                "frequency_hz": round(frequency, 2) if frequency else None,
                "midi": round(midi, 2) if midi is not None else None,
                "note": _note_name(midi),
                "pitch_confidence": round(score, 3),
            }
        )
    return frames


def _segment_phrases(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not frames:
        return []
    rms_values = sorted(frame["rms"] for frame in frames)
    threshold = max(0.004, rms_values[int(len(rms_values) * 0.55)] * 0.55)
    phrases: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for frame in frames:
        active = frame["rms"] >= threshold
        if active:
            current.append(frame)
            continue
        if current and frame["time"] - current[-1]["end"] <= 0.24:
            current.append(frame)
            continue
        if current:
            phrases.append(_phrase_summary(current))
            current = []
    if current:
        phrases.append(_phrase_summary(current))
    return phrases


def _phrase_summary(frames: list[dict[str, Any]]) -> dict[str, Any]:
    midi_values = [float(frame["midi"]) for frame in frames if frame.get("midi") is not None]
    confident = [frame for frame in frames if frame.get("pitch_confidence", 0.0) >= 0.22 and frame.get("midi") is not None]
    if len(midi_values) >= 2:
        delta = midi_values[-1] - midi_values[0]
        contour = "rising" if delta > 1.5 else "falling" if delta < -1.5 else "flat_or_wavy"
    else:
        contour = "unpitched_or_low_confidence"
    mean_midi = mean(midi_values) if midi_values else None
    return {
        "start": round(float(frames[0]["time"]), 3),
        "end": round(float(frames[-1]["end"]), 3),
        "duration": round(float(frames[-1]["end"]) - float(frames[0]["time"]), 3),
        "mean_midi": round(mean_midi, 2) if mean_midi is not None else None,
        "mean_note": _note_name(mean_midi),
        "contour": contour,
        "pitch_frame_count": len(midi_values),
        "confidence": "medium" if len(confident) >= max(2, len(frames) // 3) else "low",
    }


def code_vocal_phrases(path: str | Path) -> dict[str, Any]:
    vocal_path = Path(path).expanduser()
    metadata, channels = read_wav_float(vocal_path)
    mono = mono_mix(channels)
    frames = _pitch_frames(mono, int(metadata["sample_rate"]))
    phrases = _segment_phrases(frames)
    events = [
        {
            "id": f"phrase_{index + 1:02d}",
            "start": phrase["start"],
            "end": phrase["end"],
            "mean_note": phrase["mean_note"],
            "mean_midi": phrase["mean_midi"],
            "contour": phrase["contour"],
            "confidence": phrase["confidence"],
            "role_hint": "hook_candidate" if phrase["duration"] >= 1.0 and index < 2 else "phrase",
        }
        for index, phrase in enumerate(phrases)
    ]
    return {
        "schema_version": 1,
        "source": {
            "path": str(vocal_path),
            "analysis_type": "local_vocal_file",
        },
        "metadata": metadata,
        "phrasing": {
            "phrase_count": len(phrases),
            "phrases": phrases,
            "method": "RMS activity segmentation with short gap merging.",
        },
        "pitch_contour": {
            "frames": [
                {
                    "time": frame["time"],
                    "frequency_hz": frame["frequency_hz"],
                    "midi": frame["midi"],
                    "note": frame["note"],
                    "confidence": frame["pitch_confidence"],
                }
                for frame in frames[:256]
            ],
            "method": "Autocorrelation pitch contour heuristic; noisy or polyphonic vocals lower confidence.",
        },
        "melody_code": {
            "format": "phrase_events_v1",
            "events": events,
            "intended_use": "Guide MIDI sketching, arrangement support, and manual pitch-correction settings.",
        },
        "pitch_correction_guide": {
            "auto_tune_applied": False,
            "recommended_use": "Use phrase mean notes and contour only as manual tuning/MIDI guide.",
            "logic_manual_steps": [
                "Import the vocal file into Logic and inspect Flex Pitch or a tuner plugin manually.",
                "Set correction speed by phrase confidence and genre target; do not claim tuning was applied by this analyzer.",
                "Preserve the singer's identity and timing unless the user provided explicit edit direction.",
            ],
        },
        "limitations": [
            "Pitch contour is heuristic and can fail on breathy, distorted, doubled, or polyphonic material.",
            "No AutoTune, Flex Pitch, or vocal identity cloning is performed.",
            "The JSON representation is a production guide, not a verified score transcription.",
        ],
    }
