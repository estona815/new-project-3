from __future__ import annotations

from statistics import mean


def windowed_features(mono_samples: list[float], sample_rate: int, window_seconds: float = 1.0) -> list[dict[str, float]]:
    if sample_rate <= 0 or not mono_samples:
        return []
    window_size = max(1, int(window_seconds * sample_rate))
    features: list[dict[str, float]] = []
    previous_energy = 0.0
    for start in range(0, len(mono_samples), window_size):
        end = min(len(mono_samples), start + window_size)
        chunk = mono_samples[start:end]
        if not chunk:
            continue
        energy = sum(sample * sample for sample in chunk) / len(chunk)
        onset_density = 0.0
        if len(chunk) > 1:
            onset_density = sum(1 for a, b in zip(chunk, chunk[1:]) if abs(b - a) > 0.08) / len(chunk)
        novelty = abs(energy - previous_energy)
        previous_energy = energy
        features.append(
            {
                "start": start / sample_rate,
                "end": end / sample_rate,
                "energy": energy,
                "onset_density": onset_density,
                "novelty": novelty,
            }
        )
    return features


def detect_silence_regions(mono_samples: list[float], sample_rate: int, threshold: float = 0.001, min_seconds: float = 0.5) -> dict[str, object]:
    if sample_rate <= 0 or not mono_samples:
        return {"intro_silence": None, "outro_silence": None, "internal_silence_candidates": []}
    min_frames = max(1, int(min_seconds * sample_rate))
    regions: list[dict[str, float]] = []
    start: int | None = None
    for index, sample in enumerate(mono_samples):
        if abs(sample) < threshold:
            if start is None:
                start = index
        elif start is not None:
            if index - start >= min_frames:
                regions.append({"start": start / sample_rate, "end": index / sample_rate})
            start = None
    if start is not None and len(mono_samples) - start >= min_frames:
        regions.append({"start": start / sample_rate, "end": len(mono_samples) / sample_rate})

    duration = len(mono_samples) / sample_rate
    intro = next((region for region in regions if region["start"] <= 0.02), None)
    outro = next((region for region in reversed(regions) if region["end"] >= duration - 0.02), None)
    internal = [region for region in regions if region is not intro and region is not outro]
    return {"intro_silence": intro, "outro_silence": outro, "internal_silence_candidates": internal}


def detect_arrangement_candidates(features: list[dict[str, float]], duration: float) -> dict[str, object]:
    if not features:
        return {
            "intro": None,
            "first_hook_or_main_motif_entrance": None,
            "drop": None,
            "repeated_loop_blocks": [],
            "outro": None,
            "ai_random_transition_or_glitch_candidates": [],
            "main_melody_strongest_region": None,
        }

    energies = [feature["energy"] for feature in features]
    avg_energy = mean(energies)
    high_energy = max(energies)
    intro_end = 0.0
    for feature in features:
        if feature["energy"] < avg_energy * 0.35:
            intro_end = feature["end"]
        else:
            break

    hook = max(features, key=lambda item: item["energy"] + item["onset_density"])
    drop = max(features, key=lambda item: item["novelty"])
    outro_start = None
    for feature in reversed(features):
        if feature["energy"] < avg_energy * 0.35:
            outro_start = feature["start"]
        else:
            break

    repeated: list[dict[str, float | str]] = []
    for left, right in zip(features, features[1:]):
        if high_energy > 0 and abs(left["energy"] - right["energy"]) / high_energy < 0.04:
            repeated.append({"start": left["start"], "end": right["end"], "reason": "similar adjacent loudness/energy windows"})

    glitches: list[dict[str, float | str]] = []
    novelty_threshold = max(feature["novelty"] for feature in features) * 0.75
    for feature in features:
        if feature["novelty"] >= novelty_threshold and feature["start"] > 0.0:
            glitches.append({"start": feature["start"], "end": feature["end"], "reason": "abrupt heuristic spectral/loudness novelty change"})

    return {
        "intro": {"start": 0.0, "end": intro_end} if intro_end > 0 else {"start": 0.0, "end": min(duration, features[0]["end"])},
        "first_hook_or_main_motif_entrance": {"start": hook["start"], "end": hook["end"], "confidence": "medium"},
        "drop": {"start": drop["start"], "end": drop["end"], "confidence": "medium"},
        "repeated_loop_blocks": repeated[:12],
        "outro": {"start": outro_start, "end": duration} if outro_start is not None else None,
        "ai_random_transition_or_glitch_candidates": glitches[:12],
        "main_melody_strongest_region": {"start": hook["start"], "end": hook["end"], "reason": "highest combined energy and onset density heuristic"},
    }

