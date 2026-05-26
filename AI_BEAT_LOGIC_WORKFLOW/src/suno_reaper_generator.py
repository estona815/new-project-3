from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from suno_source_classifier import (
    BASS_OR_808,
    DRUMS,
    FEMALE_BGV,
    FX,
    GUIDE_MIDI,
    MALE_LEAD_VOCAL,
    MUSIC_OR_SYNTH,
    PROBLEM_REFERENCE,
    REFERENCE_ONLY,
    TECHNICAL_MIX_REFERENCE,
    VOCAL_ARTIFACT_QUARANTINE,
    classify_source_file,
)


BUSES = [
    "REF_BUS",
    "DRUM_BUS",
    "BASS_808_BUS",
    "MUSIC_BUS",
    "MALE_LEAD_VOX_BUS",
    "FEMALE_BGV_BUS",
    "VOCAL_FX_BUS",
    "FX_BUS",
    "ARTIFACT_QUARANTINE_BUS",
    "MIX_BUS",
    "MASTER_PREMIX_BUS",
    "PRINT_MASTER_BUS",
    "VOCAL_PLATE_SEND",
    "VOCAL_DELAY_SEND",
    "SHORT_ROOM_SEND",
    "OPTIONAL_WIDE_THROW_SEND",
]

BUS_BY_CATEGORY = {
    REFERENCE_ONLY: "REF_BUS",
    TECHNICAL_MIX_REFERENCE: "REF_BUS",
    PROBLEM_REFERENCE: "REF_BUS",
    DRUMS: "DRUM_BUS",
    BASS_OR_808: "BASS_808_BUS",
    MUSIC_OR_SYNTH: "MUSIC_BUS",
    MALE_LEAD_VOCAL: "MALE_LEAD_VOX_BUS",
    FEMALE_BGV: "FEMALE_BGV_BUS",
    FX: "FX_BUS",
    VOCAL_ARTIFACT_QUARANTINE: "ARTIFACT_QUARANTINE_BUS",
    GUIDE_MIDI: "MUSIC_BUS",
}

MUSICAL_BUSES = [
    "DRUM_BUS",
    "BASS_808_BUS",
    "MUSIC_BUS",
    "MALE_LEAD_VOX_BUS",
    "FEMALE_BGV_BUS",
    "VOCAL_FX_BUS",
    "FX_BUS",
]


def db_to_vol(db: float) -> float:
    return 10.0 ** (float(db) / 20.0)


def lua_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def category_track_defaults(category: str, female_index: int = 0) -> dict[str, object]:
    if category in {REFERENCE_ONLY, TECHNICAL_MIX_REFERENCE, PROBLEM_REFERENCE}:
        return {"vol_db": -18.0, "pan": 0.0, "mute": True, "notes": "reference muted by default"}
    if category == MALE_LEAD_VOCAL:
        return {"vol_db": -6.0, "pan": 0.0, "mute": False, "notes": "fresh center male lead vocal"}
    if category == FEMALE_BGV:
        pan = -0.4 if female_index % 2 == 0 else 0.4
        side = "L" if pan < 0 else "R"
        return {"vol_db": -21.0, "pan": pan, "mute": False, "notes": f"female BGV {side}, low support below male lead"}
    if category == DRUMS:
        return {"vol_db": -10.0, "pan": 0.0, "mute": False, "notes": "fresh conservative drums with headroom"}
    if category == BASS_OR_808:
        return {"vol_db": -10.5, "pan": 0.0, "mute": False, "notes": "mono center bass/808 with headroom"}
    if category == MUSIC_OR_SYNTH:
        return {"vol_db": -13.0, "pan": 0.0, "mute": False, "notes": "supportive controlled stereo music"}
    if category == FX:
        return {"vol_db": -20.0, "pan": 0.0, "mute": False, "notes": "fx below musical elements"}
    if category == GUIDE_MIDI:
        return {"vol_db": -18.0, "pan": 0.0, "mute": True, "notes": "guide MIDI placeholder muted, no final-truth claim"}
    return {"vol_db": -24.0, "pan": 0.0, "mute": True, "notes": "artifact quarantine muted by default"}


