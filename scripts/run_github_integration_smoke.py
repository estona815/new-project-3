#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.github_integration import (
    build_github_integration_smoke,
    write_github_integration_smoke,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GitHub REAPER integration research smoke checks.")
    parser.add_argument("audio", nargs="?", type=Path, help="Optional WAV/audio path for portable diagnostics.")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"), help="Automix output directory.")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    output_dir: Path = args.output_dir
    payload = build_github_integration_smoke(output_dir=output_dir, audio_path=args.audio)
    paths = write_github_integration_smoke(payload, output_dir)
    print(json.dumps({"status": "ok", **paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
