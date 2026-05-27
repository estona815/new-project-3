#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    out = root / "reports" / "plugin_inventory_placeholder.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "status": "placeholder_public_pc_safe",
        "plugins_scanned": False,
        "note": "Real plugin inventory must be generated on the main computer after installation.",
        "expected_core_plugins": [
            "Bertom Denoiser Classic",
            "TDR Nova",
            "Techivation T-De-Esser 2",
            "Voxengo SPAN",
            "Youlean Loudness Meter",
            "LoudMax",
        ],
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] Wrote placeholder inventory: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

