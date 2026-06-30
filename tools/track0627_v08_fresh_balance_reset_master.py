#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
CANONICAL_SOURCE = ROOT / "input" / "stems" / "track0627_source_stems"
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SLUG = "track0627_v08_fresh_balance_reset_master"
WORK = ROOT / "audio_work" / SLUG
SOURCE = WORK / "source_stems"
PROCESSED = WORK / "processed_stems"
REAPER_DIR = ROOT / "reaper" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
WORK_TRACES = ROOT / "work" / "traces"

RPP = REAPER_DIR / "track0627_v08_FRESH_BALANCE_RESET_MASTER.rpp"
BUILD_LUA = REAPER_DIR / "build_track0627_v08_fresh_balance_reset_master.lua"
RUN_BUILD_LUA = REAPER_DIR / "run_build_track0627_v08_fresh_balance_reset_master.lua"
RENDER_LUA = REAPER_DIR / "render_track0627_v08_fresh_balance_reset_master.lua"
RUN_RENDER_LUA = REAPER_DIR / "run_render_track0627_v08_fresh_balance_reset_master.lua"

TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"
TRACE_MD = REPORTS / "actual_reaper_plugin_trace.md"
WORK_TRACE_JSON = WORK_TRACES / "plugin_trace.json"
WORK_TRACE_COPY_JSON = WORK_TRACES / f"{SLUG}_plugin_trace.json"

REAPER_PRINT = RENDERS / "track0627_v08_REAPERPRINT_24-48.wav"
FINAL_WAV = RENDERS / "track0627_v08_MASTER_PRINT_24-48.wav"
FINAL_MP3 = RENDERS / "track0627_v08_FRESH_BALANCE_RESET_MASTER_320k.mp3"
VOCAL_SOLO = REPORTS / "_vocal_solo_fresh_balance_reset.wav"
MALE_SOLO = REPORTS / "_male_main_center_solo_fresh_balance_reset.wav"
REPORT_MD = REPORTS / "track0627_v08_fresh_balance_reset_master_report.md"


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


