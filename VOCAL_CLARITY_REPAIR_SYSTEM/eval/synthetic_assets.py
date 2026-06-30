from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .audio_metrics import AudioBuffer, write_wav


def _time(sr: int, duration: float) -> np.ndarray:
    return np.arange(int(sr * duration), dtype=np.float64) / sr


def _stereo(x: np.ndarray) -> np.ndarray:
    return np.column_stack([x, x]).astype(np.float32)


def _sine(sr: int, duration: float, freq: float, amp: float = 0.25) -> np.ndarray:
    t = _time(sr, duration)
    return amp * np.sin(2.0 * np.pi * freq * t)


def harmonic_stack(sr: int, duration: float, base: float = 180.0) -> np.ndarray:
    t = _time(sr, duration)
    y = np.zeros_like(t)
    for idx, amp in enumerate((0.22, 0.16, 0.12, 0.08, 0.05, 0.035, 0.025), start=1):
        y += amp * np.sin(2.0 * np.pi * base * idx * t)
    return y


def impulse_train(sr: int, duration: float) -> np.ndarray:
    y = np.zeros(int(sr * duration), dtype=np.float64)
    for pos in np.arange(0.10, duration, 0.17):
        idx = int(pos * sr)
        y[idx : idx + 3] = [0.75, -0.35, 0.12]
    return y


