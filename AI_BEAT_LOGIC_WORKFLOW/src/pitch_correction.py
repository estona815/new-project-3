from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import signal

from audio_metrics import bandpass, filter_audio, linear_to_db, mono, normalize_peak, rms


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
CHROMATIC_SCALE = tuple(range(12))
DEFAULT_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
MODE_STRENGTH = {"subtle": 0.22, "medium": 0.52, "hard_effect": 0.82}
MODE_MAX_SHIFT = {"subtle": 0.75, "medium": 1.25, "hard_effect": 2.0}


@dataclass(frozen=True)
class PitchCorrectionSettings:
    root_midi: int = 60
    scale_degrees: tuple[int, ...] = DEFAULT_MINOR_SCALE
    key_confidence: float = 0.75
    frame_size: int = 2048
    hop_size: int = 512
    blend: float = 0.12
    mode: str = "subtle"
    max_shift_semitones: float | None = None
    humanize: float = 0.18
    min_hz: float = 75.0
    max_hz: float = 850.0
    confidence_threshold: float = 0.28
    voiced_rms_threshold_db: float = -54.0
    tuned_layer_lowpass_hz: float = 4_000.0


def f0_to_midi(f0_hz: float) -> float:
    return 69.0 + 12.0 * np.log2(f0_hz / 440.0)


def midi_to_hz(midi_note: float) -> float:
    return float(440.0 * (2.0 ** ((midi_note - 69.0) / 12.0)))


def midi_to_note_name(midi_note: float) -> str:
    rounded = int(round(midi_note))
    return f"{NOTE_NAMES[rounded % 12]}{rounded // 12 - 1}"


def nearest_scale_midi(midi_note: float, root_midi: int, scale_degrees: tuple[int, ...]) -> int:
    candidates: list[int] = []
    root_pc = root_midi % 12
    center_octave = int(round(midi_note)) // 12
    for octave in range(center_octave - 2, center_octave + 3):
        candidates.extend(octave * 12 + root_pc + degree for degree in scale_degrees)
    return min(candidates, key=lambda note: abs(note - midi_note))


def estimate_pitch_autocorr(
    frame: np.ndarray,
    sample_rate: int,
    min_hz: float = 75.0,
    max_hz: float = 850.0,
) -> float | None:
    result = estimate_pitch_frame(frame, sample_rate, min_hz=min_hz, max_hz=max_hz)
    return result["f0_hz"] if result["voiced"] else None


def estimate_pitch_frame(
    frame: np.ndarray,
    sample_rate: int,
    *,
    min_hz: float = 75.0,
    max_hz: float = 850.0,
    rms_threshold_db: float = -54.0,
) -> dict[str, float | bool]:
    samples = mono(frame).astype(np.float32)
    if samples.size < 32:
        return {"voiced": False, "f0_hz": 0.0, "confidence": 0.0, "rms_dbfs": -120.0}
    frame_rms = rms(samples)
    frame_rms_db = linear_to_db(frame_rms + 1e-12)
    if frame_rms_db < rms_threshold_db:
        return {"voiced": False, "f0_hz": 0.0, "confidence": 0.0, "rms_dbfs": round(frame_rms_db, 2)}
    samples = samples - float(np.mean(samples))
    samples *= signal.windows.hann(samples.shape[0], sym=False).astype(np.float32)
    corr = signal.correlate(samples, samples, mode="full")[samples.size - 1 :]
    zero_lag = float(corr[0]) + 1e-12
    min_lag = max(1, int(sample_rate / max_hz))
    max_lag = min(corr.shape[0] - 1, int(sample_rate / min_hz))
    if max_lag <= min_lag:
        return {"voiced": False, "f0_hz": 0.0, "confidence": 0.0, "rms_dbfs": round(frame_rms_db, 2)}
    search = corr[min_lag:max_lag]
    lag = int(np.argmax(search) + min_lag)
    confidence = float(corr[lag] / zero_lag)
    zcr = float(np.mean(np.abs(np.diff(np.signbit(samples)))))
    high_ratio = rms(bandpass(samples[:, None], 4_000.0, min(10_000.0, sample_rate / 2 - 100.0), sample_rate)) / (frame_rms + 1e-12)
    voiced = bool(confidence >= 0.24 and zcr < 0.24 and high_ratio < 1.2)
    return {"voiced": voiced, "f0_hz": float(sample_rate / lag) if voiced else 0.0, "confidence": round(confidence, 4), "rms_dbfs": round(frame_rms_db, 2)}


