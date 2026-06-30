#!/usr/bin/env python3
"""Prompt 31 source classifier and conservative pitch-correction planner.

This tool does not apply FX, tune audio, render a REAPER project, or edit the
original source. It analyzes a user-owned WAV file, writes source/pitch reports,
and produces a draft-only chain plan that later REAPER automation may consume.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automix.pitch.conservative_pitch_profiles import resolve_pitch_profile
from automix.pitch.pitch_evaluation import harden_pitch_evaluation, missing_render_metrics
from automix.pitch.pitch_iteration import build_iteration_history
from automix.pitch.pitch_safety_gate import evaluate_pitch_safety, input_from_reports


SOURCE_CLASSES = {
    "raw_vocal",
    "mixed_vocal_stem",
    "ai_vocal_stem",
    "source_separated_vocal",
    "full_mix",
    "unknown",
}

CONSERVATIVE_SETTINGS = {
    "raw_vocal": {
        "correction_amount": 0.25,
        "speed": 0.30,
        "depth": 0.30,
        "formant_preserve": 1.0,
        "humanize": 0.60,
        "vibrato_preserve": 0.70,
        "dry_wet": 0.60,
        "output_gain": 0.0,
    },
    "mixed_vocal_stem": {
        "correction_amount": 0.16,
        "speed": 0.18,
        "depth": 0.18,
        "formant_preserve": 1.0,
        "humanize": 0.70,
        "vibrato_preserve": 0.80,
        "dry_wet": 0.40,
        "output_gain": 0.0,
    },
    "ai_vocal_stem": {
        "correction_amount": 0.08,
        "speed": 0.15,
        "depth": 0.15,
        "formant_preserve": 1.0,
        "humanize": 0.70,
        "vibrato_preserve": 0.80,
        "dry_wet": 0.35,
        "output_gain": 0.0,
    },
    "source_separated_vocal": {
        "correction_amount": 0.08,
        "speed": 0.10,
        "depth": 0.10,
        "formant_preserve": 1.0,
        "humanize": 0.80,
        "vibrato_preserve": 0.90,
        "dry_wet": 0.25,
        "output_gain": 0.0,
    },
    "full_mix": {
        "correction_amount": 0.0,
        "apply": False,
    },
    "unknown": {
        "correction_amount": 0.0,
        "apply": False,
    },
}

ROLLBACK_CRITERIA = [
    "robotic artifact increase",
    "metallic tone increase",
    "formant drift or vocal identity shift",
    "sibilance warble",
    "reverb tail pitch drag or warble",
    "vocal becomes thinner or cloudier",
    "full-mix instrumental damage",
    "difference signal contains too much musical source damage",
]

DEFAULT_ADAPTER_STATUS = {
    "plugin_name": None,
    "available": False,
    "mapping_confidence": 0.0,
    "semantic_controls": {},
    "reason": "No high-confidence user-learned pitch adapter mapping was provided.",
}


@dataclass(frozen=True)
class AudioData:
    sample_rate: int
    channels: int
    frames: list[list[float]]

    @property
    def mono(self) -> list[float]:
        if self.channels == 1:
            return [frame[0] for frame in self.frames]
        return [sum(frame) / len(frame) for frame in self.frames]

    @property
    def side(self) -> list[float]:
        if self.channels < 2:
            return [0.0 for _ in self.frames]
        return [(frame[0] - frame[1]) * 0.5 for frame in self.frames]

    @property
    def mid(self) -> list[float]:
        if self.channels < 2:
            return [frame[0] for frame in self.frames]
        return [(frame[0] + frame[1]) * 0.5 for frame in self.frames]


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def safe_db(value: float, floor: float = -120.0) -> float:
    if value <= 1.0e-12 or not math.isfinite(value):
        return floor
    return 20.0 * math.log10(value)


def rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(x * x for x in samples) / len(samples))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    data = sorted(values)
    idx = int(round((len(data) - 1) * clamp(q)))
    return data[idx]


def safe_filename(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "track"


def _decode_pcm(raw: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [b - 128 for b in raw]
    if sample_width == 2:
        return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)]
    if sample_width == 3:
        out = []
        for i in range(0, len(raw), 3):
            chunk = raw[i : i + 3]
            sign = 0xFF if chunk[2] & 0x80 else 0x00
            out.append(int.from_bytes(chunk + bytes([sign]), "little", signed=True))
        return out
    if sample_width == 4:
        return [int.from_bytes(raw[i : i + 4], "little", signed=True) for i in range(0, len(raw), 4)]
    raise ValueError(f"Unsupported WAV sample width: {sample_width}")


def read_wav(path: Path, max_seconds: float | None = 90.0) -> AudioData:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        frame_count = wf.getnframes()
        if max_seconds is not None:
            frame_count = min(frame_count, int(sample_rate * max_seconds))
        raw = wf.readframes(frame_count)

    ints = _decode_pcm(raw, sample_width)
    peak = float(2 ** (8 * sample_width - 1))
    frames = []
    for i in range(0, len(ints), channels):
        frame = [clamp(value / peak, -1.0, 1.0) for value in ints[i : i + channels]]
        if len(frame) == channels:
            frames.append(frame)
    return AudioData(sample_rate=sample_rate, channels=channels, frames=frames)


def write_wav(path: Path, audio: AudioData, frames: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(audio.channels)
        wf.setsampwidth(2)
        wf.setframerate(audio.sample_rate)
        raw = bytearray()
        for frame in frames:
            for value in frame[: audio.channels]:
                sample = int(round(clamp(value, -1.0, 1.0) * 32767.0))
                raw.extend(sample.to_bytes(2, "little", signed=True))
        wf.writeframes(bytes(raw))


def window_starts(length: int, window_size: int, max_windows: int) -> list[int]:
    if length <= 0:
        return []
    if length <= window_size:
        return [0]
    count = min(max_windows, max(1, length // window_size))
    if count == 1:
        return [0]
    span = length - window_size
    return [int(round(i * span / (count - 1))) for i in range(count)]


def window_rms_values(samples: list[float], window_size: int = 2048, max_windows: int = 160) -> list[float]:
    return [rms(samples[start : start + window_size]) for start in window_starts(len(samples), window_size, max_windows)]


def dynamic_features(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {
            "rms": 0.0,
            "peak": 0.0,
            "crest_factor_db": 0.0,
            "rms_density_score": 0.0,
            "peak_ceiling_ratio": 0.0,
            "transient_density_score": 0.0,
            "compression_limited_score": 0.0,
        }
    abs_samples = [abs(x) for x in samples]
    peak = max(abs_samples)
    global_rms = rms(samples)
    crest_db = safe_db(peak / max(global_rms, 1.0e-9))
    rms_windows = window_rms_values(samples)
    rms_mean = mean(rms_windows)
    rms_var = statistics.pstdev(rms_windows) / max(rms_mean, 1.0e-9) if len(rms_windows) > 1 else 0.0
    rms_density_score = clamp(1.0 - rms_var / 0.85)
    ceiling_threshold = max(0.80, peak * 0.985)
    peak_ceiling_ratio = sum(1 for value in abs_samples if value >= ceiling_threshold) / max(1, len(abs_samples))

    transient_hits = 0
    probe = samples[:: max(1, len(samples) // 24000)]
    for i in range(1, len(probe)):
        if abs(probe[i] - probe[i - 1]) > 0.35:
            transient_hits += 1
    transient_density_score = clamp(transient_hits / max(1, len(probe)) * 18.0)

    low_crest_score = clamp((11.0 - crest_db) / 8.0)
    peak_ceiling_score = clamp(peak_ceiling_ratio * 80.0)
    compression_limited_score = clamp(0.45 * low_crest_score + 0.35 * rms_density_score + 0.20 * peak_ceiling_score)

    return {
        "rms": global_rms,
        "peak": peak,
        "crest_factor_db": crest_db,
        "rms_density_score": rms_density_score,
        "peak_ceiling_ratio": peak_ceiling_ratio,
        "transient_density_score": transient_density_score,
        "compression_limited_score": compression_limited_score,
    }


def goertzel_power(samples: list[float], sample_rate: int, frequency: float) -> float:
    if not samples or frequency <= 0.0 or frequency >= sample_rate * 0.5:
        return 0.0
    n = len(samples)
    k = int(0.5 + (n * frequency) / sample_rate)
    omega = (2.0 * math.pi * k) / n
    coeff = 2.0 * math.cos(omega)
    q0 = q1 = q2 = 0.0
    for sample in samples:
        q0 = coeff * q1 - q2 + sample
        q2 = q1
        q1 = q0
    return max(0.0, q1 * q1 + q2 * q2 - coeff * q1 * q2) / max(1, n)


def spectral_features(samples: list[float], sample_rate: int) -> dict[str, float]:
    freqs = {
        "sub": [55.0, 80.0],
        "low": [120.0, 180.0],
        "body": [300.0, 500.0],
        "presence": [1200.0, 2500.0, 4000.0],
        "clarity": [6000.0],
        "air": [9000.0, 12000.0],
    }
    band_windows: dict[str, list[float]] = {key: [] for key in freqs}
    for start in window_starts(len(samples), 1024, 72):
        segment = samples[start : start + 1024]
        if len(segment) < 64:
            continue
        for band, band_freqs in freqs.items():
            values = [goertzel_power(segment, sample_rate, freq) for freq in band_freqs]
            band_windows[band].append(mean(values))

    band_energy = {band: mean(values) for band, values in band_windows.items()}
    total = sum(band_energy.values()) + 1.0e-12
    normalized = {f"{band}_ratio": clamp(value / total) for band, value in band_energy.items()}
    max_band = max(band_energy.values()) if band_energy else 0.0
    active_bands = sum(1 for value in band_energy.values() if max_band > 0 and value >= max_band * 0.10)
    spectral_density_score = clamp(active_bands / max(1, len(band_energy)))
    low_end_score = clamp((band_energy.get("sub", 0.0) + band_energy.get("low", 0.0)) / total * 2.2)
    high_air_variance = statistics.pstdev(band_windows.get("air", []) or [0.0]) / max(mean(band_windows.get("air", []) or [0.0]), 1.0e-9)
    metallic_chirp_score = clamp(high_air_variance / 2.2)

    return {
        **normalized,
        "spectral_density_score": spectral_density_score,
        "low_end_score": low_end_score,
        "metallic_chirp_score": metallic_chirp_score,
    }


def stereo_features(audio: AudioData) -> dict[str, float]:
    if audio.channels < 2:
        return {
            "stereo_width_score": 0.0,
            "side_energy_ratio": 0.0,
            "phase_instability_score": 0.0,
        }
    mid = audio.mid
    side = audio.side
    mid_rms = rms(mid)
    side_rms = rms(side)
    side_ratio = side_rms / max(mid_rms + side_rms, 1.0e-9)
    side_windows = window_rms_values(side, max_windows=80)
    mid_windows = window_rms_values(mid, max_windows=80)
    ratios = [s / max(m + s, 1.0e-9) for s, m in zip(side_windows, mid_windows)]
    phase_instability = clamp(statistics.pstdev(ratios) * 3.0) if len(ratios) > 1 else 0.0
    return {
        "stereo_width_score": clamp(side_ratio * 2.4),
        "side_energy_ratio": clamp(side_ratio),
        "phase_instability_score": phase_instability,
    }


def downsample(samples: list[float], sample_rate: int, target_rate: int = 8000) -> tuple[list[float], int]:
    step = max(1, int(round(sample_rate / target_rate)))
    return samples[::step], max(1, int(round(sample_rate / step)))


def estimate_pitch_contour(samples: list[float], sample_rate: int) -> list[dict[str, float]]:
    ds, sr = downsample(samples, sample_rate)
    window_size = 1024
    min_lag = max(8, int(sr / 520.0))
    max_lag = min(window_size - 2, int(sr / 70.0))
    contour = []
    for start in window_starts(len(ds), window_size, 120):
        segment = ds[start : start + window_size]
        if len(segment) < window_size:
            continue
        seg_rms = rms(segment)
        if seg_rms < 0.004:
            contour.append({"time": start / sr, "f0_hz": 0.0, "confidence": 0.0})
            continue
        best_lag = 0
        best_corr = -1.0
        for lag in range(min_lag, max_lag):
            a = segment[:-lag]
            b = segment[lag:]
            energy_a = sum(x * x for x in a)
            energy_b = sum(x * x for x in b)
            if energy_a <= 1.0e-12 or energy_b <= 1.0e-12:
                continue
            corr = sum(x * y for x, y in zip(a, b)) / math.sqrt(energy_a * energy_b)
            if corr > best_corr:
                best_corr = corr
                best_lag = lag
        confidence = clamp((best_corr - 0.25) / 0.65)
        f0 = sr / best_lag if best_lag > 0 and confidence > 0.0 else 0.0
        contour.append({"time": start / sr, "f0_hz": f0, "confidence": confidence})
    return contour


def hz_to_midi(f0: float) -> float:
    if f0 <= 0.0:
        return 0.0
    return 69.0 + 12.0 * math.log2(f0 / 440.0)


def pitch_metrics(samples: list[float], sample_rate: int, spectral_density_score: float) -> dict[str, Any]:
    contour = estimate_pitch_contour(samples, sample_rate)
    voiced = [frame for frame in contour if frame["confidence"] >= 0.35 and frame["f0_hz"] > 0.0]
    voiced_ratio = len(voiced) / max(1, len(contour))
    avg_conf = mean([frame["confidence"] for frame in voiced])
    midi = [hz_to_midi(frame["f0_hz"]) for frame in voiced]
    nearest_cents = [abs((note - round(note)) * 100.0) for note in midi]
    median_cents = median(nearest_cents)
    semitone_snap_score = clamp(1.0 - median_cents / 35.0)

    deltas = [abs((b - a) * 100.0) for a, b in zip(midi, midi[1:]) if abs(b - a) < 1.5]
    micro_motion = median(deltas)
    low_micro_motion_score = clamp(1.0 - micro_motion / 18.0)
    pitch_jump_density = sum(1 for a, b in zip(midi, midi[1:]) if abs(b - a) > 0.75) / max(1, len(midi) - 1)
    octave_error_suspicion = sum(1 for a, b in zip(midi, midi[1:]) if abs(b - a) > 9.5) / max(1, len(midi) - 1)

    pitch_std_cents = statistics.pstdev(midi) * 100.0 if len(midi) > 1 else 0.0
    pitch_stability = clamp(1.0 - min(80.0, pitch_std_cents) / 80.0)
    vibrato_presence = clamp(micro_motion / 30.0) if voiced_ratio > 0.1 else 0.0

    pitch_classes = [round(note) % 12 for note in midi]
    scale_key_confidence = estimate_key_confidence(pitch_classes)
    note_confidence = clamp(0.55 * semitone_snap_score + 0.45 * avg_conf)
    quantized_transition_score = clamp(pitch_jump_density * semitone_snap_score * 2.2)
    already_tuned_score = clamp(
        0.45 * semitone_snap_score
        + 0.25 * low_micro_motion_score
        + 0.20 * quantized_transition_score
        - 0.18 * vibrato_presence
    )
    polyphonic_contamination_score = clamp(0.55 * (1.0 - avg_conf) + 0.45 * spectral_density_score)
    monophonic_pitch_confidence = clamp(avg_conf * voiced_ratio * (1.0 - 0.45 * polyphonic_contamination_score))

    return {
        "pitch_contour_frame_count": len(contour),
        "voiced_frame_count": len(voiced),
        "voiced_frame_ratio": voiced_ratio,
        "monophonic_pitch_confidence": monophonic_pitch_confidence,
        "pitch_stability": pitch_stability,
        "note_confidence": note_confidence,
        "scale_key_confidence": scale_key_confidence,
        "median_pitch_error_to_semitone_cents": median_cents,
        "octave_error_suspicion": clamp(octave_error_suspicion),
        "vibrato_presence": vibrato_presence,
        "pitch_jump_density": clamp(pitch_jump_density),
        "polyphonic_contamination_score": polyphonic_contamination_score,
        "already_tuned_score": already_tuned_score,
    }


def estimate_key_confidence(pitch_classes: list[int]) -> float:
    if not pitch_classes:
        return 0.0
    major = {0, 2, 4, 5, 7, 9, 11}
    minor = {0, 2, 3, 5, 7, 8, 10}
    best = 0.0
    for root in range(12):
        for scale in (major, minor):
            allowed = {(root + pc) % 12 for pc in scale}
            score = sum(1 for pc in pitch_classes if pc in allowed) / len(pitch_classes)
            best = max(best, score)
    return clamp(best)


def baked_reverb_score(mono: list[float], side: list[float], spectral: dict[str, float]) -> float:
    windows = window_rms_values(mono, max_windows=100)
    if len(windows) < 4:
        return 0.0
    high = percentile(windows, 0.75)
    low = percentile(windows, 0.25)
    tails = 0
    for prev, current in zip(windows, windows[1:]):
        if prev > high and low * 0.35 < current < high * 0.55:
            tails += 1
    tail_ratio = tails / max(1, len(windows) - 1)
    side_tail = rms(side) / max(rms(mono) + rms(side), 1.0e-9)
    air_ratio = spectral.get("air_ratio", 0.0) + spectral.get("clarity_ratio", 0.0)
    return clamp(0.45 * tail_ratio * 3.0 + 0.35 * side_tail * 2.0 + 0.20 * air_ratio * 2.0)


def analyze_source(audio: AudioData, track_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    mono = audio.mono
    dyn = dynamic_features(mono)
    spectral = spectral_features(mono, audio.sample_rate)
    stereo = stereo_features(audio)
    baked = baked_reverb_score(mono, audio.side, spectral)
    pitch = pitch_metrics(mono, audio.sample_rate, spectral["spectral_density_score"])

    full_mix_likelihood = clamp(
        0.25 * spectral["low_end_score"]
        + 0.25 * spectral["spectral_density_score"]
        + 0.20 * dyn["transient_density_score"]
        + 0.15 * stereo["stereo_width_score"]
        + 0.15 * pitch["polyphonic_contamination_score"]
    )
    source_separated_likelihood = clamp(
        0.38 * stereo["phase_instability_score"]
        + 0.28 * baked
        + 0.20 * pitch["polyphonic_contamination_score"]
        + 0.14 * spectral["metallic_chirp_score"]
    )
    already_mixed_score = clamp(
        0.35 * dyn["compression_limited_score"]
        + 0.20 * spectral["spectral_density_score"]
        + 0.20 * stereo["stereo_width_score"]
        + 0.15 * spectral["low_end_score"]
        + 0.10 * baked
    )
    ai_artifact_score = clamp(
        0.32 * spectral["metallic_chirp_score"]
        + 0.28 * stereo["phase_instability_score"]
        + 0.22 * source_separated_likelihood
        + 0.18 * (1.0 - pitch["pitch_stability"])
    )
    vocal_stem_likelihood = clamp(
        0.55 * pitch["monophonic_pitch_confidence"]
        + 0.25 * pitch["voiced_frame_ratio"]
        + 0.20 * (1.0 - full_mix_likelihood)
    )

    scores = {
        "full_mix": full_mix_likelihood,
        "source_separated_vocal": source_separated_likelihood,
        "ai_vocal_stem": max(ai_artifact_score, pitch["already_tuned_score"] * already_mixed_score),
        "mixed_vocal_stem": already_mixed_score * vocal_stem_likelihood,
        "raw_vocal": vocal_stem_likelihood * (1.0 - already_mixed_score) * (1.0 - source_separated_likelihood),
        "unknown": 0.35,
    }

    if full_mix_likelihood > 0.65 or (
        full_mix_likelihood > 0.50
        and pitch["monophonic_pitch_confidence"] < 0.35
        and (spectral["low_end_score"] > 0.55 or stereo["stereo_width_score"] > 0.55)
    ):
        classification = "full_mix"
    elif pitch["monophonic_pitch_confidence"] < 0.25 and source_separated_likelihood < 0.50:
        classification = "unknown"
    elif source_separated_likelihood > 0.62:
        classification = "source_separated_vocal"
    elif ai_artifact_score > 0.58 or (pitch["already_tuned_score"] > 0.72 and already_mixed_score > 0.40):
        classification = "ai_vocal_stem"
    elif already_mixed_score > 0.55:
        classification = "mixed_vocal_stem"
    elif vocal_stem_likelihood > 0.50:
        classification = "raw_vocal"
    else:
        classification = max(scores, key=scores.get)

    confidence = clamp(scores.get(classification, 0.35))
    risk = pitch_correction_risk(
        classification=classification,
        full_mix_likelihood=full_mix_likelihood,
        source_separated_likelihood=source_separated_likelihood,
        already_tuned_score=pitch["already_tuned_score"],
        baked_reverb_score=baked,
        pitch_confidence=pitch["monophonic_pitch_confidence"],
    )
    recommendation = source_recommendation(classification, risk, pitch["already_tuned_score"], full_mix_likelihood)

    classification_report = {
        "schema": "automix-source-classification-v1",
        "scan_date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "track_name": track_name,
        "classification": classification,
        "confidence": confidence,
        "full_mix_likelihood": full_mix_likelihood,
        "vocal_stem_likelihood": vocal_stem_likelihood,
        "source_separated_likelihood": source_separated_likelihood,
        "already_mixed_score": already_mixed_score,
        "already_tuned_score": pitch["already_tuned_score"],
        "baked_reverb_score": baked,
        "compression_limited_score": dyn["compression_limited_score"],
        "ai_artifact_score": ai_artifact_score,
        "pitch_correction_risk": risk,
        "recommendation": recommendation,
        "metrics": {
            "dynamics": dyn,
            "spectral": spectral,
            "stereo": stereo,
        },
    }

    pitch_report = {
        "schema": "automix-pitch-analysis-v1",
        "scan_date_utc": classification_report["scan_date_utc"],
        "track_name": track_name,
        "source_classification": classification,
        **pitch,
        "pitch_correction_risk": risk,
        "rules": {
            "low_pitch_confidence_skips_auto_correction": pitch["monophonic_pitch_confidence"] < 0.45,
            "full_mix_blocks_auto_correction": full_mix_likelihood > 0.65,
            "already_tuned_prefers_skip_or_micro": pitch["already_tuned_score"] > 0.70,
            "source_separated_requires_extreme_caution": source_separated_likelihood > 0.55,
        },
    }
    return classification_report, pitch_report


def pitch_correction_risk(
    classification: str,
    full_mix_likelihood: float,
    source_separated_likelihood: float,
    already_tuned_score: float,
    baked_reverb_score: float,
    pitch_confidence: float,
) -> str:
    if classification == "full_mix" or full_mix_likelihood > 0.65:
        return "unsafe"
    if classification == "unknown" or pitch_confidence < 0.30:
        return "unsafe"
    if source_separated_likelihood > 0.55 or already_tuned_score > 0.70 or baked_reverb_score > 0.65:
        return "high"
    if classification in {"ai_vocal_stem", "mixed_vocal_stem", "source_separated_vocal"} or pitch_confidence < 0.55:
        return "medium"
    return "low"


def source_recommendation(classification: str, risk: str, already_tuned_score: float, full_mix_likelihood: float) -> str:
    if classification == "full_mix" or full_mix_likelihood > 0.65:
        return "stem_required"
    if risk == "unsafe":
        return "skip"
    if already_tuned_score > 0.85:
        return "skip"
    if already_tuned_score > 0.70:
        return "skip_or_micro_correct"
    if risk == "high":
        return "light_or_skip"
    if risk == "medium":
        return "conservative_draft_only"
    return "conservative_allowed"


def load_adapter_status(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return dict(DEFAULT_ADAPTER_STATUS)
    data = json.loads(path.read_text(encoding="utf-8"))
    status = dict(DEFAULT_ADAPTER_STATUS)
    status.update(data)
    status["mapping_confidence"] = clamp(float(status.get("mapping_confidence", 0.0)))
    return status


def semantic_settings_for_classification(classification: str, already_tuned_score: float) -> dict[str, Any]:
    settings = dict(CONSERVATIVE_SETTINGS.get(classification, CONSERVATIVE_SETTINGS["unknown"]))
    if already_tuned_score > 0.70 and settings.get("correction_amount", 0.0) > 0.0:
        settings["correction_amount"] = min(settings["correction_amount"], 0.06)
        settings["depth"] = min(settings.get("depth", 0.06), 0.08)
        settings["dry_wet"] = min(settings.get("dry_wet", 0.20), 0.22)
        settings["already_tuned_micro_correction_only"] = True
    return settings


def filtered_semantic_controls(settings: dict[str, Any], adapter_status: dict[str, Any]) -> dict[str, Any]:
    controls = adapter_status.get("semantic_controls", {})
    out: dict[str, Any] = {}
    for semantic, value in settings.items():
        if semantic == "apply":
            continue
        mapping = controls.get(semantic, {})
        if not isinstance(mapping, dict):
            continue
        if mapping.get("confidence", 0.0) >= 0.85 and mapping.get("writable", True):
            out[semantic] = {
                "value": value,
                "target_name": mapping.get("target_name"),
                "mapping_confidence": mapping.get("confidence"),
            }
    return out


def build_chain_plan(
    classification_report: dict[str, Any],
    pitch_report: dict[str, Any],
    adapter_status: dict[str, Any],
    *,
    user_goal_allows_pitch: bool,
    force_full_mix_experiment: bool,
    override_mode: str = "default_conservative",
) -> dict[str, Any]:
    classification = classification_report["classification"]
    if not user_goal_allows_pitch:
        override_mode = "no_pitch_correction"
    if force_full_mix_experiment:
        override_mode = "allow_full_mix_pitch_experiment"

    base_settings = semantic_settings_for_classification(classification, classification_report["already_tuned_score"])
    mapped_controls = filtered_semantic_controls(base_settings, adapter_status)
    gate_input = input_from_reports(
        classification_report,
        pitch_report,
        adapter_status,
        available_semantic_controls=mapped_controls,
        user_goal=override_mode,
        explicit_user_overrides={"force_full_mix_experiment": force_full_mix_experiment},
    )
    safety_gate = evaluate_pitch_safety(gate_input)
    profile = resolve_pitch_profile(classification, safety_gate, mapped_controls)
    settings = profile["settings"]

    final_recommendation = {
        "full_mix_unsafe": "full_mix_unsafe",
        "stem_required": "stem_required",
        "plugin_mapping_required": "needs_manual_tuning",
        "manual_review_required": "needs_manual_tuning",
        "skip": "reject_pitch_correction",
        "apply_micro": "accept_light",
        "apply_light": "accept_light",
    }.get(safety_gate["decision"], "needs_manual_tuning")

    reasons = list(safety_gate.get("reason_codes", []))
    if adapter_status.get("reason") and "PLUGIN_MAPPING_UNCERTAIN" in reasons:
        reasons.append(str(adapter_status["reason"]))
    if classification == "full_mix" and force_full_mix_experiment:
        settings.update({"correction_amount": 0.03, "speed": 0.08, "depth": 0.05, "dry_wet": 0.15, "output_gain": 0.0})

    return {
        "schema": "automix-conservative-pitch-chain-plan-v1",
        "scan_date_utc": classification_report["scan_date_utc"],
        "track_name": classification_report["track_name"],
        "source_classification": classification,
        "pitch_confidence": pitch_report["monophonic_pitch_confidence"],
        "already_mixed_score": classification_report["already_mixed_score"],
        "already_tuned_score": classification_report["already_tuned_score"],
        "full_mix_likelihood": classification_report["full_mix_likelihood"],
        "source_separated_likelihood": classification_report["source_separated_likelihood"],
        "baked_reverb_score": classification_report["baked_reverb_score"],
        "pitch_correction_risk": classification_report["pitch_correction_risk"],
        "apply": bool(safety_gate["eligible"]),
        "draft_only": True,
        "original_track_must_remain_untouched": True,
        "final_recommendation": final_recommendation,
        "proposed_plugin": adapter_status.get("plugin_name") or "unmapped_pitch_correction_plugin",
        "adapter_mapping_confidence": adapter_status.get("mapping_confidence", 0.0),
        "semantic_settings": settings,
        "mapped_semantic_controls": profile["semantic_controls_to_write"],
        "unknown_parameters_are_skipped": True,
        "fixed_parameter_indexes_required": False,
        "override_mode": override_mode,
        "safety_gate": safety_gate,
        "correction_profile": profile["profile"],
        "semantic_controls_to_write": profile["semantic_controls_to_write"],
        "semantic_controls_skipped": profile["semantic_controls_skipped"],
        "chain_placement": chain_placement_for_source(classification),
        "phrase_level_policy": phrase_level_policy(classification),
        "rollback_criteria": ROLLBACK_CRITERIA,
        "skip_or_caution_reasons": reasons,
        "ab_evaluation_required_if_applied": safety_gate.get("evaluation_required", True),
        "pitch_correction": {
            "proposed": bool(safety_gate["eligible"]),
            "safety_gate_decision": safety_gate["decision"],
            "reason_codes": safety_gate["reason_codes"],
            "classification": classification,
            "confidence": classification_report.get("confidence", 0.0),
            "already_mixed_score": classification_report["already_mixed_score"],
            "already_tuned_score": classification_report["already_tuned_score"],
            "full_mix_likelihood": classification_report["full_mix_likelihood"],
            "pitch_confidence": pitch_report["monophonic_pitch_confidence"],
            "plugin_adapter": adapter_status.get("plugin_name") or "unmapped_pitch_correction_plugin",
            "adapter_confidence": adapter_status.get("mapping_confidence", 0.0),
            "semantic_controls_to_write": profile["semantic_controls_to_write"],
            "semantic_controls_skipped": profile["semantic_controls_skipped"],
            "draft_track_required": True,
            "rollback_criteria": ROLLBACK_CRITERIA,
        },
    }


def chain_placement_for_source(classification: str) -> list[str]:
    if classification == "raw_vocal":
        return [
            "utility_gain",
            "pitch_correction",
            "cleanup_eq",
            "denoise_or_artifact_suppression",
            "dynamic_eq",
            "compression",
            "optional_saturation",
            "send_reverb_delay",
        ]
    if classification == "mixed_vocal_stem":
        return [
            "utility_gain",
            "very_light_cleanup_eq",
            "conservative_artifact_suppression",
            "very_light_pitch_correction_if_safe",
            "dynamic_eq_for_artifacts",
            "avoid_heavy_compression",
            "avoid_strong_saturation",
        ]
    if classification == "source_separated_vocal":
        return [
            "denoise_or_artifact_suppression",
            "dynamic_eq_or_resonance_control",
            "phrase_specific_very_light_pitch_correction_only_if_safe",
            "avoid_global_pitch_correction",
        ]
    if classification == "ai_vocal_stem":
        return [
            "utility_gain",
            "artifact_safety_check",
            "very_light_pitch_correction_only_if_benefit_is_clear",
            "dynamic_eq_for_artifacts",
            "rollback_on_metallic_or_warble_increase",
        ]
    return ["do_not_insert_pitch_correction"]


def phrase_level_policy(classification: str) -> dict[str, Any]:
    enabled = classification in {"mixed_vocal_stem", "ai_vocal_stem", "source_separated_vocal"}
    return {
        "prefer_phrase_limited_correction": enabled,
        "zero_correction_during_gaps_reverb_tails_unvoiced_consonants": enabled,
        "no_dense_automation_spam": True,
        "smooth_ramps_required": True,
        "requires_high_confidence_parameter_mapping": True,
    }


def band_proxy(audio: AudioData) -> dict[str, float]:
    spectral = spectral_features(audio.mono, audio.sample_rate)
    return {
        "formant_1k_4k": spectral.get("presence_ratio", 0.0),
        "clarity_4k_8k": spectral.get("clarity_ratio", 0.0),
        "air_8k_plus": spectral.get("air_ratio", 0.0),
    }


def evaluate_pitch_ab(original_path: Path, processed_path: Path, output_dir: Path, track_name: str) -> dict[str, Any]:
    original = read_wav(original_path)
    processed = read_wav(processed_path)
    count = min(len(original.frames), len(processed.frames))
    original_rms = rms(original.mono[:count])
    processed_rms = rms(processed.mono[:count])
    match_gain = original_rms / max(processed_rms, 1.0e-9)
    match_gain = min(max(match_gain, 0.25), 4.0)
    matched_frames = [
        [clamp(value * match_gain, -1.0, 1.0) for value in processed.frames[i][: original.channels]]
        for i in range(count)
    ]
    matched_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_pitch_processed_loudness_matched.wav"
    write_wav(matched_path, original, matched_frames)
    diff_frames: list[list[float]] = []
    for i in range(count):
        diff_frames.append(
            [
                original.frames[i][ch] - matched_frames[i][ch]
                for ch in range(min(original.channels, processed.channels))
            ]
        )
    diff_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_pitch_difference.wav"
    write_wav(diff_path, original, diff_frames)

    orig_bands = band_proxy(original)
    proc_bands = band_proxy(processed)
    orig_pitch = pitch_metrics(original.mono, original.sample_rate, spectral_features(original.mono, original.sample_rate)["spectral_density_score"])
    proc_pitch = pitch_metrics(processed.mono, processed.sample_rate, spectral_features(processed.mono, processed.sample_rate)["spectral_density_score"])
    diff_mono = [sum(frame) / len(frame) for frame in diff_frames] if diff_frames else []

    clarity_loss_db = safe_db(proc_bands["clarity_4k_8k"] + 1.0e-9) - safe_db(orig_bands["clarity_4k_8k"] + 1.0e-9)
    air_loss_db = safe_db(proc_bands["air_8k_plus"] + 1.0e-9) - safe_db(orig_bands["air_8k_plus"] + 1.0e-9)
    formant_drift_score = clamp(abs(proc_bands["formant_1k_4k"] - orig_bands["formant_1k_4k"]) * 8.0)
    metallic_increase_score = clamp(max(0.0, proc_bands["air_8k_plus"] - orig_bands["air_8k_plus"]) * 10.0)
    transient_loss = max(
        0.0,
        dynamic_features(original.mono)["transient_density_score"]
        - dynamic_features(processed.mono)["transient_density_score"],
    )
    stereo_width_change = abs(stereo_features(processed)["stereo_width_score"] - stereo_features(original)["stereo_width_score"])
    difference_source_energy = rms(diff_mono) / max(rms(original.mono), 1.0e-9)
    tail_warble_score = clamp(abs(dynamic_features(original.side)["rms"] - dynamic_features(processed.side)["rms"]) / max(rms(original.mono), 1.0e-9))
    side_tail_instability_score = clamp(abs(stereo_features(processed)["phase_instability_score"] - stereo_features(original)["phase_instability_score"]))
    reverb_tail_pitch_drag_score = clamp((tail_warble_score + side_tail_instability_score) * 0.5)
    warnings = []
    if formant_drift_score > 0.25:
        warnings.append("formant_drift_warning")
    if metallic_increase_score > 0.20:
        warnings.append("metallic_increase_warning")
    if clarity_loss_db < -1.5:
        warnings.append("clarity_loss_warning")
    if air_loss_db < -1.5:
        warnings.append("air_loss_warning")
    if difference_source_energy > 0.35:
        warnings.append("difference_contains_source_damage_warning")

    metrics = {
        "schema": "automix-pitch-ab-evaluation-v1",
        "track_name": track_name,
        "renders_created": {
            "original": original_path.exists(),
            "pitch_processed": processed_path.exists(),
            "loudness_matched": matched_path.exists(),
            "difference": diff_path.exists(),
        },
        "original_path": str(original_path),
        "processed_path": str(processed_path),
        "loudness_matched_path": str(matched_path),
        "difference_path": str(diff_path),
        "pitch_error_improvement": orig_pitch["median_pitch_error_to_semitone_cents"]
        - proc_pitch["median_pitch_error_to_semitone_cents"],
        "pitch_error_improvement_cents": orig_pitch["median_pitch_error_to_semitone_cents"]
        - proc_pitch["median_pitch_error_to_semitone_cents"],
        "formant_drift_score": formant_drift_score,
        "metallic_increase_score": metallic_increase_score,
        "clarity_loss_db": clarity_loss_db,
        "air_loss_db": air_loss_db,
        "transient_loss": transient_loss,
        "stereo_width_change": stereo_width_change,
        "tail_warble_score": tail_warble_score,
        "side_tail_instability_score": side_tail_instability_score,
        "reverb_tail_pitch_drag_score": reverb_tail_pitch_drag_score,
        "difference_source_energy": difference_source_energy,
        "warnings": warnings,
    }
    metrics = harden_pitch_evaluation(metrics)
    metrics_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_pitch_metrics.json"
    eval_metrics_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_pitch_eval_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    eval_metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def write_human_report(
    output_dir: Path,
    track_name: str,
    classification: dict[str, Any],
    pitch: dict[str, Any],
    plan: dict[str, Any],
    ab_metrics: dict[str, Any] | None,
) -> Path:
    path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_pitch_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    gate = plan.get("safety_gate", {})
    pitch_block = plan.get("pitch_correction", {})
    settings = plan.get("semantic_settings", {})
    ab_metrics = ab_metrics or missing_render_metrics(track_name)
    lines = [
        "# Pitch Correction Safety Report",
        "",
        "## Summary",
        "",
        f"- Final recommendation: `{plan['final_recommendation']}`",
        f"- Source classification: `{classification['classification']}`",
        f"- Confidence: `{classification.get('confidence', 0.0):.3f}`",
        f"- Pitch correction applied: `{str(plan['apply']).lower()}`",
        f"- Draft track: `{track_name}_PITCH_DRAFT`",
        "- Original track untouched: `true`",
        "",
        "## Source Processing Detection",
        "",
        f"- already_mixed_score: `{classification['already_mixed_score']:.3f}`",
        f"- already_tuned_score: `{classification['already_tuned_score']:.3f}`",
        f"- baked_reverb_score: `{classification['baked_reverb_score']:.3f}`",
        f"- full_mix_likelihood: `{classification['full_mix_likelihood']:.3f}`",
        f"- source_separated_likelihood: `{classification['source_separated_likelihood']:.3f}`",
        f"- pitch_correction_risk: `{classification['pitch_correction_risk']}`",
        "",
        "## Pitch Analysis",
        "",
        f"- pitch_confidence: `{pitch['monophonic_pitch_confidence']:.3f}`",
        f"- voiced_frame_ratio: `{pitch.get('voiced_frame_ratio', 0.0):.3f}`",
        f"- key_confidence: `{pitch.get('key_confidence', pitch.get('scale_key_confidence', 0.0)):.3f}`",
        f"- scale_confidence: `{pitch.get('scale_confidence', pitch.get('scale_key_confidence', 0.0)):.3f}`",
        f"- vibrato_presence: `{pitch.get('vibrato_presence', 0.0):.3f}`",
        f"- pitch_jump_density: `{pitch.get('pitch_jump_density', 0.0):.3f}`",
        f"- polyphonic_contamination_score: `{pitch.get('polyphonic_contamination_score', 0.0):.3f}`",
        "",
        "## Safety Gate Decision",
        "",
        f"- decision: `{gate.get('decision', 'skip')}`",
        f"- risk: `{gate.get('risk', 'unsafe')}`",
        f"- reason codes: `{', '.join(gate.get('reason_codes', [])) or 'none'}`",
        f"- manual approval required: `{str(gate.get('requires_manual_approval', True)).lower()}`",
        "",
        "## Plugin Adapter",
        "",
        f"- Plugin: `{plan['proposed_plugin']}`",
        f"- adapter confidence: `{plan['adapter_mapping_confidence']}`",
        f"- semantic controls written: `{', '.join(plan.get('semantic_controls_to_write', {}).keys()) or 'none'}`",
        f"- semantic controls skipped: `{', '.join(plan.get('semantic_controls_skipped', {}).keys()) or 'none'}`",
        "- unknown parameters avoided: `true`",
        "",
        "## Correction Settings",
        "",
        f"- profile: `{plan.get('correction_profile', 'unknown')}`",
        f"- correction_amount: `{settings.get('correction_amount', 0.0)}`",
        f"- speed: `{settings.get('speed', 0.0)}`",
        f"- depth: `{settings.get('depth', 0.0)}`",
        f"- formant_preserve: `{settings.get('formant_preserve', 'unmapped')}`",
        f"- humanize: `{settings.get('humanize', 'unmapped')}`",
        f"- vibrato_preserve: `{settings.get('vibrato_preserve', 'unmapped')}`",
        f"- dry_wet: `{settings.get('dry_wet', 0.0)}`",
        "```json",
        json.dumps(settings, indent=2),
        "```",
        "",
        "## A/B Render Files",
        "",
        f"- original: `{ab_metrics.get('original_path', 'not_created')}`",
        f"- pitch processed: `{ab_metrics.get('processed_path', 'not_created')}`",
        f"- loudness matched: `{ab_metrics.get('loudness_matched_path', 'not_created')}`",
        f"- difference: `{ab_metrics.get('difference_path', 'not_created')}`",
        "",
        "## Damage Metrics",
        "",
        f"- formant_drift_score: `{ab_metrics.get('formant_drift_score', 0.0)}`",
        f"- metallic_increase_score: `{ab_metrics.get('metallic_increase_score', 0.0)}`",
        f"- clarity_loss_db: `{ab_metrics.get('clarity_loss_db', 0.0)}`",
        f"- air_loss_db: `{ab_metrics.get('air_loss_db', 0.0)}`",
        f"- transient_loss: `{ab_metrics.get('transient_loss', 0.0)}`",
        f"- stereo_width_change: `{ab_metrics.get('stereo_width_change', 0.0)}`",
        f"- tail_warble_score: `{ab_metrics.get('tail_warble_score', 0.0)}`",
        f"- reverb_tail_pitch_drag_score: `{ab_metrics.get('reverb_tail_pitch_drag_score', 0.0)}`",
        f"- difference_source_energy: `{ab_metrics.get('difference_source_energy', 0.0)}`",
        "",
        "## Iteration History",
        "",
    ]
    iteration_history = build_iteration_history(settings, [ab_metrics] if ab_metrics else [])
    for item in iteration_history["iterations"]:
        lines.append(f"- iteration {item['iteration']}: `{item['decision']}`")
    lines.extend(["", "## Warnings", ""])
    warnings = list(ab_metrics.get("warnings", [])) + list(plan.get("skip_or_caution_reasons", []))
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")
    lines.extend(["", "## Final Recommendation", "", f"`{plan['final_recommendation']}`", "", "## Manual Listening Checklist", ""])
    lines.extend(
        [
            "- Does the vocal sound more robotic?",
            "- Are sibilants warbling?",
            "- Did reverb tails start bending?",
            "- Did the vocal get thinner?",
            "- Did consonants smear?",
            "- Did stereo image become unstable?",
            "- Did the source sound more AI-like?",
            "- Is the improvement only pitch-locking but not musical quality?",
            "",
            "## Rollback Conditions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in ROLLBACK_CRITERIA)
    lines.extend(["", "For Suno-style or already mixed AI audio, the safest pitch correction is often no pitch correction."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_analysis(
    input_path: Path,
    output_dir: Path,
    track_name: str,
    adapter_status_path: Path | None = None,
    processed_path: Path | None = None,
    user_goal_allows_pitch: bool = True,
    force_full_mix_experiment: bool = False,
    override_mode: str = "default_conservative",
) -> dict[str, Path]:
    audio = read_wav(input_path)
    classification, pitch = analyze_source(audio, track_name)
    adapter_status = load_adapter_status(adapter_status_path)
    plan = build_chain_plan(
        classification,
        pitch,
        adapter_status,
        user_goal_allows_pitch=user_goal_allows_pitch,
        force_full_mix_experiment=force_full_mix_experiment,
        override_mode=override_mode,
    )

    stem = safe_filename(track_name)
    classification_path = output_dir / "analysis_reports" / f"{stem}_source_classification.json"
    pitch_path = output_dir / "analysis_reports" / f"{stem}_pitch_analysis.json"
    plan_path = output_dir / "chain_plans" / f"{stem}_pitch_chain_plan.json"
    plan["source_reports"] = [str(classification_path), str(pitch_path)]
    plan["chain_plan_path"] = str(plan_path)
    write_json(classification_path, classification)
    write_json(pitch_path, pitch)
    write_json(plan_path, plan)

    ab_metrics = None
    eval_metrics_path = output_dir / "eval_reports" / f"{stem}_pitch_eval_metrics.json"
    if processed_path is not None:
        ab_metrics = evaluate_pitch_ab(input_path, processed_path, output_dir, track_name)
    else:
        ab_metrics = missing_render_metrics(track_name, {"original": str(input_path) if input_path.exists() else None})
        write_json(eval_metrics_path, ab_metrics)
    iteration_history = build_iteration_history(plan.get("semantic_settings", {}), [ab_metrics])
    iteration_history_path = output_dir / "eval_reports" / f"{stem}_pitch_iteration_history.json"
    write_json(iteration_history_path, iteration_history)
    human_path = write_human_report(output_dir, track_name, classification, pitch, plan, ab_metrics)
    return {
        "classification": classification_path,
        "pitch_analysis": pitch_path,
        "chain_plan": plan_path,
        "eval_metrics": eval_metrics_path,
        "iteration_history": iteration_history_path,
        "human_report": human_path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify already-mixed AI/Suno-style pitch correction risk.")
    parser.add_argument("--input", required=True, type=Path, help="User-owned WAV file to analyze.")
    parser.add_argument("--track-name", default=None, help="Track name used for report filenames.")
    parser.add_argument("--output-dir", default=Path("automix"), type=Path, help="Output root.")
    parser.add_argument("--adapter-status-json", default=None, type=Path, help="Optional high-confidence learned adapter mapping status.")
    parser.add_argument("--processed", default=None, type=Path, help="Optional processed draft WAV for A/B difference metrics.")
    parser.add_argument(
        "--mode",
        default="default_conservative",
        choices=[
            "default_conservative",
            "no_pitch_correction",
            "allow_light_pitch_draft",
            "allow_full_mix_pitch_experiment",
            "creative_robotic_autotune",
        ],
        help="Explicit pitch safety override mode.",
    )
    parser.add_argument("--force-full-mix-experiment", action="store_true", help="Allow only an explicit full-mix draft experiment plan.")
    parser.add_argument("--disallow-pitch-goal", action="store_true", help="Force policy to skip pitch correction.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    track_name = args.track_name or args.input.stem
    paths = run_analysis(
        input_path=args.input,
        output_dir=args.output_dir,
        track_name=track_name,
        adapter_status_path=args.adapter_status_json,
        processed_path=args.processed,
        user_goal_allows_pitch=not args.disallow_pitch_goal,
        force_full_mix_experiment=args.force_full_mix_experiment,
        override_mode=args.mode,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
