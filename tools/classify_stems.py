#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import classify_stem, discover_assets, ensure_harness_dirs, write_json
except ImportError:
    from schemas import classify_stem, discover_assets, ensure_harness_dirs, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservatively classify stems by filename.")
    parser.add_argument("paths", nargs="*", help="Optional paths to classify directly.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    if args.paths:
        payload = [{"path": path, "classification": classify_stem(Path(path).name)} for path in args.paths]
    else:
        manifest = discover_assets(root)
        payload = manifest["stems"]
    output = root / "work" / "assets" / "stem_classification.json"
    write_json(output, {"items": payload})
    print(json.dumps({"items": payload}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
