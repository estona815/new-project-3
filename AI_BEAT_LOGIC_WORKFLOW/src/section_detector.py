from __future__ import annotations

from typing import Any


def frame_energy_features(samples: list[float], sample_rate: int, window_seconds: float = 2.0) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    window = max(1, int(sample_rate * window_seconds))
    frames: list[dict[str, Any]] = []
    previous_energy = 0.0
    for start in range(0, len(samples), window):
        end = min(len(samples), start + window)
        chunk = samples[start:end]
        if not chunk:
            continue
        energy = sum(sample * sample for sample in chunk) / len(chunk)
        onset_density = sum(1 for left, right in zip(chunk, chunk[1:]) if abs(right - left) > 0.08) / max(1, len(chunk) - 1)
        novelty = abs(energy - previous_energy)
        previous_energy = energy
        frames.append({"start": start / sample_rate, "end": end / sample_rate, "energy": energy, "onset_density": onset_density, "novelty": novelty})
    return frames


def energy_rank(value: float, max_energy: float) -> int:
    if max_energy <= 0:
        return 1
    ratio = value / max_energy
    if ratio >= 0.8:
        return 5
    if ratio >= 0.55:
        return 4
    if ratio >= 0.32:
        return 3
    if ratio >= 0.12:
        return 2
    return 1


def detect_sections(features: list[dict[str, Any]], duration_seconds: float) -> list[dict[str, Any]]:
    if not features:
        return [{"name": "unknown", "start": 0.0, "end": round(duration_seconds, 3), "energy": 1, "confidence": "low", "reason": "no features available"}] if duration_seconds > 0 else []
    max_energy = max(float(item["energy"]) for item in features) or 1.0
    max_novelty = max(float(item["novelty"]) for item in features) or 1.0
    sections: list[dict[str, Any]] = []
    for index, frame in enumerate(features):
        energy = energy_rank(float(frame["energy"]), max_energy)
        start = float(frame["start"])
        end = float(frame["end"])
        if index == 0 and energy <= 2:
            name = "intro"
        elif end >= duration_seconds - 2.1 and energy <= 2:
            name = "outro"
        elif float(frame["novelty"]) >= max_novelty * 0.75 and energy >= 4:
            name = "drop"
        elif energy >= 4 and float(frame["onset_density"]) >= 0.005:
            name = "hook"
        elif energy <= 2:
            name = "bridge"
        else:
            name = "verse"
        sections.append(
            {
                "name": name,
                "start": round(start, 3),
                "end": round(min(end, duration_seconds), 3),
                "energy": energy,
                "confidence": "medium" if duration_seconds >= 8.0 else "low",
                "reason": "energy/novelty/onset heuristic",
            }
        )
    return _merge_adjacent(sections)


def _merge_adjacent(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for section in sections:
        if merged and merged[-1]["name"] == section["name"]:
            previous = merged[-1]
            previous["end"] = section["end"]
            previous["energy"] = max(int(previous["energy"]), int(section["energy"]))
            previous["reason"] = "merged adjacent " + str(previous["reason"])
        else:
            merged.append(dict(section))
    return merged