def build_track_entry(path: str | Path, category: str, *, name: str | None = None, female_index: int = 0) -> dict[str, object]:
    defaults = category_track_defaults(category, female_index=female_index)
    label = name or Path(path).stem
    if category == FEMALE_BGV:
        label = f"Female BGV {'L' if defaults['pan'] < 0 else 'R'} - {label}"
    elif category == GUIDE_MIDI:
        label = f"Guide MIDI - {label}"
    elif category == VOCAL_ARTIFACT_QUARANTINE:
        label = f"QUARANTINE - {label}"
    return {
        "path": str(Path(path).resolve()),
        "name": label,
        "category": category,
        "bus": BUS_BY_CATEGORY.get(category, "ARTIFACT_QUARANTINE_BUS"),
        "vol": db_to_vol(float(defaults["vol_db"])),
        "vol_db": float(defaults["vol_db"]),
        "pan": float(defaults["pan"]),
        "mute": bool(defaults["mute"]),
        "notes": defaults["notes"],
    }


def qc_markers_from_report(qc_report: dict[str, object] | None, *, max_markers: int = 120) -> list[dict[str, object]]:
    if not qc_report:
        return []
    markers = []
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    eligible = []
    for issue in qc_report.get("issues", []):
        source_category = classify_source_file(str(issue.get("source", ""))).category
        if source_category in {REFERENCE_ONLY, TECHNICAL_MIX_REFERENCE, PROBLEM_REFERENCE, GUIDE_MIDI}:
            continue
        if str(issue.get("severity", "medium")) in {"high", "critical"} or bool(issue.get("reaper_marker")):
            eligible.append(issue)
    issues = sorted(
        eligible,
        key=lambda issue: (severity_rank.get(str(issue.get("severity", "medium")), 2), float(issue.get("timestamp", 0.0) or 0.0)),
    )
    for issue in issues[:max_markers]:
        severity = str(issue.get("severity", "medium"))
        issue_type = str(issue.get("issue_type", "qc_issue"))
        source = Path(str(issue.get("source", "source"))).name
        markers.append(
            {
                "time": float(issue.get("timestamp", 0.0) or 0.0),
                "name": f"QC {severity}: {issue_type} ({source})",
            }
        )
    return markers


def _lua_media_entries(media: Iterable[dict[str, object]]) -> str:
    rows = []
    for entry in media:
        rows.append(
            '  {path="%s", name="%s", category="%s", bus="%s", vol=%.8f, pan=%.3f, mute=%s},'
            % (
                lua_escape(str(entry["path"])),
                lua_escape(str(entry["name"])),
                lua_escape(str(entry["category"])),
                lua_escape(str(entry["bus"])),
                float(entry["vol"]),
                float(entry["pan"]),
                "true" if entry["mute"] else "false",
            )
        )
    return "\n".join(rows)


def _lua_marker_entries(markers: Iterable[dict[str, object]]) -> str:
    rows = []
    for marker in markers:
        rows.append('  {time=%.3f, name="%s"},' % (float(marker["time"]), lua_escape(str(marker["name"]))))
    return "\n".join(rows)


def _selected_plugin(plugin_inventory: dict[str, object] | None, role: str, fallback: str) -> str:
    if not plugin_inventory:
        return fallback
    roles = plugin_inventory.get("roles", {}) if isinstance(plugin_inventory, dict) else {}
    value = roles.get(role, {}) if isinstance(roles, dict) else {}
    if isinstance(value, dict):
        selected = value.get("selected_plugin") or value.get("fallback")
        if selected:
            return str(selected)
    return fallback


