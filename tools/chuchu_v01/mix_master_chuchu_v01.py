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

import imageio_ffmpeg
import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
SLUG = "chuchu_v01"
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SOURCE = ROOT / "audio_work" / SLUG / "raw_stems"
PROCESSED = ROOT / "audio_work" / SLUG / "processed_stems"
REAPER_DIR = ROOT / "reaper" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG

RPP = REAPER_DIR / "chuchu_v01_MIX_MASTER.rpp"
BUILD_LUA = REAPER_DIR / "build_chuchu_v01_mix_master.lua"
RUN_BUILD_LUA = REAPER_DIR / "run_build_chuchu_v01_mix_master.lua"
RENDER_LUA = REAPER_DIR / "render_chuchu_v01_mix_master.lua"
RUN_RENDER_LUA = REAPER_DIR / "run_render_chuchu_v01_mix_master.lua"
TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"
TRACE_MD = REPORTS / "actual_reaper_plugin_trace.md"

REAPER_PRINT = RENDERS / "chuchu_v01_REAPERPRINT_24-48.wav"
FINAL_WAV = RENDERS / "chuchu_v01_MIX_MASTER_FINAL.wav"
FINAL_MP3 = RENDERS / "chuchu_v01_MIX_MASTER_FINAL_320k.mp3"
VOCAL_SOLO = RENDERS / "chuchu_v01_VOCAL_SOLO_check.wav"
AB_PREVIEW_MP3 = RENDERS / "chuchu_v01_AB_source_to_master_320k.mp3"
DELIVERABLE_ZIP = RENDERS / "chuchu_v01_MIX_MASTER_DELIVERABLE.zip"
REPORT_MD = REPORTS / "chuchu_v01_mix_master_report.md"

