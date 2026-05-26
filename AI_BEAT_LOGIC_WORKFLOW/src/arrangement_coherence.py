from __future__ import annotations

from typing import Any

import numpy as np

from ai_artifact_detector import detect_repeated_ai_loops
from section_detector import detect_sections, frame_energy_features
from transition_detector import dead_outro_candidates, detect_abrupt_transitions, weak_intro_candidates


def _score_1_to_5(value: float) -> int:
    return max(1, min(5, int(round(1.0 + 4.0 * max(0.0, min(1.0, value))))))


def _energy_contrast(features: list[dict[str, Any]]) -> float:
    if not features:
        return 0.0
    energies = [float(item.get("energy", 0.0)) for item in features]
    high = max(energies)
    low = min(energies)
    if high <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, (high - low) / high))


def _section_variety(sections: list[dict[str, Any]]) -> float:
    if not sections:
        return 0.0
    labels = [str(section.get("name", "unknown")) for section in sections]
    return max(0.0, min(1.0, len(set(labels)) / 4.0))


def _long_static_ratio(features: list[dict[str, Any]]) -> float:
    if len(features) < 2:
        return 1.0 if features else 0.0
    energies = np.asarray([float(item.get("energy", 0.0)) for item in features], dtype=np.float32)
    high = float(np.max(energies)) + 1e-12
    static = 0
    for left, right in zip(energies, energies[1:]):
        if abs(float(right - left)) / high < 0.025:
            static += 1
    return static / max(1, len(features) - 1)


def _variation_score(features: list[dict[str, Any]]) -> float:
    if len(features) < 4:
        return 0.2 if features else 0.0
    novelty = [float(item.get("novelty", 0.0)) for item in features]
    high = max(novelty) + 1e-12
    meaningful_changes = sum(1 for value in novelty if value / high > 0.22)
    change_ratio = meaningful_changes / len(features)
    static_penalty = _long_static_ratio(features)
    return max(0.0, min(1.0, change_ratio * 2.6 - static_penalty * 0.45))


def analyze_arrangement_coherence(mono_samples: list[float] | np.ndarray, sample_rate: int) -> dict[str, Any]:
    samples = np.asarray(mono_samples, dtype=np.float32)
    duration = float(samples.size / sample_rate) if sample_rate > 0 else 0.0
    features = frame_energy_features(samples.tolist(), sample_rate)
    sections = detect_sections(features, duration)
    repeated_loops = detect_repeated_ai_loops(features)
    abrupt = detect_abrupt_transitions(features)
    weak_intro = weak_intro_candidates(features)
    dead_outro = dead_outro_candidates(features, duration)

    contrast = _energy_contrast(features)
    variety = _section_variety(sections)
    section_clarity = _score_1_to_5(0.52 * contrast + 0.48 * variety)
    energy_curve = _score_1_to_5(contrast)
    intro_strength = 2 if weak_intro else 4 if contrast > 0.18 else 2
    transition_intentionality = _score_1_to_5(max(0.0, 1.0 - len(abrupt) * 0.12 - len(repeated_loops) * 0.04))
    variation = _score_1_to_5(_variation_score(features))

    score = round((section_clarity + energy_curve + intro_strength + transition_intentionality + variation) / 5.0, 2)
    diagnosis = "arrangement_rebuild_required" if score <= 2.4 else "needs_editing" if score < 3.5 else "coherent"
    return {
        "section_clarity": section_clarity,
        "energy_curve": energy_curve,
        "intro_strength": intro_strength,
        "transition_intentionality": transition_intentionality,
        "variation_every_4_8_bars": variation,
        "score": score,
        "diagnosis": diagnosis,
        "sections": sections,
        "repeated_ai_loop_candidates": repeated_loops,
        "abrupt_transition_candidates": abrupt,
        "weak_intro_candidates": weak_intro,
        "dead_outro_candidates": dead_outro,
        "energy_contrast": round(contrast, 4),
        "static_region_ratio": round(_long_static_ratio(features), 4),
    }
