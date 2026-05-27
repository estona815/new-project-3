#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import random
import struct
import wave
from pathlib import Path


def write_dummy(path: Path, seconds: float = 1.5, sample_rate: int = 16000) -> None:
    frames = int(seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            t = index / sample_rate
            synthetic_vowel = 0.18 * math.sin(2 * math.pi * 220 * t) + 0.06 * math.sin(2 * math.pi * 440 * t)
            hiss = random.uniform(-0.025, 0.025)
            sample = max(-1.0, min(1.0, synthetic_vowel + hiss))
            handle.writeframes(struct.pack("<h", int(sample * 32767)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic dummy vocal-noise fixture. Never use real music.")
    parser.add_argument("--output", default="local_only/test_fixtures/dummy_vocal_noise.wav")
    parser.add_argument("--execute", action="store_true", help="Write fixture into ignored local_only folder.")
    args = parser.parse_args()
    if not args.execute:
        print("[dry-run] Would generate synthetic dummy vocal-noise WAV in local_only/. Pass --execute to write it locally.")
        return 0
    write_dummy(Path(args.output))
    print(f"[ok] Wrote synthetic dummy fixture to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

