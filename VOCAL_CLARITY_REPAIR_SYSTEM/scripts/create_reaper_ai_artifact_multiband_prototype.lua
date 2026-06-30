-- Prompt 4: Reaper + TDR Nova multiband prototype session.
-- Creates a conservative DAW test template for AI noise/artifact reduction.
-- This is a prototype harness, not final plugin DSP.

local root = [[/Users/hantaeheuk/Documents/New project 3]]
local slug = "ai_noise_multiband_prototype"
local project_dir = root .. "/reaper/" .. slug
local report_dir = root .. "/reports/" .. slug
local rpp_path = project_dir .. "/AI_NOISE_MULTIBAND_PROTOTYPE.rpp"
local trace_path = report_dir .. "/reaper_multiband_prototype_trace.json"
local log_path = report_dir .. "/build_reaper.log"

local rows = {}

local function q(s)
  return string.format("%q", s)
end

local function lin(db)
  return 10 ^ ((db or 0) / 20)
end

local function esc(s)
  s = tostring(s or "")
  return s:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
end

local function log(message)
  local f = io.open(log_path, "a")
  if f then
    f:write(os.date("%F %T"), " ", tostring(message), "\n")
    f:close()
  end
end

local function add_row(track, stage, status, plugin, idx, wet, reason)
  rows[#rows + 1] = string.format(
    '{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":%s,"reason":"%s"}',
    esc(track), esc(stage), esc(status), esc(plugin), tonumber(idx or -1),
    wet and tostring(wet) or "null", esc(reason)
  )
  log(track .. " | " .. stage .. " | " .. status .. " | " .. tostring(plugin))
end

local function write_trace()
  local f = assert(io.open(trace_path, "w"))
  f:write('{\n  "slug": "' .. slug .. '",\n  "rows": [\n')
  for i, row in ipairs(rows) do
    f:write("    " .. row .. (i == #rows and "\n" or ",\n"))
  end
  f:write("  ]\n}\n")
  f:close()
end

local function make_track(name, db, pan, mute)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(db or 0))
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", mute and 1 or 0)
  return tr
end

local function insert_media(tr, path)
  if not path or path == "" then return end
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then
    add_row("source", "insert media", "missing_source", path, -1, nil, "template still created")
    return
  end
  local item = reaper.AddMediaItemToTrack(tr)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", reaper.GetMediaSourceLength(src))
end

local function add_fx(tr, label, stage, candidates, wet, reason)
  for _, name in ipairs(candidates) do
    local idx = reaper.TrackFX_AddByName(tr, name, false, -1)
    if idx and idx >= 0 then
      if wet and reaper.TrackFX_SetWetDryMix then
        pcall(reaper.TrackFX_SetWetDryMix, tr, idx, wet, 0, 0)
      end
      add_row(label, stage, "loaded", name, idx, wet, reason)
      return idx, name
    end
  end
  add_row(label, stage, "missing_all_candidates", table.concat(candidates, " | "), -1, wet, reason)
  return -1, nil
end

local function send(src, dst, db, phase_invert)
  local s = reaper.CreateTrackSend(src, dst)
  reaper.SetTrackSendInfo_Value(src, 0, s, "D_VOL", lin(db or 0))
  if phase_invert then
    pcall(reaper.SetTrackSendInfo_Value, src, 0, s, "B_PHASE", 1)
  end
  return s
end

local function add_marker(name, pos)
  reaper.AddProjectMarker2(0, false, pos, 0, name, -1, 0)
end

local function set_notes(text)
  reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", text, true)
end

os.execute("mkdir -p " .. q(project_dir))
os.execute("mkdir -p " .. q(report_dir))
os.remove(log_path)
os.remove(trace_path)

local ok, source_path = reaper.GetUserFileNameForRead("", "Select one test source for the prototype, or cancel for empty template", "")
if not ok then source_path = "" end

reaper.Undo_BeginBlock()
reaper.Main_OnCommand(40023, 0) -- new project

local original = make_track("01 Original Dry - no processing", 0, 0, false)
local processed = make_track("02 Processed Full - prototype chain", 0, 0, true)
local matched = make_track("03 Processed Matched - loudness fair A/B", 0, 0, true)
local residual = make_track("04 Residual Monitor - Original minus Processed", 0, 0, true)
local mid_bus = make_track("05 Mid Process Bus - center vocal protected", 0, 0, true)
local side_bus = make_track("06 Side Process Bus - stereo artifact cleanup", 0, 0, true)
local broad_bus = make_track("07 Broad Multiband Bus - gentle ReaXcomp/Nova", 0, 0, true)
local surgical_bus = make_track("08 Surgical Dynamic EQ Bus - TDR Nova notches", 0, 0, true)
local reafirmicro = make_track("09 ReaFIR Micro Suppression Bus - experiment", 0, 0, true)
local gate_bus = make_track("10 Gate/Expander Bus - gaps only", 0, 0, true)
local print_track = make_track("11 Print/Render A/B - record versions here", 0, 0, true)
local notes_track = make_track("12 Notes/Markers - decisions and failures", -99, 0, true)
local suppressor_candidate = make_track("13 24-64 Band Suppressor Candidate - decision log", 0, 0, true)

insert_media(original, source_path)
insert_media(processed, source_path)
insert_media(matched, source_path)

send(original, residual, 0, false)
send(processed, residual, 0, true)
send(processed, matched, 0, false)
send(original, mid_bus, 0, false)
send(original, side_bus, 0, false)
send(original, broad_bus, 0, false)
send(original, surgical_bus, 0, false)
send(original, reafirmicro, 0, false)
send(original, gate_bus, 0, false)
send(matched, print_track, 0, false)
send(original, suppressor_candidate, 0, false)

add_fx(processed, "processed_full", "Static Cleanup", {"VST: ReaEQ (Cockos)"}, 1.0, "HPF/hum/fixed whistle only; no broad presence or air cuts")
add_fx(processed, "processed_full", "Broad Dynamic Stabilization", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}, 0.75, "gentle broad movement, no auto gain")
add_fx(processed, "processed_full", "Nova Surgical A low/low-mid", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}, 0.70, "80 Hz to 1.2 kHz cleanup")
add_fx(processed, "processed_full", "Nova Surgical B mid/plastic", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}, 0.70, "1.2 kHz to 4 kHz, danger-zone conservative")
add_fx(processed, "processed_full", "Nova Surgical C presence/consonants", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}, 0.60, "3 kHz to 8 kHz, preserve intelligibility")
add_fx(processed, "processed_full", "Nova Surgical D air/fizz", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}, 0.55, "8 kHz to 16 kHz, preserve air")
add_fx(processed, "processed_full", "ReaFIR Micro Suppression", {"VST: ReaFIR (Cockos)"}, 0.35, "experimental, bypass if watery or phasey")
add_fx(processed, "processed_full", "Optional Gap Expander", {"VST: ReaGate (Cockos)"}, 0.35, "gaps only, not active vocal denoise")
add_fx(processed, "processed_full", "Level Match Meter", {"JS: Loudness Meter Peak/RMS/LUFS (Cockos)"}, 1.0, "match loudness before A/B")

