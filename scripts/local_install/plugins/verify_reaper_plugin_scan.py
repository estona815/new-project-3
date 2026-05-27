#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run REAPER plugin scan verifier. Does not launch REAPER.")
    parser.add_argument("--inventory", default="reports/plugin_inventory.json")
    args = parser.parse_args()
    path = Path(args.inventory)
    status = "missing_inventory"
    if path.exists():
        status = "inventory_present"
    print(json.dumps({"status": status, "note": "No REAPER plugin scan performed by this script."}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

