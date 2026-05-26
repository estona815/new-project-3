from __future__ import annotations

from pathlib import Path
from typing import Any

from audio_analysis import flatten_channels, mono_mix, read_wav_float
from loudness_estimation import rms_db
from section_detection import windowed_features


def analyze_reference_audio(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"available": False, "reason": "reference audio not provided"}
    if not path.exists():
        return {"available": False, "path": str(path), "reason": "reference audio missing"}
    metadata, channels = read_wav_float(path)
    mono = mono_mix(channels)
    features = windowed_features(mono, metadata["sample_rate"], window_seconds=0.5)
    samples = flatten_channels(channels)
    peak = max((abs(sample) for sample in samples), default=0.0)
    onset_density = sum(item["onset_density"] for item in features) / len(features) if features else 0.0
    energies = [item["energy"] for item in features]
    dynamic_range = (max(energies) - min(energies)) if energies else 0.0
    brightness = 0.0
    if len(mono) > 1:
        brightness = sum(abs(right - left) for left, right in zip(mono, mono[1:])) / max(1, len(mono) - 1)
    low_end_weight = 0.0
    if mono:
        slow = sum(abs(sample) for sample in mono[:: max(1, metadata["sample_rate"] // 200)]) / max(1, len(mono[:: max(1, metadata["sample_rate"] // 200)]))
        full = sum(abs(sample) for sample in mono) / len(mono)
        low_end_weight = slow / full if full > 0 else 0.0
    stereo_width = 0.0
    if len(channels) >= 2:
        length = min(len(channels[0]), len(channels[1]))
        side = sum(abs(channels[0][i] - channels[1][i]) for i in range(length)) / max(1, length)
        mid = sum(abs(channels[0][i] + channels[1][i]) for i in range(length)) / max(1, length)
        stereo_width = side / mid if mid > 0 else 0.0
    energy_curve = [
        {"start": round(item["start"], 3), "end": round(item["end"], 3), "energy": round(item["energy"], 6)}
        for item in features[:24]
    ]
    return {
        "available": True,
        "path": str(path),
        "duration_seconds": metadata["duration_seconds"],
        "sample_rate": metadata["sample_rate"],
        "tempo_estimate": None,
        "tempo_note": "Tempo is not extracted exactly; use DAW tap tempo or beat-grid confirmation.",
        "onset_density": onset_density,
        "kick_snare_event_density_heuristic": onset_density,
        "spectral_brightness_heuristic": brightness,
        "low_end_weight_heuristic": low_end_weight,
        "dynamic_range_heuristic": dynamic_range,
        "section_energy_curve": energy_curve,
        "stereo_width_estimate": stereo_width,
        "transient_sharpness": onset_density,
        "rms_dbfs": rms_db(samples),
        "peak_linear": peak,
        "safety_note": "No melodies, samples, lyrics, or exact patterns are extracted or copied.",
    }
