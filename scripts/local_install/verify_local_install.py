#!/usr/bin/env python3
from __future__ import annotations

import shutil

TOOLS = ["ffmpeg", "ffprobe", "reaper"]
PYTHON_MODULES = ["numpy", "scipy", "soundfile", "librosa", "pyloudnorm"]


def main() -> int:
    print("Local install verification. No installation will be performed.")
    for tool in TOOLS:
        print(f"{tool}: {shutil.which(tool) or 'missing'}")
    for module in PYTHON_MODULES:
        try:
            __import__(module)
            print(f"python:{module}: ok")
        except Exception:
            print(f"python:{module}: missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

