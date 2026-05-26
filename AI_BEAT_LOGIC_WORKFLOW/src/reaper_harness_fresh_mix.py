from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from audio_qc import write_audio_qc_reports
from reference_comparison import write_reference_comparison
from reaper_harness_v05 import _write
from reaper_plugin_inventory import write_plugin_inventory
from suno_reaper_generator import build_track_entry, qc_markers_from_report, render_reaper_lua, write_reaper_manifest
from suno_source_classifier import (
    FEMALE_BGV,
    PROBLEM_REFERENCE,
    REFERENCE_ONLY,
    TECHNICAL_MIX_REFERENCE,
    UNCERTAIN,
    VOCAL_ARTIFACT_QUARANTINE,
    ClassifiedSource,
    classify_sources,
    write_source_classification_report,
)


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
CURRENT_PROBLEM_REFERENCE = (
    PROJECT_ROOT
    / "suno_studio_extract"
    / "v11_precision_mix"
    / "renders"
    / "hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip"
)
USER_TECHNICAL_REFERENCE = (
    Path("/Users/hantaeheuk/Downloads")
    / "발매곡 완성본"
    / "동반자살 완성본"
    / "동반자살 WAV.wav"
)
DOWNLOAD_ARCHIVES = [
    Path("/Users/hantaeheuk/Downloads/hangang_shadow_mashup_v19_polished_balance_melody_vocal_MASTER_320k Stems.zip"),
    Path("/Users/hantaeheuk/Downloads/한강 Shadow x 얇은 Shadow (Mashup).zip"),
]


