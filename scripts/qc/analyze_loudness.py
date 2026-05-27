#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Loudness analyzer scaffold. Degrades gracefully without optional packages.")
    parser.add_argument("--input")
    parser.add_argument("--execute", action="store_true", help="Analyze a local dummy/trusted file.")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "dry_run", "input": args.input, "note": "No audio analyzed without --execute."}, indent=2))
        return 0
    if not args.input or not Path(args.input).exists():
        print(json.dumps({"status": "missing_input", "input": args.input}, indent=2))
        return 0
    try:
        import pyloudnorm  # type: ignore  # noqa: F401
        import soundfile  # type: ignore  # noqa: F401
    except Exception:
        print(json.dumps({"status": "dependency_missing", "input": args.input, "note": "Install soundfile and pyloudnorm on the main computer for real analysis."}, indent=2))
        return 0
    print(json.dumps({"status": "placeholder_ready", "input": args.input, "note": "Real loudness implementation should run only on trusted local files."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