def analyze_pitch_frames(audio: np.ndarray, sample_rate: int, settings: PitchCorrectionSettings | None = None) -> list[dict[str, Any]]:
    cfg = settings or PitchCorrectionSettings()
    samples = mono(audio)[:, None]
    frames: list[dict[str, Any]] = []
    for start in range(0, max(0, samples.shape[0] - cfg.frame_size + 1), cfg.hop_size):
        frame = samples[start : start + cfg.frame_size]
        detected = estimate_pitch_frame(frame, sample_rate, min_hz=cfg.min_hz, max_hz=cfg.max_hz, rms_threshold_db=cfg.voiced_rms_threshold_db)
        if detected["voiced"]:
            midi = f0_to_midi(float(detected["f0_hz"]))
            scale = cfg.scale_degrees if cfg.key_confidence >= 0.45 else CHROMATIC_SCALE
            target_midi = nearest_scale_midi(midi, cfg.root_midi, scale)
            note_name = midi_to_note_name(midi)
            target_note_name = midi_to_note_name(target_midi)
        else:
            midi = 0.0
            target_midi = 0
            note_name = "unvoiced"
            target_note_name = "unvoiced"
        frames.append(
            {
                "start_frame": start,
                "start_seconds": round(start / sample_rate, 4),
                **detected,
                "midi": round(float(midi), 3),
                "note": note_name,
                "target_midi": int(target_midi),
                "target_note": target_note_name,
            }
        )
    return frames


def pitch_shift_frame(frame: np.ndarray, semitones: float) -> np.ndarray:
    if abs(semitones) < 0.02 or frame.shape[0] < 8:
        return frame.astype(np.float32, copy=False)
    factor = 2.0 ** (semitones / 12.0)
    target_frames = max(8, int(frame.shape[0] / factor))
    shifted = signal.resample(mono(frame), target_frames).astype(np.float32)
    if shifted.shape[0] < frame.shape[0]:
        shifted = np.pad(shifted, (0, frame.shape[0] - shifted.shape[0]))
    return shifted[: frame.shape[0], None].astype(np.float32)


def _mode_strength(settings: PitchCorrectionSettings) -> tuple[float, float]:
    strength = MODE_STRENGTH.get(settings.mode, MODE_STRENGTH["subtle"])
    max_shift = settings.max_shift_semitones if settings.max_shift_semitones is not None else MODE_MAX_SHIFT.get(settings.mode, MODE_MAX_SHIFT["subtle"])
    return strength, max_shift


