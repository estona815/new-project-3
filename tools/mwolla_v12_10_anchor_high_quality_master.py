#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V11_SCRIPT = ROOT / "tools" / "mwolla_v11_constant_vocal_light_dyn_eq_master.py"
SLUG = "mwolla_v12_10_anchor_high_quality_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")
WORK_TRACES = ROOT / "work" / "traces"


spec = importlib.util.spec_from_file_location("mwolla_v11_constant_vocal_light_dyn_eq_master", V11_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v11 script: {V11_SCRIPT}")
v11 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v11)
base = v11.base
v2 = v11.v2


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def lua_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def configure_base() -> None:
    v11.configure_base()
    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v12_10_ANCHOR_HIGH_QUALITY_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v12_10_anchor_high_quality_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v12_10_anchor_high_quality_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v12_10_anchor_high_quality_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v12_10_anchor_high_quality_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v12_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v12_10_ANCHOR_HIGH_QUALITY_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v12_10_ANCHOR_HIGH_QUALITY_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v12_VOCAL_SOLO_10_anchor_layer_checked.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v12_AB_original_to_10_anchor_high_quality_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v12_10_ANCHOR_HIGH_QUALITY_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -7.0
    base.FEMALE_LAYER_FILENAME = "11_vocal_layer_support_wide_tucked.wav"
    base.FEMALE_TRACK_NAME = "11 VOCAL_LAYER_SUPPORT"
    base.FEMALE_REPORT_LINE = (
        "- Use `10 Vocals.wav` as imported track 11 / `11 VOCAL_LAYER_SUPPORT`, "
        "kept as a tucked support-width layer rather than a center lead replacement."
    )
    base.REPORT_FILENAME = "mwolla_v12_10_anchor_high_quality_master_report.md"
    base.REPORT_TITLE = "Mwolla v12 10-Anchor High Quality Master Report"
    base.PROJECT_NOTES = (
        "mwolla v12 10-anchor high quality master: 9 Vocals.wav maps to imported track 10 / "
        "10 MAIN_VOCAL_CENTER. 10 Vocals.wav maps to imported track 11 / 11 VOCAL_LAYER_SUPPORT. "
        "SOURCE full mix reference muted - not in master is muted with master send disabled and no active sends. "
        "Active stems route to MAIN_VOCAL_BUS, LAYER_VOCAL_BUS, VOCAL_BUS, MUSIC_BUS, and PREMASTER BUS. "
        "Main vocal first FX slot is JS: Codex Vocal AI Artifact Split Tamer. External plugin parameter writes "
        "remain blocked unless calibrated."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v12_PHRASE_LEVELED_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v12_POST_FINAL_LEVEL_LOCK_24-48.wav"


def extract_source() -> dict[str, Path]:
    if not ZIP_SOURCE.exists():
        raise FileNotFoundError(ZIP_SOURCE)
    base.SOURCE.mkdir(parents=True, exist_ok=True)
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    for path in base.SOURCE.glob("*.wav"):
        path.unlink()

    copied: list[dict[str, Any]] = []
    with zipfile.ZipFile(ZIP_SOURCE) as archive:
        for member in archive.infolist():
            name = Path(member.filename)
            if member.is_dir() or "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            if not name.name.lower().endswith(".wav"):
                continue
            target = base.SOURCE / name.name
            with archive.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            copied.append({"zip_member": member.filename, "local_copy": rel(target), "bytes": target.stat().st_size})

    def stem(prefix: int) -> Path:
        matches = sorted(base.SOURCE.glob(f"{prefix} *.wav"))
        if not matches:
            raise FileNotFoundError(f"Missing stem prefix {prefix} in {base.SOURCE}")
        return matches[0]

    full_reference = stem(0)
    sr, ref, _ = base.read_wav(full_reference)
    silence = np.zeros_like(ref, dtype=np.float32)
    placeholder_paths: dict[str, Path] = {}
    for role in ("woodwinds", "brass", "percussion"):
        path = base.SOURCE / f"__missing_{role}_silence.wav"
        base.write_wav(path, sr, silence)
        placeholder_paths[role] = path

    paths = {
        "full_reference": full_reference,
        "woodwinds": placeholder_paths["woodwinds"],
        "brass": placeholder_paths["brass"],
        "fx": stem(1),
        "synth": stem(2),
        "strings": stem(3),
        "percussion": placeholder_paths["percussion"],
        "keyboard": stem(4),
        "guitar": stem(5),
        "bass": stem(6),
        "drums": stem(7),
        "backing_vocals": stem(8),
        "lead_vocal": stem(9),
        "female_vocal": stem(10),
    }
    source_selection = {
        "slug": SLUG,
        "zip_source": str(ZIP_SOURCE),
        "copied_files": copied,
        "role_assignment_basis": (
            "The zip uses 0-based filenames. Imported REAPER track 10 corresponds to `9 Vocals.wav` "
            "and is mapped to `10 MAIN_VOCAL_CENTER`; imported track 11 corresponds to `10 Vocals.wav` "
            "and is mapped to `11 VOCAL_LAYER_SUPPORT`."
        ),
        "full_reference": rel(paths["full_reference"]),
        "main_vocal_10_MAIN_VOCAL_CENTER": rel(paths["lead_vocal"]),
        "layer_vocal_11_VOCAL_LAYER_SUPPORT": rel(paths["female_vocal"]),
        "backing_vocals": rel(paths["backing_vocals"]),
        "music_roles": {key: rel(paths[key]) for key in ("fx", "synth", "strings", "keyboard", "guitar", "bass", "drums")},
        "generated_silent_harness_placeholders": {key: rel(path) for key, path in placeholder_paths.items()},
        "placeholder_policy": "Generated silent files are harness compatibility placeholders only and are not user source stems.",
        "source_full_mix_policy": "SOURCE full mix reference muted - not in master; muted, master-send disabled, and no active sends.",
    }
    write_json(base.REPORTS / "source_selection.json", source_selection)
    write_json(base.REPORTS / "source_inventory.json", source_selection)
    return paths


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    render_pattern = base.REAPER_PRINT.stem
    notes = base.PROJECT_NOTES
    build = f'''
local slug = "{SLUG}"
local rpp = [[{lua_path(base.RPP)}]]
local render_dir = [[{lua_path(base.RENDERS)}]]
local report_dir = [[{lua_path(base.REPORTS)}]]
local trace_path = [[{lua_path(base.TRACE_JSON)}]]
local log_path = [[{lua_path(base.REPORTS / "build_reaper.log")}]]
local duration = {duration:.9f}
local rows = {{}}

local function q(s) return string.format("%q", s) end
local function lin(db) return 10 ^ ((db or 0) / 20) end
local function esc(s)
  s = tostring(s or "")
  return s:gsub("\\\\", "\\\\\\\\"):gsub('"', '\\\\"'):gsub("\\n", "\\\\n")
end
local function log(s)
  local f = io.open(log_path, "a")
  if f then f:write(os.date("%F %T"), " ", tostring(s), "\\n"); f:close() end
end
local function plugin_parameter_policy(plugin)
  local lower = tostring(plugin or ""):lower()
  if lower:find("^js:%s*codex") then return true, "repo_jsfx_wet_write_allowed" end
  if lower:find("%(cockos%)") or lower:find("^vst:%s*rea") or lower:find("^vst3:%s*rea") then
    return true, "verified_cockos_wet_write_allowed"
  end
  return false, "insert_only_external_or_unverified_no_parameter_write"
end
local function add_row(track, stage, status, plugin, idx, wet, reason, policy)
  rows[#rows + 1] = string.format(
    '{{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":%s,"parameter_write_policy":"%s","reason":"%s"}}',
    esc(track), esc(stage), esc(status), esc(plugin), tonumber(idx or -1), wet and tostring(wet) or "null", esc(policy or "no_parameter_write"), esc(reason)
  )
  log(track .. " | " .. stage .. " | " .. status .. " | " .. tostring(plugin))
end
local function write_trace()
  local f = assert(io.open(trace_path, "w"))
  f:write('{{\\n  "slug": "' .. slug .. '",\\n  "source_full_mix_policy": "muted, master-send disabled, no active sends",\\n  "required_main_track": "10 MAIN_VOCAL_CENTER",\\n  "required_layer_track": "11 VOCAL_LAYER_SUPPORT",\\n  "rows": [\\n')
  for i,row in ipairs(rows) do f:write("    " .. row .. (i == #rows and "\\n" or ",\\n")) end
  f:write("  ]\\n}}\\n")
  f:close()
end
local function make_track(name, db, pan, muted, main_send)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(db or 0))
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", muted and 1 or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", main_send and 1 or 0)
  add_row(name, "track config", "loaded", string.format("gain_db=%.3f pan=%.3f muted=%s master_send=%s", db or 0, pan or 0, tostring(muted and true or false), tostring(main_send and true or false)), -1, nil, "track creation routing state", "no_parameter_write")
  return tr
end
local function insert_media_full(tr, label, path)
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then error("source failed: " .. path) end
  local item = reaper.AddMediaItemToTrack(tr)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", duration)
  reaper.SetMediaItemInfo_Value(item, "D_FADEINLEN", 0.004)
  reaper.SetMediaItemInfo_Value(item, "D_FADEOUTLEN", 0.008)
  add_row(label, "insert media", "loaded", path, -1, nil, "media item inserted at project start", "no_parameter_write")
  return item
end
local function add_fx_candidates(tr, label, stage, candidates, wet, reason, required)
  for _, name in ipairs(candidates) do
    local idx = reaper.TrackFX_AddByName(tr, name, false, -1)
    if idx and idx >= 0 then
      local may_write, policy = plugin_parameter_policy(name)
      local applied_wet = nil
      if wet and may_write and reaper.TrackFX_SetWetDryMix then
        pcall(reaper.TrackFX_SetWetDryMix, tr, idx, wet, 0, 0)
        applied_wet = wet
      elseif wet and not may_write then
        policy = policy .. "; requested_wet_not_written"
      end
      add_row(label, stage, "loaded", name, idx, applied_wet, reason, policy)
      return idx, name
    end
  end
  add_row(label, stage, "missing_all_candidates", table.concat(candidates, " | "), -1, nil, reason, "missing_no_parameter_write")
  if required then
    write_trace()
    error("required FX missing: " .. table.concat(candidates, " | "))
  end
  return -1, nil
end
local function route_to(src, dst, db, reason)
  reaper.SetMediaTrackInfo_Value(src, "B_MAINSEND", 0)
  local send = reaper.CreateTrackSend(src, dst)
  if send and send >= 0 then
    reaper.SetTrackSendInfo_Value(src, 0, send, "D_VOL", lin(db or 0))
    reaper.SetTrackSendInfo_Value(src, 0, send, "I_SENDMODE", 0)
    add_row("routing", "send", "created", reason or "track send", send, nil, "post-fader role-bus routing", "no_parameter_write")
  else
    add_row("routing", "send", "failed", reason or "track send", -1, nil, "REAPER did not create send", "no_parameter_write")
  end
  return send
end
local function route_sidechain(src, dst, db, reason)
  reaper.SetMediaTrackInfo_Value(dst, "I_NCHAN", 4)
  local send = reaper.CreateTrackSend(src, dst)
  if send and send >= 0 then
    reaper.SetTrackSendInfo_Value(src, 0, send, "D_VOL", lin(db or 0))
    reaper.SetTrackSendInfo_Value(src, 0, send, "I_SENDMODE", 0)
    reaper.SetTrackSendInfo_Value(src, 0, send, "I_SRCCHAN", 0)
    reaper.SetTrackSendInfo_Value(src, 0, send, "I_DSTCHAN", 2)
    add_row("routing", "sidechain send", "created", reason or "sidechain", send, nil, "source channels 1/2 into destination 3/4", "no_parameter_write")
  else
    add_row("routing", "sidechain send", "failed", reason or "sidechain", -1, nil, "REAPER did not create sidechain", "no_parameter_write")
  end
  return send
end
local function add_vocal_chain(tr, label, is_main)
  add_fx_candidates(tr, label, "first-slot developed Suno/AI vocal artifact rescue", {{"JS: Codex Vocal AI Artifact Split Tamer"}}, 1.0, "mandatory first slot; clean rescue before EQ/comp/limit", is_main)
  add_fx_candidates(tr, label, "noise floor cleanup", {{"JS: Codex Noise Floor Tamer"}}, 1.0, "reduce low-level vocal noise before dynamics", false)
  add_fx_candidates(tr, label, "vocal gate expander", {{"JS: Codex Vocal Gate Expander"}}, 0.72, "tuck gaps without phrase chopping", false)
  add_fx_candidates(tr, label, "corrective EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "HPF, low-mid cleanup, guarded clarity", false)
  add_fx_candidates(tr, label, "dynamic EQ guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.62, "mud, nasal, sibilance, and AI-like edge guard; external insert-only", false)
  add_fx_candidates(tr, label, "de-ess guard", {{"JS: De-esser", "VST3: TDR Nova (Tokyo Dawn Labs)"}}, 1.0, "sibilance control after dynamic EQ", false)
  add_fx_candidates(tr, label, "light compression", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, is_main and 0.52 or 0.28, "phrase stability; GR evidence not available in this trace", false)
  add_fx_candidates(tr, label, "output limiter guard", {{"VST: ReaLimit (Cockos)"}}, 1.0, "track peak guard, not loudness push", false)
end
local function add_music_chain(tr, label, stage, reason)
  add_fx_candidates(tr, label, stage, {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.78, reason, false)
end
local function add_simple_fx(tr, label, stage, names, wet, reason)
  add_fx_candidates(tr, label, stage, names, wet, reason, false)
end

os.execute("mkdir -p " .. q(render_dir))
os.execute("mkdir -p " .. q(report_dir))
os.remove(log_path)
os.remove(trace_path)
reaper.Main_OnCommand(40023, 0)

local ref = make_track("SOURCE full mix reference muted - not in master", -99.0, 0.0, true, false)
insert_media_full(ref, "SOURCE full mix reference muted - not in master", [[{lua_path(processed["full_reference"])}]])

local fx = make_track("01 FX", -4.6, 0.18, false, false)
insert_media_full(fx, "01 FX", [[{lua_path(processed["fx"])}]])
add_simple_fx(fx, "01 FX", "FX glare cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "filtered support, no master-bus fix")

local synth = make_track("02 SYNTH", -0.9, -0.08, false, false)
insert_media_full(synth, "02 SYNTH", [[{lua_path(processed["synth"])}]])
add_music_chain(synth, "02 SYNTH", "synth music pocket", "leave presence room for 10 MAIN_VOCAL_CENTER")

local strings = make_track("03 STRINGS", 0.0, 0.12, false, false)
insert_media_full(strings, "03 STRINGS", [[{lua_path(processed["strings"])}]])
add_simple_fx(strings, "03 STRINGS", "strings cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "retained music texture")

local keyboard = make_track("04 KEYBOARD", -1.4, 0.08, false, false)
insert_media_full(keyboard, "04 KEYBOARD", [[{lua_path(processed["keyboard"])}]])
add_music_chain(keyboard, "04 KEYBOARD", "keyboard resonance/pocket", "controlled midrange around the lead")

local guitar = make_track("05 GUITAR", -0.6, -0.12, false, false)
insert_media_full(guitar, "05 GUITAR", [[{lua_path(processed["guitar"])}]])
add_simple_fx(guitar, "05 GUITAR", "guitar cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "side texture without vocal masking")

local bass = make_track("06 BASS_OR_808", 0.2, 0.0, false, false)
insert_media_full(bass, "06 BASS_OR_808", [[{lua_path(processed["bass"])}]])
add_simple_fx(bass, "06 BASS_OR_808", "bass EQ/control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.88, "mono low-end body and peak control before premaster")

local drums = make_track("07 DRUMS", -0.8, 0.0, false, false)
insert_media_full(drums, "07 DRUMS", [[{lua_path(processed["drums"])}]])
add_simple_fx(drums, "07 DRUMS", "drum transient control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.86, "kick/snare/hat control before premaster")

local backing = make_track("08 BACKING_VOCALS_WIDE_TUCKED", -3.2, 0.0, false, false)
insert_media_full(backing, "08 BACKING_VOCALS_WIDE_TUCKED", [[{lua_path(processed["backing_vocals"])}]])
add_vocal_chain(backing, "08 BACKING_VOCALS_WIDE_TUCKED", false)

local main = make_track("10 MAIN_VOCAL_CENTER", 1.2, 0.0, false, false)
insert_media_full(main, "10 MAIN_VOCAL_CENTER", [[{lua_path(processed["lead_vocal"])}]])
add_vocal_chain(main, "10 MAIN_VOCAL_CENTER", true)

local layer = make_track("11 VOCAL_LAYER_SUPPORT", -2.8, 0.0, false, false)
insert_media_full(layer, "11 VOCAL_LAYER_SUPPORT", [[{lua_path(processed["female_vocal"])}]])
add_vocal_chain(layer, "11 VOCAL_LAYER_SUPPORT", false)

local vocal_reverb = make_track("VOCAL_REVERB_TUCKED", -2.4, 0.0, false, false)
insert_media_full(vocal_reverb, "VOCAL_REVERB_TUCKED", [[{lua_path(processed["vocal_reverb"])}]])
add_simple_fx(vocal_reverb, "VOCAL_REVERB_TUCKED", "dark reverb cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "tail stays behind lead")

local vocal_delay = make_track("VOCAL_DELAY_TUCKED", -2.6, 0.0, false, false)
insert_media_full(vocal_delay, "VOCAL_DELAY_TUCKED", [[{lua_path(processed["vocal_delay"])}]])
add_simple_fx(vocal_delay, "VOCAL_DELAY_TUCKED", "dark delay cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "delay stays tucked and filtered")

local main_bus = make_track("MAIN_VOCAL_BUS", 0.0, 0.0, false, false)
add_simple_fx(main_bus, "MAIN_VOCAL_BUS", "main vocal bus EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "main vocal bus static cleanup")
add_simple_fx(main_bus, "MAIN_VOCAL_BUS", "main vocal bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.30, "light group leveling; no hardcoded external params")

local layer_bus = make_track("LAYER_VOCAL_BUS", -1.0, 0.0, false, false)
add_simple_fx(layer_bus, "LAYER_VOCAL_BUS", "layer dynamic guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.68, "keep 11 support below and around main")

local vocal_bus = make_track("VOCAL_BUS", 0.0, 0.0, false, false)
add_simple_fx(vocal_bus, "VOCAL_BUS", "vocal bus dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.52, "vocal-group harshness guard")
add_simple_fx(vocal_bus, "VOCAL_BUS", "vocal bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.24, "light vocal group glue; GR trace unavailable")

local music_bus = make_track("MUSIC_BUS", 0.4, 0.0, false, false)
add_simple_fx(music_bus, "MUSIC_BUS", "music bus dynamic pocket", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.66, "instrument bed carved around 10 MAIN_VOCAL_CENTER")
add_simple_fx(music_bus, "MUSIC_BUS", "music bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.22, "dense but not crushed music bus")

local premaster = make_track("PREMASTER BUS", 0.0, 0.0, false, true)
add_simple_fx(premaster, "PREMASTER BUS", "premaster tonal EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "final tonal guard before master")
add_simple_fx(premaster, "PREMASTER BUS", "premaster dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.42, "final guard only; upstream fixes already printed")
add_simple_fx(premaster, "PREMASTER BUS", "premaster limiter guard", {{"VST: ReaLimit (Cockos)"}}, 1.0, "safe ceiling before offline loudness print")

route_to(fx, music_bus, 0.0, "01 FX -> MUSIC_BUS")
route_to(synth, music_bus, 0.0, "02 SYNTH -> MUSIC_BUS")
route_to(strings, music_bus, 0.0, "03 STRINGS -> MUSIC_BUS")
route_to(keyboard, music_bus, 0.0, "04 KEYBOARD -> MUSIC_BUS")
route_to(guitar, music_bus, 0.0, "05 GUITAR -> MUSIC_BUS")
route_to(bass, music_bus, 0.0, "06 BASS_OR_808 -> MUSIC_BUS")
route_to(drums, music_bus, 0.0, "07 DRUMS -> MUSIC_BUS")
route_to(backing, vocal_bus, 0.0, "08 BACKING_VOCALS_WIDE_TUCKED -> VOCAL_BUS")
route_to(main, main_bus, 0.0, "10 MAIN_VOCAL_CENTER -> MAIN_VOCAL_BUS")
route_to(layer, layer_bus, 0.0, "11 VOCAL_LAYER_SUPPORT -> LAYER_VOCAL_BUS")
route_to(vocal_reverb, vocal_bus, 0.0, "VOCAL_REVERB_TUCKED -> VOCAL_BUS")
route_to(vocal_delay, vocal_bus, 0.0, "VOCAL_DELAY_TUCKED -> VOCAL_BUS")
route_to(main_bus, vocal_bus, 0.0, "MAIN_VOCAL_BUS -> VOCAL_BUS")
route_to(layer_bus, vocal_bus, 0.0, "LAYER_VOCAL_BUS -> VOCAL_BUS")
route_to(vocal_bus, premaster, 0.0, "VOCAL_BUS -> PREMASTER BUS")
route_to(music_bus, premaster, 0.0, "MUSIC_BUS -> PREMASTER BUS")
route_sidechain(main_bus, layer_bus, -1.8, "MAIN_VOCAL_BUS sidechain -> LAYER_VOCAL_BUS")
route_sidechain(main_bus, music_bus, -1.4, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")

local master = reaper.GetMasterTrack(0)
reaper.SetMediaTrackInfo_Value(master, "D_VOL", lin(0.0))
add_row("master", "master path", "active", "PREMASTER BUS routes to Master; other active tracks master-send disabled", -1, nil, "routing audit marker", "no_parameter_write")

reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", duration, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "{render_pattern}", true)
reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", [[{notes}]], true)

reaper.Main_SaveProjectEx(0, rpp, 0)
write_trace()
log("wrapper ok")
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    render = f'''
local rpp = [[{lua_path(base.RPP)}]]
local log_path = [[{lua_path(base.REPORTS / "render_prepare.log")}]]
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
os.remove(log_path)
local ok, err = xpcall(function()
  reaper.Main_openProject(rpp)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", [[{lua_path(base.RENDERS)}]], true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "{render_pattern}", true)
  reaper.Main_SaveProjectEx(0, rpp, 0)
  log("wrapper ok")
end, debug.traceback)
if not ok then log("wrapper error: " .. tostring(err)) end
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    base.BUILD_LUA.write_text(build, encoding="utf-8")
    base.RUN_BUILD_LUA.write_text(f"dofile([[{lua_path(base.BUILD_LUA)}]])\n", encoding="utf-8")
    base.RENDER_LUA.write_text(render, encoding="utf-8")
    base.RUN_RENDER_LUA.write_text(f"dofile([[{lua_path(base.RENDER_LUA)}]])\n", encoding="utf-8")


def trace_rows() -> list[dict[str, Any]]:
    data = json.loads(base.TRACE_JSON.read_text(encoding="utf-8"))
    rows = data.get("rows", [])
    return [row for row in rows if isinstance(row, dict)]


def sync_work_trace() -> None:
    WORK_TRACES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base.TRACE_JSON, WORK_TRACES / "plugin_trace.json")
    shutil.copy2(base.TRACE_JSON, WORK_TRACES / f"{SLUG}_plugin_trace.json")


