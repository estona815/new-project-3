#!/usr/bin/env python3
"""Harmonic/body/saturation proxy analysis."""

from audio_utils import clamp, read_json, resolve_path, scalar_feature, write_json


def analyze_saturation() -> dict:
    out = resolve_path("02_ANALYSIS", "saturation_analysis.json")
    current = read_json(resolve_path("02_ANALYSIS", "current_song_analysis.json"), {"stems": []})
    ref = read_json(resolve_path("00_REFERENCES", "reference_profiles", "estona_reference_profile.json"), {"feature_summary": {}})
    stems = [s for s in current.get("stems", []) if "error" not in s]
    if not stems:
        result = {"status": "no_stems", "message": "No stems available for saturation analysis.", "policy_hints": []}
        write_json(out, result)
        return result
    by_type = {s.get("stem_type"): s for s in stems}
    beat = by_type.get("beat", {})
    bass = by_type.get("bass_808", {})
    vocal = by_type.get("lead_vocal", {})
    drums = by_type.get("drums", {})
    ref_hd = scalar_feature(ref.get("feature_summary", {}), "harmonic_density_proxy", 2.0)
    beat_flat = float(beat.get("spectral_flatness", 0.0))
    vocal_flat = float(vocal.get("spectral_flatness", 0.0))
    crest_avg = sum(s.get("crest_factor", 0) for s in stems) / max(1, len(stems))
    transient_max = max(s.get("transient_density_proxy", 0) for s in stems)
    high_energy = max([s.get("air_energy_10k_plus", -120) for s in stems])
    beat_shortage = clamp((ref_hd - float(beat.get("harmonic_density_proxy", 0.0))) / max(ref_hd, 0.5), 0.0, 1.5)
    vocal_shortage = clamp((ref_hd - float(vocal.get("harmonic_density_proxy", 0.0))) / max(ref_hd, 0.5), 0.0, 1.5)
    flatness_penalty = clamp((beat_flat + vocal_flat) * 1.5, 0.0, 1.0)
    crest_penalty = clamp((crest_avg - 5.0) / 8.0, 0.0, 1.0)
    transient_penalty = clamp((8.0 - transient_max) / 8.0, 0.0, 1.0)
    glare_penalty = clamp((high_energy + 30.0) / 16.0, 0.0, 1.0)
    saturation_shortage_score = clamp(
        beat_shortage * 0.35 + vocal_shortage * 0.25 + flatness_penalty * 0.15 + crest_penalty * 0.15 + transient_penalty * 0.10,
        0.0,
        1.0,
    )
    overbright_saturation_risk = clamp(glare_penalty + max(0.0, 1.0 - crest_avg / 4.0) * 0.3, 0.0, 1.0)
    result = {
        "status": "ok",
        "harmonic_density_low": max([s.get("low_band_energy_20_120hz", -120) for s in stems]),
        "harmonic_density_mid": max([s.get("harmonic_density_proxy", 0) for s in stems]),
        "harmonic_density_high": max([s.get("air_energy_10k_plus", -120) for s in stems]),
        "spectral_flatness": sum(s.get("spectral_flatness", 0) for s in stems) / max(1, len(stems)),
        "crest_factor": crest_avg,
        "transient_density": transient_max,
        "perceived_body_proxy": max(s.get("low_mid_energy_120_350hz", -120) for s in stems),
        "808_harmonic_visibility": bass.get("low_mid_energy_120_350hz", -120) - bass.get("low_band_energy_20_120hz", -120) if bass else 0,
        "beat_harmonic_body": beat.get("harmonic_density_proxy", 0),
        "vocal_harmonic_body": vocal.get("harmonic_density_proxy", 0),
        "drum_transient_hardness": drums.get("transient_density_proxy", 0) / max(1.0, drums.get("crest_factor", 1.0)) if drums else 0,
        "reference_harmonic_density_median": ref_hd,
        "saturation_shortage_score": saturation_shortage_score,
        "overbright_saturation_risk": overbright_saturation_risk,
        "scoring_note": "Inspired by open DSP mastering references, but implemented as an original proxy from crest, flatness, high-band energy, transient density, and harmonic density.",
        "policy_hints": [],
    }
    if result["beat_harmonic_body"] < ref_hd * 0.8:
        result["policy_hints"] += ["beat bus saturation", "drum bus soft clip", "instrument bus harmonic excite"]
    if bass and result["808_harmonic_visibility"] < -8:
        result["policy_hints"] += ["808 upper harmonic saturation", "100~250Hz mud 제어"]
    if vocal and result["vocal_harmonic_body"] < ref_hd * 0.7:
        result["policy_hints"] += ["vocal parallel saturation", "200~600Hz body 보강", "3~6kHz harshness 억제"]
    if saturation_shortage_score > 0.55:
        result["policy_hints"] += ["global saturation shortage: prefer parallel/subtle drive over hard clipping"]
    if overbright_saturation_risk > 0.65:
        result["policy_hints"] += ["avoid bright exciter; control 3k-9k before adding air"]
    write_json(out, result)
    return result


if __name__ == "__main__":
    result = analyze_saturation()
    print(f"saturation analysis status: {result.get('status')}")
