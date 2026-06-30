#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import wave
from pathlib import Path
from typing import Callable


SAMPLE_RATE = 48000
DURATION_SECONDS = 10.0
SEED = 41041

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "tests" / "automix_validation" / "fixtures" / "audio"
MANIFEST_PATH = ROOT / "tests" / "automix_validation" / "fixtures" / "audio_fixture_manifest.json"


FrameFn = Callable[[float, int], list[float]]


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def envelope(t: float, duration: float = DURATION_SECONDS) -> float:
    attack = min(1.0, t / 0.08)
    release = min(1.0, max(0.0, (duration - t) / 0.18))
    phrase = 0.68 + 0.32 * (0.5 + 0.5 * math.sin(2.0 * math.pi * 0.45 * t))
    return attack * release * phrase


def semitone_snap(freq: float) -> float:
    midi = round(69.0 + 12.0 * math.log2(freq / 440.0))
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def write_wav24(path: Path, frame_fn: FrameFn, *, channels: int, duration: float = DURATION_SECONDS) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(SAMPLE_RATE * duration)
    peak = 0.0
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(3)
        wf.setframerate(SAMPLE_RATE)
        raw = bytearray()
        for n in range(total_frames):
            t = n / SAMPLE_RATE
            values = frame_fn(t, n)
            if len(values) < channels:
                values = values + [values[-1] if values else 0.0] * (channels - len(values))
            for value in values[:channels]:
                sample = int(round(clamp(value) * 8388607.0))
                peak = max(peak, abs(value))
                raw.extend(sample.to_bytes(3, "little", signed=True))
        wf.writeframes(bytes(raw))
    return {
        "path": str(path),
        "sample_rate": SAMPLE_RATE,
        "channels": channels,
        "duration_seconds": duration,
        "format": "PCM_24",
        "peak": round(min(1.0, peak), 6),
    }


def pseudo_noise(n: int, seed: int = SEED) -> float:
    return math.sin((n + seed) * 12.9898) * 43758.5453 % 1.0 * 2.0 - 1.0


def vocal_stack(t: float, *, snapped: bool = False, vibrato_depth: float = 20.0, thin: bool = False, simple: bool = False) -> float:
    if simple:
        vibrato_phase = (vibrato_depth / 40.0) * math.sin(2.0 * math.pi * 5.3 * t)
        return 0.58 * math.sin(2.0 * math.pi * 220.0 * t + vibrato_phase) * envelope(t)
    note_index = int(t / 1.25) % 6
    notes = [196.0, 220.0, 246.94, 261.63, 293.66, 246.94]
    base = notes[note_index]
    if snapped:
        freq = semitone_snap(base)
    else:
        freq = base * (2.0 ** ((vibrato_depth * math.sin(2.0 * math.pi * 5.3 * t)) / 1200.0))
    phase = 2.0 * math.pi * freq * t
    body = 0.34 * math.sin(phase) + 0.08 * math.sin(2.0 * phase) + 0.035 * math.sin(3.0 * phase)
    formant = 0.025 * math.sin(2.0 * math.pi * 900.0 * t) + 0.018 * math.sin(2.0 * math.pi * 2400.0 * t)
    if thin:
        body *= 0.45
        formant += 0.08 * math.sin(2.0 * math.pi * 5200.0 * t)
    return (body + formant) * envelope(t)


def noise_burst(t: float, n: int, rate_hz: float, width: int, amp: float, rng: random.Random | None = None) -> float:
    period = max(1, int(SAMPLE_RATE / rate_hz))
    pos = n % period
    if pos >= width:
        return 0.0
    noise = rng.random() * 2.0 - 1.0 if rng else pseudo_noise(n)
    return amp * (1.0 - pos / width) * noise


def raw_vocal_like_mono(t: float, n: int) -> list[float]:
    return [0.86 * vocal_stack(t, vibrato_depth=24.0, simple=True)]


