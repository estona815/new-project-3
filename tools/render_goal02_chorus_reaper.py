#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.render_goal02_chorus_candidate import (
    concatenate_with_silence,
    db_gain,
    limit_peak,
    limit_true_peak_estimate,
    linear_to_db,
    metrics,
    pad_or_trim,
    read_wav_slice,
    rms,
    rms_match_to,
    simple_compressor,
    soft_clip,
    write_float_wav,
)


REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
DEFAULT_MANIFEST = ROOT / "configs" / "goal02_8_reference_manifest.json"
DEFAULT_ANALYSIS = ROOT / "reports" / "goal02_8_reference_match" / "goal02_reference_match.json"
DEFAULT_SLUG = "goal02_chorus_reaper_v01"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(root: Path, value: str | None) -> Path:
    if not value:
        raise ValueError("empty path")
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def wav_duration_seconds(path: Path) -> float:
    sample_rate, data = wavfile.read(str(path), mmap=True)
    return float(data.shape[0]) / float(sample_rate)


def determine_window(root: Path, manifest: dict[str, Any], analysis: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    target_path = resolve_path(root, manifest["target"]["path"])
    mode = args.window_mode
    start = args.window_start_seconds
    duration = args.window_duration_seconds
    if start is not None or duration is not None:
        if start is None or duration is None:
            raise ValueError("--window-start-seconds and --window-duration-seconds must be provided together")
        mode = "custom"
    elif mode == "full-song":
        start = 0.0
        duration = wav_duration_seconds(target_path)
    else:
        start = float(analysis["target"]["analyzed_start_seconds"])
        duration = float(analysis["target"]["analyzed_duration_seconds"])
    if duration <= 0.0:
        raise ValueError(f"invalid render duration: {duration}")
    tag = args.window_tag
    if not tag:
        tag = "FULL_SONG" if mode == "full-song" else ("CUSTOM" if mode == "custom" else "20s")
    return {
        "mode": mode,
        "start_seconds": float(start),
        "duration_seconds": float(duration),
        "end_seconds": float(start) + float(duration),
        "tag": tag,
        "label": "full-song draft" if mode == "full-song" else ("custom window" if mode == "custom" else "20-second chorus window"),
        "target_path": str(target_path),
    }


def lua_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def lua_literal(value: str | Path) -> str:
    text = str(value).replace("\\", "/")
    if "]]" in text:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "[[" + text + "]]"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def classify_stem(
    path: Path,
    *,
    bass_gain_offset_db: float = 0.0,
    drum_gain_offset_db: float = 0.0,
    vocal_gain_offset_db: float = 0.0,
) -> tuple[str, str, float, float]:
    name = path.name.lower()
    if name.startswith("1 "):
        return "01 FX", "MUSIC BUS", -6.0, 0.0
    if name.startswith("2 "):
        return "02 SYNTH", "MUSIC BUS", -1.0, 0.0
    if name.startswith("3 "):
        return "03 KEYBOARD", "MUSIC BUS", -5.0, 0.0
    if name.startswith("4 "):
        return "04 GUITAR", "MUSIC BUS", -3.0, 0.0
    if name.startswith("5 "):
        return "05 BASS", "808/BASS BUS", 6.5 + bass_gain_offset_db, 0.0
    if name.startswith("6 "):
        return "06 DRUMS", "DRUM BUS", 3.5 + drum_gain_offset_db, 0.0
    if name.startswith("7 "):
        return "08 MALE_NONHOOK_CENTER", "VOX BUS", 4.5 + vocal_gain_offset_db, 0.0
    if name.startswith("8 "):
        return "09 VOCAL_SUPPORT_SIDE", "VOX BUS", -7.0, 0.22
    return path.stem.upper(), "MUSIC BUS", -3.0, 0.0


def build_lua(
    *,
    root: Path,
    manifest: dict[str, Any],
    analysis: dict[str, Any],
    slug: str,
    reaper_dir: Path,
    render_dir: Path,
    report_dir: Path,
    window: dict[str, Any],
    bass_gain_offset_db: float = 0.0,
    drum_gain_offset_db: float = 0.0,
    vocal_gain_offset_db: float = 0.0,
) -> tuple[Path, Path, Path, Path, Path]:
    target_start = float(window["start_seconds"])
    duration = float(window["duration_seconds"])
    window_tag = str(window["tag"])
    window_label = str(window["label"])
    target_path = resolve_path(root, manifest["target"]["path"])
    stem_dir = resolve_path(root, manifest["target_stems"]["path"])
    rpp = reaper_dir / f"{slug}.rpp"
    build_lua_path = reaper_dir / f"build_{slug}.lua"
    run_build_lua_path = reaper_dir / f"run_build_{slug}.lua"
    render_lua_path = reaper_dir / f"prepare_render_{slug}.lua"
    run_render_lua_path = reaper_dir / f"run_prepare_render_{slug}.lua"
    trace_path = report_dir / "actual_reaper_plugin_trace.json"
    log_path = report_dir / "reaper_build.log"
    render_pattern = f"{slug}_REAPERPRINT_24-48"

    primary_ids = [item["id"] for item in analysis.get("primary_references", analysis.get("closest_references", [])[:3])[:3]]
    references_by_id = {row["id"]: row for row in analysis["references"]}
    manifest_refs_by_id = {row["id"]: row for row in manifest["references"]}
    ref_entries = []
    for ref_id in primary_ids:
        ref_analysis = references_by_id[ref_id]
        ref_manifest = manifest_refs_by_id[ref_id]
        ref_entries.append(
            {
                "id": ref_id,
                "path": resolve_path(root, ref_manifest["path"]),
                "start": float(ref_analysis["analyzed_start_seconds"]),
            }
        )

    stem_entries = []
    for stem_path in sorted(stem_dir.glob("*.wav")):
        if stem_path.name.startswith("0 "):
            continue
        track_name, bus_name, gain_db, pan = classify_stem(
            stem_path,
            bass_gain_offset_db=bass_gain_offset_db,
            drum_gain_offset_db=drum_gain_offset_db,
            vocal_gain_offset_db=vocal_gain_offset_db,
        )
        stem_entries.append(
            {
                "path": stem_path,
                "track": track_name,
                "bus": bus_name,
                "gain_db": gain_db,
                "pan": pan,
            }
        )

    stem_lua = []
    for item in stem_entries:
        stem_lua.append(
            "add_stem("
            f"{lua_literal(item['track'])}, "
            f"{lua_literal(item['path'])}, "
            f"{lua_literal(item['bus'])}, "
            f"{item['gain_db']:.3f}, "
            f"{item['pan']:.3f})"
        )

    ref_lua = []
    for item in ref_entries:
        label = f"REF {item['id'].upper()} muted - not in master"
        ref_lua.append(
            "add_reference("
            f"{lua_literal(label)}, "
            f"{lua_literal(item['path'])}, "
            f"{item['start']:.6f})"
        )

    lua = f'''
local slug = {lua_literal(slug)}
local rpp = {lua_literal(rpp)}
local trace_path = {lua_literal(trace_path)}
local log_path = {lua_literal(log_path)}
local render_dir = {lua_literal(render_dir)}
local report_dir = {lua_literal(report_dir)}
local target_path = {lua_literal(target_path)}
local target_start = {target_start:.6f}
local duration = {duration:.6f}
local window_tag = {lua_literal(window_tag)}
local window_label = {lua_literal(window_label)}
local render_pattern = {lua_literal(render_pattern)}
local bass_gain_offset_db = {bass_gain_offset_db:.3f}
local drum_gain_offset_db = {drum_gain_offset_db:.3f}
local vocal_gain_offset_db = {vocal_gain_offset_db:.3f}

local rows = {{}}
local tracks = {{}}
local buses = {{}}

local function lin(db) return 10 ^ ((db or 0) / 20) end
local function esc(s)
  s = tostring(s or "")
  return s:gsub("\\\\", "\\\\\\\\"):gsub('"', '\\\\"'):gsub("\\n", "\\\\n")
end
local function ensure_dir(path)
  if reaper.RecursiveCreateDirectory then
    reaper.RecursiveCreateDirectory(path, 0)
  else
    os.execute("mkdir -p " .. string.format("%q", path))
  end
end
local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%F %T"), " ", tostring(message), "\\n")
    f:close()
  end
end
local function add_row(track, stage, status, plugin, fx_index, policy, reason)
  rows[#rows + 1] = {{
    track = track or "",
    stage = stage or "",
    status = status or "",
    plugin = plugin or "",
    fx_index = fx_index or -1,
    parameter_write_policy = policy or "no_parameter_write",
    reason = reason or ""
  }}
  log((track or "") .. " | " .. (stage or "") .. " | " .. (status or "") .. " | " .. (plugin or ""))
end
local function write_trace()
  local f = assert(io.open(trace_path, "w"))
  f:write('{{\\n')
  f:write('  "schema": "goal02-actual-reaper-plugin-trace-v1",\\n')
  f:write('  "slug": "' .. esc(slug) .. '",\\n')
  f:write('  "claim_policy": "actual REAPER runtime trace; no listening claims",\\n')
  f:write('  "required_main_track": "08 MALE_NONHOOK_CENTER",\\n')
  f:write(string.format('  "window": {{"label": "%s", "tag": "%s", "start_seconds": %.6f, "duration_seconds": %.6f}},\\n', esc(window_label), esc(window_tag), target_start, duration))
  f:write(string.format('  "revision_profile": {{"bass_gain_offset_db": %.3f, "drum_gain_offset_db": %.3f, "vocal_gain_offset_db": %.3f}},\\n', bass_gain_offset_db, drum_gain_offset_db, vocal_gain_offset_db))
  f:write('  "rows": [\\n')
  for i, row in ipairs(rows) do
    f:write(string.format(
      '    {{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"parameter_write_policy":"%s","reason":"%s"}}%s\\n',
      esc(row.track), esc(row.stage), esc(row.status), esc(row.plugin), row.fx_index or -1,
      esc(row.parameter_write_policy), esc(row.reason), i < #rows and "," or ""
    ))
  end
  f:write('  ]\\n}}\\n')
  f:close()
end
local function make_track(name, gain_db, pan, muted, master_send)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(gain_db or 0))
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", muted and 1 or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", master_send and 1 or 0)
  tracks[name] = tr
  add_row(
    name,
    "track config",
    "loaded",
    string.format("gain_db=%.3f pan=%.3f muted=%s master_send=%s", gain_db or 0, pan or 0, tostring(muted and true or false), tostring(master_send and true or false)),
    -1,
    "no_parameter_write",
    "track creation routing state"
  )
  return tr
end
local function insert_slice(track, label, path, start_offset)
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then
    add_row(label, "insert media", "missing_source", path, -1, "no_parameter_write", "source file missing or unreadable")
    return
  end
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0.0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", duration)
  reaper.SetMediaItemTakeInfo_Value(take, "D_STARTOFFS", start_offset or 0.0)
  add_row(label, "insert media slice", "loaded", path, -1, "no_parameter_write", window_label .. " source-offset slice")
end
local function send_to(src, src_name, dst, dst_name, gain_db, reason)
  if not src or not dst then
    add_row("routing", "send", "missing_track", tostring(src_name) .. " -> " .. tostring(dst_name), -1, "no_parameter_write", reason or "")
    return
  end
  local s = reaper.CreateTrackSend(src, dst)
  reaper.SetTrackSendInfo_Value(src, 0, s, "D_VOL", lin(gain_db or 0))
  add_row("routing", "send", "loaded", tostring(src_name) .. " -> " .. tostring(dst_name), 0, "no_parameter_write", reason or "")
end
local function add_fx(track, label, stage, candidates, policy, required)
  for _, name in ipairs(candidates) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx and idx >= 0 then
      local ok, actual = reaper.TrackFX_GetFXName(track, idx, "")
      if not ok or actual == "" then actual = name end
      add_row(label, stage, "loaded", actual, idx, policy, "candidate=" .. name)
      return idx
    end
  end
  add_row(label, stage, "missing_all_candidates", table.concat(candidates, " | "), -1, policy, required and "required" or "optional")
  if required then error("missing required FX: " .. tostring(candidates[1])) end
  return -1
end
local function bus(name, muted, master_send)
  local tr = make_track(name, 0, 0, muted, master_send)
  buses[name] = tr
  return tr
end
local function add_reference(name, path, start_offset)
  local tr = make_track(name, -99, 0, true, false)
  insert_slice(tr, name, path, start_offset)
  send_to(tr, name, buses["REF BUS"], "REF BUS", 0, "reference comparison only; muted bus")
  return tr
end
local function add_stem(name, path, bus_name, gain_db, pan)
  local tr = make_track(name, gain_db, pan, false, false)
  insert_slice(tr, name, path, target_start)
  send_to(tr, name, buses[bus_name], bus_name, 0, "active stem to role bus")
  return tr
end

ensure_dir({lua_literal(reaper_dir)})
ensure_dir(render_dir)
ensure_dir(report_dir)
os.remove(trace_path)
os.remove(log_path)

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
local ok, err = xpcall(function()
  reaper.Main_OnCommand(40023, 0)

  bus("REF BUS", true, false)
  bus("VOX BUS", false, false)
  bus("DRUM BUS", false, false)
  bus("808/BASS BUS", false, false)
  bus("MUSIC BUS", false, false)
  bus("MIX BUS", false, false)
  bus("PREMASTER", false, false)
  bus("PRINT MASTER", false, true)

  local full_mix = make_track("SOURCE full mix reference muted - not in master", -99, 0, true, false)
  insert_slice(full_mix, "SOURCE full mix reference muted - not in master", target_path, target_start)
  send_to(full_mix, "SOURCE full mix reference muted - not in master", buses["REF BUS"], "REF BUS", 0, "raw full mix/reference muted and not in active master path")

  {chr(10).join(ref_lua)}
  {chr(10).join(stem_lua)}

  send_to(buses["VOX BUS"], "VOX BUS", buses["MIX BUS"], "MIX BUS", 0, "role bus to mix bus")
  send_to(buses["DRUM BUS"], "DRUM BUS", buses["MIX BUS"], "MIX BUS", 0, "role bus to mix bus")
  send_to(buses["808/BASS BUS"], "808/BASS BUS", buses["MIX BUS"], "MIX BUS", 0, "role bus to mix bus")
  send_to(buses["MUSIC BUS"], "MUSIC BUS", buses["MIX BUS"], "MIX BUS", 0, "role bus to mix bus")
  send_to(buses["MIX BUS"], "MIX BUS", buses["PREMASTER"], "PREMASTER", 0, "mix bus to premaster")
  send_to(buses["PREMASTER"], "PREMASTER", buses["PRINT MASTER"], "PRINT MASTER", 0, "premaster to print master")

  add_fx(tracks["01 FX"], "01 FX", "music/FX cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(tracks["02 SYNTH"], "02 SYNTH", "music vocal-pocket dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["03 KEYBOARD"], "03 KEYBOARD", "keyboard phase-safe EQ", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(tracks["04 GUITAR"], "04 GUITAR", "guitar cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(tracks["05 BASS"], "05 BASS", "808 EQ", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(tracks["05 BASS"], "05 BASS", "808 harmonic density", {{"VST3: IVGI2", "VST3: Decapitator", "VST: ReaComp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["05 BASS"], "05 BASS", "808 clip guard", {{"VST3: FreeClip", "VST: ReaLimit (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["06 DRUMS"], "06 DRUMS", "drum cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(tracks["06 DRUMS"], "06 DRUMS", "drum transient glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["06 DRUMS"], "06 DRUMS", "hat/fizz guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["06 DRUMS"], "06 DRUMS", "drum clip guard", {{"VST3: FreeClip", "VST: ReaLimit (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)

  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "Codex Vocal AI Artifact Split Tamer FIRST SLOT", {{"JS: Codex Vocal AI Artifact Split Tamer"}}, "repo_jsfx_write_allowed_when_installed", true)
  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "vocal de-mud dynamic EQ", {{"JS: Vocal Clarity De-Mud Dynamic EQ", "JS: Codex vocal_demud_dynamic_eq", "VST: ReaEQ (Cockos)"}}, "repo_jsfx_write_allowed_when_installed_or_verified_fallback", false)
  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "vocal surgical de-ess/dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "light vocal leveling", {{"VST3: UADx LA-2A Tube Compressor", "VST: ReaComp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "vocal peak catch", {{"VST3: UADx 1176 FET Compressor", "VST: ReaComp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "vocal air guard", {{"JS: Vocal Clarity Air Guard", "JS: Codex vocal_air_guard"}}, "repo_jsfx_write_allowed_when_installed", false)
  add_fx(tracks["08 MALE_NONHOOK_CENTER"], "08 MALE_NONHOOK_CENTER", "vocal output guard", {{"JS: Vocal Clarity Output Guard", "JS: Codex vocal_output_guard", "VST: ReaLimit (Cockos)"}}, "repo_jsfx_write_allowed_when_installed_or_verified_fallback", false)

  add_fx(tracks["09 VOCAL_SUPPORT_SIDE"], "09 VOCAL_SUPPORT_SIDE", "support vocal artifact guard", {{"JS: Codex Vocal AI Artifact Split Tamer"}}, "repo_jsfx_write_allowed_when_installed", false)
  add_fx(tracks["09 VOCAL_SUPPORT_SIDE"], "09 VOCAL_SUPPORT_SIDE", "support vocal cleanup", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(tracks["09 VOCAL_SUPPORT_SIDE"], "09 VOCAL_SUPPORT_SIDE", "support vocal width", {{"VST3: Vocal Doubler", "VST: ReaDelay (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)

  add_fx(buses["REF BUS"], "REF BUS", "reference metering", {{"VST3: mvMeter2", "VST3: ClearMaster Audit"}}, "insert_only_external_or_unverified_no_parameter_write", false)
  add_fx(buses["VOX BUS"], "VOX BUS", "vocal bus dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["VOX BUS"], "VOX BUS", "vocal bus output guard", {{"JS: Vocal Clarity Output Guard", "JS: Codex vocal_output_guard", "VST: ReaLimit (Cockos)"}}, "repo_jsfx_write_allowed_when_installed_or_verified_fallback", false)
  add_fx(buses["DRUM BUS"], "DRUM BUS", "drum bus clip", {{"VST3: FreeClip", "VST: ReaLimit (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["808/BASS BUS"], "808/BASS BUS", "mono low/808 guard", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(buses["MUSIC BUS"], "MUSIC BUS", "music bus vocal pocket", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["MUSIC BUS"], "MUSIC BUS", "music bus imager after mono check", {{"VST3: Ozone Imager 2", "VST: ReaEQ (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["MIX BUS"], "MIX BUS", "mix bus cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(buses["MIX BUS"], "MIX BUS", "mix bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["PREMASTER"], "PREMASTER", "premaster EQ", {{"VST3: Ozone 12 Equalizer", "VST: ReaEQ (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["PREMASTER"], "PREMASTER", "premaster glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "JS: Codex V20 Master Glue", "VST: ReaComp (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["PREMASTER"], "PREMASTER", "premaster clip", {{"VST3: FreeClip", "VST: ReaLimit (Cockos)"}}, "insert_only_external_or_verified_fallback_no_parameter_write", false)
  add_fx(buses["PREMASTER"], "PREMASTER", "premaster limiter", {{"VST: ReaLimit (Cockos)"}}, "verified_cockos_mapping_required", false)
  add_fx(buses["PRINT MASTER"], "PRINT MASTER", "print master audit", {{"VST3: mvMeter2", "VST3: ClearMaster Audit"}}, "insert_only_external_or_unverified_no_parameter_write", false)
  add_fx(buses["PRINT MASTER"], "PRINT MASTER", "print output guard", {{"JS: Vocal Clarity Output Guard", "JS: Codex vocal_output_guard", "VST: ReaLimit (Cockos)"}}, "repo_jsfx_write_allowed_when_installed_or_verified_fallback", false)

  reaper.AddProjectMarker2(0, true, 0.0, duration, string.upper(slug) .. "_" .. window_tag .. "_REAPER", -1, 0)
  reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", duration, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", render_pattern, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)
  reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "GOAL 02 " .. window_label .. " REAPER runtime candidate. Active path uses stems only; SOURCE full mix and references are muted on REF BUS and not in master path. First lead-vocal FX must be JS: Codex Vocal AI Artifact Split Tamer. No listening claims. Revision profile: bass offset " .. tostring(bass_gain_offset_db) .. " dB, drum offset " .. tostring(drum_gain_offset_db) .. " dB, vocal offset " .. tostring(vocal_gain_offset_db) .. " dB.", true)
  reaper.Main_SaveProjectEx(0, rpp, 0)
end, debug.traceback)
reaper.PreventUIRefresh(-1)
reaper.UpdateArrange()
if ok then
  add_row("runtime", "build wrapper", "loaded", rpp, -1, "no_parameter_write", "wrapper ok")
else
  add_row("runtime", "build wrapper", "error", tostring(err), -1, "no_parameter_write", "wrapper failed")
end
write_trace()
reaper.Undo_EndBlock("Build Goal 02 chorus REAPER runtime candidate", -1)
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    reaper_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    build_lua_path.write_text(lua, encoding="utf-8")
    run_build_lua_path.write_text(f"dofile([[{lua_path(build_lua_path)}]])\n", encoding="utf-8")
    render_lua_path.write_text(
        f'''local rpp = [[{lua_path(rpp)}]]
local render_dir = [[{lua_path(render_dir)}]]
local render_pattern = [[{render_pattern}]]
reaper.Main_openProject(rpp)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", render_pattern, true)
reaper.Main_SaveProjectEx(0, rpp, 0)
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
''',
        encoding="utf-8",
    )
    run_render_lua_path.write_text(f"dofile([[{lua_path(render_lua_path)}]])\n", encoding="utf-8")
    return build_lua_path, run_build_lua_path, render_lua_path, run_render_lua_path, rpp


def run_command(cmd: list[str], timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return {
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "timeout": True,
        }


def validate_trace(trace_path: Path) -> dict[str, Any]:
    cmd = [
        "python3",
        str(ROOT / "tools" / "validate_reaper_vocal_chain_gate.py"),
        "--trace",
        str(trace_path),
        "--main-track",
        "08 MALE_NONHOOK_CENTER",
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"passed": False, "errors": ["validator_output_not_json"], "stdout": result.stdout}
    payload["returncode"] = result.returncode
    return payload


def make_safe_streaming_master(data: Any) -> Any:
    return limit_true_peak_estimate(limit_peak(data, -1.2), -1.0)


def make_loud_reference_master(data: Any, sample_rate: int) -> Any:
    mastered = simple_compressor(
        data,
        sample_rate,
        threshold_db=-18.0,
        ratio=1.8,
        attack_ms=8.0,
        release_ms=90.0,
        makeup_db=1.0,
    )
    mastered = soft_clip(mastered, 1.8)
    gain_db = max(-3.0, min(8.0, -10.0 - linear_to_db(rms(mastered))))
    mastered = db_gain(mastered, gain_db)
    mastered = soft_clip(mastered, 1.35)
    return limit_true_peak_estimate(limit_peak(mastered, -1.2), -1.0)


def render_ab_package(
    *,
    root: Path,
    manifest: dict[str, Any],
    analysis: dict[str, Any],
    render_path: Path,
    render_dir: Path,
    report_dir: Path,
    slug: str,
    window: dict[str, Any],
) -> dict[str, Any]:
    target_start = float(window["start_seconds"])
    duration = float(window["duration_seconds"])
    window_tag = str(window["tag"])
    target_path = resolve_path(root, manifest["target"]["path"])
    sample_rate, current = read_wav_slice(target_path, target_start, duration)
    render_sr, reaper_print = read_wav_slice(render_path, 0.0, duration)
    if render_sr != sample_rate:
        raise RuntimeError(f"sample rate mismatch: target {sample_rate}, render {render_sr}")
    frames = current.shape[0]
    raw_reaper_print = pad_or_trim(reaper_print, frames)
    current = limit_true_peak_estimate(limit_peak(current, -1.2), -1.0)
    safe_reaper_print = make_safe_streaming_master(raw_reaper_print)
    loud_reaper_master = make_loud_reference_master(raw_reaper_print, sample_rate)
    loud_rms_db = linear_to_db(rms(loud_reaper_master))

    current_out = render_dir / f"{slug}_CURRENT_TARGET_{window_tag}.wav"
    safe_out = render_dir / f"{slug}_REAPERPRINT_SAFE_STREAMING_{window_tag}.wav"
    legacy_safe_out = render_dir / f"{slug}_REAPERPRINT_GUARDED_{window_tag}.wav"
    loud_out = render_dir / f"{slug}_REAPERPRINT_LOUD_REFERENCE_{window_tag}.wav"
    write_float_wav(current_out, sample_rate, current)
    write_float_wav(safe_out, sample_rate, safe_reaper_print)
    write_float_wav(legacy_safe_out, sample_rate, safe_reaper_print)
    write_float_wav(loud_out, sample_rate, loud_reaper_master)

    rows = [
        metrics("current_target", current, sample_rate, current_out),
        metrics("reaper_print_safe_streaming", safe_reaper_print, sample_rate, safe_out),
        metrics("reaper_print_loud_reference", loud_reaper_master, sample_rate, loud_out),
    ]
    files = {
        "current_target_20s": str(current_out),
        "current_target_window": str(current_out),
        "reaper_print_safe_streaming_20s": str(safe_out),
        "reaper_print_safe_streaming_window": str(safe_out),
        "reaper_print_guarded_20s": str(legacy_safe_out),
        "reaper_print_guarded_window": str(legacy_safe_out),
        "reaper_print_loud_reference_20s": str(loud_out),
        "reaper_print_loud_reference_window": str(loud_out),
        "raw_reaper_render": str(render_path),
    }
    ab_items = [current, loud_reaper_master]
    primary_ids = [item["id"] for item in analysis.get("primary_references", analysis.get("closest_references", [])[:3])[:3]]
    references_by_id = {row["id"]: row for row in analysis["references"]}
    manifest_refs_by_id = {row["id"]: row for row in manifest["references"]}
    for ref_id in primary_ids:
        ref_analysis = references_by_id[ref_id]
        ref_manifest = manifest_refs_by_id[ref_id]
        ref_path = resolve_path(root, ref_manifest["path"])
        ref_sr, ref_audio = read_wav_slice(ref_path, float(ref_analysis["analyzed_start_seconds"]), duration)
        if ref_sr != sample_rate:
            raise RuntimeError(f"reference sample rate mismatch for {ref_path}: {ref_sr} != {sample_rate}")
        ref_audio = pad_or_trim(ref_audio, frames)
        ref_matched = limit_true_peak_estimate(limit_peak(rms_match_to(ref_audio, loud_rms_db, max_gain_db=18.0), -1.2), -1.0)
        ref_out = render_dir / f"{slug}_{ref_id.upper()}_RMS_MATCHED_TO_LOUD_MASTER_{window_tag}.wav"
        write_float_wav(ref_out, sample_rate, ref_matched)
        files[f"{ref_id}_rms_matched_20s"] = str(ref_out)
        files[f"{ref_id}_rms_matched_window"] = str(ref_out)
        rows.append(metrics(f"{ref_id}_matched", ref_matched, sample_rate, ref_out))
        ab_items.extend([ref_matched, loud_reaper_master])

    if window_tag == "20s":
        ab_path = render_dir / f"{slug}_AB_CURRENT_LOUDMASTER_PRIMARY_REFS.wav"
    else:
        ab_path = render_dir / f"{slug}_AB_CURRENT_LOUDMASTER_PRIMARY_REFS_{window_tag}.wav"
    ab_audio = limit_true_peak_estimate(limit_peak(concatenate_with_silence(ab_items, sample_rate), -1.0), -1.0)
    write_float_wav(ab_path, sample_rate, ab_audio)
    files["ab_current_loudmaster_primary_refs"] = str(ab_path)
    files["ab_current_loudmaster_primary_refs_window"] = str(ab_path)
    rows.append(metrics("ab_current_loudmaster_primary_refs", ab_audio, sample_rate, ab_path))

    metrics_csv = report_dir / f"{slug}_metrics.csv"
    write_csv(metrics_csv, rows)
    return {"files": files, "metrics": rows, "metrics_csv": str(metrics_csv)}


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# GOAL 02 Chorus REAPER Runtime Report: {summary.get('slug', 'unknown')}",
        "",
        f"- Created UTC: `{summary['created_at']}`",
        f"- Status: `{summary['status']}`",
        "- Claim policy: `REAPER runtime evidence only; no listening claims; user A/B still required`",
        "",
        "## Files",
        "",
    ]
    for key, value in summary.get("files", {}).items():
        lines.append(f"- {key}: `{value}`")
    if summary.get("revision_profile"):
        lines.extend(["", "## Revision Profile", ""])
        for key, value in summary["revision_profile"].items():
            lines.append(f"- {key}: `{value}`")
    if summary.get("window"):
        lines.extend(["", "## Window", ""])
        for key, value in summary["window"].items():
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Runtime", ""])
    for key in ("build_result", "prepare_render_result", "render_result"):
        result = summary.get(key)
        if result:
            lines.append(f"- {key}: returncode `{result.get('returncode')}`, timeout `{result.get('timeout')}`")
    trace_validation = summary.get("trace_validation")
    if trace_validation:
        lines.append(f"- vocal chain gate passed: `{trace_validation.get('passed')}`")
        if trace_validation.get("errors"):
            lines.append(f"- vocal chain gate errors: `{trace_validation.get('errors')}`")
    if summary.get("metrics"):
        lines.extend(
            [
                "",
                "## Metrics",
                "",
                "| item | rms dBFS | sample peak | true peak est | crest | corr | low 20-120 | high 2.5-16k |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in summary["metrics"]:
            if row["name"] not in {"current_target", "reaper_print_safe_streaming", "reaper_print_loud_reference", "ref_06_matched", "ref_07_matched", "ref_03_matched"}:
                continue
            lines.append(
                f"| `{row['name']}` | `{row['rms_dbfs']}` | `{row['sample_peak_dbfs']}` | `{row['true_peak_estimate_4x_dbTP']}` | `{row['crest_factor_db']}` | `{row['stereo_correlation']}` | `{row['low_energy_ratio_20_120']}` | `{row['high_energy_ratio_2500_16000']}` |"
            )
    lines.extend(
        [
            "",
            "## Remaining Gates",
            "",
            "- FFmpeg loudnorm target evidence or REAPER mvMeter2/ClearMaster visual confirmation is still required for approval exports.",
            "- User loudness-matched A/B approval is still required before claiming completion.",
            "- If master-stage gain reduction exceeds 2 dB in REAPER, return to vocal/808/drum/music-bus balance.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_render(render_dir: Path, slug: str) -> Path | None:
    exact = render_dir / f"{slug}_REAPERPRINT_24-48.wav"
    if exact.exists():
        return exact
    matches = sorted(render_dir.glob(f"{slug}_REAPERPRINT_24-48*.wav"))
    return matches[-1] if matches else None


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    manifest = load_json(args.manifest)
    analysis = load_json(args.analysis)
    slug = args.slug
    window = determine_window(root, manifest, analysis, args)
    reaper_dir = root / "reaper" / slug
    render_dir = root / "renders" / slug
    report_dir = root / "reports" / slug
    trace_path = report_dir / "actual_reaper_plugin_trace.json"
    report_json = report_dir / f"{slug}_runtime_summary.json"
    report_md = report_dir / f"{slug}_runtime_report.md"
    scripts = build_lua(
        root=root,
        manifest=manifest,
        analysis=analysis,
        slug=slug,
        reaper_dir=reaper_dir,
        render_dir=render_dir,
        report_dir=report_dir,
        window=window,
        bass_gain_offset_db=args.bass_gain_offset_db,
        drum_gain_offset_db=args.drum_gain_offset_db,
        vocal_gain_offset_db=args.vocal_gain_offset_db,
    )
    build_lua_path, run_build_lua_path, render_lua_path, run_render_lua_path, rpp = scripts

    summary: dict[str, Any] = {
        "schema": "goal02-reaper-runtime-summary-v1",
        "created_at": now_utc(),
        "status": "REAPER_RUNTIME_SCRIPT_WRITTEN_NOT_RUN",
        "slug": slug,
        "window": window,
        "revision_profile": {
            "bass_gain_offset_db": args.bass_gain_offset_db,
            "drum_gain_offset_db": args.drum_gain_offset_db,
            "vocal_gain_offset_db": args.vocal_gain_offset_db,
        },
        "files": {
            "build_lua": str(build_lua_path),
            "run_build_lua": str(run_build_lua_path),
            "prepare_render_lua": str(render_lua_path),
            "run_prepare_render_lua": str(run_render_lua_path),
            "rpp": str(rpp),
            "actual_reaper_plugin_trace": str(trace_path),
        },
        "remaining_gates": [
            "actual REAPER render",
            "LUFS-I and certified true peak metering",
            "user loudness-matched A/B approval",
        ],
    }

    if args.no_run:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        write_report(report_md, summary)
        return summary

    if not REAPER_BIN.exists():
        summary["status"] = "BLOCKED_REAPER_EXECUTABLE_MISSING"
    else:
        build_result = run_command([str(REAPER_BIN), "-newinst", "-nosplash", str(run_build_lua_path)], args.build_timeout)
        summary["build_result"] = build_result
        if trace_path.exists():
            trace_validation = validate_trace(trace_path)
            summary["trace_validation"] = trace_validation
            if trace_validation.get("passed"):
                summary["status"] = "REAPER_RUNTIME_TRACE_PASSED_RENDER_PENDING"
            else:
                summary["status"] = "REAPER_RUNTIME_TRACE_GATE_FAILED"
        else:
            summary["status"] = "REAPER_RUNTIME_BUILD_NO_TRACE"

        if not args.skip_render and rpp.exists() and summary["status"] != "REAPER_RUNTIME_TRACE_GATE_FAILED":
            prepare_result = run_command([str(REAPER_BIN), "-newinst", "-nosplash", str(run_render_lua_path)], args.build_timeout)
            summary["prepare_render_result"] = prepare_result
            render_result = run_command([str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(rpp)], args.render_timeout)
            summary["render_result"] = render_result
            render_path = find_render(render_dir, slug)
            if render_path and render_path.exists():
                summary["files"]["raw_reaper_render"] = str(render_path)
                ab = render_ab_package(
                    root=root,
                    manifest=manifest,
                    analysis=analysis,
                    render_path=render_path,
                    render_dir=render_dir,
                    report_dir=report_dir,
                    slug=slug,
                    window=window,
                )
                summary["files"].update(ab["files"])
                summary["metrics"] = ab["metrics"]
                summary["files"]["metrics_csv"] = ab["metrics_csv"]
                if window.get("mode") == "full-song":
                    summary["status"] = "REAPER_FULL_SONG_DRAFT_RENDERED_QC_READY_USER_AB_PENDING"
                else:
                    summary["status"] = "REAPER_RUNTIME_RENDERED_QC_READY_USER_AB_PENDING"
                summary["remaining_gates"] = [
                    "LUFS-I and certified true peak metering",
                    "user loudness-matched A/B approval",
                ]
            else:
                summary["status"] = "REAPER_RUNTIME_TRACE_PASSED_RENDER_MISSING"

    report_dir.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_md, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and render the GOAL 02 REAPER runtime candidate.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--window-mode", choices=("analysis", "full-song"), default="analysis", help="render the measured analysis window or the full target song")
    parser.add_argument("--window-start-seconds", type=float, default=None, help="custom render start in seconds; requires --window-duration-seconds")
    parser.add_argument("--window-duration-seconds", type=float, default=None, help="custom render duration in seconds; requires --window-start-seconds")
    parser.add_argument("--window-tag", default=None, help="filename/marker tag for custom or full-song windows")
    parser.add_argument("--no-run", action="store_true", help="write Lua scripts and reports without launching REAPER")
    parser.add_argument("--skip-render", action="store_true", help="build the REAPER project and trace but skip renderproject")
    parser.add_argument("--bass-gain-offset-db", type=float, default=0.0, help="additional gain in dB applied to stems classified as 808/BASS")
    parser.add_argument("--drum-gain-offset-db", type=float, default=0.0, help="additional gain in dB applied to stems classified as DRUM")
    parser.add_argument("--vocal-gain-offset-db", type=float, default=0.0, help="additional gain in dB applied to the center lead vocal stem")
    parser.add_argument("--build-timeout", type=int, default=180)
    parser.add_argument("--render-timeout", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    summary = run(parse_args())
    print(json.dumps({"status": summary["status"], "files": summary.get("files", {})}, indent=2, ensure_ascii=False))
    return 0 if not summary["status"].startswith("BLOCKED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
