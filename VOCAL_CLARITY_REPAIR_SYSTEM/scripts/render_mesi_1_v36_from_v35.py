#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
SLUG = "mesi_1_v36_vocal_clarity_forward"
SOURCE_WAV = ROOT / "renders/mesi_1_v35_louder_safe_peak_master/mesi_1_v35_LOUDER_SAFE_PEAK_MASTER_24-48.wav"
RENDER_DIR = ROOT / "renders" / SLUG
REPORT_DIR = ROOT / "reports" / SLUG
SYSTEM_REPORT_DIR = SYSTEM / "reports"
FINAL_WAV = RENDER_DIR / "mesi_1_v36_VOCAL_CLARITY_FORWARD_REAPER_24-48.wav"
FINAL_MP3 = RENDER_DIR / "mesi_1_v36_VOCAL_CLARITY_FORWARD_REAPER_320k.mp3"
ZIP_PATH = RENDER_DIR / "mesi_1_v36_VOCAL_CLARITY_FORWARD_DELIVERABLE.zip"
CHAIN = SYSTEM / "FXChains/Mesi1_V36_Mid_Clarity_Master.RfxChain"
REAPER = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
REAPER_JSFX_DIR = Path.home() / "Library/Application Support/REAPER/Effects/Codex Vocal Clarity Repair"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, text=True, capture_output=True, **kwargs)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return proc


def install_jsfx() -> None:
    REAPER_JSFX_DIR.mkdir(parents=True, exist_ok=True)
    for src in (SYSTEM / "JSFX").glob("*.jsfx"):
        shutil.copy2(src, REAPER_JSFX_DIR / src.name)


def build_fxchains() -> None:
    run([sys.executable, str(SYSTEM / "scripts/generate_reaper_fx_chains.py")], cwd=ROOT)


def reaper_batch_render() -> str:
    if not SOURCE_WAV.exists():
        raise SystemExit(f"missing source WAV: {SOURCE_WAV}")
    if not REAPER.exists():
        raise SystemExit(f"missing REAPER binary: {REAPER}")
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    batch = Path(tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name)
    batch.write_text(
        "\n".join([
            f"{SOURCE_WAV}\t{FINAL_WAV}",
            "<CONFIG",
            "SRATE 48000",
            "NCH 2",
            "RSMODE 10",
            "DITHER 3",
            "FX_NCH 2",
            f"FXCHAIN '{CHAIN}'",
            "BRICKWALL 2 -1.05",
            ">",
            "",
        ]),
        encoding="utf-8",
    )
    proc = run([str(REAPER), "-newinst", "-nosplash", "-batchconvert", str(batch), "-close:nosave:exit"], cwd=ROOT)
    log = (proc.stdout or "") + (proc.stderr or "")
    (REPORT_DIR / "reaper_batchconvert.log").write_text(log, encoding="utf-8")
    if not FINAL_WAV.exists():
        raise SystemExit(f"REAPER batch render did not create {FINAL_WAV}")
    return log


def mp3_export() -> None:
    run(["afconvert", "-f", "MPG3", "-d", ".mp3", "-b", "320000", str(FINAL_WAV), str(FINAL_MP3)], cwd=ROOT)


def copy_reports() -> None:
    run([sys.executable, str(SYSTEM / "scripts/analyze_vocal_stem.py"), str(SOURCE_WAV)], cwd=ROOT)
    before_report = SYSTEM_REPORT_DIR / "vocal_analysis_report.md"
    before_json = SYSTEM_REPORT_DIR / "vocal_analysis_report.json"
    shutil.copy2(before_report, REPORT_DIR / "v35_source_analysis.md")
    shutil.copy2(before_json, REPORT_DIR / "v35_source_analysis.json")
    run([sys.executable, str(SYSTEM / "scripts/analyze_vocal_stem.py"), str(FINAL_WAV)], cwd=ROOT)
    shutil.copy2(SYSTEM_REPORT_DIR / "vocal_analysis_report.md", REPORT_DIR / "v36_final_analysis.md")
    shutil.copy2(SYSTEM_REPORT_DIR / "vocal_analysis_report.json", REPORT_DIR / "v36_final_analysis.json")
    run([sys.executable, str(SYSTEM / "scripts/qc_vocal_clarity.py"), "--before", str(SOURCE_WAV), "--after", str(FINAL_WAV)], cwd=ROOT)
    shutil.copy2(SYSTEM_REPORT_DIR / "vocal_clarity_qc_report.md", REPORT_DIR / "vocal_clarity_qc_report.md")
    shutil.copy2(SYSTEM_REPORT_DIR / "vocal_clarity_qc_report.json", REPORT_DIR / "vocal_clarity_qc_report.json")


