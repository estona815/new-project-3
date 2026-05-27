#!/usr/bin/env python3
"""Extract abstract mix/master features from approved reference tracks."""

from pathlib import Path

from audio_utils import analyze_audio_file, environment_report, find_audio_files, resolve_path, summarize_feature_set, write_json


def build_reference_features() -> dict:
    input_dir = resolve_path("00_REFERENCES", "approved_tracks")
    raw_out = resolve_path("00_REFERENCES", "reference_profiles", "raw_reference_features.json")
    profile_out = resolve_path("00_REFERENCES", "reference_profiles", "estona_reference_profile.json")
    files = find_audio_files(input_dir)
    raw = {
        "engine": "ESTONA_AUTO_MIX_ENGINE",
        "mode": "reference_feature_extraction",
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
            "status": "empty_reference_folder",
            "message": raw["message"],
            "feature_summary": {},
            "reference_count": 0,
            "reference_is_direction_not_copy": True,
        }
        write_json(raw_out, raw)
        write_json(profile_out, profile)
        return profile
    for path in files:
        try:
            raw["files"].append(analyze_audio_file(path))
        except Exception as exc:
            raw["files"].append({"file": str(path), "error": str(exc)})
    good = [item for item in raw["files"] if "error" not in item]
    profile = {
        "engine": raw["engine"],
        "status": "ok" if good else "analysis_failed",
        "reference_count": len(good),
        "source_files": [item["file"] for item in good],
        "feature_summary": summarize_feature_set(good),
        "reference_is_direction_not_copy": True,
        "forbidden_use": "Do not copy melody, chords, lyrics, topline, arrangement, or unique performance identity.",
    }
    write_json(raw_out, raw)
    write_json(profile_out, profile)
    return profile


if __name__ == "__main__":
    result = build_reference_features()
    print(f"reference profile status: {result.get('status')} ({result.get('reference_count', 0)} files)")