def noise_burst(sr: int, duration: float, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y = np.zeros(int(sr * duration), dtype=np.float64)
    start = int(sr * 0.20)
    stop = int(sr * 0.55)
    y[start:stop] = rng.normal(0.0, 0.12, stop - start)
    return y


def stereo_side_noise(sr: int, duration: float, seed: int = 11) -> np.ndarray:
    t = _time(sr, duration)
    mid = 0.20 * np.sin(2.0 * np.pi * 440.0 * t)
    rng = np.random.default_rng(seed)
    side = rng.normal(0.0, 0.05, len(t))
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def hiss_plus_harmonic(sr: int, duration: float, seed: int = 17) -> np.ndarray:
    rng = np.random.default_rng(seed)
    source = harmonic_stack(sr, duration, 210.0)
    hiss = rng.normal(0.0, 0.025, len(source))
    shaped_hiss = hiss - np.convolve(hiss, np.ones(64) / 64, mode="same")
    return source + shaped_hiss


def consonant_vocal_proxy(sr: int, duration: float, seed: int = 23) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y = harmonic_stack(sr, duration, 190.0) * 0.75
    for pos in (0.16, 0.34, 0.52):
        start = int(pos * sr)
        stop = min(start + int(0.035 * sr), len(y))
        burst = rng.normal(0.0, 0.08, stop - start)
        burst -= np.convolve(burst, np.ones(32) / 32, mode="same")
        y[start:stop] += burst
    return y


def acoustic_guitar_proxy(sr: int, duration: float) -> np.ndarray:
    t = _time(sr, duration)
    y = np.zeros_like(t)
    for idx, pos in enumerate((0.08, 0.22, 0.38, 0.57)):
        start = int(pos * sr)
        local_t = t[: len(t) - start]
        decay = np.exp(-local_t * (10.0 + idx))
        pluck = (
            0.18 * np.sin(2 * np.pi * (220 + 35 * idx) * local_t)
            + 0.08 * np.sin(2 * np.pi * (660 + 70 * idx) * local_t)
            + 0.04 * np.sin(2 * np.pi * (2400 + 120 * idx) * local_t)
        ) * decay
        y[start:] += pluck
    return y


def ai_metallic_vocal_proxy(sr: int, duration: float) -> np.ndarray:
    t = _time(sr, duration)
    y = harmonic_stack(sr, duration, 205.0) * 0.70
    chirps = (
        0.030 * np.sin(2 * np.pi * (4200 + 800 * np.sin(2 * np.pi * 7 * t)) * t)
        + 0.020 * np.sin(2 * np.pi * (7600 + 1200 * np.sin(2 * np.pi * 5 * t)) * t)
    )
    gate = (np.sin(2 * np.pi * 13 * t) > 0.35).astype(np.float64)
    return y + chirps * gate


def watery_source_proxy(sr: int, duration: float) -> np.ndarray:
    t = _time(sr, duration)
    source = harmonic_stack(sr, duration, 185.0) * 0.70
    flutter = 0.015 * np.sin(2 * np.pi * 11 * t) * np.sin(2 * np.pi * 3100 * t)
    comb = source + 0.18 * np.roll(source, int(sr * 0.004))
    return 0.85 * comb + flutter


def room_tone_vocal_proxy(sr: int, duration: float, seed: int = 29) -> np.ndarray:
    rng = np.random.default_rng(seed)
    room = rng.normal(0.0, 0.018, int(sr * duration))
    room = np.convolve(room, np.ones(192) / 192, mode="same")
    return harmonic_stack(sr, duration, 200.0) * 0.72 + room


def full_mix_center_vocal_proxy(sr: int, duration: float, seed: int = 31) -> np.ndarray:
    t = _time(sr, duration)
    vocal = harmonic_stack(sr, duration, 205.0) * 0.45
    pad_l = 0.08 * np.sin(2 * np.pi * 330 * t) + 0.06 * np.sin(2 * np.pi * 990 * t)
    pad_r = 0.08 * np.sin(2 * np.pi * 335 * t) + 0.06 * np.sin(2 * np.pi * 1005 * t)
    rng = np.random.default_rng(seed)
    side_hiss = rng.normal(0.0, 0.012, len(t))
    return np.column_stack([vocal + pad_l + side_hiss, vocal + pad_r - side_hiss]).astype(np.float32)


def generate_synthetic_suite(root: Path, sample_rate: int = 48000) -> dict[str, Any]:
    input_dir = root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []

    def add(
        case_id: str,
        signal: np.ndarray,
        *,
        category: str,
        source_type: str,
        expected_behavior: str,
        contains_transients: bool = False,
        contains_stereo_ambience: bool = False,
        has_noise: bool = False,
        has_ai_artifact: bool = False,
        contains_vocal: bool | None = None,
        notes: str = "",
    ) -> None:
        samples = signal[:, None] if signal.ndim == 1 else signal
        path = input_dir / f"{case_id}.wav"
        write_wav(path, AudioBuffer(sample_rate, samples.astype(np.float32)))
        cases.append(
            {
                "id": case_id,
                "path": str(path.relative_to(root)),
                "category": category,
                "source_type": source_type,
                "contains_vocal": source_type == "vocal" if contains_vocal is None else contains_vocal,
                "contains_transients": contains_transients,
                "contains_stereo_ambience": contains_stereo_ambience,
                "has_noise": has_noise,
                "has_ai_artifact": has_ai_artifact,
                "expected_behavior": expected_behavior,
                "protected_bands": ["2k_8k", "8k_16k"],
                "notes": notes,
            }
        )

    duration = 0.75
    add("synthetic_silence", np.zeros(int(sample_rate * duration)), category="edge_silence", source_type="synthetic", expected_behavior="silence", notes="silence should remain silence")
    for freq in (100, 1000, 3000, 6000, 12000):
        add(
            f"synthetic_sine_{freq}hz",
            _sine(sample_rate, duration, float(freq)),
            category="clean_sine",
            source_type="instrument",
            expected_behavior="do_no_harm",
            notes=f"clean {freq} Hz sine preservation",
        )
    add("synthetic_clean_vocal", harmonic_stack(sample_rate, duration, 205.0), category="clean_vocal", source_type="vocal", expected_behavior="do_no_harm", notes="clean vocal-like harmonic stack")
    add("synthetic_harmonic_stack", harmonic_stack(sample_rate, duration), category="clean_harmonic", source_type="vocal", expected_behavior="do_no_harm", notes="vocal-like harmonic stack")
    add("synthetic_clean_consonant_vocal", consonant_vocal_proxy(sample_rate, duration), category="clean_consonant_vocal", source_type="vocal", expected_behavior="do_no_harm", has_noise=False, notes="vocal-like harmonic source with consonant bursts")
    add("synthetic_acoustic_guitar_pick", acoustic_guitar_proxy(sample_rate, duration), category="clean_acoustic_guitar", source_type="instrument", expected_behavior="do_no_harm", contains_transients=True, notes="plucked harmonic transient preservation")
    add("synthetic_impulse_train", impulse_train(sample_rate, duration), category="clean_transient", source_type="drum", expected_behavior="do_no_harm", contains_transients=True, notes="impulse/transient preservation")
    add("synthetic_clean_drum_transient", impulse_train(sample_rate, duration) * 0.75 + noise_burst(sample_rate, duration, seed=19) * 0.15, category="clean_drum_transient", source_type="drum", expected_behavior="do_no_harm", contains_transients=True, notes="drum-like transient preservation")
    add("synthetic_noise_burst", noise_burst(sample_rate, duration), category="noise_burst", source_type="noise", expected_behavior="moderate_cleanup", has_noise=True, notes="noise burst finite-output check")
    add("synthetic_stereo_side_noise", stereo_side_noise(sample_rate, duration), category="stereo_side_noise", source_type="music", expected_behavior="preserve_mid_width", contains_stereo_ambience=True, has_noise=True, notes="side noise and width check")
    add("synthetic_hiss_plus_harmonic", hiss_plus_harmonic(sample_rate, duration), category="hiss_plus_harmonic", source_type="vocal", expected_behavior="moderate_cleanup", has_noise=True, notes="hiss plus protected harmonic source")
    add("synthetic_vocal_with_hiss", hiss_plus_harmonic(sample_rate, duration, seed=37), category="vocal_with_hiss", source_type="vocal", expected_behavior="moderate_cleanup", has_noise=True, notes="vocal-like source with broadband hiss")
    add("synthetic_room_tone_vocal", room_tone_vocal_proxy(sample_rate, duration), category="room_tone_vocal", source_type="vocal", expected_behavior="moderate_cleanup", has_noise=True, notes="vocal-like source with low-level room tone")
    add("synthetic_ai_metallic_vocal", ai_metallic_vocal_proxy(sample_rate, duration), category="ai_metallic_vocal", source_type="vocal", expected_behavior="artifact_reduction_preserve_source", has_noise=True, has_ai_artifact=True, notes="vocal-like source with metallic chirp artifacts")
    add("synthetic_watery_source_vocal", watery_source_proxy(sample_rate, duration), category="watery_source_separated_vocal", source_type="vocal", expected_behavior="artifact_reduction_preserve_source", has_ai_artifact=True, notes="source-separated watery texture proxy")
    add("synthetic_stereo_ambience", stereo_side_noise(sample_rate, duration, seed=41), category="stereo_ambience", source_type="music", expected_behavior="preserve_mid_width", contains_stereo_ambience=True, has_noise=True, notes="stereo ambience preservation proxy")
    add("synthetic_full_mix_center_vocal", full_mix_center_vocal_proxy(sample_rate, duration), category="full_mix_center_vocal", source_type="music", expected_behavior="preserve_mid_width", contains_vocal=True, contains_stereo_ambience=True, has_noise=True, notes="full mix proxy with centered vocal")

    manifest = {
        "schema": "codex-vocal-ab-eval-manifest-v1",
        "description": "Synthetic CI-safe assets for preservation-first evaluation.",
        "items": cases,
    }
    (root / "manifest.synthetic.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
