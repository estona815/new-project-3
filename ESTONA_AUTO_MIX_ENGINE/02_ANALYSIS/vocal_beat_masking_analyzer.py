#!/usr/bin/env python3
"""Estimate vocal/beat fit, masking, and glue policy hints."""

from audio_utils import read_json, resolve_path, write_json


def hint_list(metrics: dict) -> list:
    hints = []
    if metrics.get("vocal_forwardness_score", 0) > 0.65:
        hints += ["lead vocal gain down", "vocal 3k dynamic cut", "beat harmonic density up"]
    if metrics.get("vocal_thin_ai_score", 0) > 0.55:
        hints += ["vocal body saturation", "low-mid support", "harshness cut 병행"]
    if metrics.get("beat_mid_support_350_2000hz", 0) < -20:
        hints += ["beat bus saturation", "drum clip", "808 upper harmonic 보강"]
    if metrics.get("vocal_beat_glue_score", 1) < 0.45:
        hints += ["vocal/beat bus glue", "short room/reverb send", "parallel saturation"]
    return sorted(set(hints))


def analyze_masking() -> dict:
    src = resolve_path("02_ANALYSIS", "current_song_analysis.json")
    out = resolve_path("02_ANALYSIS", "vocal_beat_masking_analysis.json")
    data = read_json(src, {"stems": [], "relationship_analysis": {}})
    lead = next((s for s in data.get("stems", []) if s.get("stem_type") == "lead_vocal" and "error" not in s), {})
    beat = next((s for s in data.get("stems", []) if s.get("stem_type") == "beat" and "error" not in s), {})
    rel = data.get("relationship_analysis", {})
    if not lead or not beat:
        result = {
            "status": "insufficient_stems",
            "message": "Need at least lead vocal and beat stems for vocal/beat masking analysis.",
            "policy_hints": [],
        }
        write_json(out, result)
        return result
    ratio = rel.get("vocal_to_beat_loudness_ratio", lead["integrated_lufs"] - beat["integrated_lufs"])
    metrics = {
        "status": "ok",
        "vocal_to_beat_ratio": ratio,
        "vocal_body_150_350hz": lead["low_mid_energy_120_350hz"],
        "vocal_presence_1k_4k": lead["vocal_presence_energy_1k_4k"],
        "vocal_harsh_3k_6k": lead["harshness_energy_3k_6k"],
        "vocal_sibilance_6k_9k": lead["sibilance_energy_6k_9k"],
        "beat_mid_support_350_2000hz": beat["mid_energy_350_1000hz"],
        "beat_presence_conflict_1k_4k": max(0.0, beat["vocal_presence_energy_1k_4k"] - lead["vocal_presence_energy_1k_4k"] + 6.0),
    }
    metrics["vocal_forwardness_score"] = max(0.0, min(1.0, (ratio - 1.0) / 5.0))
    metrics["vocal_buried_score"] = max(0.0, min(1.0, (-ratio - 2.0) / 6.0 + metrics["beat_presence_conflict_1k_4k"] / 12.0))
    metrics["vocal_thin_ai_score"] = max(0.0, min(1.0, (-18.0 - metrics["vocal_body_150_350hz"]) / 12.0 + max(0, metrics["vocal_harsh_3k_6k"] + 18) / 12.0))
    metrics["vocal_beat_glue_score"] = max(0.0, min(1.0, 1.0 - abs(ratio - 1.5) / 8.0 - metrics["beat_presence_conflict_1k_4k"] / 20.0))
    metrics["policy_hints"] = hint_list(metrics)
    write_json(out, metrics)
    return metrics


if __name__ == "__main__":
    result = analyze_masking()
    print(f"vocal/beat masking status: {result.get('status')}")
