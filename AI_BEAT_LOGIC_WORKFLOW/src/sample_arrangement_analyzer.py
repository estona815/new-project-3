from __future__ import annotations

import math
from pathlib import Path
from statistics import median
from typing import Any

from audio_analysis import mono_mix, read_wav_float
from loudness_estimation import linear_to_db, rms_db


STYLE_GENRES = {
    "hip-hop",
    "hyperpop",
    "digicore",
    "internet underground",
    "SYSTEM SEOUL-adjacent",
}


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def _frame_features(samples: list[float], sample_rate: int, window_seconds: float = 0.05) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    window = max(1, int(sample_rate * window_seconds))
    frames: list[dict[str, Any]] = []
    for start in range(0, len(samples), window):
        end = min(len(samples), start + window)
        chunk = samples[start:end]
        energy = _rms(chunk)
        peak = max((abs(sample) for sample in chunk), default=0.0)
        derivative = _rms([right - left for left, right in zip(chunk, chunk[1:])])
        frames.append(
            {
                "start": start / sample_rate,
                "end": end / sample_rate,
                "rms": energy,
                "peak": peak,
                "brightness_ratio": derivative / energy if energy > 0 else 0.0,
            }
        )
    return frames


def _detect_onsets(frames: list[dict[str, Any]], duration: float, limit: int = 64) -> list[dict[str, Any]]:
    if len(frames) < 3:
        return []
    flux = [max(0.0, frames[index]["rms"] - frames[index - 1]["rms"]) for index in range(1, len(frames))]
    if not flux:
        return []
    ordered = sorted(flux)
    threshold = max(ordered[int(len(ordered) * 0.75)], max(flux) * 0.25, 0.0005)
    candidates: list[dict[str, Any]] = []
    last_time = -1.0
    for index, value in enumerate(flux, start=1):
        current = frames[index]
        time = float(current["start"])
        if value < threshold or time - last_time < 0.08:
            continue
        candidates.append(
            {
                "time": round(time, 3),
                "strength": round(value, 6),
                "peak_dbfs": round(linear_to_db(float(current["peak"])), 2),
                "reason": "positive short-window energy change; transient/onset heuristic",
            }
        )
        last_time = time
        if len(candidates) >= limit:
            break
    return [item for item in candidates if 0.0 <= item["time"] <= duration]


def _normalize_bpm(bpm: float) -> float:
    while bpm < 70.0:
        bpm *= 2.0
    while bpm > 180.0:
        bpm /= 2.0
    return bpm


def _estimate_bpm(onsets: list[dict[str, Any]]) -> dict[str, Any]:
    times = [float(item["time"]) for item in onsets]
    intervals = [right - left for left, right in zip(times, times[1:]) if 0.18 <= right - left <= 1.2]
    if len(intervals) < 2:
        return {
            "bpm": None,
            "confidence": "low",
            "candidates": [],
            "method": "Not enough repeated onset intervals for a useful BPM estimate.",
        }
    base = _normalize_bpm(60.0 / median(intervals))
    candidates = sorted({round(base / 2.0, 1), round(base, 1), round(base * 2.0, 1)})
    candidates = [value for value in candidates if 45.0 <= value <= 220.0]
    confidence = "medium" if len(intervals) >= 5 else "low"
    return {
        "bpm": round(base, 1),
        "confidence": confidence,
        "candidates": candidates,
        "method": "Median spacing between transient/onset candidates; verify by ear or DAW tempo tap.",
    }


