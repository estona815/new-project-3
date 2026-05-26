#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
AUTOMIX = ROOT / "tools/0101_raw_clip_safe_automix.py"
SOURCE_QC = ROOT / "reports/0101_raw_clip_safe_v01/raw_clip_safe_qc.json"
SOURCE_REPORT = ROOT / "reports/0101_raw_clip_safe_v01/raw_clip_safe_report.md"
SOURCE_WAV = ROOT / "renders/0101_raw_clip_safe_v01/0101_RAW_CLIP_SAFE_v01.wav"

OUT_DIR = ROOT / "renders/current_pipeline_one_song"
REPORT_DIR = ROOT / "reports/current_pipeline_one_song"
FINAL_WAV = OUT_DIR / "0101_CURRENT_PIPELINE_CLIP_SAFE.wav"
FINAL_M4A = OUT_DIR / "0101_CURRENT_PIPELINE_CLIP_SAFE.m4a"
FINAL_REPORT = REPORT_DIR / "current_pipeline_one_song_report.md"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    n = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{stamp}_{n}{path.suffix}")
        n += 1
    return candidate


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    steps: list[str] = []

    code, log = run(["python3", str(AUTOMIX)])
    steps.append(f"- Raw stem analysis + clip-safe automix: {'ok' if code == 0 else 'failed'}")
    if log.strip():
        steps.append("  - Automix log: `" + log.strip().replace("`", "'")[:700] + "`")
    if code != 0:
        raise SystemExit(code)

    final_wav = unique_path(FINAL_WAV)
    shutil.copy2(SOURCE_WAV, final_wav)
    steps.append(f"- Final WAV copied: `{final_wav}`")

    final_m4a = None
    afconvert = shutil.which("afconvert")
    if afconvert:
        candidate_m4a = unique_path(FINAL_M4A)
        code, enc_log = run([afconvert, "-f", "m4af", "-d", "aac", "-b", "320000", str(final_wav), str(candidate_m4a)])
        if code == 0 and candidate_m4a.exists():
            final_m4a = candidate_m4a
            steps.append(f"- AAC preview/export created: `{final_m4a}`")
        else:
            steps.append("- AAC preview/export failed; WAV is still valid final output.")
            if enc_log.strip():
                steps.append("  - afconvert log: `" + enc_log.strip().replace("`", "'")[:500] + "`")
    else:
        steps.append("- AAC preview/export skipped: `afconvert` not found.")

    qc = {}
    if SOURCE_QC.exists():
        qc = json.loads(SOURCE_QC.read_text(encoding="utf-8"))
    metrics = qc.get("final_metrics", {})

    report = [
        "# Current Pipeline One Song Report",
        "",
        f"- Date/time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- Pipeline: source stem analysis -> raw clip-safe automix -> QC -> final WAV copy -> optional AAC export",
        f"- Final WAV: `{final_wav}`",
        f"- Final AAC/M4A: `{final_m4a}`" if final_m4a else "- Final AAC/M4A: not created",
        f"- Source QC report: `{SOURCE_REPORT}`",
        "",
        "## QC Snapshot",
        "",
        f"- True peak 4x: {metrics.get('true_peak_dbfs_4x', 'n/a')} dBFS",
        f"- Approx integrated loudness: {metrics.get('lufs_i_approx_no_gate', 'n/a')} LUFS",
        f"- Sample peak: {metrics.get('peak_dbfs', 'n/a')} dBFS",
        f"- Clipped samples >= 0.999: {metrics.get('clipped_samples_ge_0_999', 'n/a')}",
        f"- Duration: {metrics.get('duration_sec', 'n/a')} sec",
        "",
        "## Steps",
        "",
        *steps,
        "",
        "## Notes",
        "",
        "- Original raw stems were not overwritten.",
        "- Composite/reference files were analyzed but not mixed to avoid double-counting.",
        "- This version prioritizes no crackle/no clipping over loudness.",
        "- Human A/B check is still needed for vocal emotion and AI vowel-tail texture.",
    ]
    FINAL_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps({
        "final_wav": str(final_wav),
        "final_m4a": str(final_m4a) if final_m4a else None,
        "report": str(FINAL_REPORT),
        "true_peak_dbfs_4x": metrics.get("true_peak_dbfs_4x"),
        "lufs_i_approx_no_gate": metrics.get("lufs_i_approx_no_gate"),
        "clipped_samples": metrics.get("clipped_samples_ge_0_999"),
    }, indent=2))


if __name__ == "__main__":
    main()
