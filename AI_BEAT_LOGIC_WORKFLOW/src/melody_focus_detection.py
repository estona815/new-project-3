from __future__ import annotations

from statistics import mean


def band_proxy_energy(samples: list[float], mode: str) -> float:
    if len(samples) < 2:
        return 0.0
    if mode == "low":
        smoothed = []
        acc = 0.0
        alpha = 0.015
        for sample in samples:
            acc = (1.0 - alpha) * acc + alpha * sample
            smoothed.append(acc)
        return mean(value * value for value in smoothed)
    if mode == "transient":
        diffs = [b - a for a, b in zip(samples, samples[1:])]
        return mean(diff * diff for diff in diffs)
    # Mid/high melodic proxy: signal not explained by slow low component or sharp transient proxy.
    low = band_proxy_energy(samples, "low")
    full = mean(sample * sample for sample in samples)
    transient = band_proxy_energy(samples, "transient")
    return max(0.0, full - low - transient * 0.15)


def detect_low_end_excess_and_melody_burial(mono_samples: list[float], sample_rate: int, window_seconds: float = 2.0) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if sample_rate <= 0 or not mono_samples:
        return [], []
    window_size = max(1, int(window_seconds * sample_rate))
    low_end_flags: list[dict[str, object]] = []
    melody_buried: list[dict[str, object]] = []
    for start in range(0, len(mono_samples), window_size):
        end = min(len(mono_samples), start + window_size)
        chunk = mono_samples[start:end]
        if len(chunk) < sample_rate * 0.25:
            continue
        low_energy = band_proxy_energy(chunk, "low")
        melody_energy = band_proxy_energy(chunk, "melody")
        transient_energy = band_proxy_energy(chunk, "transient")
        ratio = low_energy / (melody_energy + 1e-9)
        drum_ratio = transient_energy / (melody_energy + 1e-9)
        if ratio > 2.5:
            low_end_flags.append(
                {
                    "start": start / sample_rate,
                    "end": end / sample_rate,
                    "confidence": "medium",
                    "reason": "20-120Hz proxy energy appears dominant over mid/melody proxy (heuristic)",
                }
            )
        if ratio > 1.6 and drum_ratio > 0.8:
            melody_buried.append(
                {
                    "start": start / sample_rate,
                    "end": end / sample_rate,
                    "confidence": "medium",
                    "reason": "low-end and transient proxy dominate while melodic mid/high proxy is reduced (heuristic)",
                }
            )
    return low_end_flags[:16], melody_buried[:16]