def generate_tuned_support_layer(
    audio: np.ndarray,
    sample_rate: int,
    settings: PitchCorrectionSettings | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    cfg = settings or PitchCorrectionSettings()
    samples = mono(audio)[:, None]
    if samples.shape[0] < cfg.frame_size:
        return np.zeros_like(samples, dtype=np.float32), {"applied": False, "method": "native pitch-correction approximation", "frames_corrected": 0}
    strength, max_shift = _mode_strength(cfg)
    correction_strength = float(np.clip(strength * cfg.blend, 0.0, 1.0))
    output = np.zeros_like(samples, dtype=np.float32)
    weight = np.zeros((samples.shape[0], 1), dtype=np.float32)
    window = signal.windows.hann(cfg.frame_size, sym=False).astype(np.float32)[:, None]
    frames = analyze_pitch_frames(samples, sample_rate, cfg)
    corrected = 0
    shifts: list[float] = []
    notes: list[str] = []
    for frame_report in frames:
        start = int(frame_report["start_frame"])
        frame = samples[start : start + cfg.frame_size]
        if not frame_report["voiced"] or float(frame_report["confidence"]) < cfg.confidence_threshold:
            processed = frame
        else:
            delta = float(frame_report["target_midi"]) - float(frame_report["midi"])
            if cfg.humanize > 0.0:
                vibrato_reserve = np.sin(start / sample_rate * 2.0 * np.pi * 5.1) * cfg.humanize * 0.08
                delta = delta * (1.0 - cfg.humanize * 0.35) + vibrato_reserve
            semitones = float(np.clip(delta * correction_strength, -max_shift, max_shift))
            processed = pitch_shift_frame(frame, semitones)
            corrected += 1
            shifts.append(semitones)
            notes.append(str(frame_report["target_note"]))
        output[start : start + cfg.frame_size] += processed * window
        weight[start : start + cfg.frame_size] += window
    tuned = np.divide(output, np.maximum(weight, 1e-6), out=np.zeros_like(output), where=weight > 0.0)
    tuned = filter_audio(tuned, 90.0, cfg.tuned_layer_lowpass_hz, sample_rate)
    tuned, _gain = normalize_peak(tuned, -3.0, max_gain_db=3.0)
    voiced = [frame for frame in frames if frame["voiced"]]
    confidence_values = [float(frame["confidence"]) for frame in voiced]
    return tuned.astype(np.float32), {
        "applied": corrected > 0,
        "method": "native pitch-correction approximation",
        "layer": "tuned support layer",
        "retune_mode": cfg.mode,
        "blend": cfg.blend,
        "correction_strength": round(correction_strength, 3),
        "frames_total": len(frames),
        "frames_corrected": corrected,
        "voiced_ratio": round(len(voiced) / len(frames), 3) if frames else 0.0,
        "mean_confidence": round(float(np.mean(confidence_values)) if confidence_values else 0.0, 3),
        "mean_abs_correction_semitones": round(float(np.mean(np.abs(shifts))) if shifts else 0.0, 3),
        "max_abs_correction_semitones": round(float(np.max(np.abs(shifts))) if shifts else 0.0, 3),
        "estimated_notes": sorted(set(notes))[:16],
        "key_confidence": cfg.key_confidence,
        "scale_mode": "scale_snap" if cfg.key_confidence >= 0.45 else "chromatic_gentle",
        "verified_plugin_used": False,
        "artist_voice_clone": False,
        "limitations": "Approximation only: voiced mid band is shifted conservatively, 4kHz+ sibilance/air is preserved from the original, and the result is blended as support rather than replacing the vocal.",
    }


def native_pitch_correction_approx(
    audio: np.ndarray,
    sample_rate: int,
    settings: PitchCorrectionSettings | None = None,
    *,
    return_layer: bool = False,
) -> tuple[np.ndarray, dict[str, Any]] | tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    cfg = settings or PitchCorrectionSettings()
    original = mono(audio)[:, None]
    layer, report = generate_tuned_support_layer(original, sample_rate, cfg)
    blend_amount = float(np.clip(cfg.blend, 0.0, 0.85))
    high_original = original - filter_audio(original, 0.0, cfg.tuned_layer_lowpass_hz, sample_rate)
    low_original = filter_audio(original, 70.0, cfg.tuned_layer_lowpass_hz, sample_rate)
    processed = low_original * (1.0 - blend_amount) + layer * blend_amount + high_original
    processed, _gain = normalize_peak(processed, -1.0, max_gain_db=1.5)
    report = {
        **report,
        "output": "processed vocal with optional tuned support layer",
        "professional_pitch_correction_applied": False,
        "Antares_AutoTune_applied": False,
        "bypassed_for_artifacts": False,
    }
    if report["mean_confidence"] < 0.25 or report["voiced_ratio"] < 0.08:
        processed = original.astype(np.float32)
        layer = np.zeros_like(original, dtype=np.float32)
        report["applied"] = False
        report["bypassed_for_artifacts"] = True
        report["limitations"] += " Low confidence input caused bypass."
    if return_layer:
        return processed.astype(np.float32), layer.astype(np.float32), report
    return processed.astype(np.float32), report