def _dominant_frequency(samples: list[float], sample_rate: int) -> tuple[float | None, str]:
    if sample_rate <= 0 or not samples:
        return None, "low"
    frame_size = min(len(samples), max(1024, int(sample_rate * 0.12)))
    hop = max(1, frame_size // 2)
    best_frame: list[float] = []
    best_rms = 0.0
    for start in range(0, max(1, len(samples) - frame_size + 1), hop):
        frame = samples[start : start + frame_size]
        energy = _rms(frame)
        if energy > best_rms:
            best_rms = energy
            best_frame = frame
    if best_rms <= 0.001 or not best_frame:
        return None, "low"
    min_lag = max(1, int(sample_rate / 900.0))
    max_lag = min(len(best_frame) - 2, int(sample_rate / 55.0))
    if max_lag <= min_lag:
        return None, "low"
    best_lag = 0
    best_score = 0.0
    energy = sum(sample * sample for sample in best_frame) or 1.0
    for lag in range(min_lag, max_lag + 1):
        score = sum(best_frame[index] * best_frame[index + lag] for index in range(0, len(best_frame) - lag))
        normalized = score / energy
        if normalized > best_score:
            best_score = normalized
            best_lag = lag
    if best_lag <= 0 or best_score < 0.18:
        return None, "low"
    confidence = "medium" if best_score >= 0.35 else "low"
    return sample_rate / best_lag, confidence


def _pitch_name(frequency: float | None) -> tuple[str | None, int | None]:
    if not frequency or frequency <= 0:
        return None, None
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    midi = int(round(69 + 12 * math.log2(frequency / 440.0)))
    return f"{names[midi % 12]}{midi // 12 - 1}", midi % 12


def _estimate_key(samples: list[float], sample_rate: int) -> dict[str, Any]:
    frequency, confidence = _dominant_frequency(samples, sample_rate)
    note, pitch_class = _pitch_name(frequency)
    return {
        "estimated_tonic_or_pitch_center": note,
        "pitch_class": pitch_class,
        "frequency_hz": round(frequency, 2) if frequency else None,
        "confidence": confidence,
        "method": "Autocorrelation pitch-center heuristic; this is not full harmonic key detection.",
    }


def _loop_candidates(duration: float, bpm: float | None) -> list[dict[str, Any]]:
    if duration <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    if bpm:
        beat = 60.0 / bpm
        for bars in (1, 2, 4, 8):
            length = beat * 4 * bars
            if 0.5 <= length <= duration:
                candidates.append(
                    {
                        "start": 0.0,
                        "end": round(length, 3),
                        "bars": bars,
                        "bpm": round(bpm, 1),
                        "confidence": "medium" if bars <= 4 else "low",
                        "reason": "bar-aligned candidate from estimated BPM; check loop seam manually",
                    }
                )
    if not candidates:
        end = min(duration, 4.0)
        candidates.append(
            {
                "start": 0.0,
                "end": round(end, 3),
                "bars": None,
                "bpm": None,
                "confidence": "low",
                "reason": "fixed early-region fallback because BPM estimate was weak",
            }
        )
    return candidates[:4]


def _motif_candidates(frames: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    if not frames:
        return []
    ranked = sorted(frames, key=lambda item: (item["rms"], item["brightness_ratio"]), reverse=True)
    candidates: list[dict[str, Any]] = []
    used: list[float] = []
    for frame in ranked:
        start = float(frame["start"])
        if any(abs(start - existing) < 1.5 for existing in used):
            continue
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(float(frame["end"]), 3),
                "confidence": "low",
                "reason": "short high-energy/high-texture window; use as hook or motif listening cue",
            }
        )
        used.append(start)
        if len(candidates) >= limit:
            break
    return sorted(candidates, key=lambda item: item["start"])


def analyze_sample_for_arrangement(path: str | Path, genre: str = "digicore") -> dict[str, Any]:
    audio_path = Path(path).expanduser()
    metadata, channels = read_wav_float(audio_path)
    mono = mono_mix(channels)
    frames = _frame_features(mono, int(metadata["sample_rate"]))
    onsets = _detect_onsets(frames, float(metadata["duration_seconds"]))
    bpm = _estimate_bpm(onsets)
    key = _estimate_key(mono, int(metadata["sample_rate"]))
    selected_genre = genre if genre in STYLE_GENRES else "digicore"
    return {
        "schema_version": 1,
        "source": {
            "path": str(audio_path),
            "analysis_type": "local_sample_audio",
            "genre": selected_genre,
        },
        "metadata": metadata,
        "level_summary": {
            "rms_dbfs": round(rms_db([sample for channel in channels for sample in channel]), 2),
            "peak_dbfs": round(linear_to_db(max((abs(sample) for channel in channels for sample in channel), default=0.0)), 2),
        },
        "tempo": bpm,
        "key_pitch": key,
        "transient_onset_analysis": {
            "onset_count": len(onsets),
            "onsets": onsets[:32],
            "method": "Short-window RMS flux. Not a drum transcription.",
        },
        "loop_candidates": _loop_candidates(float(metadata["duration_seconds"]), bpm.get("bpm")),
        "hook_motif_candidates": _motif_candidates(frames),
        "arrangement_seed": {
            "suggested_role": "hook_motif" if _motif_candidates(frames) else "texture_or_intro",
            "manual_logic_next_step": "Slice promising motif/loop candidates in Logic, then rebuild drums/bass with owned sounds or MIDI.",
        },
        "limitations": [
            "BPM, key, loop, onset, and motif results are heuristic estimates.",
            "No exact protected song, melody, lyric, drum pattern, or sound recording copying is performed.",
            "Sample use for exact audio placement requires a local owned/cleared source.",
        ],
    }