def render_reaper_lua(
    media: list[dict[str, object]],
    markers: list[dict[str, object]] | None = None,
    *,
    bpm: int = 180,
    plugin_inventory: dict[str, object] | None = None,
    harness_version: str = "v0.5",
    project_save_path: str | Path | None = None,
    undo_label: str = "Import Suno stems as commercial-production source layout",
) -> str:
    markers = markers or []
    bus_entries = "\n".join(f'  "{bus}",' for bus in BUSES)
    musical_bus_entries = "\n".join(f'  "{bus}",' for bus in MUSICAL_BUSES)
    pitch = _selected_plugin(plugin_inventory, "pitch_correction", "ReaTune")
    surgical_eq = _selected_plugin(plugin_inventory, "surgical_eq", "ReaEQ")
    dynamic_eq = _selected_plugin(plugin_inventory, "dynamic_eq", "ReaXcomp")
    deesser = _selected_plugin(plugin_inventory, "deesser", "ReaXcomp")
    comp_clean = _selected_plugin(plugin_inventory, "compressor_clean", "ReaComp")
    comp_character = _selected_plugin(plugin_inventory, "compressor_character", "ReaComp")
    saturation = _selected_plugin(plugin_inventory, "saturation", "JS: Saturation")
    stereo = _selected_plugin(plugin_inventory, "stereo_imager", "JS: Stereo Width")
    mid_side_eq = _selected_plugin(plugin_inventory, "mid_side_eq", surgical_eq)
    plate = _selected_plugin(plugin_inventory, "reverb_plate", "ReaVerbate")
    room = _selected_plugin(plugin_inventory, "reverb_room", "ReaVerbate")
    delay = _selected_plugin(plugin_inventory, "delay", "ReaDelay")
    limiter_fx = _selected_plugin(plugin_inventory, "limiter", "ReaLimit")
    meter = _selected_plugin(plugin_inventory, "loudness_meter", "JS: Loudness Meter Peak/RMS/LUFS")
    save_block = ""
    if project_save_path is not None:
        save_block = f'''
local project_save_path = "{lua_escape(str(Path(project_save_path).resolve()))}"
if reaper.Main_SaveProjectEx then
  pcall(function()
    reaper.Main_SaveProjectEx(0, project_save_path, 0)
  end)
end
'''
    return f'''-- Auto-generated local import for cleaned Suno Studio stems and guide MIDI.
-- Harness {lua_escape(harness_version)}: fresh zero-state rebuild from raw Suno Studio WAV stems and guide MIDI.
-- MP3/master/fullmix/reference files are muted analysis references only.
local bpm = {int(bpm)}
local buses = {{
{bus_entries}
}}
local musical_buses = {{
{musical_bus_entries}
}}
local media = {{
{_lua_media_entries(media)}
}}
local qc_markers = {{
{_lua_marker_entries(markers)}
}}
local fx = {{
  pitch_correction="{lua_escape(pitch)}",
  surgical_eq="{lua_escape(surgical_eq)}",
  dynamic_eq="{lua_escape(dynamic_eq)}",
  deesser="{lua_escape(deesser)}",
  compressor_clean="{lua_escape(comp_clean)}",
  compressor_character="{lua_escape(comp_character)}",
  saturation="{lua_escape(saturation)}",
  stereo_imager="{lua_escape(stereo)}",
  mid_side_eq="{lua_escape(mid_side_eq)}",
  reverb_plate="{lua_escape(plate)}",
  reverb_room="{lua_escape(room)}",
  delay="{lua_escape(delay)}",
  limiter="{lua_escape(limiter_fx)}",
  loudness_meter="{lua_escape(meter)}",
}}

local function safe_add_fx(track, name, label)
  local index = reaper.TrackFX_AddByName(track, name, false, -1)
  if index < 0 and label ~= nil then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_fx_" .. label, name, true)
  end
  return index
end

local function log_step(message)
  local f = io.open("/tmp/codex_fresh_reaper/build_fresh_mix.log", "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\\n")
    f:close()
  end
end

local function add_fx(track, category)
  if category == "male_lead_vocal" then
    safe_add_fx(track, fx.surgical_eq, "lead_cleanup_eq")
    safe_add_fx(track, fx.pitch_correction, "lead_pitch_correction")
    safe_add_fx(track, fx.dynamic_eq, "lead_dynamic_eq")
    safe_add_fx(track, fx.deesser, "lead_deesser")
    safe_add_fx(track, fx.compressor_clean, "lead_clean_compressor")
    safe_add_fx(track, fx.compressor_character, "lead_character_compressor")
    safe_add_fx(track, fx.surgical_eq, "lead_tone_eq")
    safe_add_fx(track, fx.saturation, "lead_light_saturation")
  elseif category == "female_bgv" then
    safe_add_fx(track, fx.surgical_eq, "bgv_hpf_soften_eq")
    safe_add_fx(track, fx.deesser, "bgv_deesser")
    safe_add_fx(track, fx.compressor_clean, "bgv_compressor")
    safe_add_fx(track, fx.stereo_imager, "bgv_width_control")
  elseif category == "drums" then
    safe_add_fx(track, fx.surgical_eq, "drum_cleanup_eq")
    safe_add_fx(track, fx.compressor_clean, "drum_punch_compressor")
  elseif category == "bass_or_808" then
    safe_add_fx(track, fx.surgical_eq, "bass_mono_low_eq")
    safe_add_fx(track, fx.dynamic_eq, "bass_kick_vocal_dynamic_control")
  elseif category == "music_or_synth" then
    safe_add_fx(track, fx.dynamic_eq, "music_vocal_pocket_dynamic_eq")
    safe_add_fx(track, fx.mid_side_eq, "music_ms_eq")
    safe_add_fx(track, fx.stereo_imager, "music_stereo_control")
  elseif category == "fx" then
    safe_add_fx(track, fx.surgical_eq, "fx_harshness_eq")
  elseif category == "vocal_artifact_quarantine" then
    safe_add_fx(track, fx.surgical_eq, "quarantine_inspection_eq")
  end
end

log_step("build script start")
reaper.Undo_BeginBlock()
log_step("undo begin")
if reaper.CountTracks and reaper.DeleteTrack then
  for track_index = reaper.CountTracks(0) - 1, 0, -1 do
    local tr = reaper.GetTrack(0, track_index)
    if tr then reaper.DeleteTrack(tr) end
  end
end
log_step("existing tracks cleared")
if reaper.SetTempoTimeSigMarker then
  reaper.SetTempoTimeSigMarker(0, -1, 0, -1, -1, bpm, 4, 4, false)
end
log_step("tempo set")

local bus_tracks = {{}}
for i, bus_name in ipairs(buses) do
  log_step("create bus " .. tostring(bus_name))
  reaper.InsertTrackAtIndex(i - 1, true)
  local tr = reaper.GetTrack(0, i - 1)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", bus_name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", 1.0)
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", 0.0)
  bus_tracks[bus_name] = tr
end

for _, bus_name in ipairs(buses) do
  reaper.SetMediaTrackInfo_Value(bus_tracks[bus_name], "B_MAINSEND", 0)
end
reaper.SetMediaTrackInfo_Value(bus_tracks["REF_BUS"], "B_MAINSEND", 1)
reaper.SetMediaTrackInfo_Value(bus_tracks["PRINT_MASTER_BUS"], "B_MAINSEND", 1)
for _, bus_name in ipairs(musical_buses) do
  reaper.CreateTrackSend(bus_tracks[bus_name], bus_tracks["MIX_BUS"])
end
reaper.CreateTrackSend(bus_tracks["VOCAL_PLATE_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["VOCAL_DELAY_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["SHORT_ROOM_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["OPTIONAL_WIDE_THROW_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["MIX_BUS"], bus_tracks["MASTER_PREMIX_BUS"])
reaper.CreateTrackSend(bus_tracks["MASTER_PREMIX_BUS"], bus_tracks["PRINT_MASTER_BUS"])
reaper.SetMediaTrackInfo_Value(bus_tracks["REF_BUS"], "B_MUTE", 1)
reaper.SetMediaTrackInfo_Value(bus_tracks["ARTIFACT_QUARANTINE_BUS"], "B_MUTE", 1)
log_step("bus routing complete")
safe_add_fx(bus_tracks["VOCAL_PLATE_SEND"], fx.reverb_plate, "vocal_plate_send_predelay_20_35ms_decay_0_8_1_6s")
safe_add_fx(bus_tracks["VOCAL_DELAY_SEND"], fx.delay, "vocal_delay_send_dotted_eighth_or_quarter_filtered_ducked")
safe_add_fx(bus_tracks["SHORT_ROOM_SEND"], fx.reverb_room, "short_room_send_low_level_glue")
safe_add_fx(bus_tracks["MIX_BUS"], fx.dynamic_eq, "mix_bus_dynamic_mud_harshness_control")
safe_add_fx(bus_tracks["MIX_BUS"], fx.mid_side_eq, "mix_bus_ms_eq_low_side_control")
safe_add_fx(bus_tracks["MASTER_PREMIX_BUS"], fx.compressor_clean, "master_premix_glue_1_2db_max")
safe_add_fx(bus_tracks["PRINT_MASTER_BUS"], fx.limiter, "print_master_true_peak_minus_1db")
safe_add_fx(bus_tracks["PRINT_MASTER_BUS"], fx.loudness_meter, "print_master_loudness_meter")

local start_index = #buses
for i, entry in ipairs(media) do
  log_step("create media track " .. tostring(i) .. " " .. tostring(entry.name) .. " category=" .. tostring(entry.category))
  reaper.InsertTrackAtIndex(start_index + i - 1, true)
  local tr = reaper.GetTrack(0, start_index + i - 1)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", entry.name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", entry.vol)
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", entry.pan)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  if entry.mute then reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1) end
  if entry.category == "guide_midi" then
    reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:guide_midi_path", entry.path, true)
    reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:guide_midi_note", "Guide MIDI placeholder only; import manually if needed to avoid REAPER MIDI import modal prompts.", true)
    log_step("guide MIDI placeholder only " .. tostring(entry.path))
  else
    reaper.SetOnlyTrackSelected(tr)
    if reaper.SetEditCurPos then reaper.SetEditCurPos(0.0, false, false) end
    log_step("insert media start " .. tostring(entry.path))
    reaper.InsertMedia(entry.path, 0)
    if reaper.CountSelectedMediaItems and reaper.GetSelectedMediaItem and reaper.SetMediaItemInfo_Value then
      local selected_count = reaper.CountSelectedMediaItems(0)
      for selected_index = 0, selected_count - 1 do
        local item = reaper.GetSelectedMediaItem(0, selected_index)
        if item then reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0.0) end
      end
    end
    log_step("insert media done " .. tostring(entry.path))
  end
  if bus_tracks[entry.bus] then
    reaper.CreateTrackSend(tr, bus_tracks[entry.bus])
  else
    reaper.CreateTrackSend(tr, bus_tracks["ARTIFACT_QUARANTINE_BUS"])
    reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  end
  add_fx(tr, entry.category)
  if entry.category == "male_lead_vocal" then
    reaper.CreateTrackSend(tr, bus_tracks["VOCAL_PLATE_SEND"])
    reaper.CreateTrackSend(tr, bus_tracks["VOCAL_DELAY_SEND"])
    reaper.CreateTrackSend(tr, bus_tracks["SHORT_ROOM_SEND"])
  elseif entry.category == "female_bgv" then
    reaper.CreateTrackSend(tr, bus_tracks["VOCAL_PLATE_SEND"])
    reaper.CreateTrackSend(tr, bus_tracks["SHORT_ROOM_SEND"])
  end
end

reaper.AddProjectMarker(0, false, 0.0, 0.0, "0s immediate hook check", -1)
reaper.AddProjectMarker(0, false, 8.0, 8.0, "8s arrangement continuity", -1)
reaper.AddProjectMarker(0, false, 16.0, 16.0, "16s hook/transition QC", -1)
reaper.AddProjectMarker(0, false, 28.0, 28.0, "28s short-form checkpoint", -1)
for _, marker in ipairs(qc_markers) do
  reaper.AddProjectMarker(0, false, marker.time, marker.time, marker.name, -1)
end
log_step("markers added")

reaper.UpdateArrange()
{save_block.rstrip()}
log_step("project save attempted")
reaper.Undo_EndBlock("{lua_escape(undo_label)}", -1)
log_step("build script done")
'''


def write_reaper_manifest(path: str | Path, *, bpm: int, media: list[dict[str, object]], script: str | Path, qc_markers: list[dict[str, object]]) -> Path:
    payload = {
        "bpm": bpm,
        "media_count": len(media),
        "script": str(script),
        "buses": BUSES,
        "qc_marker_count": len(qc_markers),
        "media": media,
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