def already_tuned_ai_like_vocal(t: float, n: int) -> list[float]:
    notes = [220.0, 246.94, 261.63, 293.66]
    note_index = int(t / 0.5) % len(notes)
    local_t = t - int(t / 0.5) * 0.5
    quantized = 0.54 * math.sin(2.0 * math.pi * notes[note_index] * local_t) * envelope(t)
    metallic = 0.045 * math.sin(2.0 * math.pi * 7600.0 * t) + 0.025 * math.sin(2.0 * math.pi * 10400.0 * t)
    wobble = 0.035 * math.sin(2.0 * math.pi * 12.0 * t) * math.sin(2.0 * math.pi * 1800.0 * t)
    tail = 0.02 * math.sin(2.0 * math.pi * notes[note_index] * max(0.0, local_t - 0.08)) if local_t > 0.08 else 0.0
    return [quantized + metallic + wobble + tail]


def source_separated_watery_vocal(t: float, n: int) -> list[float]:
    center = 0.55 * vocal_stack(t, vibrato_depth=13.0)
    comb = 0.10 * math.sin(2.0 * math.pi * (700.0 + 160.0 * math.sin(2.0 * math.pi * 0.7 * t)) * t)
    phase = 0.16 * math.sin(2.0 * math.pi * 0.9 * t)
    bleed = 0.08 * math.sin(2.0 * math.pi * 330.0 * t) + 0.05 * math.sin(2.0 * math.pi * 440.0 * t)
    return [center + comb + bleed + phase, center - comb + bleed - phase]


def full_mix_dense_polyphonic(t: float, n: int) -> list[float]:
    kick_pos = n % int(SAMPLE_RATE * 0.5)
    snare_pos = (n + int(SAMPLE_RATE * 0.25)) % int(SAMPLE_RATE * 0.5)
    hat_pos = n % int(SAMPLE_RATE * 0.125)
    kick = 0.72 * math.exp(-kick_pos / 520.0) * math.sin(2.0 * math.pi * 58.0 * t) if kick_pos < 2200 else 0.0
    snare = 0.58 * math.exp(-snare_pos / 280.0) * pseudo_noise(n, SEED + 7) if snare_pos < 1400 else 0.0
    hat = 0.34 * math.exp(-hat_pos / 95.0) * pseudo_noise(n, SEED + 13) if hat_pos < 650 else 0.0
    bass = 0.26 * math.sin(2.0 * math.pi * 52.0 * t) + 0.18 * math.sin(2.0 * math.pi * 120.0 * t)
    chords_l = 0.22 * math.sin(2.0 * math.pi * 220.0 * t) + 0.18 * math.sin(2.0 * math.pi * 300.0 * t) + 0.14 * math.sin(2.0 * math.pi * 500.0 * t)
    chords_r = -0.20 * math.sin(2.0 * math.pi * 246.94 * t) + 0.18 * math.sin(2.0 * math.pi * 1200.0 * t) - 0.13 * math.sin(2.0 * math.pi * 2500.0 * t)
    vocal = 0.16 * vocal_stack(t, vibrato_depth=8.0)
    side_air = 0.10 * math.sin(2.0 * math.pi * 6000.0 * t) + 0.07 * math.sin(2.0 * math.pi * 9000.0 * t)
    return [kick + snare + hat + bass + chords_l + vocal + side_air, 0.45 * kick + 0.8 * snare - hat + 0.8 * bass + chords_r + vocal - side_air]


def fragile_thin_ai_vocal(t: float, n: int) -> list[float]:
    fizz = 0.055 * math.sin(2.0 * math.pi * 9300.0 * t) + 0.035 * math.sin(2.0 * math.pi * 11600.0 * t)
    narrow = 0.10 * math.sin(2.0 * math.pi * 3600.0 * t)
    compressed = math.tanh(1.6 * (vocal_stack(t, vibrato_depth=12.0, thin=True) + narrow + fizz))
    return [0.55 * compressed]


def harsh_sibilant_vocal(t: float, n: int) -> list[float]:
    rng = random.Random(SEED + n)
    sib = noise_burst(t, n, 3.1, 1500, 0.28, rng)
    harsh = 0.13 * math.sin(2.0 * math.pi * 4200.0 * t) * (0.5 + 0.5 * math.sin(2.0 * math.pi * 2.0 * t))
    return [0.62 * vocal_stack(t, vibrato_depth=15.0) + sib + harsh]