def _existing(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def collect_fresh_sources(project_dir: str | Path) -> dict[str, list[Path]]:
    root = Path(project_dir)
    raw_stems = sorted((root / "suno_studio_extract" / "raw_stems").glob("*.wav"))
    external_female = sorted((root / "suno_studio_extract" / "external_female_v20_stems").glob("*.wav"))
    midi = sorted((root / "suno_studio_extract" / "midi_guides").glob("*.mid"))
    references = _existing(
        [
            CURRENT_PROBLEM_REFERENCE,
            root
            / "suno_studio_extract"
            / "v11_precision_mix"
            / "renders"
            / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3",
            root
            / "suno_studio_extract"
            / "v11_precision_mix"
            / "renders"
            / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav",
            USER_TECHNICAL_REFERENCE,
        ]
    )
    archives = _existing(
        [
            root / "exports" / "얇은_Shadow_Suno_multitrack_stems.zip",
            root / "suno_studio_extract" / "suno_studio_best_midi_stems_package.zip",
            *DOWNLOAD_ARCHIVES,
        ]
    )
    all_sources = raw_stems + external_female + midi + references + archives
    return {
        "raw_stems": raw_stems,
        "external_female": external_female,
        "midi": midi,
        "references": references,
        "archives": archives,
        "all": all_sources,
    }


def _apply_qc_quarantine_overrides(
    classified_sources: Iterable[ClassifiedSource],
    qc_report: dict[str, object],
) -> list[ClassifiedSource]:
    quarantine_sources = {str(Path(source)) for source in qc_report.get("quarantine_sources", [])}
    overridden: list[ClassifiedSource] = []
    for item in classified_sources:
        path = str(Path(item.path))
        if path in quarantine_sources and item.category not in {REFERENCE_ONLY, TECHNICAL_MIX_REFERENCE, PROBLEM_REFERENCE}:
            overridden.append(
                replace(
                    item,
                    category=VOCAL_ARTIFACT_QUARANTINE,
                    reason=f"audio QC quarantine override; original category was {item.category}",
                    reference_only=False,
                    production_eligible=False,
                    guide_only=False,
                    quarantine=True,
                )
            )
        else:
            overridden.append(item)
    return overridden


def _build_fresh_media_entries(classified_sources: Iterable[ClassifiedSource]) -> list[dict[str, object]]:
    media: list[dict[str, object]] = []
    female_index = 0
    for item in classified_sources:
        if item.category == UNCERTAIN or item.extension == ".zip":
            continue
        if item.category == TECHNICAL_MIX_REFERENCE:
            entry = build_track_entry(item.path, item.category, name=f"TECH REF - {Path(item.path).stem}")
        elif item.category == PROBLEM_REFERENCE:
            entry = build_track_entry(item.path, item.category, name=f"PROBLEM REF - {Path(item.path).stem}")
        else:
            entry = build_track_entry(item.path, item.category, female_index=female_index)
        if item.category == FEMALE_BGV:
            female_index += 1
        media.append(entry)
    return media


def _source_summary(classified_sources: Iterable[ClassifiedSource]) -> dict[str, list[str]]:
    summary = {
        "production_stems": [],
        "reference_only": [],
        "technical_references": [],
        "problem_references": [],
        "quarantine": [],
        "guide_midi": [],
        "uncertain": [],
    }
    for item in classified_sources:
        name = Path(item.path).name
        if item.production_eligible:
            summary["production_stems"].append(name)
        if item.category == REFERENCE_ONLY:
            summary["reference_only"].append(name)
        elif item.category == TECHNICAL_MIX_REFERENCE:
            summary["technical_references"].append(name)
        elif item.category == PROBLEM_REFERENCE:
            summary["problem_references"].append(name)
        elif item.category == VOCAL_ARTIFACT_QUARANTINE:
            summary["quarantine"].append(name)
        elif item.guide_only:
            summary["guide_midi"].append(name)
        elif item.category == UNCERTAIN:
            summary["uncertain"].append(name)
    return summary


def _role(plugin_inventory: dict[str, object], role: str, fallback: str) -> dict[str, object]:
    roles = plugin_inventory.get("roles", {})
    if isinstance(roles, dict) and isinstance(roles.get(role), dict):
        return roles[role]  # type: ignore[return-value]
    return {"selected_plugin": fallback, "fallback": fallback, "uses_fallback": True, "detected": []}


def _stock_safe_plugin_inventory(plugin_inventory: dict[str, object]) -> dict[str, object]:
    stock_overrides = {
        "pitch_correction": "ReaTune",
        "surgical_eq": "ReaEQ",
        "dynamic_eq": "ReaXcomp",
        "deesser": "ReaXcomp",
        "compressor_clean": "ReaComp",
        "compressor_character": "ReaComp",
        "saturation": "JS: Saturation",
        "multiband_compressor": "ReaXcomp",
        "stereo_imager": "JS: Stereo Width",
        "mid_side_eq": "ReaEQ",
        "reverb_plate": "ReaVerbate",
        "reverb_room": "ReaVerbate",
        "delay": "ReaDelay",
        "limiter": "ReaLimit",
        "loudness_meter": "JS: Loudness Meter Peak/RMS/LUFS",
        "noise_reduction": "ReaFIR",
    }
    safe = dict(plugin_inventory)
    roles = {}
    source_roles = plugin_inventory.get("roles", {})
    for role, selected in stock_overrides.items():
        source = source_roles.get(role, {}) if isinstance(source_roles, dict) else {}
        source = source if isinstance(source, dict) else {}
        roles[role] = {
            **source,
            "selected_plugin": selected,
            "uses_fallback": True,
            "fresh_auto_insert_mode": "stock_safe_fallback",
            "insertion_policy": "Fresh REAPER build inserts stock-safe fallback FX only; detected premium plugins remain manual upgrade candidates.",
        }
    safe["roles"] = roles
    return safe


def write_fresh_planning_reports(
    project_dir: str | Path,
    classified_sources: list[ClassifiedSource],
    plugin_inventory: dict[str, object],
    qc_report: dict[str, object],
    comparison: dict[str, object],
) -> dict[str, Path]:
    root = Path(project_dir)
    report_dir = root / "reports"
    summary = _source_summary(classified_sources)
    marker_count = sum(1 for issue in qc_report.get("issues", []) if issue.get("reaper_marker"))
    issue_count = int(qc_report.get("issue_count", 0))
    pitch_role = _role(plugin_inventory, "pitch_correction", "ReaTune")
    dyn_role = _role(plugin_inventory, "dynamic_eq", "ReaXcomp")
    deess_role = _role(plugin_inventory, "deesser", "ReaXcomp")
    limiter_role = _role(plugin_inventory, "limiter", "ReaLimit")

    paths: dict[str, Path] = {}
    paths["gain_staging_report"] = _write(
        report_dir / "gain_staging_report.md",
        """
# Fresh Gain Staging Report

- Rebuild mode: zero-state fresh session, no old track levels, bus chains, master chain, printed FX balance, or previous limiter choices.
- Male lead starting level: about -6 dB fader, centered, routed to `MALE_LEAD_VOX_BUS`.
- Female BGV starting level: about -21 dB fader, wide support only, roughly 12-18 dB below the male lead depending on source loudness.
- Drums start conservative around -10 dB; bass/808 around -10.5 dB and centered; music around -13 dB; FX around -20 dB.
- References are muted on `REF_BUS`.
- QC quarantine sources are muted on `ARTIFACT_QUARANTINE_BUS`.
- No loudness chasing or heavy limiter reduction is part of the starting balance.
""",
    )
    paths["vocal_tuning_plan"] = _write(
        report_dir / "vocal_tuning_plan.md",
        f"""
# Vocal Tuning Plan

- Lead tuning role selected: `{pitch_role.get('selected_plugin')}`; fallback status: `{str(bool(pitch_role.get('uses_fallback'))).lower()}`.
- Key source: guide MIDI plus lead-vocal audio only. If the key is uncertain, keep correction non-destructive and avoid hard scale-locking.
- Starting direction: retune speed 10-25 ms, humanize 25-60, formant correction enabled when the plugin supports it.
- Preserve musical slides, breaths, and consonants; do not tune noisy syllable edges aggressively.
- QC issues available: {issue_count}; high/critical marker candidates: {marker_count}.
- If marked pitch/formant artifacts remain audible after tuning, label the section as requiring regeneration or manual re-recording.
""",
    )
    paths["lead_vocal_chain"] = _write(
        report_dir / "lead_vocal_chain.md",
        f"""
# Lead Vocal Chain

Processing order:

1. Clip gain / clean gain staging.
2. Cleanup EQ, high-pass around 70-100 Hz.
3. Pitch correction using `{pitch_role.get('selected_plugin')}` if it loads; otherwise ReaTune fallback.
4. Dynamic EQ using `{dyn_role.get('selected_plugin')}` or fallback to ReaXcomp/ReaEQ automation.
5. De-esser using `{deess_role.get('selected_plugin')}` or fallback dynamic band around 5.5-9 kHz.
6. Gentle serial compression: clean compressor then character compressor if verified.
7. Tone EQ and only light saturation if the stem stays clean.
8. Send-based reverb/delay only.

Targets:

- Centered, dominant male lead.
- Mud control around 180-350 Hz, box control around 350-600 Hz, nasal/harsh control around 700 Hz-5 kHz as needed.
- Air around 10-14 kHz only if the stem is not noisy.
- No heavy compression that crushes consonants or exposes AI texture.
""",
    )
    paths["female_bgv_chain"] = _write(
        report_dir / "female_bgv_chain.md",
        """
# Female BGV Chain

- Female vocals are support layers only, never lead.
- Start about -21 dB fader and keep them roughly 12-18 dB below the male lead after listening.
- Pan doubles/support layers around 35-45 percent L/R.
- High-pass around 120-180 Hz.
- De-ess if needed and soften 2-5 kHz if the layer competes with male vocal intelligibility.
- Use more ambience than the lead but keep it filtered and controlled.
- Any lead-like, random, loud, or AI-sounding female phrase should be moved to `ARTIFACT_QUARANTINE_BUS` and muted.
""",
    )
    paths["instrumental_mix_plan"] = _write(
        report_dir / "instrumental_mix_plan.md",
        """
# Instrumental Mix Plan

- Drums: preserve punch, tame brittle hats around 7-11 kHz, avoid clipping or random glitch bursts.
- 808/Bass: mono below 120 Hz, dynamic relationship with kick, reduce mud around 120-300 Hz, add harmonics only if useful.
- Music/Synth: carve a dynamic pocket around 1-5 kHz for vocal consonants and keep side low frequencies controlled.
- FX: use only transition-supportive material; QC-suspicious FX/Guitar sources stay quarantined and muted.
- Instrumental automation should duck support material under dense vocal sections before master limiting is considered.
""",
    )
    paths["reverb_delay_plan"] = _write(
        report_dir / "reverb_delay_plan.md",
        """
# Reverb Delay Plan

- Use `VOCAL_PLATE_SEND`, `VOCAL_DELAY_SEND`, `SHORT_ROOM_SEND`, and optional `OPTIONAL_WIDE_THROW_SEND`.
- Plate: 20-35 ms predelay, 0.8-1.6 s decay, HPF 180-250 Hz, LPF 7-10 kHz, ducked under the lead.
- Delay: tempo-synced dotted 1/8 or 1/4, HPF 150-250 Hz, LPF 5.5-8 kHz, controlled feedback, phrase-end throws only.
- Short room: subtle glue at very low level.
- If phrase-end detection is uncertain, use the QC/arrangement markers as manual throw review points.
""",
    )
    paths["vocal_fx_settings"] = _write(
        report_dir / "vocal_fx_settings.md",
        """
# Vocal FX Settings

- Lead plate send starts low and should be ducked so lead syllables stay intelligible.
- Lead delay send is not constant ambience; automate throws at phrase endings only.
- Filter all vocal FX returns before they hit `VOCAL_FX_BUS`.
- Female BGV can use more plate/room than lead, but must remain quieter and wider than the lead.
- Avoid reusing printed ambience from old processed stems or old masters as an active mix decision.
""",
    )
    paths["stereo_ms_eq_plan"] = _write(
        report_dir / "stereo_ms_eq_plan.md",
        """
# Stereo M/S EQ Plan

- Kick, snare, bass/808, and male lead stay centered.
- Mono-control low end below 120 Hz.
- Reduce muddy side energy around 150-400 Hz.
- Widen synths and female BGV only above low-mid range.
- Check stereo correlation before rendering; reduce anti-phase or phasey side material.
- Hook elements must remain useful in mono.
""",
    )
    paths["mix_master_plan"] = _write(
        report_dir / "mix_master_plan.md",
        """
# Mix Master Plan

- Build a premaster first; master only after vocal balance, tuning, dynamics, and space are right.
- Mix bus: gentle corrective EQ, 1-2 dB glue compression max, subtle saturation only if useful, dynamic EQ for mud/harshness, M/S control.
- Premaster target: vocal-forward, headroom intact, no clipping, roughly -10 to -8 LUFS only if the mix naturally supports it.
- Master target: short-form pop loudness around -8 to -7 LUFS only if clean; true peak ceiling -1.0 dBTP; LRA preferably 5-8 LU.
- Do not crush the vocal or chase old loudness choices.
""",
    )
    paths["master_settings"] = _write(
        report_dir / "master_settings.md",
        f"""
# Master Settings

- Limiter role selected: `{limiter_role.get('selected_plugin')}`; fallback status: `{str(bool(limiter_role.get('uses_fallback'))).lower()}`.
- True peak ceiling: -1.0 dBTP.
- Limiter is safety first, loudness second.
- Use dynamic/multiband control only where measured harshness, mud, or low-end movement calls for it.
- Render WAV master first, MP3 only after WAV verification and ffmpeg availability.
""",
    )
    reference_available = comparison.get("reference", {}).get("available") if isinstance(comparison, dict) else False
    paths["render_report"] = _write(
        report_dir / "render_report.md",
        """
# Render Report

- Fresh render setup generated: `reaper/render_fresh_mix.lua`.
- Expected outputs:
  - `renders/FRESH_PREMASTER_24bit_48k.wav`
  - `renders/FRESH_MASTER_24bit_48k.wav`
  - `renders/FRESH_MASTER_320k.mp3` if ffmpeg is available after WAV verification.
- Automatic REAPER render is not claimed until the `.rpp` opens, plugin insertion is inspected, and output files are verified.
- Guide MIDI tracks are muted placeholders in the auto-built session to avoid REAPER command-line MIDI import dialogs; import them manually if needed for pitch/key inspection.
- If REAPER render cannot run automatically, use the launch script and render instructions in `reports/manual_plugin_notes.md`.
""",
    )
    paths["reference_notes"] = _write(
        root / "renders" / "FRESH_REFERENCE_MATCH_NOTES.md",
        f"""
# Fresh Reference Match Notes

- Technical reference available this run: {str(bool(reference_available)).lower()}.
- References are technical guides only for vocal clarity, reverb depth, delay control, dynamic movement, stereo balance, tonal balance, low-end control, and polish.
- Do not copy melody, lyrics, topline, chords, arrangement, artist identity, or musical content.
- Current/problem masters are negative references only.
""",
    )
    paths["fresh_mix_rebuild_report"] = _write(
        report_dir / "fresh_mix_rebuild_report.md",
        f"""
# Fresh Mix Rebuild Report

## Why the previous output failed

- Treated here as over-processed, noisy, unstable, poorly balanced, and not reliable enough for commercial-release claims.
- Specific avoid-list: buried or unstable lead vocal, imprecise reverb/delay, weak M/S control, uncontrolled dynamic EQ, phasey width, crushed loudness, and old FX/master decisions.

## What was rebuilt from scratch

- New REAPER build script: `reaper/build_fresh_mix.lua`.
- New chain/notes script: `reaper/apply_fresh_mix_chains.lua`.
- New render setup: `reaper/render_fresh_mix.lua`.
- New save target: `reaper/FRESH_MIX_REBUILD.rpp`.
- Required fresh buses, send returns, QC markers, muted references, and muted quarantine routing are generated from zero.
- Guide MIDI tracks are created as muted placeholders with source-path metadata instead of auto-imported MIDI items, because REAPER can block on MIDI import option dialogs during command-line session creation.

## Production stems

{json.dumps(summary["production_stems"], ensure_ascii=False, indent=2)}

## References only

{json.dumps(summary["reference_only"] + summary["technical_references"] + summary["problem_references"], ensure_ascii=False, indent=2)}

## Quarantined artifacts

{json.dumps(summary["quarantine"], ensure_ascii=False, indent=2)}

## Vocal and mix strategy

- Male lead: centered, dominant, pitch correction before dynamic EQ, de-essing, serial compression, tone EQ, light saturation only if clean.
- Female BGV: support only, quiet and wide, lower than male lead.
- Dynamic EQ: mud, sibilance, harshness, and 1-5 kHz masking are handled dynamically instead of with dull static cuts.
- Reverb/delay: send-based, tempo-aware, filtered, and ducked where possible.
- M/S space: low end centered, side low-mids reduced, width limited to synth/BGV ranges that remain mono-compatible.
- Mix/master: premaster first, conservative master second, true peak ceiling -1.0 dBTP, no extreme limiting.

## Known limitations

- Plugin inventory is detection/placeholder/fallback guidance only until verified in REAPER.
- The fresh auto-build script inserts stock-safe fallback FX to avoid premium plugin license/modal stalls; detected premium plugins remain manual upgrade candidates.
- Guide MIDI should be imported manually inside REAPER only after the session opens if you need piano-roll inspection.
- Automated QC is not a substitute for human listening to vocal pitch, phrase endings, emotional timing, or commercial polish.
- Any severe AI vocal artifact that remains audible requires regeneration or manual re-recording.
""",
    )
    return paths


def write_fresh_reaper_scripts(
    project_dir: str | Path,
    media: list[dict[str, object]],
    qc_report: dict[str, object],
    plugin_inventory: dict[str, object],
) -> dict[str, Path]:
    root = Path(project_dir)
    reaper_dir = root / "reaper"
    reaper_dir.mkdir(parents=True, exist_ok=True)
    markers = qc_markers_from_report(qc_report)
    build_path = reaper_dir / "build_fresh_mix.lua"
    project_path = reaper_dir / "FRESH_MIX_REBUILD.rpp"
    auto_insert_inventory = _stock_safe_plugin_inventory(plugin_inventory)
    build_path.write_text(
        render_reaper_lua(
            media,
            markers,
            bpm=180,
            plugin_inventory=auto_insert_inventory,
            harness_version="fresh_mix_rebuild.v0.6",
            project_save_path=project_path,
            undo_label="Build fresh Suno to REAPER mix/master rebuild",
        ),
        encoding="utf-8",
    )
    write_reaper_manifest(root / "reports" / "reaper_import_manifest.json", bpm=180, media=media, script=build_path, qc_markers=markers)
    write_reaper_manifest(root / "reports" / "fresh_reaper_import_manifest.json", bpm=180, media=media, script=build_path, qc_markers=markers)
    apply_path = _write(
        reaper_dir / "apply_fresh_mix_chains.lua",
        """
-- Fresh mix/master chain notes. Run build_fresh_mix.lua first.
-- This script intentionally avoids destructive parameter writes until plugin insertion is verified.
-- Lead: gain -> cleanup EQ -> pitch correction -> dynamic EQ -> de-esser -> serial comp -> tone EQ -> light saturation -> sends.
-- Female BGV: support only, HPF, de-ess, soften 2-5 kHz, controlled width.
-- Music: carve 1-5 kHz vocal pocket and reduce side low-mids.
-- Master: conservative EQ/glue/dynamic control, limiter ceiling -1.0 dBTP.
reaper.ShowMessageBox("Fresh mix chain checklist loaded. Inspect reports/manual_plugin_notes.md before committing plugin-specific settings.", "Fresh Mix Rebuild", 0)
""",
    )
    render_path = _write(
        reaper_dir / "render_fresh_mix.lua",
        """
-- Fresh render setup. Inspect balance/plugin insertion before rendering.
local project_dir = reaper.GetProjectPath("")
local render_dir = "/Users/hantaeheuk/Documents/New project 3/renders"
if reaper.GetSetProjectInfo_String then
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "FRESH_PREMASTER_24bit_48k", true)
end
if reaper.GetSetProjectInfo then
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
end
reaper.ShowMessageBox("Render FRESH_PREMASTER_24bit_48k first. After human balance/QC, duplicate settings for FRESH_MASTER_24bit_48k and optional FRESH_MASTER_320k.mp3.", "Fresh Render Setup", 0)
""",
    )
    launch_path = _write(
        reaper_dir / "launch_fresh_mix.sh",
        """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAP_DIR="/tmp/codex_fresh_reaper"
WRAP_SCRIPT="$WRAP_DIR/run_build_fresh_mix.lua"
mkdir -p "$WRAP_DIR"
cat > "$WRAP_SCRIPT" <<'LUA'
local log_path = "/tmp/codex_fresh_reaper/build_fresh_mix.log"
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\\n")
    f:close()
  end
end
log("wrapper start")
local ok, err = xpcall(function()
  dofile("/Users/hantaeheuk/Documents/New project 3/reaper/build_fresh_mix.lua")
end, debug.traceback)
if ok then
  log("wrapper ok")
else
  log("wrapper error: " .. tostring(err))
end
LUA
open -n -a "REAPER" --args -newinst -new "$WRAP_SCRIPT"
""",
    )
    launch_path.chmod(0o755)
    return {"build_fresh": build_path, "apply_fresh": apply_path, "render_fresh": render_path, "launch_fresh": launch_path}


def run_fresh_mix_rebuild(
    project_dir: str | Path = PROJECT_ROOT,
    *,
    current_reference: str | Path = CURRENT_PROBLEM_REFERENCE,
    technical_reference: str | Path = USER_TECHNICAL_REFERENCE,
) -> dict[str, object]:
    root = Path(project_dir)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "renders").mkdir(parents=True, exist_ok=True)
    sources = collect_fresh_sources(root)
    plugin_inventory = write_plugin_inventory(root)
    classified_initial = classify_sources(sources["all"])
    qc_report = write_audio_qc_reports(sources["raw_stems"] + sources["external_female"], root / "reports")
    classified = _apply_qc_quarantine_overrides(classified_initial, qc_report)
    classification_paths = write_source_classification_report(classified, root / "reports")
    comparison = write_reference_comparison(root, current_reference, technical_reference)
    media = _build_fresh_media_entries(classified)
    reaper_paths = write_fresh_reaper_scripts(root, media, qc_report, plugin_inventory)
    report_paths = write_fresh_planning_reports(root, classified, plugin_inventory, qc_report, comparison)
    payload = {
        "schema_version": "fresh_mix_rebuild.v0.6",
        "production_rebuild_allowed": bool(classification_paths),
        "source_counts": {
            "raw_stems": len(sources["raw_stems"]),
            "external_female": len(sources["external_female"]),
            "midi": len(sources["midi"]),
            "references": len(sources["references"]),
            "archives": len(sources["archives"]),
            "media": len(media),
        },
        "qc_issue_count": qc_report.get("issue_count", 0),
        "qc_marker_count": sum(1 for issue in qc_report.get("issues", []) if issue.get("reaper_marker")),
        "paths": {key: str(path) for key, path in {**classification_paths, **reaper_paths, **report_paths}.items()},
    }
    (root / "reports" / "fresh_mix_rebuild_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(json.dumps(run_fresh_mix_rebuild(), indent=2, ensure_ascii=False))
