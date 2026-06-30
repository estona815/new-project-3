#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SLUG = "mesi_1_v35_louder_safe_peak_master"

RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG

FINAL_WAV = RENDERS / "mesi_1_v35_LOUDER_SAFE_PEAK_MASTER_24-48.wav"
FINAL_MP3 = RENDERS / "mesi_1_v35_LOUDER_SAFE_PEAK_MASTER_320k.mp3"
ZIP_PATH = RENDERS / "mesi_1_v35_FINAL_DELIVERABLE.zip"
TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"
QC_JSON = REPORTS / "v35_final_qc.json"
DECISIONS_JSON = REPORTS / "processing_decisions.json"
RPP = REAPER_DIR / "mesi_1_v35_LOUDER_SAFE_PEAK_MASTER.rpp"
GATE_SCRIPT = ROOT / "tools" / "validate_reaper_vocal_chain_gate.py"
INTEGRATED_REPORT = ROOT / "reports" / "MESI_1_INTEGRATED_REPORT.md"
SINGLE_PIPELINE = ROOT / "MESI_1_SINGLE_PIPELINE.md"

EXPECTED_ZIP = {
    "renders/mesi_1_v35_louder_safe_peak_master/mesi_1_v35_LOUDER_SAFE_PEAK_MASTER_24-48.wav",
    "renders/mesi_1_v35_louder_safe_peak_master/mesi_1_v35_LOUDER_SAFE_PEAK_MASTER_320k.mp3",
    "reports/mesi_1_v35_louder_safe_peak_master/actual_reaper_plugin_trace.json",
    "reports/mesi_1_v35_louder_safe_peak_master/v35_final_qc.json",
    "reports/mesi_1_v35_louder_safe_peak_master/processing_decisions.json",
    "reports/mesi_1_v35_louder_safe_peak_master/mesi_1_v35_louder_safe_peak_master_report.md",
    "reports/MESI_1_INTEGRATED_REPORT.md",
    "MESI_1_SINGLE_PIPELINE.md",
    "reaper/mesi_1_v35_louder_safe_peak_master/mesi_1_v35_LOUDER_SAFE_PEAK_MASTER.rpp",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
    if path.stat().st_size <= 0:
        fail(f"empty file: {path.relative_to(ROOT)}")


def load_qc() -> dict:
    require_file(QC_JSON)
    return json.loads(QC_JSON.read_text(encoding="utf-8"))


def check_qc(qc: dict) -> None:
    final_mp3 = qc.get("final_mp3", {})
    final_wav = qc.get("final_wav", {})
    if final_mp3.get("integrated_lufs", -99) < -10.2:
        fail(f"final MP3 too quiet for locked v35 target: {final_mp3}")
    if final_mp3.get("true_peak_dbfs", 99) > -0.8:
        fail(f"final MP3 true peak is not safe enough: {final_mp3}")
    if final_wav.get("true_peak_dbfs", 99) > -0.8:
        fail(f"final WAV true peak is not safe enough: {final_wav}")


def check_zip() -> None:
    require_file(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = set(archive.namelist())
    missing = sorted(EXPECTED_ZIP - names)
    if missing:
        fail("ZIP missing expected entries: " + ", ".join(missing))
    unexpected = sorted(names - EXPECTED_ZIP)
    if unexpected:
        fail("ZIP contains intermediate/unexpected entries: " + ", ".join(unexpected))


def run_vocal_gate() -> None:
    require_file(GATE_SCRIPT)
    require_file(TRACE_JSON)
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--trace", str(TRACE_JSON.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        fail("vocal chain gate failed")


def main() -> None:
    for path in (FINAL_WAV, FINAL_MP3, ZIP_PATH, TRACE_JSON, QC_JSON, DECISIONS_JSON, RPP, INTEGRATED_REPORT, SINGLE_PIPELINE):
        require_file(path)
    check_qc(load_qc())
    check_zip()
    run_vocal_gate()
    print(json.dumps({"slug": SLUG, "passed": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
