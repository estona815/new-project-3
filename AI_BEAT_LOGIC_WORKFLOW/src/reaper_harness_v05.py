from __future__ import annotations

import json
from pathlib import Path

from audio_qc import write_audio_qc_reports
from reference_comparison import write_reference_comparison
from reaper_plugin_inventory import write_plugin_inventory
from suno_midi_cleanup import cleanup_midi_directory
from suno_reaper_generator import build_track_entry, qc_markers_from_report, render_reaper_lua, write_reaper_manifest
from suno_source_classifier import UNCERTAIN, VOCAL_ARTIFACT_QUARANTINE, classify_source_file, classify_sources, write_source_classification_report


STYLE_PROMPT = (
    "180 BPM fast melodic digicore hyperpop commercial short-form track. Clean vocal-forward modern pop mix, immediate musical hook within 2 seconds, no long intro. "
    "Controlled genre blend: digicore, hyperpop, emo rap, trap, future bass, jersey club bounce, electropop, and pop-punk energy. "
    "Instrumental sample-flip feel from resampled synth riffs, sliced plucks, tight drum edits, reversed synth tails, clean digital fills, sparkling arps, and tight 808 bounce. "
    "Main vocal must sound like a real studio singer: centered, upfront, low-mid to mid register, clean, bright, emotionally autotuned but natural, intelligible, stable, and catchy. "
    "Female vocal layers only as controlled backing doubles, harmony tails, and soft adlibs, low volume and wide stereo, never random, never lead, never main hook. "
    "Smooth transitions, no hard vocal cuts, no random vocal chops. Refined plate reverb, tempo-synced delay throws, polished human arrangement, punchy drums, clean low-end, loud but not crushed, aggressive but not noisy, commercial release quality."
)

EXCLUDE_PROMPT = (
    "random ahh, random ooh, random yeah, moaning vocal, weird vocal chop, vocal chop intro, chopped vocal hook, pitched-up chipmunk vocal, anime voice, baby voice, "
    "harsh female lead takeover, loud female hook, random female adlib, hard vocal splice, abrupt vocal cut, sudden AI cutoff, noisy glitch burst, harsh white noise, metallic digital noise, "
    "excessive bitcrush, unmusical stutter, phasey stereo, anti-phase widening, muddy bass, buried main vocal, muffled vocal, washed-out vocal, excessive reverb, messy delay, over-compression, clipping, "
    "long ambient intro, slow buildup, weak hook, random chord drift, generic AI demo, amateur demo"
)


