#!/usr/bin/env python3
"""Extract abstract mix/master features from approved reference tracks."""

from pathlib import Path

import numpy as np

from audio_utils import (
    analyze_audio_file,
    band_energy,
    environment_report,
    find_audio_files,
    load_audio,
    loudness_metrics,
    mono_signal,
    resolve_path,
    spectral_stats,
    summarize_feature_set,
    write_json,
)


PROFILE_VERSION = "2026-05-27-p1"
SECTION_SECONDS = 15.0
SECTION_HOP_SECONDS = 5.0


def feature_backend(items: list[dict]) -> dict:
    spectral = sorted({item.get("spectral_backend", "unknown") for item in items if "error" not in item})
    loudness = sorted({item.get("loudness_backend", "unknown") for item in items if "error" not in item})
    return {
        "spectral_backend": spectral[0] if len(spectral) == 1 else spectral,
        "loudness_backend": loudness[0] if len(loudness) == 1 else loudness,
    }


def acceptable_ranges(summary: dict) -> dict:
    ranges = {}
    for key, stats in summary.items():
        ranges[key] = {
            "p25": stats.get("p25"),
            "p75": stats.get("p75"),
            "iqr": stats.get("iqr"),
            "acceptable_low": stats.get("acceptable_low"),
            "acceptable_high": stats.get("acceptable_high"),
        }
    return ranges


def analyze_section(audio: np.ndarray, sr: int, start: int, end: int, label: str) -> dict:
    chunk = audio[start:end]
    mono = mono_signal(chunk)
    features = {
        "section_label": label,
        "section_start_sec": float(start / sr),
        "section_duration_sec": float(len(mono) / sr),
        **loudness_metrics(chunk, sr),
        **spectral_stats(mono, sr),
        "low_band_energy_20_120hz": band_energy(mono, sr, 20, 120),
        "low_mid_energy_120_350hz": band_energy(mono, sr, 120, 350),
        "mid_energy_350_1000hz": band_energy(mono, sr, 350, 1000),
        "vocal_presence_energy_1k_4k": band_energy(mono, sr, 1000, 4000),
        "harshness_energy_3k_6k": band_energy(mono, sr, 3000, 6000),
        "sibilance_energy_6k_9k": band_energy(mono, sr, 6000, 9000),
        "air_energy_10k_plus": band_energy(mono, sr, 10000, None),
    }
    return features


def section_summaries_for_file(path: Path) -> dict:
    audio, sr = load_audio(path)
    total = audio.shape[0]
    win = max(1, min(total, int(sr * SECTION_SECONDS)))
    hop = max(1, int(sr * SECTION_HOP_SECONDS))
    starts = list(range(0, max(1, total - win + 1), hop)) or [0]
    if starts[-1] != max(0, total - win):
        starts.append(max(0, total - win))
    sections = []
    for start in starts:
        end = min(total, start + win)
        section = analyze_section(audio, sr, start, end, "candidate")
        sections.append(section)
    loudest = max(sections, key=lambda item: item.get("integrated_lufs", -999))
    quiet = min(sections, key=lambda item: item.get("integrated_lufs", 999))
    vocal_presence = max(sections, key=lambda item: item.get("vocal_presence_energy_1k_4k", -999))
    return {
        "loudest_15s": {**loudest, "section_label": "loudest_15s"},
        "quiet_15s": {**quiet, "section_label": "quiet_15s"},
        "high_vocal_presence_15s": {**vocal_presence, "section_label": "high_vocal_presence_15s"},
    }


def build_reference_features() -> dict:
    input_dir = resolve_path("00_REFERENCES", "approved_tracks")
    raw_out = resolve_path("00_REFERENCES", "reference_profiles", "raw_reference_features.json")
    profile_out = resolve_path("00_REFERENCES", "reference_profiles", "estona_reference_profile.json")
    files = find_audio_files(input_dir)
    raw = {
        "engine": "ESTONA_AUTO_MIX_ENGINE",
        "mode": "reference_feature_extraction",
        "profile_version": PROFILE_VERSION,
        "environment": environment_report(),
        "input_dir": str(input_dir),
        "note": "Only abstract audio statistics are extracted; melody, lyrics, arrangement, and vocal lines are not copied.",
        "files": [],
        "status": "ok" if files else "empty_reference_folder",
    }
    if not files:
        raw["message"] = "No reference audio found. Add WAV/MP3/AIFF/FLAC files later to build an estona reference profile."
        profile = {
            "engine": raw["engine"],
            "profile_version": PROFILE_VERSION,
            "status": "empty_reference_folder",
            "message": raw["message"],
            "feature_summary": {},
            "acceptable_ranges": {},
            "reference_count": 0,
            "reference_is_direction_not_copy": True,
        }
        write_json(raw_out, raw)
        write_json(profile_out, profile)
        return profile
    for path in files:
        try:
            item = analyze_audio_file(path)
            item["section_summaries"] = section_summaries_for_file(path)
            raw["files"].append(item)
        except Exception as exc:
            raw["files"].append({"file": str(path), "error": str(exc)})
    good = [item for item in raw["files"] if "error" not in item]
    summary = summarize_feature_set(good)
    sections_by_name = {}
    for section_name in ("loudest_15s", "quiet_15s", "high_vocal_presence_15s"):
        sections = [item.get("section_summaries", {}).get(section_name) for item in good]
        sections_by_name[section_name] = summarize_feature_set([item for item in sections if item])
    profile = {
        "engine": raw["engine"],
        "profile_version": PROFILE_VERSION,
        "status": "ok" if good else "analysis_failed",
        "reference_count": len(good),
        "source_files": [item["file"] for item in good],
        "feature_backend": feature_backend(good),
        "feature_summary": summary,
        "acceptable_ranges": acceptable_ranges(summary),
        "section_summaries": sections_by_name,
        "reference_is_direction_not_copy": True,
        "forbidden_use": "Do not copy melody, chords, lyrics, topline, arrangement, or unique performance identity.",
    }
    write_json(raw_out, raw)
    write_json(profile_out, profile)
    return profile


if __name__ == "__main__":
    result = build_reference_features()
    print(f"reference profile status: {result.get('status')} ({result.get('reference_count', 0)} files)")
