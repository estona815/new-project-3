#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_DISPLAY = "JS: Codex Vocal AI Artifact Split Tamer"
REQUIRED_FILE = "Codex Vocal/vocal_ai_artifact_split_tamer.jsfx"
REAPER_RESOURCE = Path.home() / "Library/Application Support/REAPER"
REQUIRED_EFFECT_PATH = REAPER_RESOURCE / "Effects" / "Codex Vocal" / "vocal_ai_artifact_split_tamer.jsfx"
REAPER_JSFX_INDEX = REAPER_RESOURCE / "reaper-jsfx.ini"

MAIN_VOCAL_EXACT = "08 MALE_NONHOOK_CENTER"
MAIN_TRACK_ALIASES = {
    MAIN_VOCAL_EXACT.lower(),
    "male_nonhook_center",
    "male nonhook center",
    "male_lead",
    "male lead",
    "center male",
    "main male",
    "vocal_anchor",
    "main_vocal",
    "lead_vocal",
    "main vocal",
    "lead vocal",
}

TUNE_PLUGINS = (
    "mautopitch",
    "reatune",
    "graillon",
    "antares",
    "auto-tune",
    "auto_tune",
    "autotune",
)

UNREGISTERED_OLD_NOISE_NAMES = (
    "estona_sunonoiseguard",
    "estona_sunonoise",
    "estona_deai_noisereducer",
    "estona_vocal_antiai_harsh",
)


def load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError(f"{path} does not contain a trace row list")
    return [row for row in rows if isinstance(row, dict)]


def plugin_is_required_noise_plugin(plugin: str) -> bool:
    text = plugin.strip().lower()
    return text in {
        REQUIRED_DISPLAY.lower(),
        f"js: {REQUIRED_FILE.lower()}",
        REQUIRED_FILE.lower(),
    } or "codex vocal ai artifact split tamer" in text


def track_is_main_vocal(track: str, explicit: set[str]) -> bool:
    normalized = track.strip().lower()
    return normalized in MAIN_TRACK_ALIASES or normalized in explicit


def select_main_vocal_rows(rows: list[dict[str, Any]], explicit_tracks: set[str]) -> list[dict[str, Any]]:
    fx_rows = [
        row
        for row in rows
        if trace_row_is_fx_evidence(row)
    ]
    exact = MAIN_VOCAL_EXACT.lower()
    exact_rows = [
        row
        for row in fx_rows
        if str(row.get("track", "")).strip().lower() == exact
    ]
    if exact_rows:
        return exact_rows
    return [
        row
        for row in fx_rows
        if track_is_main_vocal(str(row.get("track", "")), explicit_tracks)
    ]


def trace_row_is_fx_evidence(row: dict[str, Any]) -> bool:
    try:
        if int(row.get("fx_index", -1)) < 0:
            return False
    except (TypeError, ValueError):
        return False
    stage = str(row.get("stage", "")).strip().lower()
    if stage.startswith("insert media"):
        return False
    if stage in {"send", "routing"}:
        return False
    return True


def check_registry() -> list[str]:
    errors: list[str] = []
    if not REQUIRED_EFFECT_PATH.exists():
        errors.append(f"missing JSFX file: {REQUIRED_EFFECT_PATH}")
    if not REAPER_JSFX_INDEX.exists():
        errors.append(f"missing REAPER JSFX index: {REAPER_JSFX_INDEX}")
        return errors
    index = REAPER_JSFX_INDEX.read_text(encoding="utf-8", errors="ignore")
    if REQUIRED_DISPLAY not in index or REQUIRED_FILE not in index:
        errors.append(
            "required JSFX is not registered in reaper-jsfx.ini "
            f"as {REQUIRED_DISPLAY!r} / {REQUIRED_FILE!r}"
        )
    return errors


def check_trace(path: Path, explicit_tracks: set[str], allow_tune: bool) -> list[str]:
    rows = load_rows(path)
    errors: list[str] = []
    main_rows = select_main_vocal_rows(rows, explicit_tracks)
    if not main_rows:
        return [f"no main vocal trace rows found in {path}"]

    main_rows.sort(key=lambda row: int(row.get("fx_index", 999999)))
    first = main_rows[0]
    first_plugin = str(first.get("plugin", ""))
    first_status = str(first.get("status", ""))
    first_fx = int(first.get("fx_index", -1))
    if first_status != "loaded" or first_fx != 0 or not plugin_is_required_noise_plugin(first_plugin):
        errors.append(
            "main vocal first FX slot is not the developed Suno/AI noise plugin: "
            f"fx_index={first_fx}, status={first_status}, plugin={first_plugin!r}"
        )

    for row in main_rows:
        plugin = str(row.get("plugin", ""))
        plugin_lower = plugin.lower()
        stage = str(row.get("stage", ""))
        if not allow_tune and any(name in plugin_lower for name in TUNE_PLUGINS):
            errors.append(
                "main vocal tune/pitch insert is blocked for clean rescue: "
                f"fx_index={row.get('fx_index')}, plugin={plugin!r}, stage={stage!r}"
            )
        if "developed" in stage.lower() or "anti-ai" in stage.lower() or "suno" in stage.lower():
            if "noise" in stage.lower() and not plugin_is_required_noise_plugin(plugin):
                errors.append(
                    "stage claims developed/Suno noise rescue but loaded another plugin: "
                    f"fx_index={row.get('fx_index')}, plugin={plugin!r}, stage={stage!r}"
                )

    return errors


def check_script(path: Path, allow_tune: bool) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lowered = text.lower()
    errors: list[str] = []
    if REQUIRED_DISPLAY not in text:
        errors.append(f"{path} does not reference the registered plugin name {REQUIRED_DISPLAY!r}")
    for old_name in UNREGISTERED_OLD_NOISE_NAMES:
        if old_name in lowered:
            errors.append(f"{path} still references unregistered old noise plugin name {old_name!r}")
    if not allow_tune:
        for number, line in enumerate(text.splitlines(), 1):
            candidate_line = "add_fx(" in line or "TrackFX_AddByName" in line or '"VST' in line or "'VST" in line
            if candidate_line and any(name in line.lower() for name in TUNE_PLUGINS):
                errors.append(
                    f"{path}:{number} still inserts or offers a tune/pitch plugin blocked for clean rescue"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the mandatory REAPER main-vocal Suno/AI noise rescue gate."
    )
    parser.add_argument("--trace", type=Path, help="actual_reaper_plugin_trace.json to validate")
    parser.add_argument("--script", type=Path, help="optional generator script to statically check")
    parser.add_argument(
        "--main-track",
        action="append",
        default=[],
        help="additional main vocal track label in the trace",
    )
    parser.add_argument(
        "--allow-main-vocal-tune",
        action="store_true",
        help="allow MAutoPitch/ReaTune/Graillon/Antares on the main vocal",
    )
    args = parser.parse_args()

    errors = check_registry()
    explicit = {track.strip().lower() for track in args.main_track}
    if args.trace:
        errors.extend(check_trace(args.trace, explicit, args.allow_main_vocal_tune))
    if args.script:
        errors.extend(check_script(args.script, args.allow_main_vocal_tune))

    summary = {
        "required_plugin": REQUIRED_DISPLAY,
        "required_file": str(REQUIRED_EFFECT_PATH),
        "trace": str(args.trace) if args.trace else None,
        "script": str(args.script) if args.script else None,
        "passed": not errors,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
