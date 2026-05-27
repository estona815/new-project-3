#!/usr/bin/env python3
"""Generate dummy audio for ESTONA_AUTO_MIX_ENGINE tests."""

from pathlib import Path
import math
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def write_wav(path: Path, freq: float, seconds: float = 2.0, sr: int = 44100, amp: float = 0.2, noise: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(sr * seconds)) / sr
    y = amp * np.sin(2 * math.pi * freq * t)
    if noise:
        rng = np.random.default_rng(42)
        y += noise * rng.standard_normal(y.shape)
    y = np.clip(y, -0.95, 0.95)
    stereo = np.column_stack([y, y * 0.98])
    pcm = (stereo * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        handle.writeframes(pcm.tobytes())


def generate() -> None:
    write_wav(ROOT / "00_REFERENCES" / "approved_tracks" / "dummy_approved_reference.wav", 220, amp=0.22, noise=0.01)
    write_wav(ROOT / "01_CURRENT_SONG" / "stems" / "lead_vocal_dummy.wav", 330, amp=0.18, noise=0.01)
    write_wav(ROOT / "01_CURRENT_SONG" / "stems" / "female_adlib_dummy.wav", 440, amp=0.08, noise=0.01)
    write_wav(ROOT / "01_CURRENT_SONG" / "stems" / "beat_dummy.wav", 110, amp=0.20, noise=0.03)
    write_wav(ROOT / "01_CURRENT_SONG" / "stems" / "808_sub_dummy.wav", 55, amp=0.25)
    write_wav(ROOT / "06_OUTPUTS" / "renders" / "estona_dummy_v29_normal_20260525.wav", 180, amp=0.22, noise=0.02)


if __name__ == "__main__":
    generate()
    print("dummy audio generated")