def clean_instrumental_bus(t: float, n: int) -> list[float]:
    kick_pos = n % int(SAMPLE_RATE * 0.5)
    kick = 0.62 * math.exp(-kick_pos / 850.0) * math.sin(2.0 * math.pi * 54.0 * t) if kick_pos < 2600 else 0.0
    hat = noise_burst(t, n, 8.0, 300, 0.06)
    bass = 0.28 * math.sin(2.0 * math.pi * 60.0 * t)
    chord_l = 0.18 * math.sin(2.0 * math.pi * 185.0 * t) + 0.12 * math.sin(2.0 * math.pi * 277.0 * t)
    chord_r = 0.18 * math.sin(2.0 * math.pi * 207.65 * t) + 0.12 * math.sin(2.0 * math.pi * 311.0 * t)
    lead = 0.12 * math.sin(2.0 * math.pi * (660.0 + 30.0 * math.sin(2.0 * math.pi * 0.8 * t)) * t)
    return [kick + bass + chord_l + lead + hat, 0.7 * kick + bass + chord_r - lead + hat]


def vocal_buried_mix(t: float, n: int) -> list[float]:
    inst_l, inst_r = clean_instrumental_bus(t, n)
    mask_l = 0.20 * math.sin(2.0 * math.pi * 1800.0 * t) + 0.15 * math.sin(2.0 * math.pi * 3100.0 * t)
    mask_r = 0.18 * math.sin(2.0 * math.pi * 2100.0 * t) + 0.14 * math.sin(2.0 * math.pi * 3600.0 * t)
    vocal = 0.16 * vocal_stack(t, vibrato_depth=18.0)
    return [0.65 * inst_l + mask_l + vocal, 0.65 * inst_r + mask_r + vocal]


def clean_vocal_fixture(t: float, n: int) -> list[float]:
    return [0.54 * vocal_stack(t, vibrato_depth=18.0)]


def muddy_vocal_fixture(t: float, n: int) -> list[float]:
    env = envelope(t)
    vocal = 0.42 * vocal_stack(t, vibrato_depth=16.0)
    low_mid = env * (0.26 * math.sin(2.0 * math.pi * 190.0 * t) + 0.20 * math.sin(2.0 * math.pi * 285.0 * t))
    box = env * 0.13 * math.sin(2.0 * math.pi * 420.0 * t)
    dull_air = 0.02 * math.sin(2.0 * math.pi * 1800.0 * t)
    return [math.tanh(1.15 * (vocal + low_mid + box + dull_air))]


def fake_stereo_halo_vocal(t: float, n: int) -> list[float]:
    center = 0.42 * vocal_stack(t, vibrato_depth=12.0)
    shimmer = 0.10 * math.sin(2.0 * math.pi * (4200.0 + 180.0 * math.sin(2.0 * math.pi * 0.6 * t)) * t)
    micro_delay = 0.05 * math.sin(2.0 * math.pi * 0.75 * t)
    halo = shimmer + micro_delay + 0.025 * pseudo_noise(n, SEED + 31)
    return [center + halo, center - 0.92 * halo]


def over_limited_master(t: float, n: int) -> list[float]:
    left, right = full_mix_dense_polyphonic(t, n)
    return [0.96 * math.tanh(2.85 * left), 0.96 * math.tanh(2.85 * right)]


def low_end_buildup_mix(t: float, n: int) -> list[float]:
    left, right = clean_instrumental_bus(t, n)
    sub = 0.48 * math.sin(2.0 * math.pi * 36.0 * t) + 0.32 * math.sin(2.0 * math.pi * 58.0 * t)
    bloom = 0.22 * math.sin(2.0 * math.pi * 92.0 * t) * (0.65 + 0.35 * math.sin(2.0 * math.pi * 0.5 * t))
    return [left + sub + bloom, right + sub + bloom]


