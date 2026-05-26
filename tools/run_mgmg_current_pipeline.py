from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
PIPELINE = ROOT / "tools" / "mgmg_v13_vocal_blended_stems_clear.py"
AUDIT_CSV = ROOT / "reports" / "render_audit_v13.csv"

EXPECTED_OUTPUTS = [
    ROOT / "output" / "mgmg_mashup_v13_vocal_blended_stems_clear_balanced_24-48.wav",
    ROOT / "output" / "mgmg_mashup_v13_vocal_blended_stems_clear_loud_24-48.wav",
    ROOT / "output" / "mgmg_mashup_v13_preview_320.mp3",
    ROOT / "reports" / "final_balance_audit.md",
    ROOT / "reports" / "final_processing_settings.json",
]


def ensure_inputs() -> None:
    required = [
        Path("/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems.zip"),
        Path("/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems (1).zip"),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing required stem zip(s):\n" + "\n".join(missing))


def run_pipeline() -> None:
    subprocess.run([sys.executable, str(PIPELINE)], cwd=ROOT, check=True)


def print_audit_summary() -> None:
    if not AUDIT_CSV.exists():
        print(f"Audit CSV not found: {AUDIT_CSV}")
        return
    with AUDIT_CSV.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            label = row.get("label", "")
            lufs = row.get("integrated_lufs", "")
            tp = row.get("true_peak_dbfs", "")
            lra = row.get("lra_lu", "")
            print(f"{label}: {lufs} LUFS / {tp} dBTP / LRA {lra}")


def main() -> None:
    ensure_inputs()
    run_pipeline()
    print("\nGenerated:")
    for path in EXPECTED_OUTPUTS:
        status = "ok" if path.exists() else "missing"
        print(f"- [{status}] {path}")
    print("\nMetrics:")
    print_audit_summary()


if __name__ == "__main__":
    main()
