from __future__ import annotations

import math
import shutil
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from audio_analysis import clipping_count, flatten_channels, mono_mix, read_wav_float
from loudness_estimation import linear_to_db, rms_db, short_term_loudness_windows
from section_detection import detect_silence_regions
from vocal_to_code import analyze_vocal_to_code


PITCH_TOOLS = ("rubberband", "soundstretch", "sox")


def pitch_tool_status() -> tuple[bool, str]:
    for tool in PITCH_TOOLS:
        found = shutil.which(tool)
        if found:
            return True, found
    return False, "pitch correction/autotune tool unavailable"


def _rms_linear(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def _window_samples(samples: list[float], sample_rate: int, seconds: float = 0.25) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    window_size = max(1, int(sample_rate * seconds))
    windows: list[dict[str, Any]] = []
    for start in range(0, len(samples), window_size):
        end = min(len(samples), start + window_size)
        chunk = samples[start:end]
        if not chunk:
            continue
        peak = max(abs(sample) for sample in chunk)
        rms = _rms_linear(chunk)
        zero_crossings = 0
        if len(chunk) > 1:
            zero_crossings = sum(1 for left, right in zip(chunk, chunk[1:]) if (left < 0 <= right) or (right < 0 <= left))
        derivative_rms = _rms_linear([right - left for left, right in zip(chunk, chunk[1:])])
        windows.append(
            {
                "start": start / sample_rate,
                "end": end / sample_rate,
                "peak": peak,
                "peak_dbfs": linear_to_db(peak),
                "rms": rms,
                "rms_dbfs": linear_to_db(rms),
                "zero_crossing_rate": zero_crossings / max(1, len(chunk) - 1),
                "brightness_ratio": derivative_rms / rms if rms > 0 else 0.0,
            }
        )
    return windows


def _candidate_windows(
    windows: list[dict[str, Any]],
    predicate: Any,
    reason: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for window in windows:
        if predicate(window):
            candidates.append(
                {
                    "start": round(window["start"], 3),
                    "end": round(window["end"], 3),
                    "peak_dbfs": round(window["peak_dbfs"], 2) if math.isfinite(window["peak_dbfs"]) else None,
                    "rms_dbfs": round(window["rms_dbfs"], 2) if math.isfinite(window["rms_dbfs"]) else None,
                    "reason": reason,
                }
            )
    return candidates[:limit]


def _noise_floor_estimate(windows: list[dict[str, Any]]) -> dict[str, Any]:
    voiced = [window["rms_dbfs"] for window in windows if math.isfinite(window["rms_dbfs"]) and window["rms_dbfs"] > -90.0]
    if not voiced:
        return {"estimated_noise_floor_dbfs": None, "method": "No readable non-silent windows."}
    ordered = sorted(voiced)
    quiet_count = max(1, len(ordered) // 10)
    return {
        "estimated_noise_floor_dbfs": round(mean(ordered[:quiet_count]), 2),
        "method": "Mean of quietest readable short windows; heuristic, not a calibrated noise print.",
    }


def _dynamic_summary(loudness_windows: list[dict[str, float]]) -> dict[str, Any]:
    values = [item["loudness_dbfs"] for item in loudness_windows if math.isfinite(item["loudness_dbfs"])]
    if not values:
        return {"dynamic_range_db": None, "phrase_loudness_variation_db": None, "window_count": 0}
    ordered = sorted(values)
    low = ordered[max(0, int(len(ordered) * 0.1) - 1)]
    high = ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))]
    return {
        "dynamic_range_db": round(high - low, 2),
        "phrase_loudness_variation_db": round(pstdev(values), 2) if len(values) > 1 else 0.0,
        "quiet_phrase_loudness_dbfs": round(low, 2),
        "loud_phrase_loudness_dbfs": round(high, 2),
        "window_count": len(values),
    }


def _vocal_density(windows: list[dict[str, Any]], noise_floor_dbfs: float | None) -> dict[str, Any]:
    if not windows:
        return {"active_ratio": 0.0, "active_window_count": 0, "window_count": 0}
    threshold = -45.0 if noise_floor_dbfs is None else max(-45.0, noise_floor_dbfs + 10.0)
    active = [window for window in windows if window["rms_dbfs"] > threshold]
    return {
        "active_ratio": round(len(active) / len(windows), 3),
        "active_window_count": len(active),
        "window_count": len(windows),
        "threshold_dbfs": round(threshold, 2),
    }


