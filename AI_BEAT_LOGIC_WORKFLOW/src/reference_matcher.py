from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile

from audio_metrics import (
    BAND_RANGES,
    band_eq,
    bandpass,
    clipping_count,
    crest_db,
    db_to_linear,
    harshness_score,
    mono,
    mono_compatibility,
    oversampled_peak_db,
    peak_db,
    rms,
    rms_db,
    side_mid_db,
    sibilance_score,
    spectral_band_profile,
)


def _to_float_audio(data: np.ndarray) -> np.ndarray:
    if data.dtype.kind in "iu":
        peak = float(np.iinfo(data.dtype).max)
        return (data.astype(np.float32) / max(1.0, peak)).astype(np.float32)
    return data.astype(np.float32, copy=False)


def _round_float(value: float, digits: int = 2) -> float:
    if not np.isfinite(value):
        return 0.0
    return round(float(value), digits)


def _median(values: Iterable[float], digits: int = 2) -> float:
    vals = [float(value) for value in values if np.isfinite(float(value))]
    if not vals:
        return 0.0
    return round(float(np.median(vals)), digits)


def side_mid_by_band(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    stereo = np.asarray(audio, dtype=np.float32)
    if stereo.ndim == 1:
        stereo = np.column_stack((stereo, stereo)).astype(np.float32)
    elif stereo.shape[1] == 1:
        stereo = np.repeat(stereo, 2, axis=1).astype(np.float32)
    left = stereo[:, 0]
    right = stereo[:, 1]
    mid = ((left + right) * 0.5)[:, None]
    side = ((left - right) * 0.5)[:, None]
    out: dict[str, float] = {}
    for name, (low, high) in BAND_RANGES.items():
        mid_rms = rms(bandpass(mid, low, high, sample_rate)) + 1e-12
        side_rms = rms(bandpass(side, low, high, sample_rate)) + 1e-12
        out[name] = _round_float(20.0 * np.log10(side_rms / mid_rms))
    return out


def transient_density(audio: np.ndarray, sample_rate: int) -> float:
    samples = mono(audio)
    frame = max(128, int(sample_rate * 0.02))
    hop = max(64, frame // 2)
    if samples.shape[0] < frame:
        return 0.0
    env = []
    for start in range(0, samples.shape[0] - frame + 1, hop):
        chunk = samples[start : start + frame]
        env.append(float(np.sqrt(np.mean(np.square(chunk, dtype=np.float64)))))
    envelope = np.asarray(env, dtype=np.float32)
    if envelope.size < 3:
        return 0.0
    diff = np.maximum(np.diff(envelope), 0.0)
    threshold = float(np.median(diff) + np.std(diff) * 1.5)
    events = int(np.sum(diff > threshold))
    duration = samples.shape[0] / sample_rate
    return _round_float(events / max(duration, 1e-9), 3)


def low_end_tightness(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    mono_audio = mono(audio)[:, None]
    sub = bandpass(mono_audio, 20.0, 60.0, sample_rate)
    bass = bandpass(mono_audio, 60.0, 120.0, sample_rate)
    low_mid = bandpass(mono_audio, 120.0, 400.0, sample_rate)
    sub_rms = rms(sub) + 1e-12
    bass_rms = rms(bass) + 1e-12
    low_mid_rms = rms(low_mid) + 1e-12
    sub_peak = float(np.max(np.abs(sub))) + 1e-12
    return {
        "sub_to_bass_db": _round_float(20.0 * np.log10(sub_rms / bass_rms)),
        "bass_to_low_mid_db": _round_float(20.0 * np.log10(bass_rms / low_mid_rms)),
        "sub_crest_db": _round_float(20.0 * np.log10(sub_peak / sub_rms)),
    }


def vocal_presence_proxy(audio: np.ndarray, sample_rate: int) -> float:
    mono_audio = mono(audio)[:, None]
    presence = rms(bandpass(mono_audio, 1_500.0, 4_500.0, sample_rate)) + 1e-12
    low_mid = rms(bandpass(mono_audio, 150.0, 400.0, sample_rate)) + 1e-12
    mid = rms(bandpass(mono_audio, 400.0, 1_500.0, sample_rate)) + 1e-12
    return _round_float(20.0 * np.log10(presence / ((low_mid + mid) * 0.5)))


def analyze_reference_audio(audio: np.ndarray, sample_rate: int, path: str | None = None) -> dict[str, Any]:
    current_peak = peak_db(audio)
    current_rms = rms_db(audio)
    mono_report = mono_compatibility(audio)
    mono_report["side_mid_db"] = side_mid_db(audio)
    return {
        "path": path,
        "peak_dbfs": _round_float(current_peak),
        "oversampled_peak_proxy_dbfs": _round_float(oversampled_peak_db(audio, 4)),
        "rms_dbfs": _round_float(current_rms),
        "crest_db": _round_float(current_peak - current_rms),
        "side_mid_db": side_mid_db(audio),
        "band_db_rel_to_mono_rms": spectral_band_profile(audio, sample_rate),
        "side_mid_by_band_db": side_mid_by_band(audio, sample_rate),
        "transient_density_per_sec": transient_density(audio, sample_rate),
        "low_end_tightness": low_end_tightness(audio, sample_rate),
        "harshness_score_db": harshness_score(audio, sample_rate),
        "sibilance_score_db": sibilance_score(audio, sample_rate),
        "vocal_presence_proxy_db": vocal_presence_proxy(audio, sample_rate),
        "mono_compatibility": mono_report,
        "clipping_count": clipping_count(audio),
    }


def _profile_from_existing(ref: dict[str, Any]) -> dict[str, Any]:
    profile = dict(ref)
    bands = profile.get("band_db_rel_to_mono_rms", {})
    profile.setdefault("side_mid_by_band_db", {name: profile.get("side_mid_db", 0.0) for name in BAND_RANGES})
    profile.setdefault("transient_density_per_sec", 0.0)
    profile.setdefault("low_end_tightness", {"sub_to_bass_db": 0.0, "bass_to_low_mid_db": 0.0, "sub_crest_db": profile.get("crest_db", 0.0)})
    bite = bands.get("bite_4500_8000", -18.0)
    presence = bands.get("presence_1500_4500", -14.0)
    air = bands.get("air_8000_16000", -18.0)
    profile.setdefault("harshness_score_db", _round_float(bite - presence))
    profile.setdefault("sibilance_score_db", _round_float(air))
    profile.setdefault("vocal_presence_proxy_db", _round_float(presence - bands.get("low_mid_150_400", presence)))
    profile.setdefault("mono_compatibility", {"left_right_correlation": 1.0, "mono_level_delta_db": 0.0, "side_mid_db": profile.get("side_mid_db", 0.0)})
    return profile


def build_reference_profile(references: list[dict[str, Any]]) -> dict[str, Any]:
    refs = [_profile_from_existing(ref) for ref in references if ref]
    if not refs:
        return {}
    return {
        "reference_count": len(refs),
        "broad_texture_only": True,
        "no_exact_copying": True,
        "aggregation": "median",
        "rms_dbfs": _median(ref["rms_dbfs"] for ref in refs),
        "crest_db": _median(ref["crest_db"] for ref in refs),
        "side_mid_db": _median(ref["side_mid_db"] for ref in refs),
        "band_db_rel_to_mono_rms": {
            name: _median(ref["band_db_rel_to_mono_rms"][name] for ref in refs if name in ref.get("band_db_rel_to_mono_rms", {}))
            for name in BAND_RANGES
        },
        "side_mid_by_band_db": {
            name: _median(ref["side_mid_by_band_db"][name] for ref in refs if name in ref.get("side_mid_by_band_db", {}))
            for name in BAND_RANGES
        },
        "transient_density_per_sec": _median((ref["transient_density_per_sec"] for ref in refs), 3),
        "low_end_tightness": {
            key: _median(ref.get("low_end_tightness", {}).get(key, 0.0) for ref in refs)
            for key in ["sub_to_bass_db", "bass_to_low_mid_db", "sub_crest_db"]
        },
        "harshness_score_db": _median(ref["harshness_score_db"] for ref in refs),
        "sibilance_score_db": _median(ref["sibilance_score_db"] for ref in refs),
        "vocal_presence_proxy_db": _median(ref["vocal_presence_proxy_db"] for ref in refs),
        "mono_compatibility": {
            "left_right_correlation": _median((ref.get("mono_compatibility", {}).get("left_right_correlation", 1.0) for ref in refs), 4),
            "mono_level_delta_db": _median(ref.get("mono_compatibility", {}).get("mono_level_delta_db", 0.0) for ref in refs),
        },
    }


def load_reference_average(path: str | Path) -> dict[str, Any]:
    ref_path = Path(path)
    if not ref_path.exists():
        return {}
    data = json.loads(ref_path.read_text(encoding="utf-8"))
    refs: list[dict[str, Any]] = []
    for key, value in data.items():
        if not key.startswith("ref_"):
            continue
        wav_path = value.get("path")
        resolved = (ref_path.parents[1] / wav_path).resolve() if wav_path and not Path(wav_path).is_absolute() else Path(wav_path or "")
        if wav_path and resolved.exists():
            sample_rate, audio = wavfile.read(resolved)
            refs.append(analyze_reference_audio(_to_float_audio(audio), int(sample_rate), str(resolved)))
        else:
            refs.append(_profile_from_existing(value))
    return build_reference_profile(refs)


def compare_to_reference(audio: np.ndarray, sample_rate: int, reference_average: dict[str, Any]) -> dict[str, Any]:
    current = analyze_reference_audio(audio, sample_rate)
    out: dict[str, Any] = {key: current[key] for key in ["peak_dbfs", "rms_dbfs", "crest_db", "side_mid_db", "band_db_rel_to_mono_rms"]}
    if not reference_average:
        return out
    out["band_delta_vs_reference_average_db"] = {
        name: _round_float(current["band_db_rel_to_mono_rms"][name] - reference_average["band_db_rel_to_mono_rms"][name])
        for name in BAND_RANGES
    }
    out["stereo_delta_by_band_db"] = {
        name: _round_float(current["side_mid_by_band_db"][name] - reference_average["side_mid_by_band_db"][name])
        for name in BAND_RANGES
    }
    out["loudness_density_delta"] = {
        "rms_db": _round_float(current["rms_dbfs"] - reference_average["rms_dbfs"]),
        "crest_db": _round_float(current["crest_db"] - reference_average["crest_db"]),
        "transient_density_per_sec": _round_float(current["transient_density_per_sec"] - reference_average["transient_density_per_sec"], 3),
    }
    out["harshness_sibilance_delta"] = {
        "harshness_db": _round_float(current["harshness_score_db"] - reference_average["harshness_score_db"]),
        "sibilance_db": _round_float(current["sibilance_score_db"] - reference_average["sibilance_score_db"]),
    }
    out["low_end_tightness_delta"] = {
        key: _round_float(current["low_end_tightness"][key] - reference_average["low_end_tightness"][key])
        for key in ["sub_to_bass_db", "bass_to_low_mid_db", "sub_crest_db"]
    }
    out["vocal_presence_proxy_delta_db"] = _round_float(current["vocal_presence_proxy_db"] - reference_average["vocal_presence_proxy_db"])
    return out


def build_tone_corrections(audio: np.ndarray, sample_rate: int, reference_profile: dict[str, Any], max_tonal_db: float = 1.5) -> tuple[list[dict[str, float]], list[str]]:
    current = analyze_reference_audio(audio, sample_rate)
    warnings: list[str] = []
    corrections: list[dict[str, float]] = []
    if not reference_profile:
        return corrections, ["reference profile unavailable; skipped tone-aware correction"]
    for name, (low, high) in BAND_RANGES.items():
        current_band = current["band_db_rel_to_mono_rms"][name]
        target_band = reference_profile["band_db_rel_to_mono_rms"][name]
        delta = target_band - current_band
        gain = float(np.clip(delta * 0.45, -max_tonal_db, max_tonal_db))
        if name in {"bite_4500_8000", "air_8000_16000"} and gain > 0.0:
            if current["harshness_score_db"] >= reference_profile["harshness_score_db"] - 0.5 or current["sibilance_score_db"] >= reference_profile["sibilance_score_db"] - 1.0:
                warnings.append(f"ignored {name} boost to avoid harsher/sibilant top-end chasing")
                gain = 0.0
            else:
                gain = min(gain, 0.6)
        if name in {"presence_1500_4500", "mid_400_1500"} and gain < -0.75 and current["vocal_presence_proxy_db"] <= reference_profile["vocal_presence_proxy_db"] + 0.5:
            warnings.append(f"limited {name} cut to preserve vocal clarity")
            gain = -0.75
        if abs(gain) >= 0.1:
            corrections.append({"band": name, "low_hz": low, "high_hz": high, "gain_db": _round_float(gain)})
    return corrections, warnings


def apply_tone_aware_reference_correction(
    audio: np.ndarray,
    sample_rate: int,
    reference_profile: dict[str, Any],
    max_tonal_db: float = 1.5,
    max_width_db: float = 0.45,
) -> tuple[np.ndarray, dict[str, Any]]:
    before = analyze_reference_audio(audio, sample_rate)
    corrections, warnings = build_tone_corrections(audio, sample_rate, reference_profile, max_tonal_db=max_tonal_db)
    out = audio.astype(np.float32, copy=True)
    applied: list[dict[str, float]] = []
    for correction in corrections:
        out = band_eq(out, correction["low_hz"], correction["high_hz"], correction["gain_db"], sample_rate)
        applied.append(correction)
    after = analyze_reference_audio(out, sample_rate)
    ignored: list[str] = [
        "RMS/crest numeric match is advisory only; no extra compression is applied here",
        "no sample, melody, pattern, or vocal identity extraction from references",
    ]
    if clipping_count(out) > clipping_count(audio) or oversampled_peak_db(out, 4) > -0.2:
        warnings.append("rejected correction because clipping or true-peak proxy safety worsened")
        out = audio.astype(np.float32, copy=False)
        after = before
        applied = []
    elif after["harshness_score_db"] > before["harshness_score_db"] + 1.0 and after["vocal_presence_proxy_db"] <= before["vocal_presence_proxy_db"]:
        warnings.append("rejected correction because musical QC worsened: harsher top without vocal clarity gain")
        out = audio.astype(np.float32, copy=False)
        after = before
        applied = []
    stereo_delta = {}
    if reference_profile:
        current_width = before["side_mid_by_band_db"]
        target_width = reference_profile.get("side_mid_by_band_db", {})
        stereo_delta = {name: _round_float(current_width.get(name, 0.0) - target_width.get(name, 0.0)) for name in BAND_RANGES}
        if any(abs(value) > max_width_db for value in stereo_delta.values()):
            warnings.append("width differences reported only; no fake widening applied by reference matcher")
    return out.astype(np.float32), {
        "matched_traits": {
            "spectral_band_energy": True,
            "stereo_by_band_analyzed": True,
            "transient_density_analyzed": True,
            "low_end_tightness_analyzed": True,
            "harshness_sibilance_guarded": True,
            "mono_compatibility_guarded": True,
        },
        "ignored_traits": ignored,
        "correction_amounts": applied,
        "stereo_delta_by_band_db": stereo_delta,
        "warnings": warnings,
        "limitations": [
            "reference tracks are used for broad tone and texture only",
            "single-bus matching cannot infer stems or vocal arrangement decisions",
            "corrections are intentionally capped and may leave numeric deltas unresolved",
        ],
        "before": compare_to_reference(audio, sample_rate, reference_profile),
        "after": compare_to_reference(out, sample_rate, reference_profile),
    }
