#!/usr/bin/env python3
"""Analyze current song stems and estimate mix relationship diagnostics."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from audio_utils import analyze_audio_file, band_energy, find_audio_files, load_audio, mono_signal, resolve_path, scalar_feature, write_json


TYPE_KEYWORDS = {
    "lead_vocal": ["lead", "main", "vocal", "vox"],
    "backing_vocal": ["backing", "double", "harmony", "female", "adlib", "bgv"],
    "beat": ["beat", "inst", "instrumental"],
    "drums": ["drum", "drums", "kick", "snare"],
    "bass_808": ["bass", "808", "sub"],
    "melody": ["melody", "sample", "piano", "synth", "lead"],
}


def guess_stem_type(path: Path) -> tuple:
    name = path.stem.lower()
    hits = []
    for stem_type, words in TYPE_KEYWORDS.items():
        if any(word in name for word in words):
            hits.append(stem_type)
    if not hits:
        return "unknown", True
    if "backing_vocal" in hits:
        return "backing_vocal", len(hits) > 1
    if "lead_vocal" in hits:
        return "lead_vocal", len(hits) > 1
    return hits[0], len(hits) > 1


def _first_by_type(stems: List[dict], stem_type: str) -> dict:
    for item in stems:
        if item.get("stem_type") == stem_type and "error" not in item:
            return item
    return {}


def _ratio_db(a: float, b: float) -> float:
    return float(a - b)


def analyze_current_song() -> dict:
    stem_dir = resolve_path("01_CURRENT_SONG", "stems")
    output = resolve_path("02_ANALYSIS", "current_song_analysis.json")
    files = find_audio_files(stem_dir)
    report = {
        "engine": "ESTONA_AUTO_MIX_ENGINE",
        "status": "ok" if files else "empty_stem_folder",
        "input_dir": str(stem_dir),
        "stems": [],
        "relationship_analysis": {},
        "warnings": [],
    }
    if not files:
        report["message"] = "No current song stems found. Dummy tests can still exercise the engine."
        write_json(output, report)
        return report
    for path in files:
        stem_type, uncertain = guess_stem_type(path)
        try:
            features = analyze_audio_file(path)
            features["stem_type"] = stem_type
            features["guessed_stem_type"] = uncertain or stem_type == "unknown"
            if features["guessed_stem_type"]:
                features["user_confirmation_needed"] = "사용자 확인 필요"
            report["stems"].append(features)
        except Exception as exc:
            report["stems"].append({"file": str(path), "stem_type": stem_type, "error": str(exc)})
    lead = _first_by_type(report["stems"], "lead_vocal")
    beat = _first_by_type(report["stems"], "beat")
    backing = [s for s in report["stems"] if s.get("stem_type") == "backing_vocal" and "error" not in s]
    bass = _first_by_type(report["stems"], "bass_808")
    drums = _first_by_type(report["stems"], "drums")
    rel = {}
    if lead and beat:
        rel["vocal_to_beat_loudness_ratio"] = _ratio_db(lead["integrated_lufs"], beat["integrated_lufs"])
        rel["vocal_presence_vs_beat_mid_ratio"] = _ratio_db(
            lead["vocal_presence_energy_1k_4k"], beat["mid_energy_350_1000hz"]
        )
        rel["masking_1k_4k"] = max(0.0, beat["vocal_presence_energy_1k_4k"] - lead["vocal_presence_energy_1k_4k"] + 6.0)
        rel["vocal_body_shortage"] = max(0.0, -18.0 - lead["low_mid_energy_120_350hz"])
        rel["vocal_sibilance_excess"] = max(0.0, lead["sibilance_energy_6k_9k"] + 21.0)
        rel["vocal_harshness_excess"] = max(0.0, lead["harshness_energy_3k_6k"] + 19.0)
        rel["lead_center_stability"] = max(0.0, min(1.0, (lead["stereo_correlation"] + 1.0) / 2.0))
        rel["beat_body_shortage"] = max(0.0, -16.0 - beat["low_mid_energy_120_350hz"])
        rel["beat_harmonic_shortage"] = max(0.0, 2.0 - beat["harmonic_density_proxy"])
    else:
        report["warnings"].append("lead vocal and beat pair not confidently found; vocal/beat relationship requires user confirmation.")
    if bass:
        rel["808_phone_translation_proxy"] = bass["low_mid_energy_120_350hz"] - bass["low_band_energy_20_120hz"]
        rel["kick_808_conflict_proxy"] = max(0.0, bass["low_band_energy_20_120hz"] - (drums or bass)["low_band_energy_20_120hz"] + 3.0)
    if lead and backing:
        lead_lufs = lead["integrated_lufs"]
        backing_loud = max(s["integrated_lufs"] for s in backing)
        rel["backing_time_overlap_ratio"] = estimate_overlap(lead["file"], [s["file"] for s in backing])
        rel["backing_presence_overlap_1k_4k"] = max(s["vocal_presence_energy_1k_4k"] for s in backing) - lead["vocal_presence_energy_1k_4k"]
        rel["backing_sibilance_overlap_6k_9k"] = max(s["sibilance_energy_6k_9k"] for s in backing) - lead["sibilance_energy_6k_9k"]
        rel["backing_center_energy_ratio"] = max(s["stereo_correlation"] for s in backing)
        rel["backing_intrusion_score"] = max(0.0, (backing_loud - lead_lufs + 9.0) / 9.0) + max(
            0.0, rel["backing_presence_overlap_1k_4k"] + 3.0
        ) / 6.0
        rel["lead_vocal_dominance_score"] = max(0.0, 1.0 - rel["backing_intrusion_score"] / 2.0)
    report["relationship_analysis"] = rel
    if any(s.get("guessed_stem_type") for s in report["stems"]):
        report["warnings"].append("Some stem classifications are uncertain: 사용자 확인 필요.")
    write_json(output, report)
    return report


def estimate_overlap(lead_file: str, backing_files: List[str]) -> float:
    try:
        lead_audio, sr = load_audio(Path(lead_file), mono=True, target_sr=8000)
        lead_env = abs(mono_signal(lead_audio))
        lead_active = lead_env > max(0.01, float(lead_env.mean() * 2.0))
        if lead_active.size == 0:
            return 0.0
        overlaps = []
        for name in backing_files:
            b_audio, _ = load_audio(Path(name), mono=True, target_sr=8000)
            b_env = abs(mono_signal(b_audio))
            n = min(lead_active.size, b_env.size)
            b_active = b_env[:n] > max(0.01, float(b_env.mean() * 2.0))
            overlaps.append(float((lead_active[:n] & b_active).sum() / max(1, lead_active[:n].sum())))
        return max(overlaps) if overlaps else 0.0
    except Exception:
        return 0.0


if __name__ == "__main__":
    result = analyze_current_song()
    print(f"current song analysis status: {result.get('status')} ({len(result.get('stems', []))} stems)")