def analyze_audio_file(path: Path, label: str, analysis_scope: str) -> dict[str, Any]:
    metadata, channel_samples = read_wav_float(path)
    all_samples = flatten_channels(channel_samples)
    mono = mono_mix(channel_samples)
    windows = _window_samples(mono, metadata["sample_rate"])
    loudness_windows = short_term_loudness_windows(mono, metadata["sample_rate"], window_seconds=1.0, hop_seconds=0.5)
    peak = max((abs(sample) for sample in all_samples), default=0.0)
    noise_floor = _noise_floor_estimate(windows)
    dynamic_summary = _dynamic_summary(loudness_windows)
    density = _vocal_density(windows, noise_floor.get("estimated_noise_floor_dbfs"))
    clipping = clipping_count(all_samples)
    pitch_available, pitch_note = pitch_tool_status()

    direct_metrics = {
        "duration_seconds": metadata["duration_seconds"],
        "sample_rate": metadata["sample_rate"],
        "channels": metadata["channels"],
        "bit_depth": metadata["bit_depth"],
        "peak_dbfs": linear_to_db(peak),
        "rms_dbfs": rms_db(all_samples),
        "clipping_count": clipping,
        "silence": detect_silence_regions(mono, metadata["sample_rate"], threshold=0.001, min_seconds=0.25),
        "noise_floor_estimate": noise_floor,
        "dynamic_range": dynamic_summary,
        "vocal_density": density,
        "phrase_level_loudness_variation": {
            "variation_db": dynamic_summary["phrase_loudness_variation_db"],
            "method": "Short-window RMS spread; practical phrase-ride cue, not LUFS automation.",
        },
        "pitch_instability_note": (
            f"Pitch tool available at {pitch_note}; optional pitch drift detection can be added before tuning."
            if pitch_available
            else "Pitch instability was not measured because no pitch correction/analysis tool was found."
        ),
    }

    return {
        "label": label,
        "path": str(path),
        "exists": path.exists(),
        "analysis_scope": analysis_scope,
        "metrics": direct_metrics,
        "plosive_candidates": _candidate_windows(
            windows,
            lambda window: window["peak_dbfs"] > -8.0 and window["brightness_ratio"] < 0.35,
            "direct vocal-file candidate: sudden high-energy low-frequency burst; check P/B consonants manually",
        ),
        "sibilance_candidates": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -48.0 and window["brightness_ratio"] > 1.5 and window["zero_crossing_rate"] > 0.12,
            "direct vocal-file candidate: bright high-frequency energy; check S/T/SH consonants",
        ),
        "harshness_candidates": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -28.0 and 0.65 <= window["brightness_ratio"] <= 1.8,
            "direct vocal-file candidate: dense upper-mid energy; sweep 2-5 kHz manually",
        ),
        "low_rumble": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -42.0 and window["brightness_ratio"] < 0.25,
            "direct vocal-file candidate: low rumble/proximity energy; consider high-pass or clip cleanup",
        ),
        "breath_noise_heavy_sections": _candidate_windows(
            windows,
            lambda window: -55.0 < window["rms_dbfs"] < -28.0 and window["brightness_ratio"] > 1.0,
            "direct vocal-file candidate: breath/noise-like low-level bright section; edit or gate carefully",
        ),
    }