def write_trace_md() -> None:
    payload = json.loads(base.TRACE_JSON.read_text(encoding="utf-8"))
    lines = ["# Actual REAPER Plugin Trace", "", "| track | fx | status | plugin | stage | policy |", "| --- | ---: | --- | --- | --- | --- |"]
    for row in payload.get("rows", []):
        lines.append(
            f"| {row.get('track')} | {row.get('fx_index')} | {row.get('status')} | "
            f"{row.get('plugin')} | {row.get('stage')} | {row.get('parameter_write_policy', '')} |"
        )
    base.TRACE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_gate() -> dict[str, Any]:
    sync_work_trace()
    proc = subprocess.run(
        [
            "python3",
            "tools/validate_reaper_vocal_chain_gate.py",
            "--trace",
            rel(base.TRACE_JSON),
            "--main-track",
            "10 MAIN_VOCAL_CENTER",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout)
    write_json(base.REPORTS / "vocal_chain_gate.json", payload)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    return payload


def write_routing_and_preflight() -> dict[str, Any]:
    rows = trace_rows()
    routing_rows = [
        row
        for row in rows
        if str(row.get("stage", "")) in {"track config", "send", "sidechain send", "master path"}
        or str(row.get("track", "")) == "routing"
    ]
    write_json(base.REPORTS / "routing_trace.json", {"slug": SLUG, "rows": routing_rows})
    write_csv(base.REPORTS / "routing_trace.csv", routing_rows)

    def has_loaded_fx(track: str, fx_index: int, plugin: str) -> bool:
        return any(
            str(row.get("track")) == track
            and str(row.get("status")) == "loaded"
            and int(row.get("fx_index", -99)) == fx_index
            and str(row.get("plugin")) == plugin
            for row in rows
        )

    def track_config(track: str) -> str:
        for row in rows:
            if str(row.get("track")) == track and str(row.get("stage")) == "track config":
                return str(row.get("plugin", ""))
        return ""

    send_plugins = [str(row.get("plugin", "")) for row in rows if str(row.get("track")) == "routing"]
    expected_sends = {
        "10 MAIN_VOCAL_CENTER -> MAIN_VOCAL_BUS",
        "11 VOCAL_LAYER_SUPPORT -> LAYER_VOCAL_BUS",
        "MAIN_VOCAL_BUS -> VOCAL_BUS",
        "LAYER_VOCAL_BUS -> VOCAL_BUS",
        "VOCAL_BUS -> PREMASTER BUS",
        "MUSIC_BUS -> PREMASTER BUS",
        "MAIN_VOCAL_BUS sidechain -> LAYER_VOCAL_BUS",
        "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS",
    }
    active_track_names = {
        "01 FX",
        "02 SYNTH",
        "03 STRINGS",
        "04 KEYBOARD",
        "05 GUITAR",
        "06 BASS_OR_808",
        "07 DRUMS",
        "08 BACKING_VOCALS_WIDE_TUCKED",
        "10 MAIN_VOCAL_CENTER",
        "11 VOCAL_LAYER_SUPPORT",
        "VOCAL_REVERB_TUCKED",
        "VOCAL_DELAY_TUCKED",
        "MAIN_VOCAL_BUS",
        "LAYER_VOCAL_BUS",
        "VOCAL_BUS",
        "MUSIC_BUS",
    }
    direct_master_violations = [
        track
        for track in sorted(active_track_names)
        if "master_send=true" in track_config(track)
    ]
    reference_config = track_config("SOURCE full mix reference muted - not in master")
    reference_send_violations = [
        plugin
        for plugin in send_plugins
        if plugin.startswith("SOURCE full mix reference muted - not in master ->")
    ]
    preflight = {
        "schema": "mwolla-v12-preflight-evidence-v1",
        "main_vocal": {
            "track": "10 MAIN_VOCAL_CENTER",
            "source": "9 Vocals.wav",
            "slot0_required_plugin": "JS: Codex Vocal AI Artifact Split Tamer",
            "slot0_passed": has_loaded_fx("10 MAIN_VOCAL_CENTER", 0, "JS: Codex Vocal AI Artifact Split Tamer"),
        },
        "layer_vocal": {
            "track": "11 VOCAL_LAYER_SUPPORT",
            "source": "10 Vocals.wav",
            "support_role": True,
        },
        "reference": {
            "track": "SOURCE full mix reference muted - not in master",
            "track_config": reference_config,
            "muted": "muted=true" in reference_config,
            "master_send_disabled": "master_send=false" in reference_config,
            "send_violations": reference_send_violations,
            "passed": "muted=true" in reference_config and "master_send=false" in reference_config and not reference_send_violations,
        },
        "routing": {
            "expected_sends": sorted(expected_sends),
            "observed_expected_sends": sorted(expected_sends.intersection(send_plugins)),
            "missing_expected_sends": sorted(expected_sends.difference(send_plugins)),
            "active_track_direct_master_send_violations": direct_master_violations,
            "premaster_master_send": track_config("PREMASTER BUS"),
        },
        "sidechain": {
            "main_to_layer": "MAIN_VOCAL_BUS sidechain -> LAYER_VOCAL_BUS" in send_plugins,
            "main_to_music": "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS" in send_plugins,
        },
        "gr_trace": "unavailable; plugin GR is not emitted by this REAPER trace, so bus pressure is inferred from render/QC metrics only",
    }
    preflight["passed"] = (
        preflight["main_vocal"]["slot0_passed"]
        and preflight["reference"]["passed"]
        and not preflight["routing"]["missing_expected_sends"]
        and not direct_master_violations
        and preflight["sidechain"]["main_to_layer"]
        and preflight["sidechain"]["main_to_music"]
        and "master_send=true" in preflight["routing"]["premaster_master_send"]
    )
    write_json(base.REPORTS / "preflight_evidence.json", preflight)
    lines = [
        "# Mwolla v12 Preflight Evidence",
        "",
        f"- Main vocal slot 0 passed: `{preflight['main_vocal']['slot0_passed']}`",
        f"- Reference inactive path passed: `{preflight['reference']['passed']}`",
        f"- Missing expected sends: `{len(preflight['routing']['missing_expected_sends'])}`",
        f"- Direct master-send violations: `{len(direct_master_violations)}`",
        f"- Sidechain main -> layer: `{preflight['sidechain']['main_to_layer']}`",
        f"- Sidechain main -> music: `{preflight['sidechain']['main_to_music']}`",
        f"- Overall preflight passed: `{preflight['passed']}`",
        "",
        "GR trace: unavailable in this trace; render/QC metrics are used as the measurable substitute.",
    ]
    (base.REPORTS / "preflight_evidence.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return preflight


def patch_v12_report(preflight: dict[str, Any]) -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    replacements = {
        "Mwolla v11 Constant Vocal Light Dynamic EQ Master Report": "Mwolla v12 10-Anchor High Quality Master Report",
        "Use `12 Vocals.wav` as the centered main vocal.": "Use `9 Vocals.wav` as imported track 10 / `10 MAIN_VOCAL_CENTER`, centered as the anchor vocal.",
        "Use `13 Vocals.wav` as a wide panned support layer, roughly 1 dB under the lead in active RMS but de-centered and side-weighted so it masks AI/noise texture without becoming the lead.": base.FEMALE_REPORT_LINE,
        "Female layer vs lead active RMS": "Layer vocal vs main active RMS",
        "female layer": "layer vocal",
        "Female layer": "Layer vocal",
        "female side": "layer support",
        "female_side_vocal": "layer_support_vocal",
        "## Constant Vocal Light Dynamic EQ v11": "## Constant Vocal Light Dynamic EQ v12",
        "v11 final": "v12 final",
        "v11 1.5s": "v12 1.5s",
        "v11 3s": "v12 3s",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v12 Evidence Contract",
            "",
            f"- Source selection: `{rel(base.REPORTS / 'source_selection.json')}`",
            f"- Routing trace: `{rel(base.REPORTS / 'routing_trace.json')}`",
            f"- Preflight evidence: `{rel(base.REPORTS / 'preflight_evidence.json')}`",
            f"- Work plugin trace: `{rel(WORK_TRACES / 'plugin_trace.json')}`",
            f"- Main vocal slot 0 pass: `{preflight['main_vocal']['slot0_passed']}`",
            f"- Reference inactive path pass: `{preflight['reference']['passed']}`",
            f"- Routing preflight pass: `{preflight['passed']}`",
            "- External plugin parameters were not hardcoded; external processors are insert-only unless the trace/policy says otherwise.",
            "- GR trace is unavailable, so compression/limiter pressure remains a review risk despite render/QC metrics.",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v11.write_reports(paths, processed, vocal_balance, gate)
    preflight = write_routing_and_preflight()
    patch_v12_report(preflight)
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["preflight"] = {
        "passed": preflight["passed"],
        "path": rel(base.REPORTS / "preflight_evidence.json"),
        "routing_trace": rel(base.REPORTS / "routing_trace.json"),
        "work_plugin_trace": rel(WORK_TRACES / "plugin_trace.json"),
    }
    qc["role_mapping"] = {
        "10_MAIN_VOCAL_CENTER": "9 Vocals.wav",
        "11_VOCAL_LAYER_SUPPORT": "10 Vocals.wav",
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v11.build_zip()
    extras = [
        base.REPORTS / "source_inventory.json",
        base.REPORTS / "routing_trace.json",
        base.REPORTS / "routing_trace.csv",
        base.REPORTS / "preflight_evidence.json",
        base.REPORTS / "preflight_evidence.md",
        WORK_TRACES / "plugin_trace.json",
        WORK_TRACES / f"{SLUG}_plugin_trace.json",
    ]
    with base.zipfile.ZipFile(base.DELIVERABLE_ZIP, "a", compression=base.zipfile.ZIP_DEFLATED) as archive:
        existing = set(archive.namelist())
        for path in extras:
            if path.exists():
                arcname = path.relative_to(ROOT).as_posix()
                if arcname not in existing:
                    archive.write(path, arcname)


def main() -> int:
    configure_base()
    base.extract_source = extract_source
    base.write_reaper_scripts = write_reaper_scripts
    base.write_trace_md = write_trace_md
    base.run_gate = run_gate
    base.write_reports = write_reports
    base.build_zip = build_zip
    base.process_lead_vocal = v2.v1.process_lead_vocal
    base.process_female_layer = v2.v1.process_female_mask_layer
    base.process_backing_vocals = v2.v1.process_backing_vocals
    base.process_instrument = v2.v1.process_instrument
    base.write_processed = v11.write_processed
    base.final_master = v11.final_master
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
