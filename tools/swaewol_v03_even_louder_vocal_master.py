#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SOURCE_EXTERNAL = Path("/Users/hantaeheuk/Downloads/쇄월 x 쇄월 (Mashup)")
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SLUG = "swaewol_v03_even_louder_vocal_master"
WORK = ROOT / "audio_work" / SLUG
SOURCE = WORK / "source_stems"
PROCESSED = WORK / "processed_stems"
REAPER_DIR = ROOT / "reaper" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
WORK_TRACES = ROOT / "work" / "traces"

RPP = REAPER_DIR / "swaewol_v03_EVEN_LOUDER_VOCAL_MASTER.rpp"
BUILD_LUA = REAPER_DIR / "build_swaewol_v03_even_louder_vocal_master.lua"
RUN_BUILD_LUA = REAPER_DIR / "run_build_swaewol_v03_even_louder_vocal_master.lua"
RENDER_LUA = REAPER_DIR / "render_swaewol_v03_even_louder_vocal_master.lua"
RUN_RENDER_LUA = REAPER_DIR / "run_render_swaewol_v03_even_louder_vocal_master.lua"

TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"
TRACE_MD = REPORTS / "actual_reaper_plugin_trace.md"
WORK_TRACE_JSON = WORK_TRACES / "plugin_trace.json"
WORK_TRACE_COPY_JSON = WORK_TRACES / f"{SLUG}_plugin_trace.json"

REVIEW_WAV = RENDERS / "swaewol_v03_review_copy_even_louder_vocal_24-48.wav"
REAPER_PRINT = REVIEW_WAV
REVIEW_MP3 = RENDERS / "swaewol_v03_review_copy_even_louder_vocal_320k.mp3"
VOCAL_SOLO = REPORTS / "_processed_vocal_solo_male_forward_female_pan_ott.wav"
MALE_SOLO = REPORTS / "_processed_male_forward_solo_check.wav"
AB_PREVIEW_MP3 = RENDERS / "swaewol_v03_AB_v02_to_review_copy_loudness_matched_320k.mp3"
V01_FINAL = ROOT / "renders" / "swaewol_v01_female_pan_male_up_master" / "swaewol_v01_FEMALE_PAN_MALE_UP_MASTER.wav"

REPORT_MD = REPORTS / "swaewol_v03_even_louder_vocal_master_report.md"