def analyze_full_stereo_song(path: Path, label: str = "full_stereo_song") -> dict[str, Any]:
    metadata, channel_samples = read_wav_float(path)
    mono = mono_mix(channel_samples)
    windows = _window_samples(mono, metadata["sample_rate"], seconds=0.5)
    loudness_windows = short_term_loudness_windows(mono, metadata["sample_rate"], window_seconds=1.0, hop_seconds=0.5)
    peak = max((abs(sample) for sample in flatten_channels(channel_samples)), default=0.0)

    return {
        "label": label,
        "path": str(path),
        "exists": path.exists(),
        "analysis_scope": "heuristic_full_stereo_song",
        "stereo_song_metrics": {
            "duration_seconds": metadata["duration_seconds"],
            "sample_rate": metadata["sample_rate"],
            "channels": metadata["channels"],
            "peak_dbfs": linear_to_db(peak),
            "rms_dbfs": rms_db(flatten_channels(channel_samples)),
            "clipping_count": clipping_count(flatten_channels(channel_samples)),
            "dynamic_range": _dynamic_summary(loudness_windows),
            "note": "These are full-mix metrics, not isolated vocal measurements.",
        },
        "likely_vocal_forward_sections": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -30.0 and 0.5 <= window["brightness_ratio"] <= 1.8,
            "heuristic full-stereo candidate: vocal band may be forward here; verify by listening",
        ),
        "likely_vocal_masked_sections": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -24.0 and window["brightness_ratio"] < 0.35,
            "heuristic full-stereo candidate: dense low/mid energy may mask vocal intelligibility",
        ),
        "harsh_vocal_band_candidates": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -30.0 and 0.65 <= window["brightness_ratio"] <= 1.8,
            "heuristic full-stereo candidate: upper-mid vocal band may be harsh, but source is not isolated",
        ),
        "sibilance_like_high_frequency_candidates": _candidate_windows(
            windows,
            lambda window: window["rms_dbfs"] > -45.0 and window["brightness_ratio"] > 1.5 and window["zero_crossing_rate"] > 0.12,
            "heuristic full-stereo candidate: sibilance-like high-frequency energy; could also be hats/noise",
        ),
        "limitations": [
            "No isolated vocal analysis is claimed from this full stereo file.",
            "No real vocal removal or stem-level vocal control is claimed.",
            "All vocal-region labels are heuristic listening targets only.",
        ],
    }


def analyze_vocal_inputs(options: dict[str, Any]) -> dict[str, Any]:
    mode = options.get("mode", "instrumental_beat")
    analysis: dict[str, Any] = {
        "mode": mode,
        "analysis_version": 1,
        "files": {},
        "limitations": [],
    }

    if mode == "full_song_stereo":
        source = options.get("input_path") or options.get("reference_audio") or options.get("beat_file")
        if source and Path(source).expanduser().exists():
            path = Path(source).expanduser()
            try:
                analysis["full_stereo_song"] = analyze_full_stereo_song(path)
                analysis["vocal_to_code"] = analyze_vocal_to_code(path, mode="full_song_stereo")
            except (OSError, ValueError) as error:
                analysis["full_stereo_song"] = {
                    "exists": True,
                    "path": str(path),
                    "analysis_scope": "heuristic_full_stereo_song",
                    "analysis_error": str(error),
                }
        else:
            analysis["full_stereo_song"] = {"exists": False, "path": source, "analysis_scope": "heuristic_full_stereo_song"}
        analysis["limitations"] = [
            "Full stereo mode uses heuristic language only.",
            "The analyzer cannot isolate or directly control embedded vocals from a stereo mix.",
        ]
        return analysis

    if mode in {"vocal_plus_beat", "stems"}:
        direct_inputs = [
            ("lead_vocal", options.get("lead_vocal_file") or options.get("vocal_file")),
            ("adlibs", options.get("adlib_file")),
            ("backing_vocals", options.get("backing_vocal_file")),
        ]
        for label, path_text in direct_inputs:
            if not path_text:
                analysis["files"][label] = {"exists": False, "path": None}
                continue
            path = Path(path_text).expanduser()
            if path.exists():
                try:
                    analysis["files"][label] = analyze_audio_file(path, label, "direct_separate_vocal_file")
                    if label == "lead_vocal":
                        analysis["vocal_to_code"] = analyze_vocal_to_code(path, mode="vocal_plus_beat")
                except (OSError, ValueError) as error:
                    analysis["files"][label] = {
                        "exists": True,
                        "path": str(path),
                        "analysis_scope": "direct_separate_vocal_file",
                        "analysis_error": str(error),
                    }
            else:
                analysis["files"][label] = {"exists": False, "path": str(path), "analysis_scope": "direct_separate_vocal_file"}
        if options.get("vocal_file"):
            analysis["files"]["vocal_file"] = analysis["files"]["lead_vocal"]
        beat_path = options.get("beat_file")
        if beat_path:
            path = Path(beat_path).expanduser()
            analysis["beat_file"] = {"path": str(path), "exists": path.exists()}
        analysis["limitations"] = [
            "Separate vocal processing applies only to the user-provided vocal files.",
            "Beat or instrumental changes are not stem-level unless stems are provided.",
        ]
        return analysis

    analysis["limitations"] = [
        "Instrumental beat mode has no vocal file to analyze.",
        "Any vocal-like texture detection in the beat workflow remains heuristic.",
    ]
    return analysis
