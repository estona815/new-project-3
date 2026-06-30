#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import detect_environment, ensure_harness_dirs, write_json
except ImportError:
    from schemas import detect_environment, ensure_harness_dirs, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect local REAPER, Python, and encoder availability.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", default="work/logs/environment.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    payload = detect_environment(root)
    output = root / args.output
    write_json(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