spec = importlib.util.spec_from_file_location("base_audio", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load helper script: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.REPORTS = REPORTS


def ensure_dirs() -> None:
    for path in (WORK, SOURCE, PROCESSED, REAPER_DIR, RENDERS, REPORTS, WORK_TRACES):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


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


def db_to_amp(db: float) -> float:
    return float(np.power(10.0, db / 20.0))


def lua_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def lua_long_string(value: str) -> str:
    return "[[" + value.replace("]", "] ]") + "]]"


def lua_array(values: list[str]) -> str:
    return "{" + ", ".join(lua_long_string(value) for value in values) + "}"


def copy_sources() -> dict[str, Any]:
    if not SOURCE_EXTERNAL.exists():
        raise FileNotFoundError(SOURCE_EXTERNAL)
    copied: list[dict[str, Any]] = []
    for path in sorted(SOURCE_EXTERNAL.glob("*.wav")):
        target = SOURCE / path.name
        shutil.copy2(path, target)
        copied.append({"source": str(path), "local_copy": rel(target), "bytes": target.stat().st_size})
    if not copied:
        raise FileNotFoundError(f"No wav files found in {SOURCE_EXTERNAL}")
    inventory = {
        "slug": SLUG,
        "source_folder": str(SOURCE_EXTERNAL),
        "local_source_folder": rel(SOURCE),
        "copied_files": copied,
        "raw_sources_excluded_from_review_artifacts": True,
    }
    write_json(REPORTS / "source_inventory.json", inventory)
    return inventory


def stem(prefix: int) -> Path:
    matches = sorted(SOURCE.glob(f"{prefix} *.wav"))
    if not matches:
        raise FileNotFoundError(f"Missing source stem prefix {prefix} in {SOURCE}")
    return matches[0]


def stems() -> dict[str, Path]:
    return {
        "full_reference": stem(0),
        "synth": stem(1),
        "keyboard": stem(2),
        "guitar": stem(3),
        "bass": stem(4),
        "drums": stem(5),
        "backing_vocals": stem(6),
        "male_vocal": stem(7),
        "female_vocal": stem(8),
    }


def read_padded(path: Path, sr: int, length: int) -> np.ndarray:
    got_sr, y, _dtype = base.read_wav(path)
    if got_sr != sr:
        raise RuntimeError(f"Sample-rate mismatch: {path} is {got_sr}, expected {sr}")
    return base.pad_or_trim(y, length)


def crude_f0_median(path: Path) -> dict[str, Any]:
    sr, y, dtype_name = base.read_wav(path)
    mono = y.mean(axis=1)
    frame = 4096
    hop = 2048
    f0s: list[float] = []
    max_frames = min(700, max(0, (len(mono) - frame) // hop))
    for i in range(max_frames):
        seg = mono[i * hop : i * hop + frame].astype(np.float64)
        if np.sqrt(np.mean(seg * seg)) < db_to_amp(-45.0):
            continue
        seg = seg - np.mean(seg)
        ac = np.correlate(seg, seg, mode="full")[frame - 1 :]
        lo = int(sr / 420)
        hi = int(sr / 70)
        if hi >= len(ac):
            continue
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > ac[0] * 0.23:
            f0s.append(sr / k)
    return {
        "sample_rate": sr,
        "dtype": dtype_name,
        "crude_f0_median_hz": round(float(np.median(f0s)), 1) if f0s else None,
        "crude_f0_frames": len(f0s),
    }


def source_metric(path: Path, label: str) -> dict[str, Any]:
    row = base.audio_metrics(path, label)
    row.update(crude_f0_median(path))
    return row


def process_male_main(y: np.ndarray, sr: int) -> np.ndarray:
    x = base.process_lead_vocal(y, sr)
    x = base.rbj_peaking(x, sr, 170, 0.45, 0.80)
    x = base.rbj_peaking(x, sr, 2850, 0.45, 0.88)
    x = base.dynamic_band_tame(x, sr, 5200, 9300, max_cut_db=2.8, percentile=55.0, slope=0.72, smooth_ms=7.0)
    x = base.dynamic_band_tame(x, sr, 9700, 16500, max_cut_db=1.9, percentile=58.0, slope=0.62, smooth_ms=8.0)
    x = base.match_active_rms(x, -18.2, max_gain_db=8.5)
    return base.peak_cap(x.astype(np.float32), -3.4)


def process_female_side_assets(y: np.ndarray, sr: int, male: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = base.mono_center(y)
    x = base.peak_cap(x, -5.8)
    x = base.spectral_denoise(x, sr, reduction_db=2.2, percentile=11.0)
    x = base.butter_filter(x, sr, "highpass", 135, 2)
    x = base.rbj_peaking(x, sr, 245, -1.4, 0.95)
    x = base.dynamic_band_tame(x, sr, 1800, 4600, max_cut_db=1.15, percentile=54.0, slope=0.58, smooth_ms=105.0)
    x = base.dynamic_band_tame(x, sr, 5600, 10000, max_cut_db=3.2, percentile=55.0, slope=0.76, smooth_ms=7.0)
    x = base.compressor(x, sr, threshold_db=-24.0, ratio=1.45, attack_ms=15.0, release_ms=105.0, makeup_db=0.05)
    x = base.match_active_rms(x, base.active_rms_db(male) - 5.4, max_gain_db=18.0)
    x = base.sidechain_band_duck(x, male, sr, 1800, 4700, max_cut_db=0.95, percentile=53.0, smooth_ms=125.0)
    mono = np.mean(x, axis=1).astype(np.float32)
    right = np.zeros_like(mono)
    delay = int(round(sr * 0.014))
    right[delay:] = mono[:-delay]
    left_asset = np.column_stack([mono, mono]).astype(np.float32)
    right_asset = np.column_stack([right, right]).astype(np.float32)
    return base.peak_cap(left_asset, -6.0), base.peak_cap(right_asset, -6.2)


def process_backing(y: np.ndarray, sr: int, male: np.ndarray) -> np.ndarray:
    x = base.process_backing_vocals(y, sr, male)
    x = base.match_active_rms(x, base.active_rms_db(male) - 9.5, max_gain_db=18.0)
    return base.peak_cap(x.astype(np.float32), -7.0)


def process_music(role: str, y: np.ndarray, sr: int, male: np.ndarray) -> np.ndarray:
    x = base.process_instrument(role, y, sr, male)
    if role in {"synth", "keyboard", "guitar"}:
        x = base.sidechain_band_duck(x, male, sr, 1450, 4650, max_cut_db=0.95, percentile=52.0, smooth_ms=120.0)
    if role == "bass":
        mono = np.mean(x, axis=1, dtype=np.float64).astype(np.float32)
        x = np.column_stack([mono, mono]).astype(np.float32)
    if role == "drums":
        x = base.soft_saturation(x, drive_db=0.35, mix=0.018)
    return base.peak_cap(x.astype(np.float32), -2.4)


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], float, dict[str, Any]]:
    sr, ref, _dtype = base.read_wav(paths["full_reference"])
    length = len(ref)
    male_raw = read_padded(paths["male_vocal"], sr, length)
    female_raw = read_padded(paths["female_vocal"], sr, length)
    backing_raw = read_padded(paths["backing_vocals"], sr, length)

    male = process_male_main(male_raw, sr)
    female_l, female_r = process_female_side_assets(female_raw, sr, male)
    backing = process_backing(backing_raw, sr, male)
    reverb, delay = base.make_space(male, sr)
    reverb *= db_to_amp(-2.0)
    delay *= db_to_amp(-2.4)

    processed = {
        "full_reference": PROCESSED / "source_full_mix_reference_muted.wav",
        "male_vocal": PROCESSED / "male_7_center_main_up_clean.wav",
        "female_l": PROCESSED / "female_8_shadow_L_role_asset.wav",
        "female_r": PROCESSED / "female_8_shadow_R_role_asset.wav",
        "backing_vocals": PROCESSED / "backing_vocals_tucked_wide.wav",
        "vocal_reverb": PROCESSED / "male_vocal_reverb_tucked.wav",
        "vocal_delay": PROCESSED / "male_vocal_delay_tucked.wav",
    }
    base.write_wav(processed["full_reference"], sr, ref)
    base.write_wav(processed["male_vocal"], sr, male)
    base.write_wav(processed["female_l"], sr, female_l)
    base.write_wav(processed["female_r"], sr, female_r)
    base.write_wav(processed["backing_vocals"], sr, backing)
    base.write_wav(processed["vocal_reverb"], sr, reverb)
    base.write_wav(processed["vocal_delay"], sr, delay)

    for role in ("synth", "keyboard", "guitar", "bass", "drums"):
        raw = read_padded(paths[role], sr, length)
        out = process_music(role, raw, sr, male)
        processed[role] = PROCESSED / f"{role}_processed.wav"
        base.write_wav(processed[role], sr, out)

    vocal_sum = male + (female_l * 0.46 + female_r * 0.44) + backing * db_to_amp(-1.8) + reverb + delay
    base.write_wav(MALE_SOLO, sr, male)
    base.write_wav(VOCAL_SOLO, sr, base.peak_cap(vocal_sum.astype(np.float32), -1.5))

    raw_rows = [
        source_metric(paths["backing_vocals"], "raw_6_backing_vocals"),
        source_metric(paths["male_vocal"], "raw_7_vocals_assigned_male_center"),
        source_metric(paths["female_vocal"], "raw_8_vocals_assigned_female_side"),
    ]
    write_json(REPORTS / "source_vocal_probe.json", raw_rows)

    selection = {
        "status": "review_copy",
        "role_assignment_basis": "7 Vocals has lower crude f0 and lower active RMS; 8 Vocals has higher crude f0/brightness and starts louder, so 7 is boosted as center male and 8 is split as L/R female side layer.",
        "male_main_center": rel(paths["male_vocal"]),
        "female_panned_layer": rel(paths["female_vocal"]),
        "backing_vocals": rel(paths["backing_vocals"]),
        "raw_7_active_rms_dbfs": raw_rows[1]["active_rms_dbfs"],
        "raw_8_active_rms_dbfs": raw_rows[2]["active_rms_dbfs"],
        "raw_8_minus_7_active_rms_db": round(raw_rows[2]["active_rms_dbfs"] - raw_rows[1]["active_rms_dbfs"], 2),
        "processed_male_active_rms_dbfs": round(base.active_rms_db(male), 2),
        "processed_female_l_active_rms_dbfs": round(base.active_rms_db(female_l), 2),
        "processed_female_r_active_rms_dbfs": round(base.active_rms_db(female_r), 2),
        "female_l_vs_male_processed_db": round(base.active_rms_db(female_l) - base.active_rms_db(male), 2),
        "female_r_vs_male_processed_db": round(base.active_rms_db(female_r) - base.active_rms_db(male), 2),
        "reaper_gain_map_db": {
            "08_MALE_NONHOOK_CENTER_track": 3.2,
            "MALE_LEAD_BUS": 0.8,
            "11_FEMALE_L_SIDE_track": -2.0,
            "12_FEMALE_R_SIDE_track": -2.2,
            "FEMALE_SIDE_BUS": -1.1,
            "MUSIC_BUS": 1.2,
            "VOCAL_BUS": 0.4,
            "male_effective_gain_before_vocal_bus": 4.0,
            "female_l_effective_gain_before_vocal_bus": -3.1,
            "female_r_effective_gain_before_vocal_bus": -3.3,
            "female_l_vs_male_after_reaper_gain_db": round((base.active_rms_db(female_l) - 3.1) - (base.active_rms_db(male) + 4.0), 2),
            "female_r_vs_male_after_reaper_gain_db": round((base.active_rms_db(female_r) - 3.3) - (base.active_rms_db(male) + 4.0), 2),
        "v03_revision": "review_copy follow-up: male forward and whole-song loudness lifted again versus v02 while female/space stays tucked",
        },
        "source_full_mix_policy": "SOURCE full mix reference muted - not in master; muted and master send disabled in REAPER.",
    }
    write_json(REPORTS / "source_selection.json", selection)
    return processed, length / sr, selection


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    render_pattern = REAPER_PRINT.stem
    notes = (
        "swaewol_v03_even_louder_vocal_master review_copy only: 7 Vocals assigned to 08 MALE_NONHOOK_CENTER "
        "and lifted as the clean center main. 8 Vocals is split into FEMALE_L_SIDE/FEMALE_R_SIDE "
        "with L/R pan. 6 Backing_Vocals is tucked as wide support. The source full mix/reference "
        "track is named exactly SOURCE full mix reference muted - not in master, muted, and master-send "
        "disabled. Active stems route through MUSIC_BUS/VOCAL_BUS into PREMASTER BUS. Main vocal first "
        "FX slot is JS: Codex Vocal AI Artifact Split Tamer. This pass targets vocal_clarity and keeps "
        "male center lead with female side/shadow support at least 5 dB below male. External plugins are "
        "insert-only with no hardcoded parameter or wet writes. No pitch/tune inserts. No final, delivery, "
        "or master approval claim is made."
    )

    build = f'''
local slug = "{SLUG}"
local root = [[{lua_path(ROOT)}]]
local reaper_dir = [[{lua_path(REAPER_DIR)}]]
local render_dir = [[{lua_path(RENDERS)}]]
local report_dir = [[{lua_path(REPORTS)}]]
local rpp = [[{lua_path(RPP)}]]
local trace_path = [[{lua_path(TRACE_JSON)}]]
local log_path = [[{lua_path(REPORTS / "build_reaper.log")}]]
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
  f:write('{{\\n  "slug": "' .. slug .. '",\\n  "source_full_mix_policy": "muted and master-send disabled",\\n  "required_main_track": "08 MALE_NONHOOK_CENTER",\\n  "rows": [\\n')
  for i, row in ipairs(rows) do f:write("    " .. row .. (i == #rows and "\\n" or ",\\n")) end
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
  if main_send == false then reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0) end
  return tr
end
local function insert_media_full(tr, path)
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then error("source failed: " .. path) end
  local item = reaper.AddMediaItemToTrack(tr)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", duration)
  reaper.SetMediaItemInfo_Value(item, "D_FADEINLEN", 0.004)
  reaper.SetMediaItemInfo_Value(item, "D_FADEOUTLEN", 0.008)
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
    add_row("routing", "send", "created", reason or "track send", send, nil, "post-fader role-bus routing")
  else
    add_row("routing", "send", "failed", reason or "track send", -1, nil, "REAPER did not create send")
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
    add_row("routing", "sidechain send", "created", reason or "sidechain", send, nil, "source channels 1/2 into destination 3/4")
  else
    add_row("routing", "sidechain send", "failed", reason or "sidechain", -1, nil, "REAPER did not create sidechain")
  end
  return send
end
local function add_vocal_chain(tr, label, is_main)
  add_fx_candidates(tr, label, "first-slot developed Suno/AI vocal artifact rescue", {{"JS: Codex Vocal AI Artifact Split Tamer"}}, 1.0, "mandatory first slot on 08 MALE_NONHOOK_CENTER; clean rescue before any other processing", is_main)
  add_fx_candidates(tr, label, "noise floor cleanup", {{"JS: Codex Noise Floor Tamer"}}, 1.0, "reduce low-level vocal noise before dynamics", false)
  add_fx_candidates(tr, label, "vocal gate expander", {{"JS: Codex Vocal Gate Expander"}}, 0.72, "tuck gaps without chopping phrases", false)
  add_fx_candidates(tr, label, "corrective EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "HPF, low-mid cleanup, guarded clarity", false)
  add_fx_candidates(tr, label, "dynamic EQ guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.62, "mud, nasal, sibilance, and AI-like edge guard", false)
  add_fx_candidates(tr, label, "de-ess guard", {{"JS: De-esser", "VST3: TDR Nova (Tokyo Dawn Labs)"}}, 1.0, "sibilance control after dynamic EQ", false)
  add_fx_candidates(tr, label, "light compression", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, is_main and 0.58 or 0.36, "steady vocal without overclamping", false)
  add_fx_candidates(tr, label, "light OTT multiband lift", {{"VST3: OTT (Xfer Records)", "VST: OTT (Xfer Records)", "OTT (Xfer Records)"}}, is_main and 0.24 or 0.12, "user-requested OTT for forward vocal density; generic wet only, no hardcoded external params", false)
  add_fx_candidates(tr, label, "output limiter guard", {{"VST: ReaLimit (Cockos)"}}, 1.0, "track peak guard", false)
end
local function add_music_chain(tr, label, stage, reason)
  add_fx_candidates(tr, label, stage, {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.78, reason, false)
end
local function add_simple_fx(tr, label, stage, names, wet, reason)
  add_fx_candidates(tr, label, stage, names, wet, reason, false)
end

os.execute("mkdir -p " .. q(reaper_dir))
os.execute("mkdir -p " .. q(render_dir))
os.execute("mkdir -p " .. q(report_dir))
os.remove(log_path)
os.remove(trace_path)

reaper.Main_OnCommand(40023, 0)

local ref = make_track("SOURCE full mix reference muted - not in master", -99.0, 0.0, true, false)
insert_media_full(ref, [[{lua_path(processed["full_reference"])}]])

local synth = make_track("01 SYNTH", -0.2, -0.08, false, false)
insert_media_full(synth, [[{lua_path(processed["synth"])}]])
add_music_chain(synth, "01 SYNTH", "synth music pocket", "leave presence room for center male vocal")

local keyboard = make_track("02 KEYBOARD", -0.3, 0.07, false, false)
insert_media_full(keyboard, [[{lua_path(processed["keyboard"])}]])
add_music_chain(keyboard, "02 KEYBOARD", "keyboard resonance/pocket", "controlled midrange around the lead")

local guitar = make_track("03 GUITAR", -0.2, -0.14, false, false)
insert_media_full(guitar, [[{lua_path(processed["guitar"])}]])
add_simple_fx(guitar, "03 GUITAR", "guitar cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "side texture without vocal masking")

local bass = make_track("04 BASS", 0.5, 0.0, false, false)
insert_media_full(bass, [[{lua_path(processed["bass"])}]])
add_simple_fx(bass, "04 BASS", "bass EQ/control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.85, "mono low-end body and peak control")

local drums = make_track("05 DRUMS", 0.3, 0.0, false, false)
insert_media_full(drums, [[{lua_path(processed["drums"])}]])
add_simple_fx(drums, "05 DRUMS", "drum transient control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.86, "tighten kick/snare while preserving punch")

local backing = make_track("06 BACKING_VOCALS_WIDE_TUCKED", -3.0, 0.0, false, false)
insert_media_full(backing, [[{lua_path(processed["backing_vocals"])}]])
add_vocal_chain(backing, "06 BACKING_VOCALS_WIDE_TUCKED", false)

local male = make_track("08 MALE_NONHOOK_CENTER", 3.45, 0.0, false, false)
insert_media_full(male, [[{lua_path(processed["male_vocal"])}]])
add_vocal_chain(male, "08 MALE_NONHOOK_CENTER", true)

local female_l = make_track("11 FEMALE_L_SIDE", -2.0, -0.74, false, false)
insert_media_full(female_l, [[{lua_path(processed["female_l"])}]])
add_vocal_chain(female_l, "11 FEMALE_L_SIDE", false)

local female_r = make_track("12 FEMALE_R_SIDE", -2.2, 0.74, false, false)
insert_media_full(female_r, [[{lua_path(processed["female_r"])}]])
add_vocal_chain(female_r, "12 FEMALE_R_SIDE", false)

local vocal_reverb = make_track("13 VOCAL_REVERB_TUCKED", -8.2, 0.0, false, false)
insert_media_full(vocal_reverb, [[{lua_path(processed["vocal_reverb"])}]])
add_simple_fx(vocal_reverb, "13 VOCAL_REVERB_TUCKED", "dark reverb cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "tail stays behind lead")

local vocal_delay = make_track("14 VOCAL_DELAY_TUCKED", -8.6, 0.0, false, false)
insert_media_full(vocal_delay, [[{lua_path(processed["vocal_delay"])}]])
add_simple_fx(vocal_delay, "14 VOCAL_DELAY_TUCKED", "dark delay cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "delay stays tucked and filtered")

local male_bus = make_track("MALE_LEAD_BUS", 0.95, 0.0, false, false)
add_simple_fx(male_bus, "MALE_LEAD_BUS", "male bus clarity EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "center lead stays readable")
add_simple_fx(male_bus, "MALE_LEAD_BUS", "male bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.32, "light bus leveling")

local female_bus = make_track("FEMALE_SIDE_BUS", -1.1, 0.0, false, false)
add_simple_fx(female_bus, "FEMALE_SIDE_BUS", "female side dynamic guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.68, "keep L/R female below and around male center")

local vocal_bus = make_track("VOCAL_BUS", 0.55, 0.0, false, false)
add_simple_fx(vocal_bus, "VOCAL_BUS", "vocal bus dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.55, "smooth vocal harshness after balance")
add_simple_fx(vocal_bus, "VOCAL_BUS", "vocal bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.28, "light vocal group glue")
add_simple_fx(vocal_bus, "VOCAL_BUS", "light OTT vocal bus lift", {{"VST3: OTT (Xfer Records)", "VST: OTT (Xfer Records)", "OTT (Xfer Records)"}}, 0.16, "subtle OTT density so male stays above the beat")

local music_bus = make_track("MUSIC_BUS", 1.35, 0.0, false, false)
add_simple_fx(music_bus, "MUSIC_BUS", "music bus dynamic pocket", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.70, "instrument bed loud but carved around vocal presence")
add_simple_fx(music_bus, "MUSIC_BUS", "music bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.24, "dense but not crushed music bus")

local premaster = make_track("PREMASTER BUS", 0.0, 0.0, false, true)
add_simple_fx(premaster, "PREMASTER BUS", "premaster tonal EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "final tonal guard before master")
add_simple_fx(premaster, "PREMASTER BUS", "premaster dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.50, "250-350 Hz and 3-9 kHz guard")
add_simple_fx(premaster, "PREMASTER BUS", "light OTT premaster density", {{"VST3: OTT (Xfer Records)", "VST: OTT (Xfer Records)", "OTT (Xfer Records)"}}, 0.10, "small OTT amount for louder perceived master without forcing external params")
add_simple_fx(premaster, "PREMASTER BUS", "premaster limiter guard", {{"VST: ReaLimit (Cockos)", "VST: Event Horizon Limiter/Clipper"}}, 1.0, "safe ceiling before offline loudness print")

route_to(synth, music_bus, 0.0, "01 SYNTH -> MUSIC_BUS")
route_to(keyboard, music_bus, 0.0, "02 KEYBOARD -> MUSIC_BUS")
route_to(guitar, music_bus, 0.0, "03 GUITAR -> MUSIC_BUS")
route_to(bass, music_bus, 0.0, "04 BASS -> MUSIC_BUS")
route_to(drums, music_bus, 0.0, "05 DRUMS -> MUSIC_BUS")
route_to(backing, vocal_bus, 0.0, "06 BACKING_VOCALS_WIDE_TUCKED -> VOCAL_BUS")
route_to(male, male_bus, 0.0, "08 MALE_NONHOOK_CENTER -> MALE_LEAD_BUS")
route_to(female_l, female_bus, 0.0, "11 FEMALE_L_SIDE -> FEMALE_SIDE_BUS")
route_to(female_r, female_bus, 0.0, "12 FEMALE_R_SIDE -> FEMALE_SIDE_BUS")
route_to(vocal_reverb, vocal_bus, 0.0, "13 VOCAL_REVERB_TUCKED -> VOCAL_BUS")
route_to(vocal_delay, vocal_bus, 0.0, "14 VOCAL_DELAY_TUCKED -> VOCAL_BUS")
route_to(male_bus, vocal_bus, 0.0, "MALE_LEAD_BUS -> VOCAL_BUS")
route_to(female_bus, vocal_bus, 0.0, "FEMALE_SIDE_BUS -> VOCAL_BUS")
route_to(vocal_bus, premaster, 0.0, "VOCAL_BUS -> PREMASTER BUS")
route_to(music_bus, premaster, 0.0, "MUSIC_BUS -> PREMASTER BUS")
route_sidechain(male_bus, female_bus, -1.5, "MALE_LEAD_BUS sidechain -> FEMALE_SIDE_BUS")
route_sidechain(male_bus, music_bus, -1.35, "MALE_LEAD_BUS sidechain -> MUSIC_BUS")

local master = reaper.GetMasterTrack(0)
reaper.SetMediaTrackInfo_Value(master, "D_VOL", lin(0.0))
add_row("master", "master path", "active", "PREMASTER BUS routes to Master; other active tracks master-send disabled", -1, nil, "routing audit marker")

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
local rpp = [[{lua_path(RPP)}]]
local log_path = [[{lua_path(REPORTS / "render_prepare.log")}]]
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
os.remove(log_path)
local ok, err = xpcall(function()
  reaper.Main_openProject(rpp)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", [[{lua_path(RENDERS)}]], true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "{render_pattern}", true)
  reaper.Main_SaveProjectEx(0, rpp, 0)
  log("wrapper ok")
end, debug.traceback)
if not ok then log("wrapper error: " .. tostring(err)) end
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''

    BUILD_LUA.write_text(build, encoding="utf-8")
    RUN_BUILD_LUA.write_text(f"dofile([[{lua_path(BUILD_LUA)}]])\n", encoding="utf-8")
    RENDER_LUA.write_text(render, encoding="utf-8")
    RUN_RENDER_LUA.write_text(f"dofile([[{lua_path(RENDER_LUA)}]])\n", encoding="utf-8")


def run_reaper() -> None:
    if not REAPER_BIN.exists():
        raise FileNotFoundError(REAPER_BIN)
    REAPER_PRINT.unlink(missing_ok=True)
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_BUILD_LUA)], check=True)
    build_log = (REPORTS / "build_reaper.log").read_text(encoding="utf-8", errors="ignore")
    if "wrapper ok" not in build_log:
        raise RuntimeError("REAPER build wrapper failed")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_RENDER_LUA)], check=True)
    render_log = (REPORTS / "render_prepare.log").read_text(encoding="utf-8", errors="ignore")
    if "wrapper ok" not in render_log:
        raise RuntimeError("REAPER render wrapper failed")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(RPP)], check=True)
    if not REAPER_PRINT.exists():
        matches = sorted(RENDERS.glob(f"{REAPER_PRINT.stem}*.wav"))
        if matches:
            matches[-1].rename(REAPER_PRINT)
    if not REAPER_PRINT.exists():
        raise FileNotFoundError(REAPER_PRINT)


def run_gate() -> dict[str, Any]:
    proc = subprocess.run(
        [
            "python3",
            "tools/validate_reaper_vocal_chain_gate.py",
            "--trace",
            rel(TRACE_JSON),
            "--script",
            rel(BUILD_LUA),
            "--main-track",
            "08 MALE_NONHOOK_CENTER",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "passed": False,
            "errors": ["vocal chain gate did not return JSON"],
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    write_json(REPORTS / "vocal_chain_gate.json", payload)
    if proc.returncode != 0:
        payload["passed"] = False
        payload.setdefault("errors", []).append(proc.stderr.strip() or "vocal chain gate returned non-zero")
    return payload


def normalize_review_wav() -> None:
    temp = REVIEW_WAV.with_name(REVIEW_WAV.stem + "_normalized_tmp.wav")
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(REVIEW_WAV),
            "-af",
            "highpass=f=24,loudnorm=I=-10.4:TP=-1.1:LRA=3.8:linear=false,alimiter=limit=0.8:attack=2:release=90:level=false",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(temp),
        ],
        check=True,
    )
    temp.replace(REVIEW_WAV)


def write_review_mp3() -> None:
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(REVIEW_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(REVIEW_MP3)],
        check=True,
    )


def write_ab(paths: dict[str, Path]) -> None:
    temp = REPORTS / "_ab_source_to_review_copy"
    temp.mkdir(parents=True, exist_ok=True)
    before = temp / "before_source.wav"
    after = temp / "after_review_copy.wav"
    concat = temp / "concat.txt"
    before_source = V01_FINAL if V01_FINAL.exists() else paths["full_reference"]
    loudness_match = "loudnorm=I=-16:TP=-1.5:LRA=8:linear=false"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "32", "-t", "24", "-i", str(before_source), "-af", loudness_match, "-c:a", "pcm_s16le", str(before)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "32", "-t", "24", "-i", str(REVIEW_WAV), "-af", loudness_match, "-c:a", "pcm_s16le", str(after)], check=True)
    concat.write_text(f"file '{before}'\nfile '{after}'\n", encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "320k", str(AB_PREVIEW_MP3)], check=True)
    shutil.rmtree(temp, ignore_errors=True)


def sync_work_trace() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    payload["work_trace_note"] = "Copied after actual REAPER plugin insertion for the current active pass."
    write_json(WORK_TRACE_JSON, payload)
    write_json(WORK_TRACE_COPY_JSON, payload)


def write_trace_md() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    lines = ["# Actual REAPER Plugin Trace", "", "| track | fx | status | plugin | stage | reason |", "| --- | ---: | --- | --- | --- | --- |"]
    for row in payload.get("rows", []):
        lines.append(
            f"| {row.get('track')} | {row.get('fx_index')} | {row.get('status')} | {row.get('plugin')} | {row.get('stage')} | {row.get('reason')} |"
        )
    TRACE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(paths: dict[str, Path], selection: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    rows = [
        base.audio_metrics(paths["full_reference"], "source_full_mix_reference_muted"),
        base.audio_metrics(paths["male_vocal"], "raw_7_vocals_assigned_male_center"),
        base.audio_metrics(paths["female_vocal"], "raw_8_vocals_assigned_female_side"),
        base.audio_metrics(MALE_SOLO, "processed_male_center_solo"),
        base.audio_metrics(VOCAL_SOLO, "processed_vocal_solo"),
        base.audio_metrics(REVIEW_WAV, "primary_review_wav"),
    ]
    write_json(REPORTS / "qc_metrics.json", rows)
    write_csv(REPORTS / "qc_metrics.csv", rows)
    source = next(row for row in rows if row["label"] == "source_full_mix_reference_muted")
    review = next(row for row in rows if row["label"] == "primary_review_wav")
    female_l_after = selection["reaper_gain_map_db"]["female_l_vs_male_after_reaper_gain_db"]
    female_r_after = selection["reaper_gain_map_db"]["female_r_vs_male_after_reaper_gain_db"]
    female_rule_passed = female_l_after <= -5.0 and female_r_after <= -5.0
    review_tp = review.get("true_peak_dbfs")
    review_peak_safe = (review_tp is not None) and review_tp <= -0.2
    review_copy_qc_passed = bool(gate.get("passed")) and female_rule_passed and review_peak_safe and REVIEW_WAV.exists()
    status = "review_copy" if review_copy_qc_passed else "blocked"
    summary = {
        "status": status,
        "primary_target": "vocal_clarity",
        "review_copy_qc_passed": review_copy_qc_passed,
        "source_lufs": source.get("integrated_lufs"),
        "review_wav": rel(REVIEW_WAV),
        "review_mp3": rel(REVIEW_MP3),
        "review_lufs": review.get("integrated_lufs"),
        "review_true_peak_dbfs": review_tp,
        "review_stereo_correlation": review.get("stereo_corr"),
        "review_side_mid_db": review.get("side_mid_db"),
        "male_main_center": selection["male_main_center"],
        "female_panned_layer": selection["female_panned_layer"],
        "raw_8_minus_7_active_rms_db": selection["raw_8_minus_7_active_rms_db"],
        "processed_female_l_vs_male_db": selection["female_l_vs_male_processed_db"],
        "processed_female_r_vs_male_db": selection["female_r_vs_male_processed_db"],
        "female_l_vs_male_after_reaper_gain_db": female_l_after,
        "female_r_vs_male_after_reaper_gain_db": female_r_after,
        "female_relative_to_male_rule_passed": female_rule_passed,
        "source_full_mix_policy": selection["source_full_mix_policy"],
        "external_plugin_policy": "insert-only; no hardcoded parameter or wet writes for external/unverified plugins",
        "approval_status": "blocked from final/delivery/master approval; human review required",
        "loudness_matched_ab_preview": rel(AB_PREVIEW_MP3) if AB_PREVIEW_MP3.exists() else None,
        "reaper_gain_map_db": selection["reaper_gain_map_db"],
        "vocal_gate": gate,
    }
    write_json(REPORTS / "qc_summary.json", summary)

    notes = [
        "# Swaewol v03 Even Louder Vocal Review Copy Report",
        "",
        "## Status",
        "",
        f"- Runtime status: `{status}`.",
        "- Primary target: `vocal_clarity`.",
        "- Approval status: `blocked` from final/delivery/master approval; human review required.",
        "",
        "## Direction",
        "",
        "- `7 Vocals.wav` is the center male main vocal role.",
        "- `8 Vocals.wav` is split into left/right female side layers.",
        "- `6 Backing_Vocals.wav` is tucked as wide support.",
        "- The full mix/reference is present only as `SOURCE full mix reference muted - not in master` and is muted with master send disabled.",
        "",
        "## Review Artifacts",
        "",
        f"- Primary review WAV: `{rel(REVIEW_WAV)}`",
        f"- REAPER project: `{rel(RPP)}`",
        f"- Plugin trace: `{rel(TRACE_JSON)}`",
        f"- Work plugin trace: `{rel(WORK_TRACE_JSON)}`",
        f"- QC metrics: `{rel(REPORTS / 'qc_metrics.json')}`",
        f"- QC summary: `{rel(REPORTS / 'qc_summary.json')}`",
        f"- Loudness-matched A/B preview: `{rel(AB_PREVIEW_MP3) if AB_PREVIEW_MP3.exists() else 'not created'}`",
        "",
        "## Evidence",
        "",
        f"- Raw 8-vocal active RMS vs raw 7-vocal: `{selection['raw_8_minus_7_active_rms_db']}` dB; male role needed lift relative to the brighter/louder female role.",
        f"- Processed female L vs male active RMS: `{selection['female_l_vs_male_processed_db']}` dB.",
        f"- Processed female R vs male active RMS: `{selection['female_r_vs_male_processed_db']}` dB.",
        f"- REAPER male gain before vocal bus: `+{selection['reaper_gain_map_db']['male_effective_gain_before_vocal_bus']}` dB.",
        f"- REAPER female side gain before vocal bus: L `{selection['reaper_gain_map_db']['female_l_effective_gain_before_vocal_bus']}` dB / R `{selection['reaper_gain_map_db']['female_r_effective_gain_before_vocal_bus']}` dB.",
        f"- Female side vs male after REAPER gain: L `{selection['reaper_gain_map_db']['female_l_vs_male_after_reaper_gain_db']}` dB / R `{selection['reaper_gain_map_db']['female_r_vs_male_after_reaper_gain_db']}` dB.",
        f"- Primary review WAV: `{review.get('integrated_lufs')}` LUFS / TP `{review.get('true_peak_dbfs')}` dBFS.",
        f"- Vocal chain gate passed: `{gate.get('passed')}`.",
        "- External/unverified plugin writes were not applied; plugin trace records insert-only policy rows.",
        "",
        "## Limits",
        "",
        "- This is a measured `review_copy` or `blocked` automation result only; no listening claim or reference-match claim is made.",
        "- Missing plugins, if any, are recorded in the trace. External plugin parameters were not hardcoded.",
    ]
    REPORT_MD.write_text("\n".join(notes) + "\n", encoding="utf-8")
    return summary


def verify_outputs(summary: dict[str, Any]) -> None:
    required = [
        REVIEW_WAV,
        REVIEW_MP3,
        RPP,
        TRACE_JSON,
        TRACE_MD,
        WORK_TRACE_JSON,
        WORK_TRACE_COPY_JSON,
        REPORTS / "qc_metrics.json",
        REPORTS / "qc_summary.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required outputs: " + ", ".join(missing))
    if summary.get("status") not in {"review_copy", "blocked"}:
        raise RuntimeError("QC summary status must remain blocked/review_copy")


def main() -> int:
    ensure_dirs()
    copy_sources()
    paths = stems()
    processed, duration, selection = write_processed(paths)
    write_reaper_scripts(processed, duration)
    run_reaper()
    normalize_review_wav()
    write_review_mp3()
    write_trace_md()
    sync_work_trace()
    gate = run_gate()
    write_ab(paths)
    summary = write_reports(paths, selection, gate)
    verify_outputs(summary)
    result = {
        "status": summary["status"],
        "slug": SLUG,
        "primary_target": "vocal_clarity",
        "review_wav": rel(REVIEW_WAV),
        "review_mp3": rel(REVIEW_MP3),
        "reaper_project": rel(RPP),
        "plugin_trace": rel(TRACE_JSON),
        "work_plugin_trace": rel(WORK_TRACE_JSON),
        "qc_metrics": rel(REPORTS / "qc_metrics.json"),
        "qc_summary": rel(REPORTS / "qc_summary.json"),
        "review_lufs": summary["review_lufs"],
        "review_true_peak_dbfs": summary["review_true_peak_dbfs"],
        "female_l_vs_male_after_reaper_gain_db": summary["female_l_vs_male_after_reaper_gain_db"],
        "female_r_vs_male_after_reaper_gain_db": summary["female_r_vs_male_after_reaper_gain_db"],
        "vocal_gate_passed": summary["vocal_gate"]["passed"],
        "loudness_matched_ab_preview": summary["loudness_matched_ab_preview"],
    }
    write_json(REPORTS / "runtime_status.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
