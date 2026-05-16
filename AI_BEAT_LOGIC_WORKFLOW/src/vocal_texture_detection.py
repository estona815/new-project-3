from __future__ import annotations

from statistics import mean


def zero_crossing_rate(samples: list[float]) -> float:
    if len(samples) < 2:
        return 0.0
    crossings = sum(1 for left, right in zip(samples, samples[1:]) if (left >= 0) != (right >= 0))
    return crossings / (len(samples) - 1)


def detect_vocal_like_textures(channel_samples: list[list[float]], sample_rate: int, window_seconds: float = 2.0) -> list[dict[str, object]]:
    # Heuristic only. This is not real vocal detection and should be interpreted as candidate regions.
    if sample_rate <= 0 or not channel_samples or not channel_samples[0]:
        return []
    channels = len(channel_samples)
    mono = [sum(channel[index] for channel in channel_samples) / channels for index in range(len(channel_samples[0]))]
    window_size = max(1, int(window_seconds * sample_rate))
    candidates: list[dict[str, object]] = []
    for start in range(0, len(mono), window_size):
        end = min(len(mono), start + window_size)
        chunk = mono[start:end]
        if len(chunk) < sample_rate * 0.25:
            continue
        zcr = zero_crossing_rate(chunk)
        avg_abs = mean(abs(sample) for sample in chunk)
        modulation = mean(abs(b - a) for a, b in zip(chunk, chunk[1:])) if len(chunk) > 1 else 0.0
        center_ratio = 1.0
        if channels == 2:
            side = [0.5 * (channel_samples[0][i] - channel_samples[1][i]) for i in range(start, end)]
            mid = [0.5 * (channel_samples[0][i] + channel_samples[1][i]) for i in range(start, end)]
            side_energy = mean(abs(sample) for sample in side) + 1e-9
            mid_energy = mean(abs(sample) for sample in mid) + 1e-9
            center_ratio = mid_energy / side_energy
        score = 0
        reasons: list[str] = []
        if 0.025 <= zcr <= 0.22 and avg_abs > 0.015:
            score += 1
            reasons.append("heuristic high-mid/formant-like activity range")
        if modulation > 0.006:
            score += 1
            reasons.append("modulated texture pattern")
        if center_ratio > 1.8:
            score += 1
            reasons.append("mono-centered texture")
        if score >= 2:
            confidence = "medium" if score == 2 else "high"
            candidates.append(
                {
                    "start": start / sample_rate,
                    "end": end / sample_rate,
                    "confidence": confidence,
                    "reason": "; ".join(reasons) + " (heuristic only, not model-based vocal detection)",
                }
            )
    return candidates[:16]