def _existing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def collect_project_sources(project_dir: str | Path) -> dict[str, list[Path]]:
    root = Path(project_dir)
    raw_stems = sorted((root / "suno_studio_extract" / "raw_stems").glob("*.wav"))
    external_female = sorted((root / "suno_studio_extract" / "external_female_v20_stems").glob("*.wav"))
    midi = sorted((root / "suno_studio_extract" / "midi_guides").glob("*.mid"))
    current_refs = _existing(
        [
            root / "suno_studio_extract" / "v11_precision_mix" / "renders" / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3",
            root / "suno_studio_extract" / "v11_precision_mix" / "renders" / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav",
            root / "suno_studio_extract" / "v11_precision_mix" / "renders" / "hangang_shadow_mashup_v21_clear_male_blended_female_MASTER_320k.mp3.zip",
        ]
    )
    archives = _existing(
        [
            root / "exports" / "얇은_Shadow_Suno_multitrack_stems.zip",
            root / "suno_studio_extract" / "suno_studio_best_midi_stems_package.zip",
        ]
    )
    return {
        "raw_stems": raw_stems,
        "external_female": external_female,
        "midi": midi,
        "current_refs": current_refs,
        "archives": archives,
        "all": raw_stems + external_female + midi + current_refs + archives,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_planning_reports(project_dir: str | Path, plugin_inventory: dict[str, object], qc_report: dict[str, object]) -> dict[str, Path]:
    root = Path(project_dir)
    report_dir = root / "reports"
    paths: dict[str, Path] = {}
    roles = plugin_inventory.get("roles", {})
    pitch = roles.get("pitch_correction", {}).get("selected_plugin", "ReaTune") if isinstance(roles, dict) else "ReaTune"
    issue_count = int(qc_report.get("issue_count", 0))
    marker_count = sum(1 for issue in qc_report.get("issues", []) if issue.get("reaper_marker"))

    paths["vocal_tuning_plan"] = _write(
        report_dir / "vocal_tuning_plan.md",
        f"""
# Vocal Tuning Plan

- Main vocal priority: centered, locked, intelligible, human, and upfront.
- Pitch correction role selected: `{pitch}`.
- If key is reliable from MIDI/audio, lock scale before tuning. If key remains uncertain, insert ReaTune or the detected plugin as a non-destructive placeholder and mark manual correction sections.
- Suggested modern digicore/hyperpop tuning: retune speed 10-25 ms, humanize 25-60, formant correction on if available.
- Avoid hard tuning on breaths, consonants, noisy syllables, or severe AI artifacts.
- QC issues available for marker review: {issue_count}; marker candidates: {marker_count}.
- If severe AI formant instability remains audible, mark the section as requires regeneration or manual re-recording.
""",
    )
    paths["reverb_delay_plan"] = _write(
        report_dir / "reverb_delay_plan.md",
        """
# Reverb Delay Plan

- Use send-based space only: `VOCAL_PLATE_SEND`, `VOCAL_DELAY_SEND`, `SHORT_ROOM_SEND`, and optional throw send.
- Plate: predelay 20-35 ms, decay 0.8-1.6 s, HPF 180-250 Hz, LPF 7-10 kHz, duck under lead vocal.
- Delay: tempo-synced dotted 1/8 or 1/4, HPF 150-250 Hz, LPF 5.5-8 kHz, controlled feedback, phrase-end throws only.
- Short room: subtle glue at very low level.
- Avoid constant messy delay under every vocal line and avoid printed ambience that hides the lead.
""",
    )
    paths["vocal_fx_settings"] = _write(
        report_dir / "vocal_fx_settings.md",
        """
# Vocal FX Settings

- Lead chain order: gain staging, cleanup EQ, pitch correction, dynamic EQ, de-esser, serial compression, tone EQ, light saturation, sends.
- Lead EQ: HPF 70-100 Hz, reduce 180-350 Hz mud if needed, control 350-600 Hz boxiness, control 700 Hz-1.5 kHz nasal tone, add 3-5 kHz clarity only as needed, de-ess 5.5-9 kHz.
- Female BGV: HPF 120-180 Hz, lower than lead by 12-18 dB, pan doubles about 35-45 percent L/R, soften 2-5 kHz if competing.
- Quarantine random AI vocal material before adding vocal ambience.
""",
    )
    paths["stereo_ms_eq_plan"] = _write(
        report_dir / "stereo_ms_eq_plan.md",
        """
# Stereo M/S EQ Plan

- Keep lead vocal, kick, snare, and bass in the mid channel.
- Mono-control low end below 120 Hz.
- Reduce muddy side energy around 150-400 Hz.
- Widen synths and BGV only above the low-mid range.
- Check mono compatibility and avoid fake super-wide AI stereo.
- Keep hook elements audible when collapsed to mono.
""",
    )
    paths["mix_master_plan"] = _write(
        report_dir / "mix_master_plan.md",
        """
# Mix Master Plan

- Build premaster first, then conservative master.
- Do not rebuild from MP3 masters; production source must be WAV stems and guide MIDI.
- Lead vocal stays dominant at roughly -4 to -7 dB starting level and centered.
- Music bus uses dynamic EQ/M/S EQ to carve around the lead from 1-5 kHz.
- Mix bus: gentle corrective EQ, 1-2 dB glue compression max, subtle saturation only if useful, dynamic EQ for mud/harshness.
- Master bus: final EQ, optional multiband/dynamic control, limiter safety, true peak ceiling -1.0 dBTP.
- Short-form pop can target around -8 to -7 LUFS only if the mix supports it. Prefer not crushed; target LRA around 5-8 LU when possible.
""",
    )
    paths["master_settings"] = _write(
        report_dir / "master_settings.md",
        """
# Master Settings

- Render `PREMASTER_24bit_48k.wav` before any aggressive limiter.
- Render `MASTER_24bit_48k.wav` with true peak ceiling -1.0 dBTP.
- Render `MASTER_320k.mp3` only after WAV master exists and ffmpeg is available.
- Avoid over-limiting, upper-mid buildup, clipped transients, buried vocal, and phasey side material.
- Use loudness/reference numbers as direction, not as a cloning target.
""",
    )
    paths["render_report"] = _write(
        report_dir / "render_report.md",
        """
# Render Report

- REAPER render scripts were generated for premaster and master targets.
- This Codex patch did not claim a verified REAPER audio render because REAPER was not run and no rendered files were verified in this turn.
- Expected render targets:
  - `renders/PREMASTER_24bit_48k.wav`
  - `renders/MASTER_24bit_48k.wav`
  - `renders/MASTER_320k.mp3` if ffmpeg is available
- Run the generated REAPER project script, inspect plugin insertions, then run the render script.
""",
    )
    paths["reference_match_notes"] = _write(
        root / "renders" / "REFERENCE_MATCH_NOTES.md",
        """
# Reference Match Notes

Technical references are for vocal clarity, placement, reverb depth, delay control, stereo image, tonal balance, low-end control, dynamic movement, and polish only.

Do not copy melody, lyrics, chords, arrangement, topline, artist identity, or musical content.
""",
    )
    return paths


def write_suno_prompt_reports(project_dir: str | Path) -> dict[str, Path]:
    root = Path(project_dir)
    report_dir = root / "reports"
    paths = {
        "style": _write(report_dir / "suno_style_prompt.txt", STYLE_PROMPT),
        "exclude": _write(report_dir / "suno_exclude_prompt.txt", EXCLUDE_PROMPT),
        "settings": _write(
            report_dir / "suno_generation_settings.md",
            """
# Suno Generation Settings

- Custom Mode: ON
- Instrumental: OFF
- Vocal Gender: Male for main generation
- Weirdness: 6-12%
- Style Influence: 84-88%
- Audio Influence: 0-15% unless using clean instrumental reference only
- Do not use noisy vocal reference audio
- Reject generations with random vocal chops, weird adlibs, or female lead takeover
""",
        ),
    }
    payload = {
        "style_prompt": STYLE_PROMPT,
        "exclude_prompt": EXCLUDE_PROMPT,
        "recommended_settings": {
            "custom_mode": True,
            "instrumental": False,
            "vocal_gender": "male_main_generation",
            "weirdness_percent": "6-12",
            "style_influence_percent": "84-88",
            "audio_influence_percent": "0-15 unless clean instrumental reference only",
            "reject_if": ["random vocal chops", "weird adlibs", "female lead takeover", "buried main vocal", "hard vocal cuts"],
        },
    }
    path = report_dir / "suno_prompt_payload.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["payload"] = path
    return paths


def write_studio_export_plan(project_dir: str | Path) -> Path:
    return _write(
        Path(project_dir) / "reports" / "studio_export_plan.md",
        """
# Studio Export Plan

- Export 12-track WAV stems if available.
- Export vocals stem.
- Export male lead vocal stem if available.
- Export female BGV/adlib/double stem if available.
- Export instrumental stem.
- Export drums stem.
- Export bass/808 stem.
- Export music/synth stem.
- Export FX stem.
- Export MIDI from useful stems.
- Export tempo-locked WAV if available.
- Export full mix WAV only as reference.
- MP3 only as reference, never as production source.

## Warnings

- Do not rebuild from MP3 master.
- Reject Suno generations with strange vocal artifacts.
- Lower Weirdness if vocals become artificial.
- Generate female backing vocals separately if they keep overtaking the lead.
- Export stems before REAPER rebuild.
""",
    )


def write_reaper_scripts(project_dir: str | Path, media: list[dict[str, object]], qc_report: dict[str, object], plugin_inventory: dict[str, object]) -> dict[str, Path]:
    root = Path(project_dir)
    reaper_dir = root / "reaper"
    reaper_dir.mkdir(parents=True, exist_ok=True)
    markers = qc_markers_from_report(qc_report)
    build_path = reaper_dir / "build_project.lua"
    build_path.write_text(render_reaper_lua(media, markers, bpm=180, plugin_inventory=plugin_inventory), encoding="utf-8")
    write_reaper_manifest(root / "reports" / "reaper_import_manifest.json", bpm=180, media=media, script=build_path, qc_markers=markers)

    apply_path = _write(
        reaper_dir / "apply_mix_chains.lua",
        """
-- Harness v0.5 supplemental mix-chain notes.
-- Run build_project.lua first. This file is intentionally conservative and non-destructive.
-- If a premium plugin failed insertion, insert the fallback listed in reports/manual_plugin_notes.md.
-- Lead vocal chain: cleanup EQ -> pitch correction -> dynamic EQ -> de-esser -> serial compression -> tone EQ -> light saturation -> sends.
-- MUSIC_BUS: dynamic EQ/M/S EQ for vocal pocket around 1-5 kHz and side low-mid control.
-- VOCAL_PLATE_SEND: 20-35 ms predelay, 0.8-1.6 s decay, HPF 180-250 Hz, LPF 7-10 kHz, ducked.
-- VOCAL_DELAY_SEND: dotted 1/8 or 1/4, HPF 150-250 Hz, LPF 5.5-8 kHz, phrase throws only.
reaper.ShowMessageBox("Apply/check v0.5 mix chains using reports/manual_plugin_notes.md and reports/*_plan.md. No destructive processing was applied.", "Suno REAPER Harness v0.5", 0)
""",
    )
    render_path = _write(
        reaper_dir / "render_project.lua",
        """
-- Harness v0.5 render setup. Inspect the session before rendering.
local project_dir = reaper.GetProjectPath("")
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", project_dir .. "/renders", true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "PREMASTER_24bit_48k", true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.ShowMessageBox("Render premaster first, then duplicate settings for MASTER_24bit_48k after confirming the master chain. MP3 export is optional after WAV verification.", "Render targets prepared", 0)
""",
    )
    launch_sh = _write(
        reaper_dir / "launch_reaper.sh",
        """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v reaper >/dev/null 2>&1; then
  reaper -newinst -new "$SCRIPT_DIR/build_project.lua"
else
  open -n -a "REAPER" --args -newinst -new "$SCRIPT_DIR/build_project.lua"
fi
""",
    )
    launch_ps1 = _write(
        reaper_dir / "launch_reaper.ps1",
        """$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Reaper = $env:REAPER_EXE
if (-not $Reaper) { $Reaper = "C:\\Program Files\\REAPER (x64)\\reaper.exe" }
Start-Process -FilePath $Reaper -ArgumentList "-newinst", "-reascript", (Join-Path $ScriptDir "build_project.lua")
""",
    )
    return {"build": build_path, "apply": apply_path, "render": render_path, "launch_sh": launch_sh, "launch_ps1": launch_ps1}


def build_media_entries(classified_sources: list[object], qc_report: dict[str, object] | None = None) -> list[dict[str, object]]:
    media: list[dict[str, object]] = []
    female_index = 0
    quarantine_sources = {str(Path(source)) for source in (qc_report or {}).get("quarantine_sources", [])}
    for item in classified_sources:
        category = getattr(item, "category")
        if category == UNCERTAIN:
            continue
        if getattr(item, "extension") == ".zip":
            continue
        path = str(getattr(item, "path"))
        route_category = VOCAL_ARTIFACT_QUARANTINE if path in quarantine_sources else category
        entry = build_track_entry(path, route_category, female_index=female_index)
        if route_category == VOCAL_ARTIFACT_QUARANTINE and category != VOCAL_ARTIFACT_QUARANTINE:
            entry["notes"] = f"QC quarantine override from {category}"
        media.append(entry)
        if category == "female_bgv":
            female_index += 1
    return media


def write_codex_patch_report(project_dir: str | Path, paths: dict[str, Path], comparison: dict[str, object], plugin_inventory: dict[str, object], qc_report: dict[str, object]) -> Path:
    root = Path(project_dir)
    current_available = comparison.get("current", {}).get("available") if isinstance(comparison, dict) else False
    reference_available = comparison.get("reference", {}).get("available") if isinstance(comparison, dict) else False
    fallback_roles = []
    roles = plugin_inventory.get("roles", {})
    if isinstance(roles, dict):
        fallback_roles = [role for role, info in roles.items() if isinstance(info, dict) and info.get("uses_fallback")]
    return _write(
        root / "reports" / "codex_patch_report.md",
        f"""
# Codex Patch Report

- Harness patched to v0.5 for Suno Studio stem/MIDI to REAPER production workflow.
- Changed/added classifier, QC, plugin inventory, reference comparison, MIDI cleanup, REAPER session generation, prompt payload, and planning reports.
- Plugin behavior: scans safe REAPER/AU/VST locations when available; uses configured preferred plugins if detected; falls back to REAPER stock/JS/ffmpeg options without hard failure.
- Fallback roles this run: {", ".join(fallback_roles) if fallback_roles else "none detected as fallback-only"}.
- Source classification: MP3/master/fullmix files are `problem_reference` or `reference_only`; WAV stems can be production tracks unless named master/fullmix/reference; MIDI is `guide_midi`; AI vocal chops are quarantined.
- Reference comparison: current available `{str(bool(current_available)).lower()}`, technical reference available `{str(bool(reference_available)).lower()}`.
- Audio QC: {qc_report.get("issue_count", 0)} issues detected; high/critical or marker-flagged issues become REAPER markers.
- Vocal repair strategy: centered lead, pitch correction before dynamic EQ, de-essing around 5.5-9 kHz, serial compression, tone EQ, light saturation, filtered sends.
- Autotune strategy: use detected pitch plugin or ReaTune fallback; lock key only when reliable; severe AI pitch/formant artifacts require regeneration or manual re-recording.
- Dynamic EQ strategy: control mud, harshness, sibilance, and music masking around 1-5 kHz without dull static cuts.
- Reverb/delay strategy: send-based plate, short room, tempo-synced delay throws, filtered and ducked.
- M/S EQ strategy: mono low end below 120 Hz, reduce side low-mids, keep lead/bass mid, widen only safe synth/BGV ranges.
- Mix/master strategy: premaster first, conservative master second, true peak target -1.0 dBTP, avoid crushed LRA 2-3 style masters.
- Render targets: `renders/PREMASTER_24bit_48k.wav`, `renders/MASTER_24bit_48k.wav`, optional `renders/MASTER_320k.mp3`.
- Known limitations: Codex generated scripts and reports but did not run REAPER or verify a REAPER render in this patch. Premium plugin insertion cannot be claimed until verified inside REAPER.
- Manual next steps: run `reaper/launch_reaper.sh`, inspect plugin insertions, check QC markers, tune the lead vocal, confirm sends, render premaster/master, then update `reports/render_report.md`.
""",
    )


def run_harness_v05(
    project_dir: str | Path,
    *,
    current_reference: str | Path,
    technical_reference: str | Path,
) -> dict[str, object]:
    root = Path(project_dir)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "renders").mkdir(parents=True, exist_ok=True)

    sources = collect_project_sources(root)
    plugin_inventory = write_plugin_inventory(root)
    classified = classify_sources(sources["all"])
    source_report_paths = write_source_classification_report(classified, root / "reports")
    qc_report = write_audio_qc_reports(sources["raw_stems"] + sources["external_female"], root / "reports")
    midi_report = {}
    midi_source = root / "suno_studio_extract" / "midi_guides"
    if midi_source.exists():
        midi_report = cleanup_midi_directory(midi_source, root / "midi" / "cleaned", root / "reports")
    comparison = write_reference_comparison(root, current_reference, technical_reference)
    planning_paths = write_planning_reports(root, plugin_inventory, qc_report)
    prompt_paths = write_suno_prompt_reports(root)
    studio_export_plan = write_studio_export_plan(root)
    media = build_media_entries(classified, qc_report)
    reaper_paths = write_reaper_scripts(root, media, qc_report, plugin_inventory)
    paths = {**planning_paths, **prompt_paths, **reaper_paths, "studio_export_plan": studio_export_plan, **source_report_paths}
    patch_report = write_codex_patch_report(root, paths, comparison, plugin_inventory, qc_report)
    paths["codex_patch_report"] = patch_report
    return {
        "schema_version": "suno_reaper_harness.v0.5",
        "paths": {key: str(value) for key, value in paths.items()},
        "plugin_inventory": plugin_inventory,
        "source_status": source_report_paths,
        "qc_issue_count": qc_report.get("issue_count", 0),
        "midi_report": midi_report,
        "comparison": comparison,
        "media_count": len(media),
    }
