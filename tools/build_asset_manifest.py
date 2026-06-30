#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import ASSET_MANIFEST_PATH, discover_assets, ensure_harness_dirs, write_asset_report, write_json
except ImportError:
    from schemas import ASSET_MANIFEST_PATH, discover_assets, ensure_harness_dirs, write_asset_report, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover source stems and references.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    manifest = discover_assets(root)
    write_json(root / ASSET_MANIFEST_PATH.relative_to(Path(__file__).resolve().parents[1]), manifest)
    write_asset_report(manifest, root)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
