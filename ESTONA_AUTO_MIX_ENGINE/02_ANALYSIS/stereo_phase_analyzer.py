#!/usr/bin/env python3
"""Stereo and phase safety report for current stems."""

from audio_utils import read_json, resolve_path, write_json


def analyze_stereo_phase() -> dict:
    current = read_json(resolve_path("02_ANALYSIS", "current_song_analysis.json"), {"stems": []})
    stems = []
    for item in current.get("stems", []):
        if "error" in item:
            continue
        stems.append({
            "file": item.get("file"),
            "stem_type": item.get("stem_type"),
            "stereo_correlation": item.get("stereo_correlation"),
            "mid_side_ratio": item.get("mid_side_ratio"),
            "side_low_energy_below_120hz": item.get("side_low_energy_below_120hz"),
            "low_end_mono_warning": item.get("side_low_energy_below_120hz", -120) > -24,
        })
    result = {"status": "ok" if stems else "no_stems", "stems": stems}
    write_json(resolve_path("02_ANALYSIS", "stereo_phase_analysis.json"), result)
    return result


if __name__ == "__main__":
    print(f"stereo/phase status: {analyze_stereo_phase().get('status')}")