def phase_issue_stereo(t: float, n: int) -> list[float]:
    center = 0.46 * vocal_stack(t, vibrato_depth=14.0)
    side = 0.12 * math.sin(2.0 * math.pi * 1300.0 * t) + 0.08 * math.sin(2.0 * math.pi * 3700.0 * t)
    return [center + side, -0.82 * center + 0.35 * side]


FIXTURES: list[tuple[str, int, FrameFn, dict]] = [
    ("raw_vocal_like_mono.wav", 1, raw_vocal_like_mono, {"expected": "raw_vocal; low full_mix_likelihood; high pitch confidence", "coverage_tags": ["clean_vocal", "raw_vocal"]}),
    ("already_tuned_ai_like_vocal.wav", 1, already_tuned_ai_like_vocal, {"expected": "already_tuned_score high; pitch skipped or micro", "coverage_tags": ["already_tuned_ai_vocal", "suno_high_fizz"]}),
    ("source_separated_watery_vocal.wav", 2, source_separated_watery_vocal, {"expected": "source separated/watery risk high; conservative recovery", "coverage_tags": ["watery_smear", "fake_stereo_halo"]}),
    ("full_mix_dense_polyphonic.wav", 2, full_mix_dense_polyphonic, {"expected": "full_mix_likelihood high; pitch blocked", "coverage_tags": ["full_mix", "dense_polyphonic"]}),
    ("fragile_thin_ai_vocal.wav", 1, fragile_thin_ai_vocal, {"expected": "thin/fizz risk; body preservation", "coverage_tags": ["suno_high_fizz", "fragile_ai_vocal"]}),
    ("harsh_sibilant_vocal.wav", 1, harsh_sibilant_vocal, {"expected": "sibilance and harshness guard", "coverage_tags": ["harsh_vocal", "sibilant_vocal"]}),
    ("clean_instrumental_bus.wav", 2, clean_instrumental_bus, {"expected": "instrumental role; pitch ineligible", "coverage_tags": ["clean_instrumental_bus"]}),
    ("vocal_buried_mix.wav", 2, vocal_buried_mix, {"expected": "vocal masking; dynamic space preferred", "coverage_tags": ["buried_vocal", "masking_balance"]}),
    ("clean_vocal_fixture.wav", 1, clean_vocal_fixture, {"expected": "clean vocal baseline for conservative comparison", "coverage_tags": ["clean_vocal"]}),
    ("muddy_vocal_fixture.wav", 1, muddy_vocal_fixture, {"expected": "muddy/boxy low-mid vocal cleanup target", "coverage_tags": ["muddy_vocal"]}),
    ("fake_stereo_halo_vocal.wav", 2, fake_stereo_halo_vocal, {"expected": "fake stereo halo should trigger phase-aware conservative treatment", "coverage_tags": ["fake_stereo_halo", "phase_issue"]}),
    ("over_limited_master.wav", 2, over_limited_master, {"expected": "over-limited master should block aggressive final limiting claims", "coverage_tags": ["over_limited_master"]}),
    ("low_end_buildup_mix.wav", 2, low_end_buildup_mix, {"expected": "low-end buildup should favor conservative cleanup over heavy mastering", "coverage_tags": ["low_end_buildup"]}),
    ("phase_issue_stereo.wav", 2, phase_issue_stereo, {"expected": "phase issue should require mono compatibility and human review", "coverage_tags": ["phase_issue"]}),
]


def generate() -> dict:
    random.seed(SEED)
    generated = []
    for filename, channels, fn, meta in FIXTURES:
        info = write_wav24(FIXTURE_DIR / filename, fn, channels=channels)
        info["path"] = str(Path("audio") / filename)
        info.update(meta)
        generated.append(info)
    manifest = {
        "schema": "prompt41-audio-fixture-manifest-v1",
        "seed": SEED,
        "copyrighted_material": False,
        "external_downloads": False,
        "sample_rate": SAMPLE_RATE,
        "duration_seconds": DURATION_SECONDS,
        "fixtures": generated,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    manifest = generate()
    print(json.dumps({"generated": len(manifest["fixtures"]), "manifest": str(MANIFEST_PATH)}, indent=2))
