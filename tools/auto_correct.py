#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import AUTO_CORRECT_LOG, QC_JSON_PATH, ensure_harness_dirs, now_iso, read_json
except ImportError:
    from schemas import AUTO_CORRECT_LOG, QC_JSON_PATH, ensure_harness_dirs, now_iso, read_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan safe auto-correction passes from QC.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--max-passes", type=int, default=4)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    qc_path = root / QC_JSON_PATH.relative_to(Path(__file__).resolve().parents[1])
    if not qc_path.exists():
        entries = [{"timestamp": now_iso(), "pass": 0, "status": "BLOCKED", "change": None, "reason": "QC report missing"}]
    else:
        qc = read_json(qc_path)
        if qc.get("status") == "BLOCKED":
            entries = [{"timestamp": now_iso(), "pass": 0, "status": "BLOCKED", "change": None, "reason": qc.get("summary")}]
        else:
            entries = [{"timestamp": now_iso(), "pass": 0, "status": "NO_SAFE_CHANGE_APPLIED", "change": None, "reason": "automatic REAPER correction requires a verified render loop"}]
    AUTO_CORRECT_LOG.parent.mkdir(parents=True, exist_ok=True)
    AUTO_CORRECT_LOG.write_text("".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries), encoding="utf-8")
    print(json.dumps({"entries": entries}, indent=2, sort_keys=True))
    return 0 if entries[0]["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