spec = importlib.util.spec_from_file_location("sonyeo_luka_v01_clear_master", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load helper script: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.REPORTS = REPORTS


def ensure_dirs() -> None:
    for path in (SOURCE, PROCESSED, REAPER_DIR, RENDERS, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


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


def find_stems() -> dict[str, Path]:
    files = sorted(SOURCE.glob("*.wav"))
    by_name = {path.name: path for path in files}
    required_names = [
        "0 추추.wav",
        "1 Brass.wav",
        "2 FX.wav",
        "3 Synth.wav",
        "4 Keyboard.wav",
        "5 Guitar.wav",
        "6 Bass.wav",
        "7 Drums.wav",
        "8 Vocals.wav",
        "9 Vocals.wav",
        "10 New Track.wav",
    ]
    missing = [name for name in required_names if name not in by_name]
    if missing:
        raise FileNotFoundError(f"Missing expected stems: {missing}")
    return {
        "full_reference": by_name["0 추추.wav"],
        "brass": by_name["1 Brass.wav"],
        "fx": by_name["2 FX.wav"],
        "synth": by_name["3 Synth.wav"],
        "keyboard": by_name["4 Keyboard.wav"],
        "guitar": by_name["5 Guitar.wav"],
        "bass": by_name["6 Bass.wav"],
        "drums": by_name["7 Drums.wav"],
        "support_vocal": by_name["8 Vocals.wav"],
        "lead_vocal": by_name["9 Vocals.wav"],
        "new_track_silent": by_name["10 New Track.wav"],
    }


def read_padded(path: Path, sr: int, length: int) -> np.ndarray:
    got_sr, y, _dtype = base.read_wav(path)
    if got_sr != sr:
        raise RuntimeError(f"Sample-rate mismatch: {path} is {got_sr}, expected {sr}")
    return base.pad_or_trim(y, length)


def source_metrics(paths: dict[str, Path]) -> list[dict[str, Any]]:
    return [base.audio_metrics(path, key) for key, path in paths.items()]


def process_support_vocal(y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    x = base.process_female_layer(y, sr, lead, target_delta_db=-9.6)
    x = base.butter_filter(x, sr, "highpass", 145, 2)
    x = base.dynamic_band_tame(x, sr, 1800, 4700, max_cut_db=0.55, percentile=55.0, smooth_ms=120.0)
    x = base.dynamic_band_tame(x, sr, 5400, 9200, max_cut_db=1.9, percentile=58.0, smooth_ms=8.0)
    return base.peak_cap(x.astype(np.float32), -4.8)


def process_music(role: str, y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    if role in {"brass", "fx", "new_track_silent"} and base.peak(y) < float(db_to_amp(-45.0)):
        return y.astype(np.float32)
    x = base.process_instrument("fx" if role == "new_track_silent" else role, y, sr, lead)
    if role in {"synth", "keyboard", "guitar"}:
        x = base.sidechain_band_duck(x, lead, sr, 1700, 4300, max_cut_db=0.82, percentile=54.0, smooth_ms=110.0)
    if role == "bass":
        mono = np.mean(x, axis=1, dtype=np.float64).astype(np.float32)
        x = np.column_stack([mono, mono]).astype(np.float32)
    return base.peak_cap(x.astype(np.float32), -2.5)


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, Any]]:
    sr, reference, _dtype = base.read_wav(paths["full_reference"])
    length = len(reference)
    lead_raw = read_padded(paths["lead_vocal"], sr, length)
    support_raw = read_padded(paths["support_vocal"], sr, length)

    lead = base.process_lead_vocal(lead_raw, sr)
    support = process_support_vocal(support_raw, sr, lead)
    reverb, delay = base.make_space(lead, sr)

    processed: dict[str, Path] = {
        "full_reference": PROCESSED / "source_full_mix_muted_reference.wav",
        "lead_vocal": PROCESSED / "lead_vocal_9_clean_center.wav",
        "support_vocal": PROCESSED / "support_vocal_8_tucked_wide.wav",
        "vocal_reverb": PROCESSED / "vocal_reverb_print_dark.wav",
        "vocal_delay": PROCESSED / "vocal_delay_print_dark.wav",
    }
    base.write_wav(processed["full_reference"], sr, reference)
    base.write_wav(processed["lead_vocal"], sr, lead)
    base.write_wav(processed["support_vocal"], sr, support)
    base.write_wav(processed["vocal_reverb"], sr, reverb)
    base.write_wav(processed["vocal_delay"], sr, delay)

    for role in ("brass", "fx", "synth", "keyboard", "guitar", "bass", "drums", "new_track_silent"):
        raw = read_padded(paths[role], sr, length)
        out = process_music(role, raw, sr, lead)
        processed[role] = PROCESSED / f"{role}_processed.wav"
        base.write_wav(processed[role], sr, out)

    vocal_solo = lead + support * float(db_to_amp(-0.8)) + reverb + delay
    base.write_wav(VOCAL_SOLO, sr, base.peak_cap(vocal_solo.astype(np.float32), -1.5))
    selection = {
        "lead_vocal": rel(paths["lead_vocal"]),
        "support_vocal": rel(paths["support_vocal"]),
        "lead_active_rms_dbfs": round(base.active_rms_db(lead), 2),
        "support_active_rms_dbfs": round(base.active_rms_db(support), 2),
        "support_vs_lead_db": round(base.active_rms_db(support) - base.active_rms_db(lead), 2),
        "muted_reference": rel(paths["full_reference"]),
        "near_silent_retained": [rel(paths["brass"]), rel(paths["fx"]), rel(paths["new_track_silent"])],
    }
    write_json(REPORTS / "source_selection.json", selection)
    return processed, sr, length / sr, selection


def lua_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    track_plan = [
        ("SOURCE full mix reference muted", "full_reference", -99.0, 0.0, True, "reference", []),
        ("01 Brass retained near-silent", "brass", -2.0, 0.14, False, "brass", ["VST: ReaEQ (Cockos)"]),
        ("02 FX retained near-silent", "fx", -2.0, -0.14, False, "fx", ["VST: ReaEQ (Cockos)"]),
        ("03 Synth main pocket", "synth", -1.0, -0.04, False, "synth", ["VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"]),
        ("04 Keyboard width support", "keyboard", -0.4, 0.10, False, "keyboard", ["VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"]),
        ("05 Guitar side texture", "guitar", -0.2, -0.16, False, "guitar", ["VST: ReaEQ (Cockos)"]),
        ("06 Bass mono body", "bass", 0.45, 0.0, False, "bass", ["VST: ReaEQ (Cockos)"]),
        ("07 Drums transient frame", "drums", -0.2, 0.0, False, "drums", ["VST: ReaEQ (Cockos)"]),
        ("08 Support vocal tucked wide", "support_vocal", -4.4, 0.0, False, "support_vocal", ["JS: Codex Vocal AI Artifact Split Tamer", "VST: ReaEQ (Cockos)", "JS: De-esser"]),
        ("09 Lead vocal clean center", "lead_vocal", 0.75, 0.0, False, "lead_vocal", ["JS: Codex Vocal AI Artifact Split Tamer", "VST: ReaEQ (Cockos)", "VST3: TDR Nova (Tokyo Dawn Labs)", "JS: De-esser", "VST: ReaComp (Cockos)", "VST: ReaLimit (Cockos)"]),
        ("Vocal reverb print dark", "vocal_reverb", -2.6, 0.0, False, "vocal_reverb", ["VST: ReaEQ (Cockos)"]),
        ("Vocal delay print dark", "vocal_delay", -2.8, 0.0, False, "vocal_delay", ["VST: ReaEQ (Cockos)"]),
        ("10 New Track silent retained", "new_track_silent", -99.0, 0.0, True, "new_track_silent", []),
    ]

    def lua_long_string(value: str) -> str:
        return "[[" + value.replace("]", "] ]") + "]]"

    def lua_array(values: list[str]) -> str:
        return "{" + ", ".join(lua_long_string(value) for value in values) + "}"

    lua_tracks = "{\n" + "\n".join(
        "  {"
        + f"name={lua_long_string(name)}, "
        + f"path={lua_long_string(lua_path(processed[key]))}, "
        + f"volume_db={volume:.6f}, "
        + f"pan={pan:.6f}, "
        + f"muted={'true' if muted else 'false'}, "
        + f"trace_label={lua_long_string(trace_label)}, "
        + f"fx={lua_array(fx)}"
        + "},"
        for name, key, volume, pan, muted, trace_label, fx in track_plan
    ) + "\n}"

    project_notes = (
        "chuchu_v01 mix master. Source full mix is muted reference only. "
        "9 Vocals is lead_vocal, 8 Vocals is support_vocal. "
        "No tune/pitch insert on main vocal. Codex Vocal AI Artifact Split Tamer "
        "is first FX slot on lead vocal and support vocal when available."
    )
    build = f'''
local rpp = [[{lua_path(RPP)}]]
local render_dir = [[{lua_path(RENDERS)}]]
local trace_path = [[{lua_path(TRACE_JSON)}]]
local log_path = [[{lua_path(REPORTS / "build_reaper.log")}]]
local duration = {duration:.9f}
local tracks = {lua_tracks}
local rows = {{}}
local function lin(db) return 10 ^ ((db or 0) / 20) end
local function esc(s) s=tostring(s or ""); return s:gsub("\\\\","\\\\\\\\"):gsub('"','\\\\"'):gsub("\\n","\\\\n") end
local function q(s) return string.format("%q", s) end
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
local function add_row(track, stage, status, plugin, fx_index, wet, reason)
  rows[#rows+1] = string.format('{{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":%s,"reason":"%s"}}', esc(track), esc(stage), esc(status), esc(plugin), tonumber(fx_index or -1), wet and tostring(wet) or "null", esc(reason))
  log(track .. " | " .. stage .. " | " .. status .. " | " .. tostring(plugin))
end
local function write_trace()
  local f = assert(io.open(trace_path, "w"))
  f:write('{{\\n  "slug": "{SLUG}",\\n  "rows": [\\n')
  for i,row in ipairs(rows) do f:write("    " .. row .. (i == #rows and "\\n" or ",\\n")) end
  f:write("  ]\\n}}\\n")
  f:close()
end
local function make_track(spec)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", spec.name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(spec.volume_db or 0))
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", spec.pan or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", spec.muted and 1 or 0)
  return tr
end
local function insert_media(tr, path)
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then error("source failed: " .. path) end
  local item = reaper.AddMediaItemToTrack(tr)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", duration)
end
local function add_fx(tr, label, plugin, fx_order)
  local idx = reaper.TrackFX_AddByName(tr, plugin, false, -1)
  if idx and idx >= 0 then
    add_row(label, fx_order == 1 and "first-slot cleanup/processing" or "mix processing", "loaded", plugin, idx, 1.0, "")
    return idx
  end
  add_row(label, fx_order == 1 and "first-slot cleanup/processing" or "mix processing", "missing", plugin, -1, 1.0, "")
  if label == "lead_vocal" and fx_order == 1 then write_trace(); error("required first-slot Codex vocal artifact tamer missing") end
  return -1
end
os.execute("mkdir -p " .. q(render_dir))
os.execute("mkdir -p " .. q([[{lua_path(REPORTS)}]]))
os.remove(log_path)
os.remove(trace_path)
reaper.Main_OnCommand(40023, 0)
for _,spec in ipairs(tracks) do
  local tr = make_track(spec)
  insert_media(tr, spec.path)
  for i,plugin in ipairs(spec.fx) do
    add_fx(tr, spec.trace_label, plugin, i)
  end
end
local master = reaper.GetMasterTrack(0)
local master_fx = {{"VST: ReaEQ (Cockos)", "VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaLimit (Cockos)"}}
for i,plugin in ipairs(master_fx) do
  local idx = reaper.TrackFX_AddByName(master, plugin, false, -1)
  if idx and idx >= 0 then add_row("master", "master bus clean guard", "loaded", plugin, idx, 1.0, "") else add_row("master", "master bus clean guard", "missing", plugin, -1, 1.0, "") end
end
reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", duration, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "chuchu_v01_REAPERPRINT_24-48", true)
reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", [[{project_notes}]], true)
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
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "chuchu_v01_REAPERPRINT_24-48", true)
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
    build_log = REPORTS / "build_reaper.log"
    if "wrapper ok" not in build_log.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"REAPER build wrapper failed: {build_log}")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_RENDER_LUA)], check=True)
    render_log = REPORTS / "render_prepare.log"
    if "wrapper ok" not in render_log.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"REAPER render wrapper failed: {render_log}")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(RPP)], check=True)
    if not REAPER_PRINT.exists():
        matches = sorted(RENDERS.glob("chuchu_v01_REAPERPRINT_24-48*.wav"))
        if matches:
            matches[-1].rename(REAPER_PRINT)
    if not REAPER_PRINT.exists():
        raise FileNotFoundError(REAPER_PRINT)


def run_gate() -> dict[str, Any]:
    proc = subprocess.run(
        ["python3", "tools/validate_reaper_vocal_chain_gate.py", "--trace", rel(TRACE_JSON)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout)
    write_json(REPORTS / "vocal_chain_gate.json", payload)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    return payload


def final_master() -> None:
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=230:t=q:w=1:g=-0.35,"
        "equalizer=f=3300:t=q:w=0.9:g=0.24,"
        "equalizer=f=11800:t=q:w=0.8:g=-0.35,"
        "loudnorm=I=-10.8:TP=-1.15:LRA=3.8:linear=false,"
        "alimiter=limit=0.84:attack=2:release=80:level=false"
    )
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(REAPER_PRINT),
            "-af",
            filter_graph,
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(FINAL_WAV),
        ],
        check=True,
    )
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(FINAL_MP3)],
        check=True,
    )


def write_ab_preview(source_ref: Path) -> None:
    temp = REPORTS / "_ab_preview"
    temp.mkdir(parents=True, exist_ok=True)
    before = temp / "before.wav"
    after = temp / "after.wav"
    concat = temp / "concat.txt"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "28", "-t", "22", "-i", str(source_ref), "-c:a", "pcm_s16le", str(before)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "28", "-t", "22", "-i", str(FINAL_WAV), "-c:a", "pcm_s16le", str(after)], check=True)
    concat.write_text(f"file '{before}'\nfile '{after}'\n", encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "320k", str(AB_PREVIEW_MP3)], check=True)
    shutil.rmtree(temp, ignore_errors=True)


def write_trace_md() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    lines = ["# Actual REAPER Plugin Trace", "", "| track | fx | status | plugin | stage |", "| --- | ---: | --- | --- | --- |"]
    for row in payload.get("rows", []):
        lines.append(f"| {row.get('track')} | {row.get('fx_index')} | {row.get('status')} | {row.get('plugin')} | {row.get('stage')} |")
    TRACE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(paths: dict[str, Path], selection: dict[str, Any], gate: dict[str, Any]) -> None:
    rows = source_metrics(paths)
    rows.extend(
        [
            base.audio_metrics(VOCAL_SOLO, "processed_vocal_solo"),
            base.audio_metrics(REAPER_PRINT, "reaper_print"),
            base.audio_metrics(FINAL_WAV, "final_master_wav"),
            base.audio_metrics(FINAL_MP3, "final_master_mp3"),
        ]
    )
    write_json(REPORTS / "qc_metrics.json", rows)
    write_csv(REPORTS / "qc_metrics.csv", rows)
    source = next(row for row in rows if row["label"] == "full_reference")
    final = next(row for row in rows if row["label"] == "final_master_wav")
    mp3 = next(row for row in rows if row["label"] == "final_master_mp3")
    qc = {
        "passed": bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -0.8 and (mp3.get("true_peak_dbfs") or 99) <= -0.2,
        "status": "genre_based_draft",
        "source_lufs": source.get("integrated_lufs"),
        "reaper_print_lufs": next(row for row in rows if row["label"] == "reaper_print").get("integrated_lufs"),
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "vocal_gate": gate,
        "selection": selection,
    }
    write_json(REPORTS / "qc_summary.json", qc)
    notes = [
        "# Chuchu v01 Mix Master Report",
        "",
        "## Intent",
        "",
        "- Build a REAPER-rendered stem mix/master from the user-provided zip.",
        "- Keep `0 추추.wav` as muted full-mix reference only.",
        "- Treat `9 Vocals.wav` as lead and `8 Vocals.wav` as tucked support based on measured level.",
        "- Retain near-silent Brass/FX/New Track stems in the project for source completeness.",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- REAPER print: `{rel(REAPER_PRINT)}`",
        f"- Vocal solo check: `{rel(VOCAL_SOLO)}`",
        f"- A/B preview MP3: `{rel(AB_PREVIEW_MP3)}`",
        f"- REAPER project: `{rel(RPP)}`",
        f"- Deliverable ZIP: `{rel(DELIVERABLE_ZIP)}`",
        "",
        "## QC",
        "",
        f"- Source full mix: `{source.get('integrated_lufs')}` LUFS / TP `{source.get('true_peak_dbfs')}` dBFS",
        f"- Final WAV: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}` dBFS",
        f"- Final MP3 TP: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Vocal chain gate passed: `{gate.get('passed')}`",
        f"- Support vocal vs lead active RMS: `{selection.get('support_vs_lead_db')}` dB",
        "",
        "## Notes",
        "",
        "- No external reference matching was performed; status remains `genre_based_draft`.",
        "- No pitch/tune insert was used on the main vocal.",
        "- Actual REAPER plugin loading is recorded in `actual_reaper_plugin_trace.json`.",
        "- Final headphone A/B approval is still the subjective acceptance gate.",
    ]
    REPORT_MD.write_text("\n".join(notes) + "\n", encoding="utf-8")


def build_zip() -> None:
    DELIVERABLE_ZIP.unlink(missing_ok=True)
    files = [
        FINAL_WAV,
        FINAL_MP3,
        REAPER_PRINT,
        VOCAL_SOLO,
        AB_PREVIEW_MP3,
        RPP,
        BUILD_LUA,
        RENDER_LUA,
        TRACE_JSON,
        TRACE_MD,
        REPORTS / "vocal_chain_gate.json",
        REPORTS / "source_selection.json",
        REPORTS / "qc_metrics.json",
        REPORTS / "qc_metrics.csv",
        REPORTS / "qc_summary.json",
        REPORT_MD,
    ]
    with zipfile.ZipFile(DELIVERABLE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.exists():
                archive.write(path, path.relative_to(ROOT).as_posix())


def main() -> int:
    ensure_dirs()
    paths = find_stems()
    write_json(REPORTS / "source_metrics_preflight.json", source_metrics(paths))
    processed, _sr, duration, selection = write_processed(paths)
    write_reaper_scripts(processed, duration)
    run_reaper()
    write_trace_md()
    gate = run_gate()
    final_master()
    write_ab_preview(paths["full_reference"])
    write_reports(paths, selection, gate)
    build_zip()
    summary = json.loads((REPORTS / "qc_summary.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "final_wav": rel(FINAL_WAV),
                "final_mp3": rel(FINAL_MP3),
                "deliverable_zip": rel(DELIVERABLE_ZIP),
                "reaper_project": rel(RPP),
                "duration_s": round(duration, 3),
                "final_lufs": summary.get("final_lufs"),
                "final_true_peak_dbfs": summary.get("final_true_peak_dbfs"),
                "mp3_true_peak_dbfs": summary.get("mp3_true_peak_dbfs"),
                "vocal_gate_passed": summary.get("vocal_gate", {}).get("passed"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
