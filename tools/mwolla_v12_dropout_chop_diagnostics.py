#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
SOURCE_SLUG = "mwolla_v12_10_anchor_high_quality_master"
SLUG = "mwolla_v12_dropout_chop_diagnostics"

BASE_RPP = ROOT / "reaper" / SOURCE_SLUG / "mwolla_v12_10_ANCHOR_HIGH_QUALITY_MASTER.rpp"
SOURCE_REPORTS = ROOT / "reports" / SOURCE_SLUG
SOURCE_RENDERS = ROOT / "renders" / SOURCE_SLUG
SOURCE_PROCESSED = ROOT / "audio_work" / SOURCE_SLUG / "processed_stems"
SOURCE_STEMS = ROOT / "audio_work" / SOURCE_SLUG / "source_stems"

DIAG_REAPER = ROOT / "reaper" / SLUG
DIAG_RENDERS = ROOT / "renders" / SLUG
DIAG_REPORTS = ROOT / "reports" / SLUG

FINAL_WAV = SOURCE_RENDERS / "mwolla_v12_10_ANCHOR_HIGH_QUALITY_MASTER.wav"
REAPERPRINT_WAV = SOURCE_RENDERS / "mwolla_v12_REAPERPRINT_24-48.wav"
POST_FINAL_WAV = SOURCE_RENDERS / "mwolla_v12_POST_FINAL_LEVEL_LOCK_24-48.wav"
PHRASE_PREMASTER_WAV = SOURCE_RENDERS / "mwolla_v12_PHRASE_LEVELED_PREMASTER_24-48.wav"
SOURCE_REF_WAV = SOURCE_PROCESSED / "source_full_mix_reference.wav"
LEAD_PROCESSED_WAV = SOURCE_PROCESSED / "lead_vocal_clean_center.wav"
LEAD_RAW_REF_WAV = SOURCE_PROCESSED / "lead_vocal_raw_center_reference.wav"
LAYER_PROCESSED_WAV = SOURCE_PROCESSED / "11_vocal_layer_support_wide_tucked.wav"

WINDOW_S = 0.05
DIAG_START_S = 0.0
DIAG_END_S = 16.0


VARIANTS: list[dict[str, Any]] = [
    {
        "id": "baseline",
        "label": "baseline",
        "ops": [],
        "reason": "v12 project segment without diagnostic bypass changes",
    },
    {
        "id": "premaster_all_bypass",
        "label": "PREMASTER ReaEQ Nova ReaLimit bypass",
        "ops": [
            {"op": "bypass_fx_track", "track": "PREMASTER BUS", "contains": "ReaEQ"},
            {"op": "bypass_fx_track", "track": "PREMASTER BUS", "contains": "TDR Nova"},
            {"op": "bypass_fx_track", "track": "PREMASTER BUS", "contains": "ReaLimit"},
        ],
        "reason": "priority 1: separate premaster EQ/dynamic EQ/limiter from upstream issues",
    },
    {
        "id": "main_to_music_sidechain_disabled",
        "label": "MAIN_VOCAL_BUS to MUSIC_BUS sidechain disabled",
        "ops": [
            {
                "op": "mute_send",
                "source": "MAIN_VOCAL_BUS",
                "dest": "MUSIC_BUS",
                "require_srcchan": 0,
                "require_dstchan": 2,
            }
        ],
        "reason": "priority 3: separate music bus sidechain ducking",
    },
    {
        "id": "music_bus_nova_bypass",
        "label": "MUSIC_BUS TDR Nova bypass",
        "ops": [{"op": "bypass_fx_track", "track": "MUSIC_BUS", "contains": "TDR Nova"}],
        "reason": "priority 6: separate music bus dynamic EQ",
    },
    {
        "id": "music_bus_kotelnikov_bypass",
        "label": "MUSIC_BUS Kotelnikov bypass",
        "ops": [{"op": "bypass_fx_track", "track": "MUSIC_BUS", "contains": "Kotelnikov"}],
        "reason": "priority 6: separate music bus compression",
    },
    {
        "id": "vocal_gate_expander_bypass",
        "label": "10 and 11 Vocal Gate Expander bypass",
        "ops": [
            {"op": "bypass_fx_track", "track": "10 MAIN_VOCAL_CENTER", "contains": "Codex Vocal Gate Expander"},
            {"op": "bypass_fx_track", "track": "11 VOCAL_LAYER_SUPPORT", "contains": "Codex Vocal Gate Expander"},
        ],
        "reason": "priority 7: separate live JS gate phrase chop",
    },
    {
        "id": "vocal_noise_floor_tamer_bypass",
        "label": "10 and 11 Noise Floor Tamer bypass",
        "ops": [
            {"op": "bypass_fx_track", "track": "10 MAIN_VOCAL_CENTER", "contains": "Codex Noise Floor Tamer"},
            {"op": "bypass_fx_track", "track": "11 VOCAL_LAYER_SUPPORT", "contains": "Codex Noise Floor Tamer"},
        ],
        "reason": "priority 8: separate live noise floor tail truncation",
    },
]


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


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(path)
    x = np.asarray(data)
    if x.dtype == np.int32:
        x = x.astype(np.float64) / float(2**31)
    elif x.dtype == np.int16:
        x = x.astype(np.float64) / float(2**15)
    elif x.dtype == np.uint8:
        x = (x.astype(np.float64) - 128.0) / 128.0
    else:
        x = x.astype(np.float64)
    if x.ndim == 1:
        x = x[:, None]
    return sr, x


