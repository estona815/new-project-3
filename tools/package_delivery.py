#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import ensure_harness_dirs, package_delivery
except ImportError:
    from schemas import ensure_harness_dirs, package_delivery


def main() -> int:
    parser = argparse.ArgumentParser(description="Create delivery ZIP only when required files exist.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    manifest = package_delivery(root)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
