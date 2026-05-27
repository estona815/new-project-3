#!/usr/bin/env python3
"""Smoke test feature extraction and analyzers."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str) -> None:
    subprocess.run([sys.executable, script], cwd=str(ROOT), check=True)


if __name__ == "__main__":
    run("08_TESTS/test_audio_generation.py")
    run("02_ANALYSIS/reference_feature_extractor.py")
    run("02_ANALYSIS/current_song_analyzer.py")
    run("02_ANALYSIS/vocal_beat_masking_analyzer.py")
    run("02_ANALYSIS/vocal_pitch_analyzer.py")
    run("02_ANALYSIS/saturation_analyzer.py")
    run("02_ANALYSIS/stereo_phase_analyzer.py")
    assert (ROOT / "00_REFERENCES/reference_profiles/estona_reference_profile.json").exists()
    assert (ROOT / "02_ANALYSIS/current_song_analysis.json").exists()
    reference_features = json.loads((ROOT / "00_REFERENCES/reference_profiles/raw_reference_features.json").read_text(encoding="utf-8"))
    current_features = json.loads((ROOT / "02_ANALYSIS/current_song_analysis.json").read_text(encoding="utf-8"))
    feature_items = reference_features.get("tracks", []) + current_features.get("stems", [])
    assert feature_items, "expected generated test audio features"
    for item in feature_items:
        assert item.get("spectral_backend") in {"librosa", "numpy_fft"}, item
        assert item.get("loudness_backend") in {"pyloudnorm_bs1770", "rms_proxy"}, item
    print("feature extraction smoke test passed")