add_fx(matched, "processed_matched", "Level trim for matched A/B", {"JS: Volume Adjustment", "JS: Volume/Pan Smoother v5", "VST: ReaEQ (Cockos)"}, 1.0, "trim only; no tone changes")
add_fx(mid_bus, "mid_bus", "M/S Encoder", {"JS: Mid/Side Encoder"}, 1.0, "prototype mid extraction; verify routing by ear")
add_fx(mid_bus, "mid_bus", "Mid conservative dynamic EQ", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}, 0.60, "protect center vocal 2-8 kHz")
add_fx(side_bus, "side_bus", "M/S Encoder", {"JS: Mid/Side Encoder"}, 1.0, "prototype side extraction; verify routing by ear")
add_fx(side_bus, "side_bus", "Side artifact cleanup", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}, 0.75, "slightly stronger side cleanup, preserve width")
add_fx(broad_bus, "broad_bus", "Broad multiband only", {"VST: ReaXcomp (Cockos)", "VST3: TDR Nova (Tokyo Dawn Labs)"}, 0.75, "compare broad-only cleanup")
add_fx(surgical_bus, "surgical_bus", "Surgical Nova stack", {"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}, 0.70, "fewest active dynamic notches")
add_fx(reafirmicro, "reafir_bus", "ReaFIR micro-band experiment", {"VST: ReaFIR (Cockos)"}, 0.30, "micro suppression test, not trusted by default")
add_fx(gate_bus, "gate_bus", "Gap expander only", {"VST: ReaGate (Cockos)"}, 0.40, "tails and gaps only")
add_fx(residual, "residual_monitor", "Residual loudness/phase meter", {"JS: Channel Phase Meter", "JS: Loudness Meter Peak/RMS/LUFS (Cockos)"}, 1.0, "residual should not sound like ghost vocal")
add_fx(suppressor_candidate, "suppressor_candidate", "24-64 band spectrum monitor", {"JS: Frequency Spectrum Analyzer Meter (Cockos)", "JS: Spectrograph Spectrogram Meter (Cockos)", "VST: ReaEQ (Cockos)"}, 1.0, "visual check only; no active suppressor DSP in this patch")
add_row("suppressor_candidate", "24-64 Band Dynamic Suppressor", "design_only", "24 default / 48 balanced / 64 sparse stress", -1, nil, "M/S independent artifact-score detector with vocal/transient/harmonic guards and residual validation")

add_marker("A/B loop: clean vocal or active phrase", 0)
add_marker("Check residual after Static Cleanup", 10)
add_marker("Check residual after Broad Dynamic Stabilization", 20)
add_marker("Check residual after Surgical Dynamic EQ", 30)
add_marker("Check ReaFIR underwater risk", 40)
add_marker("Check gate tail/chatter risk", 50)
add_marker("Check 24/48/64 suppressor candidate decision table", 60)
add_marker("Score preset and write keep/reduce/remove decisions", 70)

set_notes([[
AI noise/artifact multiband prototype template.

Solo workflow:
1 Original Dry, 2 Processed Full, 3 Processed Matched, 4 Residual Monitor,
5 Mid-only, 6 Side-only, 7 Broad-only, 8 Surgical-only, 9 ReaFIR-only, 10 Gate-only,
13 24-64 Band Suppressor Candidate.

Rules:
- Match loudness before judging.
- Residual should contain noise/artifact, not phrases, consonants, harmonics, guitar pick, snare attack, or musical air.
- Moderate remaining noise is acceptable. Source damage is not.
- 24-band is the only preservation-first suppressor default; 48/64 bands are validation or stress modes.
- Mid/Side suppressor decisions must be independent, with stricter Mid vocal/transient/harmonic guards.
- Artifact score must be vetoed by vocal, transient, harmonic, air, and residual-leak guards.
- ReaFIR and gate stages are experiments, not default recommendations.
- Every active band needs a keep/reduce/remove decision in the band log.
]])

reaper.GetSetProjectInfo_String(0, "RENDER_FILE", project_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "AI_NOISE_MULTIBAND_PROTOTYPE_$track", true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)

reaper.Main_SaveProjectEx(0, rpp_path, 0)
write_trace()
reaper.Undo_EndBlock("Create AI noise multiband prototype session", -1)
log("wrapper ok: " .. rpp_path)
