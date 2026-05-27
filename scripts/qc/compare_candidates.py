#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Placeholder candidate comparator.")
    parser.add_argument("candidates", nargs="*")
    args = parser.parse_args()
    print(json.dumps({"status": "dry_run", "candidates": args.candidates, "decision": "manual_listening_required"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

