#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import discover_assets, ensure_harness_dirs, now_iso, write_json
except ImportError:
    from schemas import discover_assets, ensure_harness_dirs, now_iso, write_json


INSTRUMENT_ROLES = {"FX", "SYNTH", "KEYBOARD", "GUITAR", "BASS", "DRUMS"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a processed residual rescue asset when safe.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", default="work/assets/male_hook_residual_rescue.wav")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    manifest = discover_assets(root)
    references = manifest["references"]
    instrument_stems = [asset for asset in manifest["stems"] if asset["classification"] in INSTRUMENT_ROLES]
    report = {
        "timestamp": now_iso(),
        "status": "BLOCKED",
        "output": args.output,
        "reason": None,
        "inputs": {
            "reference_count": len(references),
            "instrument_stem_count": len(instrument_stems),
        },
        "policy": "raw full mix may only be used as source; active routing of raw full mix is forbidden",
    }
    if not references:
        report["reason"] = "No full mix reference found under input/reference/"
    elif not instrument_stems:
        report["reason"] = "No confidently classified instrument stems found for subtraction"
    else:
        report["reason"] = "Residual extraction requires runtime DSP dependencies and manual confidence review before use"
        report["status"] = "UNVERIFIED"
    write_json(root / "work" / "assets" / "residual_rescue_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