def rms_db(x: np.ndarray) -> float:
    if x.size == 0:
        return -180.0
    return float(20.0 * math.log10(math.sqrt(float(np.mean(x * x))) + 1e-18))


def peak_db(x: np.ndarray) -> float:
    if x.size == 0:
        return -180.0
    return float(20.0 * math.log10(float(np.max(np.abs(x))) + 1e-18))


def file_metrics(path: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    sr, x = read_wav(path)
    rows: list[dict[str, Any]] = []
    for event in events:
        start = int(round(float(event["start_s"]) * sr))
        end = int(round(float(event["end_s"]) * sr))
        seg = x[max(0, start) : max(0, end)]
        rows.append(
            {
                "event_id": event["id"],
                "start_s": event["start_s"],
                "end_s": event["end_s"],
                "rms_dbfs": round(rms_db(seg), 2),
                "peak_dbfs": round(peak_db(seg), 2),
            }
        )
    full = x[int(DIAG_START_S * sr) : int(DIAG_END_S * sr)]
    return {
        "path": rel(path),
        "sample_rate": sr,
        "duration_s": round(x.shape[0] / sr, 6),
        "segment_rms_dbfs": round(rms_db(full), 2),
        "segment_peak_dbfs": round(peak_db(full), 2),
        "events": rows,
    }


def window_meters(x: np.ndarray, sr: int, window_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    hop = int(round(sr * window_s))
    frames = x.shape[0] // hop
    y = x[: frames * hop].reshape(frames, hop, x.shape[1])
    rms = np.sqrt(np.mean(y * y, axis=(1, 2)) + 1e-18)
    peak = np.max(np.abs(y), axis=(1, 2)) + 1e-18
    times = np.arange(frames, dtype=np.float64) * hop / sr
    return times, 20 * np.log10(rms), 20 * np.log10(peak)


def local_median(values: np.ndarray, index: int, radius: int = 10) -> float:
    start = max(0, index - radius)
    end = min(values.shape[0], index + radius + 1)
    left = values[start : max(start, index - 1)]
    right = values[min(end, index + 2) : end]
    merged = np.concatenate([left, right])
    if merged.size == 0:
        return float(values[index])
    return float(np.median(merged))


def merge_indices(indices: np.ndarray, times: np.ndarray) -> list[tuple[int, int]]:
    if indices.size == 0:
        return []
    segments: list[tuple[int, int]] = []
    start = int(indices[0])
    last = int(indices[0])
    for raw in indices[1:]:
        idx = int(raw)
        if idx <= last + 2:
            last = idx
        else:
            segments.append((start, last))
            start = idx
            last = idx
    segments.append((start, last))
    return segments


def detect_dropout_events() -> list[dict[str, Any]]:
    inputs = {
        "final": FINAL_WAV,
        "source_ref": SOURCE_REF_WAV,
        "reaperprint": REAPERPRINT_WAV,
        "post_final": POST_FINAL_WAV,
        "phrase_premaster": PHRASE_PREMASTER_WAV,
        "lead_processed": LEAD_PROCESSED_WAV,
        "lead_raw_ref": LEAD_RAW_REF_WAV,
        "layer_processed": LAYER_PROCESSED_WAV,
    }
    sr = None
    audio: dict[str, np.ndarray] = {}
    for key, path in inputs.items():
        this_sr, x = read_wav(path)
        if sr is None:
            sr = this_sr
        elif this_sr != sr:
            raise RuntimeError(f"sample rate mismatch: {key} {this_sr} != {sr}")
        audio[key] = x
    assert sr is not None
    length = min(x.shape[0] for x in audio.values())
    audio = {key: x[:length] for key, x in audio.items()}

    meters: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {
        key: window_meters(x, sr, WINDOW_S) for key, x in audio.items()
    }
    times, final_rms, final_peak = meters["final"]
    source_rms = meters["source_ref"][1]
    reaper_rms = meters["reaperprint"][1]
    post_rms = meters["post_final"][1]
    lead_processed_rms = meters["lead_processed"][1]
    lead_raw_rms = meters["lead_raw_ref"][1]
    layer_processed_rms = meters["layer_processed"][1]

    local = np.array([local_median(final_rms, i) for i in range(final_rms.shape[0])])
    source_delta = source_rms - final_rms
    local_delta = local - final_rms

    active_unexpected_drop = np.where((source_rms > -38.0) & ((source_delta > 10.0) | (local_delta > 10.0)))[0]
    segments = merge_indices(active_unexpected_drop, times)

    events: list[dict[str, Any]] = []
    for seg_index, (start_idx, end_idx) in enumerate(segments, start=1):
        idxs = np.arange(start_idx, end_idx + 1)
        score = np.maximum(source_delta[idxs], local_delta[idxs])
        worst_idx = int(idxs[int(np.argmax(score))])
        if times[worst_idx] >= DIAG_END_S:
            continue
        event = {
            "id": f"E{seg_index:02d}",
            "start_s": round(float(times[start_idx]), 3),
            "end_s": round(float(times[end_idx] + WINDOW_S), 3),
            "duration_s": round(float((end_idx - start_idx + 1) * WINDOW_S), 3),
            "worst_s": round(float(times[worst_idx]), 3),
            "final_rms_dbfs": round(float(np.min(final_rms[idxs])), 2),
            "final_peak_dbfs": round(float(np.min(final_peak[idxs])), 2),
            "source_ref_rms_dbfs_at_worst": round(float(source_rms[worst_idx]), 2),
            "source_minus_final_db_at_worst": round(float(source_delta[worst_idx]), 2),
            "local_median_minus_final_db_at_worst": round(float(local_delta[worst_idx]), 2),
            "reaperprint_rms_dbfs_at_worst": round(float(reaper_rms[worst_idx]), 2),
            "post_final_rms_dbfs_at_worst": round(float(post_rms[worst_idx]), 2),
            "lead_processed_rms_dbfs_at_worst": round(float(lead_processed_rms[worst_idx]), 2),
            "lead_raw_rms_dbfs_at_worst": round(float(lead_raw_rms[worst_idx]), 2),
            "layer_processed_rms_dbfs_at_worst": round(float(layer_processed_rms[worst_idx]), 2),
        }
        events.append(event)

    events.sort(
        key=lambda e: max(float(e["source_minus_final_db_at_worst"]), float(e["local_median_minus_final_db_at_worst"])),
        reverse=True,
    )
    # Keep the highest-severity user-facing problem windows in the first diagnostic render span.
    events = [event for event in events if event["duration_s"] >= 0.05][:10]
    write_json(
        DIAG_REPORTS / "dropout_timestamp_candidates.json",
        {
            "schema": "mwolla-v12-dropout-timestamp-candidates-v1",
            "source_final": rel(FINAL_WAV),
            "reference_for_unexpected_activity": rel(SOURCE_REF_WAV),
            "window_s": WINDOW_S,
            "render_region_s": {"start": DIAG_START_S, "end": DIAG_END_S},
            "selection_rule": "source_ref_rms > -38 dBFS and final is >10 dB below source_ref or local median in 50 ms windows",
            "events": events,
        },
    )
    return events


def source_stem_table(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = sorted(path for path in SOURCE_STEMS.glob("*.wav") if not path.name.startswith("__"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        sr, x = read_wav(path)
        row: dict[str, Any] = {"file": rel(path)}
        for event in events:
            seg = x[int(float(event["start_s"]) * sr) : int(float(event["end_s"]) * sr)]
            row[f"{event['id']}_rms_dbfs"] = round(rms_db(seg), 2)
        rows.append(row)
    write_csv(DIAG_REPORTS / "source_stem_event_rms.csv", rows)
    return rows


def processed_stem_table(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = sorted(path for path in SOURCE_PROCESSED.glob("*.wav") if path.is_file())
    rows: list[dict[str, Any]] = []
    for path in paths:
        sr, x = read_wav(path)
        row: dict[str, Any] = {"file": rel(path)}
        for event in events:
            seg = x[int(float(event["start_s"]) * sr) : int(float(event["end_s"]) * sr)]
            row[f"{event['id']}_rms_dbfs"] = round(rms_db(seg), 2)
        rows.append(row)
    write_csv(DIAG_REPORTS / "processed_stem_event_rms.csv", rows)
    return rows


def lua_string(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def write_prepare_lua() -> Path:
    variants_json = json.dumps(VARIANTS, ensure_ascii=False)
    lua = f'''
local base_rpp = [[{lua_string(BASE_RPP)}]]
local render_dir = [[{lua_string(DIAG_RENDERS)}]]
local reaper_dir = [[{lua_string(DIAG_REAPER)}]]
local report_dir = [[{lua_string(DIAG_REPORTS)}]]
local render_start = {DIAG_START_S:.9f}
local render_end = {DIAG_END_S:.9f}
local variants_json = [==[{variants_json}]==]
local rows = {{}}

local function q(s) return string.format("%q", s) end
local function esc(s)
  s = tostring(s or "")
  return s:gsub("\\\\", "\\\\\\\\"):gsub('"', '\\\\"'):gsub("\\n", "\\\\n")
end
local function add_row(variant, area, status, detail)
  rows[#rows + 1] = string.format('{{"variant":"%s","area":"%s","status":"%s","detail":"%s"}}', esc(variant), esc(area), esc(status), esc(detail))
end
local function write_trace()
  local path = report_dir .. "/reaper_variant_prep_trace.json"
  local f = assert(io.open(path, "w"))
  f:write('{{\\n  "schema": "mwolla-v12-dropout-reaper-variant-prep-v1",\\n  "base_rpp": "' .. esc(base_rpp) .. '",\\n  "render_region_s": {{"start": {DIAG_START_S:.3f}, "end": {DIAG_END_S:.3f}}},\\n  "rows": [\\n')
  for i,row in ipairs(rows) do
    f:write("    " .. row .. (i == #rows and "\\n" or ",\\n"))
  end
  f:write("  ]\\n}}\\n")
  f:close()
end
local function json_variants()
  local ok, result = pcall(function()
    return assert(load("return " .. variants_json:gsub('"%s*:', '"=')))()
  end)
  if ok and type(result) == "table" then return result end
  -- Small hand-coded fallback avoids depending on an external JSON library in REAPER.
  return {{
    {{id="baseline", ops={{}}}},
    {{id="premaster_all_bypass", ops={{{{op="bypass_fx_track", track="PREMASTER BUS", contains="ReaEQ"}}, {{op="bypass_fx_track", track="PREMASTER BUS", contains="TDR Nova"}}, {{op="bypass_fx_track", track="PREMASTER BUS", contains="ReaLimit"}}}}}},
    {{id="main_to_music_sidechain_disabled", ops={{{{op="mute_send", source="MAIN_VOCAL_BUS", dest="MUSIC_BUS", require_srcchan=0, require_dstchan=2}}}}}},
    {{id="music_bus_nova_bypass", ops={{{{op="bypass_fx_track", track="MUSIC_BUS", contains="TDR Nova"}}}}}},
    {{id="music_bus_kotelnikov_bypass", ops={{{{op="bypass_fx_track", track="MUSIC_BUS", contains="Kotelnikov"}}}}}},
    {{id="vocal_gate_expander_bypass", ops={{{{op="bypass_fx_track", track="10 MAIN_VOCAL_CENTER", contains="Codex Vocal Gate Expander"}}, {{op="bypass_fx_track", track="11 VOCAL_LAYER_SUPPORT", contains="Codex Vocal Gate Expander"}}}}}},
    {{id="vocal_noise_floor_tamer_bypass", ops={{{{op="bypass_fx_track", track="10 MAIN_VOCAL_CENTER", contains="Codex Noise Floor Tamer"}}, {{op="bypass_fx_track", track="11 VOCAL_LAYER_SUPPORT", contains="Codex Noise Floor Tamer"}}}}}},
  }}
end
local function track_name(track)
  local ok, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  if ok then return name end
  return ""
end
local function find_track(name)
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    if track_name(tr) == name then return tr, i end
  end
  return nil, -1
end
local function fx_name(track, fx)
  local ok, name = reaper.TrackFX_GetFXName(track, fx, "")
  if ok then return name end
  return ""
end
local function bypass_fx(variant, track_name_target, contains)
  local tr = find_track(track_name_target)
  if not tr then
    add_row(variant, "fx_bypass", "missing_track", track_name_target)
    return
  end
  local count = reaper.TrackFX_GetCount(tr)
  local hit = 0
  for fx = 0, count - 1 do
    local name = fx_name(tr, fx)
    if name:lower():find(tostring(contains):lower(), 1, true) then
      reaper.TrackFX_SetEnabled(tr, fx, false)
      hit = hit + 1
      add_row(variant, "fx_bypass", "bypassed", track_name_target .. " fx=" .. fx .. " name=" .. name)
    end
  end
  if hit == 0 then
    add_row(variant, "fx_bypass", "missing_fx", track_name_target .. " contains=" .. tostring(contains))
  end
end
local function mute_send(variant, source_name, dest_name, require_srcchan, require_dstchan)
  local src = find_track(source_name)
  local dst = find_track(dest_name)
  if not src or not dst then
    add_row(variant, "send_mute", "missing_track", tostring(source_name) .. " -> " .. tostring(dest_name))
    return
  end
  local count = reaper.GetTrackNumSends(src, 0)
  local hit = 0
  for send = 0, count - 1 do
    local dest = reaper.GetTrackSendInfo_Value(src, 0, send, "P_DESTTRACK")
    if dest == dst then
      local srcchan = reaper.GetTrackSendInfo_Value(src, 0, send, "I_SRCCHAN")
      local dstchan = reaper.GetTrackSendInfo_Value(src, 0, send, "I_DSTCHAN")
      local status = "channel_pass"
      if tonumber(dstchan) == 0 then status = "FAIL_1_2_to_1_2" end
      if require_srcchan and tonumber(srcchan) ~= tonumber(require_srcchan) then status = "FAIL_srcchan" end
      if require_dstchan and tonumber(dstchan) ~= tonumber(require_dstchan) then status = "FAIL_dstchan" end
      add_row(variant, "sidechain_channel", status, source_name .. " -> " .. dest_name .. " srcchan=" .. tostring(srcchan) .. " dstchan=" .. tostring(dstchan))
      reaper.SetTrackSendInfo_Value(src, 0, send, "B_MUTE", 1)
      add_row(variant, "send_mute", "muted", source_name .. " -> " .. dest_name .. " send=" .. send)
      hit = hit + 1
    end
  end
  if hit == 0 then
    add_row(variant, "send_mute", "missing_send", source_name .. " -> " .. dest_name)
  end
end
local function inspect_envelopes(variant)
  local names = {{"MUSIC_BUS", "VOCAL_BUS", "PREMASTER BUS", "10 MAIN_VOCAL_CENTER", "11 VOCAL_LAYER_SUPPORT"}}
  for _, name in ipairs(names) do
    local tr = find_track(name)
    if tr then
      local env_count = reaper.CountTrackEnvelopes(tr)
      add_row(variant, "envelope_count", "observed", name .. " envelopes=" .. tostring(env_count))
      for env = 0, env_count - 1 do
        local envelope = reaper.GetTrackEnvelope(tr, env)
        local ok, env_name = reaper.GetEnvelopeName(envelope, "")
        local points = reaper.CountEnvelopePoints(envelope)
        add_row(variant, "envelope_detail", "observed", name .. " env=" .. tostring(ok and env_name or "") .. " points=" .. tostring(points))
      end
    else
      add_row(variant, "envelope_count", "missing_track", name)
    end
  end
end
local function inspect_sidechain(variant)
  mute_send(variant, "MAIN_VOCAL_BUS", "MUSIC_BUS", 0, 2)
  -- Undo only the mute for baseline inspection.
  local src = find_track("MAIN_VOCAL_BUS")
  local dst = find_track("MUSIC_BUS")
  if src and dst then
    local count = reaper.GetTrackNumSends(src, 0)
    for send = 0, count - 1 do
      local dest = reaper.GetTrackSendInfo_Value(src, 0, send, "P_DESTTRACK")
      if dest == dst then reaper.SetTrackSendInfo_Value(src, 0, send, "B_MUTE", 0) end
    end
  end
end
local function apply_ops(variant)
  for _, op in ipairs(variant.ops or {{}}) do
    if op.op == "bypass_fx_track" then
      bypass_fx(variant.id, op.track, op.contains)
    elseif op.op == "mute_send" then
      mute_send(variant.id, op.source, op.dest, op.require_srcchan, op.require_dstchan)
    else
      add_row(variant.id, "operation", "unknown", tostring(op.op))
    end
  end
end
local function save_variant(variant)
  reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
  reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", render_start, true)
  reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", render_end, true)
  reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
  reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "mwolla_v12_DIAG_" .. variant.id .. "_0-16s", true)
  reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)
  local path = reaper_dir .. "/mwolla_v12_DIAG_" .. variant.id .. ".rpp"
  reaper.Main_SaveProjectEx(0, path, 0)
  add_row(variant.id, "variant_rpp", "saved", path)
end

os.execute("mkdir -p " .. q(render_dir))
os.execute("mkdir -p " .. q(reaper_dir))
os.execute("mkdir -p " .. q(report_dir))

local variants = json_variants()
for _, variant in ipairs(variants) do
  reaper.Main_openProject(base_rpp)
  inspect_envelopes(variant.id)
  inspect_sidechain(variant.id)
  apply_ops(variant)
  save_variant(variant)
end
write_trace()
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    path = DIAG_REAPER / "prepare_mwolla_v12_dropout_diagnostic_variants.lua"
    run_path = DIAG_REAPER / "run_prepare_mwolla_v12_dropout_diagnostic_variants.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lua, encoding="utf-8")
    run_path.write_text(f"dofile([[{lua_string(path)}]])\n", encoding="utf-8")
    return run_path


def run_reaper_prepare(run_lua: Path) -> None:
    subprocess.run(
        [str(REAPER_BIN), "-newinst", "-nosplash", str(run_lua)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )


def render_variants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        rpp = DIAG_REAPER / f"mwolla_v12_DIAG_{variant['id']}.rpp"
        expected = DIAG_RENDERS / f"mwolla_v12_DIAG_{variant['id']}_0-16s.wav"
        start = time.time()
        proc = subprocess.run(
            [str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(rpp)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=180,
        )
        rows.append(
            {
                "variant": variant["id"],
                "label": variant["label"],
                "rpp": rel(rpp),
                "render": rel(expected),
                "exists": expected.exists(),
                "bytes": expected.stat().st_size if expected.exists() else 0,
                "returncode": proc.returncode,
                "elapsed_s": round(time.time() - start, 2),
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
        if proc.returncode != 0 or not expected.exists():
            raise RuntimeError(f"REAPER render failed for {variant['id']}: {proc.stderr[-2000:]}")
    write_json(DIAG_REPORTS / "render_variant_manifest.json", {"schema": "mwolla-v12-dropout-render-variants-v1", "rows": rows})
    return rows


def write_problem_excerpts(render_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in render_rows:
        variant = row["variant"]
        source = ROOT / row["render"]
        sr, data = wavfile.read(source)
        end = min(data.shape[0], int(round(DIAG_END_S * sr)))
        excerpt = data[int(round(DIAG_START_S * sr)) : end]
        output = DIAG_RENDERS / f"mwolla_v12_DIAG_{variant}_PROBLEM_0-16s.wav"
        wavfile.write(output, sr, excerpt)
        rows.append(
            {
                "variant": variant,
                "source_full_reaper_render": row["render"],
                "problem_excerpt": rel(output),
                "start_s": DIAG_START_S,
                "end_s": DIAG_END_S,
                "duration_s": round(excerpt.shape[0] / sr, 6),
                "sample_rate": sr,
                "bytes": output.stat().st_size,
            }
        )
    write_json(
        DIAG_REPORTS / "problem_excerpt_manifest.json",
        {"schema": "mwolla-v12-dropout-problem-excerpts-v1", "rows": rows},
    )
    return rows


def analyze_variant_renders(events: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_path = DIAG_RENDERS / "mwolla_v12_DIAG_baseline_0-16s.wav"
    source_metrics = file_metrics(SOURCE_REF_WAV, events)
    baseline = file_metrics(baseline_path, events)
    variant_metrics: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    source_by_event = {row["event_id"]: row for row in source_metrics["events"]}
    baseline_by_event = {row["event_id"]: row for row in baseline["events"]}

    for variant in VARIANTS:
        path = DIAG_RENDERS / f"mwolla_v12_DIAG_{variant['id']}_0-16s.wav"
        metrics = file_metrics(path, events)
        metrics["variant"] = variant["id"]
        metrics["label"] = variant["label"]
        metrics["reason"] = variant["reason"]
        event_rows = []
        for row in metrics["events"]:
            eid = row["event_id"]
            source_row = source_by_event[eid]
            base_row = baseline_by_event[eid]
            source_minus_variant = round(float(source_row["rms_dbfs"]) - float(row["rms_dbfs"]), 2)
            baseline_minus_variant = round(float(base_row["rms_dbfs"]) - float(row["rms_dbfs"]), 2)
            variant_minus_baseline = round(float(row["rms_dbfs"]) - float(base_row["rms_dbfs"]), 2)
            cleared = source_minus_variant < 15.0 and variant_minus_baseline > 8.0
            out = {
                "variant": variant["id"],
                "event_id": eid,
                "start_s": row["start_s"],
                "end_s": row["end_s"],
                "variant_rms_dbfs": row["rms_dbfs"],
                "variant_peak_dbfs": row["peak_dbfs"],
                "source_ref_rms_dbfs": source_row["rms_dbfs"],
                "baseline_rms_dbfs": base_row["rms_dbfs"],
                "source_minus_variant_db": source_minus_variant,
                "variant_minus_baseline_db": variant_minus_baseline,
                "baseline_minus_variant_db": baseline_minus_variant,
                "cleared_by_this_bypass": cleared,
            }
            event_rows.append(out)
            csv_rows.append(out)
        metrics["event_comparison"] = event_rows
        variant_metrics.append(metrics)

    write_csv(DIAG_REPORTS / "variant_event_comparison.csv", csv_rows)
    payload = {
        "schema": "mwolla-v12-dropout-variant-comparison-v1",
        "clear_definition": "source_minus_variant_db < 15 and variant_minus_baseline_db > 8 for the same event",
        "source_reference": source_metrics,
        "baseline": baseline,
        "variants": variant_metrics,
    }
    write_json(DIAG_REPORTS / "variant_event_comparison.json", payload)
    return payload


def inspect_static_evidence(events: list[dict[str, Any]], variant_payload: dict[str, Any]) -> dict[str, Any]:
    prep_trace_path = DIAG_REPORTS / "reaper_variant_prep_trace.json"
    prep_trace = json.loads(prep_trace_path.read_text(encoding="utf-8")) if prep_trace_path.exists() else {"rows": []}
    rows = prep_trace.get("rows", [])
    sidechain_rows = [row for row in rows if row.get("area") == "sidechain_channel"]
    envelope_rows = [row for row in rows if str(row.get("area", "")).startswith("envelope")]
    sidechain_fail = any("FAIL_1_2_to_1_2" in str(row.get("status", "")) for row in sidechain_rows)
    sidechain_channel_pass = any(
        row.get("status") == "channel_pass"
        and "MAIN_VOCAL_BUS -> MUSIC_BUS" in str(row.get("detail"))
        and "srcchan=0" in str(row.get("detail"))
        and "dstchan=2" in str(row.get("detail"))
        for row in sidechain_rows
    )
    envelope_points = []
    for row in envelope_rows:
        detail = str(row.get("detail", ""))
        if "points=" in detail:
            try:
                points = int(detail.rsplit("points=", 1)[-1])
            except ValueError:
                points = 0
            if points > 0:
                envelope_points.append(row)

    vocal_gap = json.loads((SOURCE_REPORTS / "vocal_gap_cleanup_decisions.json").read_text(encoding="utf-8"))
    recon = json.loads((SOURCE_REPORTS / "vocal_reconstruction_clip_gain_report.json").read_text(encoding="utf-8"))

    cleared_by: list[str] = []
    for variant in variant_payload["variants"]:
        if variant["variant"] == "baseline":
            continue
        if any(row["cleared_by_this_bypass"] for row in variant["event_comparison"]):
            cleared_by.append(variant["variant"])

    # The user-provided bucket list does not include printed pre-render gap cleanup. Keep
    # the requested one-bucket classification, but retain the exact subtype as evidence.
    if "premaster_all_bypass" in cleared_by:
        bucket = "PREMASTER"
        subtype = "premaster processing or plugin/dropout"
    elif "main_to_music_sidechain_disabled" in cleared_by:
        bucket = "MUSIC_BUS sidechain"
        subtype = "music bus sidechain ducking"
    elif "music_bus_nova_bypass" in cleared_by or "music_bus_kotelnikov_bypass" in cleared_by:
        bucket = "MUSIC_BUS sidechain"
        subtype = "music bus dynamic EQ/compression pressure"
    elif "vocal_gate_expander_bypass" in cleared_by or "vocal_noise_floor_tamer_bypass" in cleared_by:
        bucket = "Gate Expander"
        subtype = "live JS vocal gate/noise floor tail chopping"
    elif envelope_points:
        bucket = "automation"
        subtype = "track/send/fx envelope points found in inspected tracks"
    else:
        bucket = "Gate Expander"
        subtype = "printed pre-render vocal gap cleanup/clip-gain gating, not fixed by live JS bypass"

    payload = {
        "schema": "mwolla-v12-dropout-root-cause-classification-v1",
        "requested_category": bucket,
        "exact_subtype": subtype,
        "bypass_stage_that_cleared_events": cleared_by,
        "sidechain_channel": {
            "main_to_music_srcchan": 0,
            "main_to_music_dstchan": 2,
            "interpretation": "REAPER 0-based dstchan=2 means destination 3/4",
            "required_1_2_to_3_4_passed": sidechain_channel_pass and not sidechain_fail,
            "fail_1_2_to_1_2": sidechain_fail,
            "rows": sidechain_rows,
        },
        "automation_envelope_scan": {
            "tracks": ["MUSIC_BUS", "VOCAL_BUS", "PREMASTER BUS", "10 MAIN_VOCAL_CENTER", "11 VOCAL_LAYER_SUPPORT"],
            "envelope_points_found": len(envelope_points),
            "envelope_rows_with_points": envelope_points,
            "all_rows": envelope_rows,
        },
        "source_processing_evidence": {
            "vocal_gap_cleanup": vocal_gap,
            "vocal_reconstruction_gap_floor_db": recon.get("gap_floor_db"),
            "vocal_reconstruction_non_vocal_windows_attenuated_count": recon.get("non_vocal_windows_attenuated_count"),
            "lead_events_show_raw_active_processed_low": [
                {
                    "event_id": event["id"],
                    "start_s": event["start_s"],
                    "end_s": event["end_s"],
                    "lead_raw_rms_dbfs_at_worst": event["lead_raw_rms_dbfs_at_worst"],
                    "lead_processed_rms_dbfs_at_worst": event["lead_processed_rms_dbfs_at_worst"],
                    "raw_minus_processed_db": round(
                        float(event["lead_raw_rms_dbfs_at_worst"]) - float(event["lead_processed_rms_dbfs_at_worst"]),
                        2,
                    ),
                }
                for event in events
            ],
        },
    }
    write_json(DIAG_REPORTS / "root_cause_classification.json", payload)
    return payload


def write_report(
    events: list[dict[str, Any]],
    render_rows: list[dict[str, Any]],
    excerpt_rows: list[dict[str, Any]],
    variant_payload: dict[str, Any],
    root_cause: dict[str, Any],
) -> None:
    lines = [
        "# Mwolla v12 Dropout/Chop Diagnostic Report",
        "",
        "## Scope",
        "",
        "- Target: v12 dropout/chop diagnosis only.",
        "- Loudness was not increased.",
        "- No Ozone, OTT, or clipper was added.",
        "- External plugin parameters were not written.",
        f"- Problem analysis/excerpt region: `{DIAG_START_S:.2f}-{DIAG_END_S:.2f}s`.",
        "- REAPER diagnostic renders are full-length; matching 0-16s problem excerpts are written separately for review.",
        "",
        "## Timestamp Candidates",
        "",
        "| event | range | worst | final RMS | final peak | source ref RMS | source-final delta | lead raw | lead processed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for event in events[:8]:
        lines.append(
            f"| {event['id']} | {event['start_s']}-{event['end_s']}s | {event['worst_s']}s | "
            f"{event['final_rms_dbfs']} | {event['final_peak_dbfs']} | {event['source_ref_rms_dbfs_at_worst']} | "
            f"{event['source_minus_final_db_at_worst']} | {event['lead_raw_rms_dbfs_at_worst']} | {event['lead_processed_rms_dbfs_at_worst']} |"
        )
    lines.extend(
        [
            "",
            "## Bypass Render Manifest",
            "",
            "| variant | render exists | bytes | elapsed |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in render_rows:
        lines.append(f"| {row['variant']} | {row['exists']} | {row['bytes']} | {row['elapsed_s']}s |")

    lines.extend(
        [
            "",
            "## Problem Excerpts",
            "",
            "| variant | excerpt | duration | bytes |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for row in excerpt_rows:
        lines.append(f"| {row['variant']} | `{row['problem_excerpt']}` | {row['duration_s']}s | {row['bytes']} |")

    lines.extend(
        [
            "",
            "## Stage Split",
            "",
            f"- Bypass stage that cleared events by the diagnostic threshold: `{root_cause['bypass_stage_that_cleared_events']}`",
            f"- Requested bucket classification: `{root_cause['requested_category']}`",
            f"- Exact subtype: `{root_cause['exact_subtype']}`",
            f"- MAIN_VOCAL_BUS -> MUSIC_BUS sidechain 1/2 -> 3/4 passed: `{root_cause['sidechain_channel']['required_1_2_to_3_4_passed']}`",
            f"- MAIN_VOCAL_BUS -> MUSIC_BUS 1/2 -> 1/2 fail: `{root_cause['sidechain_channel']['fail_1_2_to_1_2']}`",
            f"- Envelope points found on inspected tracks: `{root_cause['automation_envelope_scan']['envelope_points_found']}`",
            f"- v12 vocal reconstruction gap windows attenuated: `{root_cause['source_processing_evidence']['vocal_reconstruction_non_vocal_windows_attenuated_count']}`",
            f"- v12 vocal reconstruction gap floor: `{root_cause['source_processing_evidence']['vocal_reconstruction_gap_floor_db']}` dB",
            "",
            "## Files",
            "",
            f"- Timestamp candidates: `{rel(DIAG_REPORTS / 'dropout_timestamp_candidates.json')}`",
            f"- Variant comparison JSON: `{rel(DIAG_REPORTS / 'variant_event_comparison.json')}`",
            f"- Variant comparison CSV: `{rel(DIAG_REPORTS / 'variant_event_comparison.csv')}`",
            f"- Problem excerpts: `{rel(DIAG_REPORTS / 'problem_excerpt_manifest.json')}`",
            f"- REAPER variant prep trace: `{rel(DIAG_REPORTS / 'reaper_variant_prep_trace.json')}`",
            f"- Root-cause classification: `{rel(DIAG_REPORTS / 'root_cause_classification.json')}`",
            f"- Source stem event RMS: `{rel(DIAG_REPORTS / 'source_stem_event_rms.csv')}`",
            f"- Processed stem event RMS: `{rel(DIAG_REPORTS / 'processed_stem_event_rms.csv')}`",
        ]
    )
    (DIAG_REPORTS / "mwolla_v12_dropout_chop_diagnostic_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_required_inputs() -> None:
    missing = [
        path
        for path in [
            REAPER_BIN,
            BASE_RPP,
            FINAL_WAV,
            REAPERPRINT_WAV,
            POST_FINAL_WAV,
            PHRASE_PREMASTER_WAV,
            SOURCE_REF_WAV,
            LEAD_PROCESSED_WAV,
            LEAD_RAW_REF_WAV,
            LAYER_PROCESSED_WAV,
        ]
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError("\n".join(str(path) for path in missing))


def main() -> int:
    verify_required_inputs()
    for path in (DIAG_REAPER, DIAG_RENDERS, DIAG_REPORTS):
        path.mkdir(parents=True, exist_ok=True)

    events = detect_dropout_events()
    if not events:
        raise RuntimeError("No dropout timestamp candidates found by the configured thresholds.")
    source_stem_table(events)
    processed_stem_table(events)

    run_lua = write_prepare_lua()
    run_reaper_prepare(run_lua)
    render_rows = render_variants()
    excerpt_rows = write_problem_excerpts(render_rows)
    variant_payload = analyze_variant_renders(events)
    root_cause = inspect_static_evidence(events, variant_payload)
    write_report(events, render_rows, excerpt_rows, variant_payload, root_cause)

    print(json.dumps({
        "report": rel(DIAG_REPORTS / "mwolla_v12_dropout_chop_diagnostic_report.md"),
        "root_cause": rel(DIAG_REPORTS / "root_cause_classification.json"),
        "render_manifest": rel(DIAG_REPORTS / "render_variant_manifest.json"),
        "events": events[:5],
        "classification": {
            "requested_category": root_cause["requested_category"],
            "exact_subtype": root_cause["exact_subtype"],
            "cleared_by": root_cause["bypass_stage_that_cleared_events"],
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
