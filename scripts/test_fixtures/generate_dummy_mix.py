#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import random
import struct
import wave
from pathlib import Path


def write_dummy(path: Path, seconds: float = 2.0, sample_rate: int = 16000) -> None:
    frames = int(seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            t = index / sample_rate
            tone = 0.12 * math.sin(2 * math.pi * 110 * t) + 0.08 * math.sin(2 * math.pi * 330 * t)
            pulse = 0.08 if int(t * 4) % 4 == 0 else 0.0
            noise = random.uniform(-0.015, 0.015)
            left = max(-1.0, min(1.0, tone + pulse + noise))
            right = max(-1.0, min(1.0, tone - pulse + noise))
            handle.writeframes(struct.pack("<hh", int(left * 32767), int(right * 32767)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic dummy mix fixture with sine/noise only.")
    parser.add_argument("--output", default="local_only/test_fixtures/dummy_mix.wav")
    parser.add_argument("--execute", action="store_true", help="Write fixture into ignored local_only folder.")
    args = parser.parse_args()
    if not args.execute:
        print("[dry-run] Would generate synthetic dummy mix WAV in local_only/. Pass --execute to write it locally.")
        return 0
    write_dummy(Path(args.output))
    print(f"[ok] Wrote synthetic dummy fixture to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

