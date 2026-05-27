#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Placeholder loudness analyzer. Intended for local trusted machine.")
    parser.add_argument("--input")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    print(json.dumps({"status": "dry_run", "input": args.input, "note": "No audio analyzed by this scaffold."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

