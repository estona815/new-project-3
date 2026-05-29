from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
REAPER_EFFECTS = Path.home() / "Library" / "Application Support" / "REAPER" / "Effects" / "codex_fresh_mix"
REPORT = ROOT / "reports" / "codex_tune_eq_substitute_install.json"

JSFX = [
    ROOT / "reaper" / "jsfx" / "codex_dynamic_eq_band.jsfx",
    ROOT / "reaper" / "jsfx" / "codex_noise_floor_tamer.jsfx",
    ROOT / "reaper" / "jsfx" / "codex_pro_dynamic_ms_eq.jsfx",
    ROOT / "reaper" / "jsfx" / "codex_v20_channel_polish.jsfx",
    ROOT / "reaper" / "jsfx" / "codex_vocal_pitch_monitor.jsfx",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    REAPER_EFFECTS.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    max_status = "PASS"
    for src in JSFX:
        row = {"source": str(src), "target": str(REAPER_EFFECTS / src.name)}
        if not src.exists():
            row.update({"severity": "FAIL", "status": "missing_source"})
            max_status = "FAIL"
        else:
            dst = REAPER_EFFECTS / src.name
            shutil.copy2(src, dst)
            row.update(
                {
                    "severity": "PASS",
                    "status": "installed",
                    "sha256": sha256(dst),
                    "bytes": dst.stat().st_size,
                }
            )
        rows.append(row)

    payload = {
        "schema_version": 1,
        "max_status": max_status,
        "reaper_effects_dir": str(REAPER_EFFECTS),
        "rows": rows,
        "note": "Restart REAPER or rescan JSFX if the new plugins do not appear immediately.",
    }
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if max_status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
