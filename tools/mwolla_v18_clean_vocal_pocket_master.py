#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V16B_SCRIPT = ROOT / "tools" / "mwolla_v16b_source_stem_repair_reference_density_master.py"
SLUG = "mwolla_v18_clean_vocal_pocket_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v16b_source_stem_repair_reference_density_master", V16B_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v16B script: {V16B_SCRIPT}")
v16b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v16b)

base = v16b.base


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configure_base() -> None:
    v16b.SLUG = SLUG
    v16b.ZIP_SOURCE = ZIP_SOURCE
    v16b.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v18_CLEAN_VOCAL_POCKET_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v18_clean_vocal_pocket_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v18_clean_vocal_pocket_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v18_clean_vocal_pocket_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v18_clean_vocal_pocket_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v18_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v18_CLEAN_VOCAL_POCKET_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v18_CLEAN_VOCAL_POCKET_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v18_VOCAL_SOLO_clean_vocal_pocket.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v18_AB_v16b_to_clean_vocal_pocket_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v18_CLEAN_VOCAL_POCKET_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v18_clean_vocal_pocket_master_report.md"
    base.REPORT_TITLE = "Mwolla v18 Clean Vocal Pocket Master Report"
    base.PROJECT_NOTES = (
        "mwolla v18: conservative follow-up after v17 introduced too many processed-stem phase warnings. "
        "This pass keeps the v16B source-stem repair chain and changes only REAPER routing/gain pocket: "
        "main vocal slightly forward, music bus slightly tucked, sidechain preserved at 1/2 -> 3/4, no master loudness push."
    )

    v16b.v11.PHRASE_PREMASTER_NAME = "mwolla_v18_PHRASE_SAFE_CLEAN_VOCAL_POCKET_PREMASTER_24-48.wav"
    v16b.v11.FINAL_LOCKED_NAME = "mwolla_v18_POST_FINAL_CLEAN_VOCAL_POCKET_NO_LOUDNESS_PUSH_24-48.wav"


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v16b.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v16B source stem repair reference density master", "mwolla v18 clean vocal pocket master")
    build_text = build_text.replace("mwolla_v16B", "mwolla_v18")
    build_text = build_text.replace('local main = make_track("10 MAIN_VOCAL_CENTER", 1.55, 0.0, false, false)', 'local main = make_track("10 MAIN_VOCAL_CENTER", 1.68, 0.0, false, false)')
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.18, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.12, 0.0, false, false)')
    build_text = build_text.replace('route_sidechain(main_bus, music_bus, -1.4, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")', 'route_sidechain(main_bus, music_bus, -1.1, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")')
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def patch_v18_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("Mwolla v16B Source Stem Repair Reference Density Master Report", base.REPORT_TITLE)
    text = text.replace("mwolla v16B source stem repair reference density master", "mwolla v18 clean vocal pocket master")
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v18 Clean Vocal Pocket Pass",
            "",
            "- Reason: v17 rendered and passed delivery gates, but independent processed-stem QC showed additional phase warnings and did not improve the 1.5-5 kHz stem-level proxy.",
            "- v18 keeps v16B printed stem repair and changes only REAPER balance/routing to reduce new artifact risk.",
            "- REAPER gain changes vs v16B: 10 MAIN_VOCAL_CENTER `+0.13 dB`, MUSIC_BUS `-0.06 dB`, MAIN_VOCAL_BUS -> MUSIC_BUS sidechain send `-1.4 dB` to `-1.1 dB`.",
            "- Preserved: v14 no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, MAIN_VOCAL_BUS -> MUSIC_BUS source 1/2 into destination 3/4, and no-loudness-push final stage.",
            "- Explicitly avoided: new Ozone/OTT/clipper, PREMASTER limiter push, and external plugin parameter writes.",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v16b.write_reports(paths, processed, vocal_balance, gate)
    patch_v18_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["v18_clean_vocal_pocket"] = {
        "reason": "v17 kept as diagnostic candidate; v18 is the conservative routing/gain pocket pass after processed-stem phase warnings.",
        "main_track_gain_change_vs_v16b_db": 0.13,
        "music_bus_gain_change_vs_v16b_db": -0.06,
        "main_to_music_sidechain_send_change_vs_v16b_db": 0.3,
        "no_loudness_push_preserved": True,
        "external_parameter_writes": "none_added",
        "new_master_processors": "none_added",
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v16b.build_zip()


def main() -> int:
    configure_base()
    base.extract_source = v16b.v12.extract_source
    base.write_reaper_scripts = write_reaper_scripts
    base.write_trace_md = v16b.v12.write_trace_md
    base.run_gate = v16b.v12.run_gate
    base.write_reports = write_reports
    base.build_zip = build_zip
    base.process_lead_vocal = v16b.v14.process_lead_vocal_clarity
    base.process_female_layer = v16b.v14.process_layer_vocal_clarity
    base.process_backing_vocals = v16b.v2.v1.process_backing_vocals
    base.process_instrument = v16b.v2.v1.process_instrument
    base.write_processed = v16b.write_processed
    base.final_master = v16b.v13.final_master_no_loudness_push
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