def write_decisions() -> None:
    trace = {
        "slug": SLUG,
        "source": str(SOURCE_WAV),
        "render_method": "REAPER batch converter",
        "source_limitation": "Current v35 RPP references missing v34 processed stem WAV files, so this is a stereo-master mid-focused clarity pass, not isolated vocal-stem reprocessing.",
        "paid_plugin_policy": "No Antares, Ozone, or paid iZotope chain used in v36 batch render.",
        "fxchain": str(CHAIN),
        "plugins_from_fxchain": [
            "JS: Vocal De-Mud Dynamic EQ",
            "JS: Vocal De-Mud Dynamic EQ (box band)",
            "JS: Vocal Presence Enhancer Guarded",
            "JS: Vocal Air Guard",
            "JS: Vocal Output Guard",
        ],
        "v35_vocal_gate_reference": "reports/mesi_1_v35_louder_safe_peak_master/actual_reaper_plugin_trace.json passed first-slot Codex guard before this final stereo clarity pass.",
    }
    decisions = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "goal": "Improve perceived vocal clarity without adding harsh 3k-6k stab or 10kHz+ AI fizz.",
        "moves": [
            "Used v35 final WAV because current RPP stem media is missing.",
            "Reduced mid-channel mud/box energy conservatively through JSFX dynamic de-mud bands.",
            "Added guarded 3.1kHz presence at low mix amount.",
            "Disabled air boost and used air/fizz guard instead.",
            "Used REAPER batch converter with custom JSFX and true-peak brickwall target.",
        ],
        "avoid": ["Antares", "Ozone", "paid iZotope", "heavy OTT", "heavy Decapitator", "insert reverb on lead"],
    }
    (REPORT_DIR / "plugin_trace_report.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "processing_decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Mesi 1 v36 Vocal Clarity Forward",
        "",
        "## Summary",
        "",
        "- v35 final WAV를 입력으로 REAPER Batch Converter에서 무료/JSFX 체인만 사용한 마지막 clarity pass입니다.",
        "- 현재 v35 RPP가 참조하는 isolated processed stem들이 디스크에 없어, stem 재믹스가 아니라 stereo master의 center/mid 보컬 선명도 보정입니다.",
        "- Ozone, Antares, 유료 iZotope, Decapitator는 v36 batch render에 사용하지 않았습니다.",
        "- 보컬을 더 밝게 만들기보다 180~800Hz 막을 줄이고 3.1kHz presence를 낮은 비율로 보강했습니다.",
        "",
        "## Files",
        "",
        f"- Final WAV: `{FINAL_WAV}`",
        f"- Final MP3: `{FINAL_MP3}`",
        f"- FXChain: `{CHAIN}`",
        f"- QC: `{REPORT_DIR / 'vocal_clarity_qc_report.md'}`",
    ]
    (REPORT_DIR / "render_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(REPORT_DIR / "render_summary.md", SYSTEM_REPORT_DIR / "render_summary.md")


def make_zip() -> None:
    entries = [
        FINAL_WAV,
        FINAL_MP3,
        REPORT_DIR / "render_summary.md",
        REPORT_DIR / "vocal_clarity_qc_report.md",
        REPORT_DIR / "vocal_clarity_qc_report.json",
        REPORT_DIR / "plugin_trace_report.json",
        REPORT_DIR / "processing_decisions.json",
        REPORT_DIR / "v35_source_analysis.md",
        REPORT_DIR / "v36_final_analysis.md",
        CHAIN,
        SYSTEM / "README.md",
    ]
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in entries:
            zf.write(path, path.relative_to(ROOT))


def main() -> None:
    install_jsfx()
    build_fxchains()
    reaper_batch_render()
    mp3_export()
    copy_reports()
    write_decisions()
    make_zip()
    print(json.dumps({"slug": SLUG, "wav": str(FINAL_WAV), "mp3": str(FINAL_MP3), "zip": str(ZIP_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
