#!/usr/bin/env python3
"""Analyze current song stems and estimate mix relationship diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from audio_utils import analyze_audio_file, find_audio_files, frame_rms, load_audio, mono_signal, resolve_path, write_json


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
    matched_keywords = {}
    for stem_type, words in TYPE_KEYWORDS.items():
        matched = [word for word in words if word in name]
        if matched:
            hits.append(stem_type)
            matched_keywords[stem_type] = matched
    if not hits:
        return "unknown", True, 0.0, {}
    if "backing_vocal" in hits:
        confidence = 0.68 if len(hits) > 1 else 0.9
        return "backing_vocal", len(hits) > 1, confidence, matched_keywords
    if "lead_vocal" in hits:
        confidence = 0.68 if len(hits) > 1 else 0.88
        return "lead_vocal", len(hits) > 1, confidence, matched_keywords
    confidence = 0.62 if len(hits) > 1 else 0.86
    return hits[0], len(hits) > 1, confidence, matched_keywords


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
        "unknown_stems_requiring_user_confirmation": [],
        "warnings": [],
    }
    if not files:
        report["message"] = "No current song stems found. Dummy tests can still exercise the engine."
        write_json(output, report)
        return report
    for path in files:
        stem_type, uncertain, confidence, matched_keywords = guess_stem_type(path)
        try:
            features = analyze_audio_file(path)
            features["stem_type"] = stem_type
            features["stem_classification_confidence"] = confidence
            features["stem_classification_matches"] = matched_keywords
            features["guessed_stem_type"] = uncertain or stem_type == "unknown"
            if features["guessed_stem_type"]:
                features["user_confirmation_needed"] = "사용자 확인 필요"
                report["unknown_stems_requiring_user_confirmation"].append(
                    {
                        "file": str(path),
                        "suggested_stem_type": stem_type,
                        "confidence": confidence,
                        "reason": "ambiguous filename match" if stem_type != "unknown" else "no stem keyword match",
                    }
                )
            report["stems"].append(features)
        except Exception as exc:
            report["stems"].append(
                {
                    "file": str(path),
                    "stem_type": stem_type,
                    "stem_classification_confidence": confidence,
                    "error": str(exc),
                }
            )
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
    if bass and drums:
        rel["kick_808_low_envelope_correlation"] = low_envelope_correlation(drums["file"], bass["file"])
        rel["kick_808_conflict_score"] = max(
            rel.get("kick_808_conflict_proxy", 0.0),
            rel["kick_808_low_envelope_correlation"] * 4.0,
        )
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


def low_envelope_correlation(kick_or_drums_file: str, bass_file: str) -> float:
    try:
        drum_audio, sr = load_audio(Path(kick_or_drums_file), mono=True, target_sr=8000)
        bass_audio, _ = load_audio(Path(bass_file), mono=True, target_sr=8000)
        drum_env = frame_rms(mono_signal(drum_audio), sr, 0.08, 0.02)
        bass_env = frame_rms(mono_signal(bass_audio), sr, 0.08, 0.02)
        n = min(drum_env.size, bass_env.size)
        if n < 3:
            return 0.0
        a = drum_env[:n]
        b = bass_env[:n]
        if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
            return 0.0
        return float(max(0.0, np.corrcoef(a, b)[0, 1]))
    except Exception:
        return 0.0


if __name__ == "__main__":
    result = analyze_current_song()
    print(f"current song analysis status: {result.get('status')} ({len(result.get('stems', []))} stems)")