def extract_sources() -> dict[str, Any]:
    if not CANONICAL_SOURCE.exists():
        raise FileNotFoundError(CANONICAL_SOURCE)
    shutil.rmtree(SOURCE, ignore_errors=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    for source_path in sorted(CANONICAL_SOURCE.glob("*.wav")):
        target = SOURCE / source_path.name
        shutil.copy2(source_path, target)
        copied.append(
            {
                "canonical_source": rel(source_path),
                "local_copy": rel(target),
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
    if not copied:
        raise FileNotFoundError(f"No wav files found in {CANONICAL_SOURCE}")
    inventory = {
        "slug": SLUG,
        "source_root": rel(CANONICAL_SOURCE),
        "local_source_folder": rel(SOURCE),
        "copied_files": copied,
        "raw_sources_preserved": True,
        "restart_scope": "fresh balance reset from preserved raw stems after clearing previous track0627 generated artifacts",
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
        "fx": stem(1),
        "synth": stem(2),
        "keyboard": stem(3),
        "guitar": stem(4),
        "bass_a": stem(5),
        "drums": stem(6),
        "backing_vocals": stem(7),
        "male_vocal": stem(8),
        "female_vocal": stem(9),
        "bass_b": stem(10),
    }


def read_padded(path: Path, sr: int, length: int) -> np.ndarray:
    got_sr, y, _dtype = base.read_wav(path)
    if got_sr != sr:
        raise RuntimeError(f"Sample-rate mismatch: {path} is {got_sr}, expected {sr}")
    return base.pad_or_trim(y, length)


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y, sr, "bandpass", (low, high), order=3)
    return float(base.amp_to_db(base.rms(band)))


def process_male_main(y: np.ndarray, sr: int) -> np.ndarray:
    x = base.process_lead_vocal(y, sr)
    x = base.rbj_peaking(x, sr, 210, -0.55, 0.92)
    x = base.rbj_peaking(x, sr, 2950, 0.26, 0.86)
    x = base.dynamic_band_tame(x, sr, 5200, 9200, max_cut_db=2.35, percentile=54.0, slope=0.72, smooth_ms=7.0)
    x = base.dynamic_band_tame(x, sr, 9800, 16000, max_cut_db=1.8, percentile=57.0, slope=0.58, smooth_ms=8.0)
    x = base.match_active_rms(x, -19.1, max_gain_db=6.8)
    return base.peak_cap(x.astype(np.float32), -4.0)


def female_hook_curve(cleaned_female: np.ndarray, lead: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, Any]]:
    female_env = base.envelope(np.mean(np.abs(cleaned_female), axis=1), sr, 180.0)
    lead_env = base.envelope(np.mean(np.abs(lead), axis=1), sr, 130.0)
    female_db = base.amp_to_db(female_env)
    lead_db = base.amp_to_db(lead_env)
    f_active = female_db[female_db > -90.0]
    l_active = lead_db[lead_db > -90.0]
    f_lo = float(np.percentile(f_active, 50.0)) if len(f_active) else -48.0
    f_hi = float(np.percentile(f_active, 84.0)) if len(f_active) else -24.0
    l_lo = float(np.percentile(l_active, 43.0)) if len(l_active) else -48.0
    l_hi = float(np.percentile(l_active, 78.0)) if len(l_active) else -24.0
    female_score = np.clip((female_db - f_lo) / max(f_hi - f_lo, 1e-6), 0.0, 1.0)
    lead_score = np.clip((lead_db - l_lo) / max(l_hi - l_lo, 1e-6), 0.0, 1.0)
    score = np.clip((female_score ** 1.05) * (0.18 + 0.82 * lead_score), 0.0, 1.0)
    smooth = max(1, int(sr * 1.0))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        score = np.convolve(score, kernel, mode="same")
    gain_db = -7.4 + 1.8 * score
    return base.db_to_amp(gain_db).astype(np.float32), {
        "quiet_gain_db": -7.4,
        "max_hook_gain_db": -5.6,
        "active_seconds_above_half_score": round(float(np.sum(score > 0.5) / sr), 3),
    }


def process_female_side_assets(y: np.ndarray, sr: int, male: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    x = base.mono_center(y)
    x = base.peak_cap(x, -6.6)
    x = base.spectral_denoise(x, sr, reduction_db=2.6, percentile=11.0)
    x = base.butter_filter(x, sr, "highpass", 170, 2)
    x = base.rbj_peaking(x, sr, 250, -2.0, 0.95)
    x = base.dynamic_band_tame(x, sr, 380, 1150, max_cut_db=1.7, percentile=63.0, slope=0.56, smooth_ms=22.0)
    x = base.dynamic_band_tame(x, sr, 5200, 9800, max_cut_db=3.8, percentile=54.0, slope=0.80, smooth_ms=7.0)
    x = base.compressor(x, sr, threshold_db=-25.0, ratio=1.58, attack_ms=13.0, release_ms=120.0, makeup_db=0.0)
    curve, report = female_hook_curve(x, male, sr)

    mono = np.mean(x, axis=1).astype(np.float32) * curve
    left = base.haas_layer(mono, sr, pan=-0.82, delay_ms=12.0)
    right = base.haas_layer(mono, sr, pan=0.82, delay_ms=20.0)
    left = base.match_active_rms(left, base.active_rms_db(male) - 8.8, max_gain_db=18.0)
    right = base.match_active_rms(right, base.active_rms_db(male) - 9.0, max_gain_db=18.0)
    left = base.sidechain_band_duck(left, male, sr, 1800, 5000, max_cut_db=1.35, percentile=50.0, smooth_ms=135.0)
    right = base.sidechain_band_duck(right, male, sr, 1800, 5000, max_cut_db=1.35, percentile=50.0, smooth_ms=135.0)
    report.update(
        {
            "processed_l_active_rms_dbfs": round(base.active_rms_db(left), 2),
            "processed_r_active_rms_dbfs": round(base.active_rms_db(right), 2),
            "design": "female vocal is aggressively de-centered, lead-keyed, and tucked as support only.",
        }
    )
    return base.peak_cap(left, -7.2), base.peak_cap(right, -7.2), report


def process_backing(y: np.ndarray, sr: int, male: np.ndarray) -> np.ndarray:
    x = base.process_backing_vocals(y, sr, male)
    x = base.match_active_rms(x, base.active_rms_db(male) - 12.2, max_gain_db=18.0)
    return base.peak_cap(x.astype(np.float32), -7.8)


def process_music(role: str, y: np.ndarray, sr: int, male: np.ndarray) -> np.ndarray:
    x = base.process_instrument(role, y, sr, male)
    if role in {"fx", "synth", "keyboard", "guitar"}:
        x = base.sidechain_band_duck(x, male, sr, 1550, 4550, max_cut_db=0.72, percentile=54.0, smooth_ms=110.0)
    if role == "guitar":
        x = base.dynamic_band_tame(x, sr, 1900, 4300, max_cut_db=0.6, percentile=60.0, slope=0.5, smooth_ms=18.0)
    if role == "keyboard":
        x = base.rbj_peaking(x, sr, 2400, 0.18, 0.88)
    if role == "drums":
        x = base.soft_saturation(x, drive_db=0.22, mix=0.01)
    return base.peak_cap(x.astype(np.float32), -2.4)


def process_bass_pair(paths: dict[str, Path], sr: int, length: int, male: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    bass_a = read_padded(paths["bass_a"], sr, length)
    bass_b = read_padded(paths["bass_b"], sr, length)
    scores = {
        "bass_a": band_rms_db(bass_a, sr, 35, 120) - band_rms_db(bass_a, sr, 120, 520),
        "bass_b": band_rms_db(bass_b, sr, 35, 120) - band_rms_db(bass_b, sr, 120, 520),
    }
    low_key = "bass_a" if scores["bass_a"] >= scores["bass_b"] else "bass_b"
    harmonic_key = "bass_b" if low_key == "bass_a" else "bass_a"
    raw_low = bass_a if low_key == "bass_a" else bass_b
    raw_harm = bass_b if harmonic_key == "bass_b" else bass_a

    low = base.process_instrument("bass", raw_low, sr, male)
    low = base.mono_center(low)
    low = base.butter_filter(low, sr, "highpass", 26, 2)
    low = base.butter_filter(low, sr, "lowpass", 520, 2)
    low = base.rbj_peaking(low, sr, 72, 0.18, 0.9)
    low = base.soft_saturation(low, drive_db=0.34, mix=0.018)
    low = base.match_active_rms(low, base.active_rms_db(raw_low) - 0.25, max_gain_db=1.2)

    harmonic = base.process_instrument("bass", raw_harm, sr, male)
    harmonic = base.mono_center(harmonic)
    harmonic = base.butter_filter(harmonic, sr, "highpass", 58, 2)
    harmonic = base.butter_filter(harmonic, sr, "lowpass", 1300, 2)
    harmonic = base.rbj_peaking(harmonic, sr, 190, -0.48, 1.0)
    harmonic = base.rbj_peaking(harmonic, sr, 760, 0.35, 0.95)
    harmonic = base.soft_saturation(harmonic, drive_db=0.55, mix=0.03)
    harmonic = base.match_active_rms(harmonic, base.active_rms_db(low) - 3.4, max_gain_db=5.0)

    report = {
        "bass_low_source": rel(paths[low_key]),
        "bass_harmonic_source": rel(paths[harmonic_key]),
        "low_role_score_db": round(scores[low_key], 3),
        "harmonic_role_score_db": round(scores[harmonic_key], 3),
        "processed_low_active_rms_dbfs": round(base.active_rms_db(low), 2),
        "processed_harmonic_active_rms_dbfs": round(base.active_rms_db(harmonic), 2),
    }
    return {"bass_low": base.peak_cap(low, -2.8), "bass_harmonic": base.peak_cap(harmonic, -3.2)}, report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], float, dict[str, Any]]:
    sr, ref, _dtype = base.read_wav(paths["full_reference"])
    length = len(ref)
    male_raw = read_padded(paths["male_vocal"], sr, length)
    female_raw = read_padded(paths["female_vocal"], sr, length)
    backing_raw = read_padded(paths["backing_vocals"], sr, length)

    male = process_male_main(male_raw, sr)
    female_l, female_r, female_report = process_female_side_assets(female_raw, sr, male)
    backing = process_backing(backing_raw, sr, male)
    reverb, delay = base.make_space(male, sr)
    reverb *= db_to_amp(-2.4)
    delay *= db_to_amp(-2.8)

    processed = {
        "full_reference": PROCESSED / "source_full_mix_reference_muted_not_in_master.wav",
        "male_vocal": PROCESSED / "male_track9_main_center_clean.wav",
        "female_l": PROCESSED / "female_track10_hook_layer_L.wav",
        "female_r": PROCESSED / "female_track10_hook_layer_R.wav",
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

    for role in ("fx", "synth", "keyboard", "guitar", "drums"):
        raw = read_padded(paths[role], sr, length)
        out = process_music(role, raw, sr, male)
        processed[role] = PROCESSED / f"{role}_processed.wav"
        base.write_wav(processed[role], sr, out)

    bass_outputs, bass_report = process_bass_pair(paths, sr, length, male)
    for key, audio in bass_outputs.items():
        processed[key] = PROCESSED / f"{key}_processed.wav"
        base.write_wav(processed[key], sr, audio)

    vocal_sum = male + (female_l * 0.42 + female_r * 0.42) + backing * db_to_amp(-2.2) + reverb + delay
    base.write_wav(MALE_SOLO, sr, male)
    base.write_wav(VOCAL_SOLO, sr, base.peak_cap(vocal_sum.astype(np.float32), -1.5))

    raw_rows = [base.audio_metrics(path, f"raw_{key}") for key, path in paths.items()]
    write_json(REPORTS / "source_stem_metrics.json", raw_rows)
    write_csv(REPORTS / "source_stem_metrics.csv", raw_rows)
    write_json(REPORTS / "female_hook_layer_decisions.json", female_report)
    write_json(REPORTS / "bass_role_decisions.json", bass_report)

    reaper_gain = {
        "01_FX_FILTERED_SUPPORT_track": -1.9,
        "02_SYNTH_VOCAL_POCKET_track": -0.8,
        "03_KEYBOARD_VOCAL_POCKET_track": -0.25,
        "04_GUITAR_SIDE_TEXTURE_track": -0.55,
        "05_BASS_SUB_BODY_track": 0.0,
        "06_DRUMS_TRANSIENT_BALANCED_track": -0.15,
        "07_BACKING_VOCALS_WIDE_TUCKED_track": -3.8,
        "08_MALE_NONHOOK_CENTER_track": 2.1,
        "MALE_LEAD_BUS": 0.35,
        "female_tracks": -4.5,
        "FEMALE_SIDE_BUS": -2.0,
        "VOCAL_BUS": 0.15,
        "MUSIC_BUS": 0.25,
        "BASS_BUS": -0.55,
    }
    male_effective = reaper_gain["08_MALE_NONHOOK_CENTER_track"] + reaper_gain["MALE_LEAD_BUS"]
    female_effective = reaper_gain["female_tracks"] + reaper_gain["FEMALE_SIDE_BUS"]
    selection = {
        "status": "genre_based_draft_runtime",
        "male_main_center": rel(paths["male_vocal"]),
        "female_hook_layer": rel(paths["female_vocal"]),
        "bass_sources": [rel(paths["bass_a"]), rel(paths["bass_b"])],
        "bass_role_decisions": bass_report,
        "processed_male_active_rms_dbfs": round(base.active_rms_db(male), 2),
        "processed_female_l_active_rms_dbfs": round(base.active_rms_db(female_l), 2),
        "processed_female_r_active_rms_dbfs": round(base.active_rms_db(female_r), 2),
        "female_l_vs_male_processed_db": round(base.active_rms_db(female_l) - base.active_rms_db(male), 2),
        "female_r_vs_male_processed_db": round(base.active_rms_db(female_r) - base.active_rms_db(male), 2),
        "female_l_vs_male_after_reaper_gain_db": round((base.active_rms_db(female_l) + female_effective) - (base.active_rms_db(male) + male_effective), 2),
        "female_r_vs_male_after_reaper_gain_db": round((base.active_rms_db(female_r) + female_effective) - (base.active_rms_db(male) + male_effective), 2),
        "reaper_gain_map_db": reaper_gain,
        "source_full_mix_policy": "SOURCE full mix reference muted - not in master; muted and master send disabled.",
        "user_direction": "fresh reset: male lead center and readable, female support tucked, loudness and balance kept conservative.",
    }
    write_json(REPORTS / "source_selection.json", selection)
    write_json(
        REPORTS / "balance_reset_decisions.json",
        {
            "intent": "Rebuild from preserved raw stems after clearing previous generated passes.",
            "female_support_strategy": {
                "curve_quiet_gain_db": -7.4,
                "curve_max_hook_gain_db": -5.6,
                "match_vs_male_db": [-8.8, -9.0],
                "female_track_gain_db": -4.5,
                "female_bus_gain_db": -2.0,
            },
            "master_strategy": {
                "target_lufs": -12.2,
                "target_true_peak_dbfs": -1.5,
                "goal": "less limiter pressure and less forward female support than prior track0627 passes",
            },
        },
    )
    return processed, length / sr, selection


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    render_pattern = REAPER_PRINT.stem
    notes = (
        "track0627 v08 fresh reset: 8 Vocals.wav is assigned to required 08 MALE_NONHOOK_CENTER as the centered male lead. "
        "9 Vocals.wav is split into 10 FEMALE_HOOK_LAYER_L/R for panned hook/adlib support only with stronger ducking and lower gain. "
        "Both bass stems are retained as BASS_SUB_BODY and BASS_HARMONIC_BODY through BASS_BUS. "
        "The source full mix/reference track is named exactly SOURCE full mix reference muted - not in master, muted, "
        "and master-send disabled. Active stems route through MUSIC_BUS/VOCAL_BUS into PREMASTER BUS with more conservative bus gains. "
        "Main vocal first FX slot is JS: Codex Vocal AI Artifact Split Tamer. External plugins are insert-only with "
        "no hardcoded parameter writes. No listening, final-master, or reference-match claim is made."
    )
    build = f'''
local slug = "{SLUG}"
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
  add_fx_candidates(tr, label, "corrective EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "HPF, low-mid cleanup, guarded clarity", false)
  add_fx_candidates(tr, label, "dynamic EQ guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.62, "mud, nasal, sibilance, and AI-like edge guard", false)
  add_fx_candidates(tr, label, "de-ess guard", {{"JS: De-esser", "VST3: TDR Nova (Tokyo Dawn Labs)"}}, 1.0, "sibilance control after dynamic EQ", false)
  add_fx_candidates(tr, label, "light compression", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, is_main and 0.58 or 0.34, "steady vocal without overclamping", false)
  add_fx_candidates(tr, label, "light OTT multiband lift", {{"VST3: OTT (Xfer Records)", "VST: OTT (Xfer Records)", "OTT (Xfer Records)"}}, is_main and 0.18 or 0.08, "small vocal density lift; no hardcoded external params", false)
  add_fx_candidates(tr, label, "output limiter guard", {{"VST: ReaLimit (Cockos)"}}, 1.0, "track peak guard", false)
end
local function add_simple_fx(tr, label, stage, names, wet, reason)
  add_fx_candidates(tr, label, stage, names, wet, reason, false)
end
local function add_music_chain(tr, label, reason)
  add_fx_candidates(tr, label, "music pocket dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.74, reason, false)
end

os.execute("mkdir -p " .. q(reaper_dir))
os.execute("mkdir -p " .. q(render_dir))
os.execute("mkdir -p " .. q(report_dir))
os.remove(log_path)
os.remove(trace_path)
reaper.Main_OnCommand(40023, 0)

local ref = make_track("SOURCE full mix reference muted - not in master", -99.0, 0.0, true, false)
insert_media_full(ref, [[{lua_path(processed["full_reference"])}]])

local fx = make_track("01 FX_FILTERED_SUPPORT", -1.9, 0.16, false, false)
insert_media_full(fx, [[{lua_path(processed["fx"])}]])
add_simple_fx(fx, "01 FX_FILTERED_SUPPORT", "FX cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "FX retained but filtered away from vocal diction")

local synth = make_track("02 SYNTH_VOCAL_POCKET", -0.8, -0.08, false, false)
insert_media_full(synth, [[{lua_path(processed["synth"])}]])
add_music_chain(synth, "02 SYNTH_VOCAL_POCKET", "leave presence room for center male vocal")

local keyboard = make_track("03 KEYBOARD_VOCAL_POCKET", -0.25, 0.07, false, false)
insert_media_full(keyboard, [[{lua_path(processed["keyboard"])}]])
add_music_chain(keyboard, "03 KEYBOARD_VOCAL_POCKET", "controlled midrange around the lead")

local guitar = make_track("04 GUITAR_SIDE_TEXTURE", -0.55, -0.14, false, false)
insert_media_full(guitar, [[{lua_path(processed["guitar"])}]])
add_simple_fx(guitar, "04 GUITAR_SIDE_TEXTURE", "guitar cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "side texture without vocal masking")

local bass_low = make_track("05 BASS_SUB_BODY", 0.0, 0.0, false, false)
insert_media_full(bass_low, [[{lua_path(processed["bass_low"])}]])
add_simple_fx(bass_low, "05 BASS_SUB_BODY", "bass sub EQ/control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.84, "mono sub/body and peak control")

local drums = make_track("06 DRUMS_TRANSIENT_BALANCED", -0.15, 0.0, false, false)
insert_media_full(drums, [[{lua_path(processed["drums"])}]])
add_simple_fx(drums, "06 DRUMS_TRANSIENT_BALANCED", "drum transient control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.86, "tighten kick/snare while preserving punch")

local backing = make_track("07 BACKING_VOCALS_WIDE_TUCKED", -3.8, 0.0, false, false)
insert_media_full(backing, [[{lua_path(processed["backing_vocals"])}]])
add_vocal_chain(backing, "07 BACKING_VOCALS_WIDE_TUCKED", false)

local male = make_track("08 MALE_NONHOOK_CENTER", 2.1, 0.0, false, false)
insert_media_full(male, [[{lua_path(processed["male_vocal"])}]])
add_vocal_chain(male, "08 MALE_NONHOOK_CENTER", true)

local female_l = make_track("10 FEMALE_HOOK_LAYER_L", -4.5, -0.8, false, false)
insert_media_full(female_l, [[{lua_path(processed["female_l"])}]])
add_vocal_chain(female_l, "10 FEMALE_HOOK_LAYER_L", false)

local female_r = make_track("10 FEMALE_HOOK_LAYER_R", -4.6, 0.8, false, false)
insert_media_full(female_r, [[{lua_path(processed["female_r"])}]])
add_vocal_chain(female_r, "10 FEMALE_HOOK_LAYER_R", false)

local bass_harmonic = make_track("10 BASS_HARMONIC_BODY", -1.1, 0.0, false, false)
insert_media_full(bass_harmonic, [[{lua_path(processed["bass_harmonic"])}]])
add_simple_fx(bass_harmonic, "10 BASS_HARMONIC_BODY", "bass harmonic EQ/control", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.80, "second bass retained as harmonic/body layer without low-end smear")

local vocal_reverb = make_track("11 VOCAL_REVERB_TUCKED", -9.0, 0.0, false, false)
insert_media_full(vocal_reverb, [[{lua_path(processed["vocal_reverb"])}]])
add_simple_fx(vocal_reverb, "11 VOCAL_REVERB_TUCKED", "dark reverb cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "tail stays behind lead")

local vocal_delay = make_track("12 VOCAL_DELAY_TUCKED", -9.2, 0.0, false, false)
insert_media_full(vocal_delay, [[{lua_path(processed["vocal_delay"])}]])
add_simple_fx(vocal_delay, "12 VOCAL_DELAY_TUCKED", "dark delay cleanup", {{"VST: ReaEQ (Cockos)"}}, 1.0, "delay stays tucked and filtered")

local bass_bus = make_track("BASS_BUS", -0.55, 0.0, false, false)
add_simple_fx(bass_bus, "BASS_BUS", "bass bus mono glue", {{"VST: ReaEQ (Cockos)", "VST: ReaComp (Cockos)"}}, 0.72, "two bass stems controlled before music bus")

local male_bus = make_track("MALE_LEAD_BUS", 0.35, 0.0, false, false)
add_simple_fx(male_bus, "MALE_LEAD_BUS", "male bus clarity EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "center lead stays readable")
add_simple_fx(male_bus, "MALE_LEAD_BUS", "male bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.30, "light bus leveling")

local female_bus = make_track("FEMALE_SIDE_BUS", -2.0, 0.0, false, false)
add_simple_fx(female_bus, "FEMALE_SIDE_BUS", "female side dynamic guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.62, "keep female layer below and around male center")

local vocal_bus = make_track("VOCAL_BUS", 0.15, 0.0, false, false)
add_simple_fx(vocal_bus, "VOCAL_BUS", "vocal bus dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.52, "smooth vocal harshness after balance")
add_simple_fx(vocal_bus, "VOCAL_BUS", "vocal bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.26, "light vocal group glue")

local music_bus = make_track("MUSIC_BUS", 0.25, 0.0, false, false)
add_simple_fx(music_bus, "MUSIC_BUS", "music bus dynamic pocket", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)", "VST: ReaEQ (Cockos)"}}, 0.68, "instrument bed loud but carved around vocal presence")
add_simple_fx(music_bus, "MUSIC_BUS", "music bus glue", {{"VST3: TDR Kotelnikov (Tokyo Dawn Labs)", "VST: ReaComp (Cockos)"}}, 0.22, "dense but not crushed music bus")

local premaster = make_track("PREMASTER BUS", 0.0, 0.0, false, true)
add_simple_fx(premaster, "PREMASTER BUS", "premaster tonal EQ", {{"VST: ReaEQ (Cockos)"}}, 1.0, "final tonal guard before master")
add_simple_fx(premaster, "PREMASTER BUS", "premaster dynamic EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, 0.46, "250-350 Hz and 3-9 kHz guard")
add_simple_fx(premaster, "PREMASTER BUS", "premaster limiter guard", {{"VST: ReaLimit (Cockos)", "VST: Event Horizon Limiter/Clipper"}}, 1.0, "safe ceiling before offline loudness print")

route_to(fx, music_bus, 0.0, "01 FX_FILTERED_SUPPORT -> MUSIC_BUS")
route_to(synth, music_bus, 0.0, "02 SYNTH_VOCAL_POCKET -> MUSIC_BUS")
route_to(keyboard, music_bus, 0.0, "03 KEYBOARD_VOCAL_POCKET -> MUSIC_BUS")
route_to(guitar, music_bus, 0.0, "04 GUITAR_SIDE_TEXTURE -> MUSIC_BUS")
route_to(bass_low, bass_bus, 0.0, "05 BASS_SUB_BODY -> BASS_BUS")
route_to(bass_harmonic, bass_bus, 0.0, "10 BASS_HARMONIC_BODY -> BASS_BUS")
route_to(bass_bus, music_bus, 0.0, "BASS_BUS -> MUSIC_BUS")
route_to(drums, music_bus, 0.0, "06 DRUMS_TRANSIENT_BALANCED -> MUSIC_BUS")
route_to(backing, vocal_bus, 0.0, "07 BACKING_VOCALS_WIDE_TUCKED -> VOCAL_BUS")
route_to(male, male_bus, 0.0, "08 MALE_NONHOOK_CENTER -> MALE_LEAD_BUS")
route_to(female_l, female_bus, 0.0, "10 FEMALE_HOOK_LAYER_L -> FEMALE_SIDE_BUS")
route_to(female_r, female_bus, 0.0, "10 FEMALE_HOOK_LAYER_R -> FEMALE_SIDE_BUS")
route_to(vocal_reverb, vocal_bus, 0.0, "11 VOCAL_REVERB_TUCKED -> VOCAL_BUS")
route_to(vocal_delay, vocal_bus, 0.0, "12 VOCAL_DELAY_TUCKED -> VOCAL_BUS")
route_to(male_bus, vocal_bus, 0.0, "MALE_LEAD_BUS -> VOCAL_BUS")
route_to(female_bus, vocal_bus, 0.0, "FEMALE_SIDE_BUS -> VOCAL_BUS")
route_to(vocal_bus, premaster, 0.0, "VOCAL_BUS -> PREMASTER BUS")
route_to(music_bus, premaster, 0.0, "MUSIC_BUS -> PREMASTER BUS")
route_sidechain(male_bus, female_bus, -0.9, "MALE_LEAD_BUS sidechain -> FEMALE_SIDE_BUS")
route_sidechain(male_bus, music_bus, -1.1, "MALE_LEAD_BUS sidechain -> MUSIC_BUS")

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


def final_master() -> None:
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=235:t=q:w=0.95:g=-0.28,"
        "equalizer=f=3150:t=q:w=0.95:g=0.08,"
        "equalizer=f=7300:t=q:w=1.0:g=-0.35,"
        "loudnorm=I=-12.2:TP=-1.5:LRA=5.0:linear=false,"
        "alimiter=limit=0.82:attack=2:release=95:level=false"
    )
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(REAPER_PRINT), "-af", filter_graph, "-ar", "48000", "-c:a", "pcm_s24le", str(FINAL_WAV)],
        check=True,
    )
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(FINAL_MP3)],
        check=True,
    )


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
        payload = {"passed": False, "errors": ["vocal chain gate did not return JSON"], "stdout": proc.stdout, "stderr": proc.stderr}
    if proc.returncode != 0:
        payload["passed"] = False
        payload.setdefault("errors", []).append(proc.stderr.strip() or "vocal chain gate returned non-zero")
    write_json(REPORTS / "vocal_chain_gate.json", payload)
    return payload


def sync_work_trace() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    payload["work_trace_note"] = "Copied after actual REAPER plugin insertion for the current active pass."
    write_json(WORK_TRACE_JSON, payload)
    write_json(WORK_TRACE_COPY_JSON, payload)


def write_trace_md() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    lines = ["# Actual REAPER Plugin Trace", "", "| track | fx | status | plugin | stage | reason |", "| --- | ---: | --- | --- | --- | --- |"]
    for row in payload.get("rows", []):
        lines.append(f"| {row.get('track')} | {row.get('fx_index')} | {row.get('status')} | {row.get('plugin')} | {row.get('stage')} | {row.get('reason')} |")
    TRACE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(paths: dict[str, Path], selection: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    rows = [
        base.audio_metrics(MALE_SOLO, "processed_male_center_solo"),
        base.audio_metrics(VOCAL_SOLO, "processed_vocal_solo"),
        base.audio_metrics(REAPER_PRINT, "reaper_print"),
        base.audio_metrics(FINAL_WAV, "final_master_wav_intermediate"),
        base.audio_metrics(FINAL_MP3, "final_master_mp3"),
    ]
    write_json(REPORTS / "qc_metrics.json", rows)
    write_csv(REPORTS / "qc_metrics.csv", rows)
    final_wav = next(row for row in rows if row["label"] == "final_master_wav_intermediate")
    mp3 = next(row for row in rows if row["label"] == "final_master_mp3")
    trace = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    missing_plugins = [row for row in trace.get("rows", []) if str(row.get("status", "")).startswith("missing")]
    female_rule_passed = selection["female_l_vs_male_after_reaper_gain_db"] <= -10.0 and selection["female_r_vs_male_after_reaper_gain_db"] <= -10.0
    mp3_tp = mp3.get("true_peak_dbfs")
    wav_tp = final_wav.get("true_peak_dbfs")
    peak_safe = (mp3_tp is not None and mp3_tp <= -0.6) and (wav_tp is not None and wav_tp <= -0.8)
    passed = bool(gate.get("passed")) and female_rule_passed and peak_safe and FINAL_MP3.exists()
    summary = {
        "status": "rendered_mp3_review_master" if passed else "rendered_unverified_or_blocked",
        "approval_status": "human_review_required",
        "genre_status": "genre_based_draft",
        "final_mp3": rel(FINAL_MP3),
        "final_wav_intermediate": rel(FINAL_WAV),
        "reaper_print": rel(REAPER_PRINT),
        "reaper_project": rel(RPP),
        "plugin_trace": rel(TRACE_JSON),
        "work_plugin_trace": rel(WORK_TRACE_JSON),
        "final_lufs": final_wav.get("integrated_lufs"),
        "final_true_peak_dbfs": wav_tp,
        "mp3_true_peak_dbfs": mp3_tp,
        "female_l_vs_male_after_reaper_gain_db": selection["female_l_vs_male_after_reaper_gain_db"],
        "female_r_vs_male_after_reaper_gain_db": selection["female_r_vs_male_after_reaper_gain_db"],
        "female_relative_to_male_rule_passed": female_rule_passed,
        "vocal_gate": gate,
        "missing_plugin_rows": len(missing_plugins),
        "source_full_mix_policy": selection["source_full_mix_policy"],
        "delivery_scope": "one final MP3 requested; no AB MP3 or deliverable ZIP created.",
    }
    write_json(REPORTS / "qc_summary.json", summary)
    notes = [
        "# Track0627 v08 Fresh Balance Reset Report",
        "",
        "## Direction",
        "",
        "- Track 9 role: centered male main vocal from `8 Vocals.wav`.",
        "- Track 10 role: panned female hook/adlib layer from `9 Vocals.wav`, explicitly pushed back below the male lead.",
        "- Both bass stems are retained and split into low/body and harmonic/body roles.",
        "- Source full mix/reference is muted, master-send disabled, and not routed to active buses.",
        "",
        "## Deliverable Scope",
        "",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        "- No AB MP3 or delivery ZIP was created because the request was for one MP3 only.",
        "",
        "## Evidence",
        "",
        f"- Final WAV intermediate: `{final_wav.get('integrated_lufs')}` LUFS / TP `{wav_tp}` dBFS.",
        f"- Final MP3 TP: `{mp3_tp}` dBFS.",
        f"- Female L/R after REAPER gain vs male: `{selection['female_l_vs_male_after_reaper_gain_db']}` / `{selection['female_r_vs_male_after_reaper_gain_db']}` dB.",
        f"- Vocal chain gate passed: `{gate.get('passed')}`.",
        f"- Missing optional plugin trace rows: `{len(missing_plugins)}`.",
        "",
        "## Limits",
        "",
        "- This is a measured render/QC result only; no listening claim or reference-match claim is made.",
        "- External/unverified plugin parameters were not hardcoded.",
    ]
    REPORT_MD.write_text("\n".join(notes) + "\n", encoding="utf-8")
    return summary


def verify_outputs(summary: dict[str, Any]) -> None:
    required = [
        FINAL_MP3,
        FINAL_WAV,
        REAPER_PRINT,
        RPP,
        TRACE_JSON,
        TRACE_MD,
        WORK_TRACE_JSON,
        WORK_TRACE_COPY_JSON,
        REPORTS / "qc_metrics.json",
        REPORTS / "qc_summary.json",
        REPORT_MD,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required outputs: " + ", ".join(missing))
    if not summary.get("final_mp3"):
        raise RuntimeError("QC summary did not record final MP3")


def leave_reaper_open() -> None:
    subprocess.Popen([str(REAPER_BIN), str(RPP)])


def main() -> int:
    ensure_dirs()
    extract_sources()
    paths = stems()
    processed, duration, selection = write_processed(paths)
    write_reaper_scripts(processed, duration)
    run_reaper()
    final_master()
    write_trace_md()
    sync_work_trace()
    gate = run_gate()
    summary = write_reports(paths, selection, gate)
    verify_outputs(summary)
    runtime = {
        "status": summary["status"],
        "slug": SLUG,
        "final_mp3": rel(FINAL_MP3),
        "reaper_project": rel(RPP),
        "plugin_trace": rel(TRACE_JSON),
        "work_plugin_trace": rel(WORK_TRACE_JSON),
        "qc_summary": rel(REPORTS / "qc_summary.json"),
        "final_lufs": summary["final_lufs"],
        "final_true_peak_dbfs": summary["final_true_peak_dbfs"],
        "mp3_true_peak_dbfs": summary["mp3_true_peak_dbfs"],
        "vocal_gate_passed": summary["vocal_gate"]["passed"],
        "missing_plugin_rows": summary["missing_plugin_rows"],
    }
    write_json(REPORTS / "runtime_status.json", runtime)
    leave_reaper_open()
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
