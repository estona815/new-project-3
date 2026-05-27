#!/usr/bin/env python3
"""Diagnostic f0/pitch-feel analysis for policy hints, not manual tuning."""

from pathlib import Path

import numpy as np

from audio_utils import find_audio_files, load_audio, mono_signal, resolve_path, write_json
from current_song_analyzer import guess_stem_type

try:
    import librosa
except Exception:  # pragma: no cover
    librosa = None


def autocorr_f0(signal: np.ndarray, sr: int, frame: int = 2048, hop: int = 512) -> np.ndarray:
    f0s = []
    low, high = int(sr / 600), int(sr / 70)
    for start in range(0, max(1, len(signal) - frame), hop):
        x = signal[start : start + frame]
        if len(x) < frame or np.sqrt(np.mean(x * x) + 1e-12) < 0.01:
            f0s.append(np.nan)
            continue
        x = x - np.mean(x)
        corr = np.correlate(x, x, mode="full")[len(x) - 1 :]
        segment = corr[low:high]
        if segment.size == 0 or np.max(segment) <= 0:
            f0s.append(np.nan)
        else:
            lag = low + int(np.argmax(segment))
            f0s.append(float(sr / lag))
    return np.asarray(f0s, dtype=np.float64)


def analyze_pitch() -> dict:
    out = resolve_path("02_ANALYSIS", "vocal_pitch_analysis.json")
    stems = [p for p in find_audio_files(resolve_path("01_CURRENT_SONG", "stems")) if guess_stem_type(p)[0] in {"lead_vocal", "backing_vocal"}]
    if not stems:
        result = {"status": "no_vocal_stems", "message": "No vocal stems found for pitch diagnostics.", "tracks": []}
        write_json(out, result)
        return result
    tracks = []
    for path in stems:
        try:
            audio, sr = load_audio(path, mono=True, target_sr=22050)
            y = mono_signal(audio)
            if librosa is not None:
                f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C6"), sr=sr)
            else:
                f0 = autocorr_f0(y, sr)
            valid = f0[np.isfinite(f0)]
            coverage = float(valid.size / max(1, f0.size))
            if valid.size > 2:
                cents = 1200 * np.log2(valid / np.median(valid))
                diffs = np.diff(cents)
                stability = float(max(0.0, 1.0 - np.std(diffs) / 250.0))
                jump_rate = float(np.mean(np.abs(diffs) > 250))
                transition = float(max(0.0, 1.0 - np.mean(np.abs(diffs)) / 180.0))
                snap = float(np.mean((np.abs(diffs) > 80) & (np.abs(diffs) < 220)))
                vib_depth = float(np.percentile(cents, 90) - np.percentile(cents, 10))
            else:
                stability = transition = 0.0
                jump_rate = snap = vib_depth = 0.0
            tracks.append({
                "file": str(path),
                "stem_type": guess_stem_type(path)[0],
                "f0_coverage_ratio": coverage,
                "pitch_stability_score": stability,
                "pitch_jump_rate": jump_rate,
                "note_transition_smoothness": transition,
                "phrase_end_instability": max(0.0, 1.0 - stability) * coverage,
                "vibrato_depth_proxy": vib_depth,
                "vibrato_rate_proxy": 0.0,
                "pitch_snap_artifact_score": snap,
                "formant_shift_suspicion_proxy": max(0.0, snap - transition * 0.3),
                "confidence": "medium" if coverage > 0.35 else "low",
                "policy_hints": policy_hints(coverage, stability, snap),
            })
        except Exception as exc:
            tracks.append({"file": str(path), "error": str(exc), "confidence": "low"})
    result = {"status": "ok", "tracks": tracks}
    write_json(out, result)
    return result


def policy_hints(coverage: float, stability: float, snap: float) -> list:
    hints = []
    if coverage < 0.25:
        hints.append("피치 분석 신뢰도 낮음")
    if snap > 0.35:
        hints += ["보컬 고역 harshness 완화", "short ambience 추가", "double layer gain down"]
    if stability < 0.35:
        hints += ["phrase-end automation 필요 표시", "끝음 구간 backing vocal 침범 확인"]
    return hints


if __name__ == "__main__":
    result = analyze_pitch()
    print(f"vocal pitch status: {result.get('status')}")
