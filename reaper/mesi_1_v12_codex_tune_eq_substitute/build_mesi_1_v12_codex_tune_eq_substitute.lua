-- Build an evidence-backed REAPER session for the Codex no-paid-plugin tune/EQ substitute.
-- This inserts ReaTune and Codex JSFX, but does not claim completed vocal tuning.

local root = "/Users/hantaeheuk/Documents/New project 3"
local slug = "mesi_1_v12_codex_tune_eq_substitute"
local reaper_dir = root .. "/reaper/" .. slug
local reports_dir = root .. "/reports/" .. slug
local rpp = reaper_dir .. "/mesi_1_v12_CODEX_TUNE_EQ_SUBSTITUTE.rpp"
local report_json = reports_dir .. "/mesi_1_v12_codex_tune_eq_substitute_session.json"
local report_md = reports_dir .. "/mesi_1_v12_codex_tune_eq_substitute_session.md"

local source_dir = root .. "/audio_work/mesi_1_v09_tuned_ducked_space_dynamic_master/source_stems"
local lead_vocal = source_dir .. "/mesi_1_main_vocal_trigger.wav"
local full_mix = source_dir .. "/mesi_1_full_mix_original.wav"
local keyboard_b = source_dir .. "/mesi_1_keyboard_b_raw.wav"
local drums = source_dir .. "/mesi_1_drums_raw.wav"
local bass = source_dir .. "/mesi_1_bass_raw.wav"
local v11_ref = root .. "/renders/mesi_1_v11_reaper_pipeline/mesi_1_v11_MASTER_24-48.wav"

local rows = {}

local function esc(value)
  value = tostring(value or "")
  value = value:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
  return value
end

local function ensure_dir(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

local function file_exists(path)
  local f = io.open(path, "rb")
  if f then
    f:close()
    return true
  end
  return false
end

local function add_row(severity, stage, status, target, detail)
  table.insert(rows, {
    severity = severity,
    stage = stage,
    status = status,
    target = target or "",
    detail = detail or "",
  })
end

local function new_track(name, volume_db, pan, muted)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local track = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
  reaper.SetMediaTrackInfo_Value(track, "D_VOL", 10 ^ ((volume_db or 0) / 20))
  reaper.SetMediaTrackInfo_Value(track, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(track, "B_MUTE", muted and 1 or 0)
  return track
end

local function select_only(track)
  local count = reaper.CountTracks(0)
  for i = 0, count - 1 do
    reaper.SetTrackSelected(reaper.GetTrack(0, i), false)
  end
  reaper.SetTrackSelected(track, true)
end

local function insert_media(track, path)
  select_only(track)
  local _, track_name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  if file_exists(path) then
    reaper.SetEditCurPos(0, false, false)
    reaper.InsertMedia(path, 0)
    add_row("PASS", "media", "inserted", track_name, path)
    return true
  end
  add_row("FAIL", "media", "missing", track_name, path)
  return false
end

local function add_first(track, candidates, stage, required)
  for _, name in ipairs(candidates) do
    local fx = reaper.TrackFX_AddByName(track, name, false, -1)
    if fx and fx >= 0 then
      add_row("PASS", stage, "loaded", name, "fx_index=" .. tostring(fx))
      return fx, name
    end
  end
  add_row(required and "FAIL" or "WARN", stage, "missing_plugin", candidates[1] or "", "no candidate loaded")
  return -1, candidates[1] or ""
end

local function write_reports(max_severity)
  local f = io.open(report_json, "w")
  if f then
    f:write("{\n")
    f:write('  "schema_version": 1,\n')
    f:write('  "song": "mesi_1",\n')
    f:write('  "version": "v12",\n')
    f:write('  "classification": "vocal_repair_chain_prepared + Codex_tune_EQ_substitute_session",\n')
    f:write('  "claim_status": "not_vocal_tuned_until_pitch_QC_and_human_AB",\n')
    f:write('  "rpp": "' .. esc(rpp) .. '",\n')
    f:write('  "source_vocal": "' .. esc(lead_vocal) .. '",\n')
    f:write('  "max_severity": "' .. esc(max_severity) .. '",\n')
    f:write('  "forbidden_claims": ["Antares-quality tuning", "FabFilter clone", "vocal tuned", "professional final master"],\n')
    f:write('  "rows": [\n')
    for i, row in ipairs(rows) do
      f:write("    {\n")
      f:write('      "severity": "' .. esc(row.severity) .. '",\n')
      f:write('      "stage": "' .. esc(row.stage) .. '",\n')
      f:write('      "status": "' .. esc(row.status) .. '",\n')
      f:write('      "target": "' .. esc(row.target) .. '",\n')
      f:write('      "detail": "' .. esc(row.detail) .. '"\n')
      f:write("    }" .. (i == #rows and "\n" or ",\n"))
    end
    f:write("  ]\n")
    f:write("}\n")
    f:close()
  end

  local m = io.open(report_md, "w")
  if m then
    m:write("# mesi_1 v12 Codex Tune/EQ Substitute Session\n\n")
    m:write("- Classification: `vocal_repair_chain_prepared + Codex_tune_EQ_substitute_session`\n")
    m:write("- RPP: `" .. rpp .. "`\n")
    m:write("- Source vocal: `" .. lead_vocal .. "`\n")
    m:write("- Max severity: `" .. max_severity .. "`\n")
    m:write("- Claim status: `not_vocal_tuned_until_pitch_QC_and_human_AB`\n\n")
    m:write("## What Was Applied\n\n")
    m:write("- `Codex Vocal Pitch Monitor`\n")
    m:write("- `ReaTune` as the stock REAPER pitch-correction engine\n")
    m:write("- `Codex Pro Dynamic MS EQ`\n")
    m:write("- `Codex Dynamic EQ Band`\n")
    m:write("- `Codex Noise Floor Tamer`\n\n")
    m:write("## Honesty Notes\n\n")
    m:write("- This is not Antares Auto-Tune.\n")
    m:write("- This is not FabFilter Pro-Q.\n")
    m:write("- `vocal tuned` is still forbidden until key/scale, correction settings, rendered before/after, and human A/B exist.\n\n")
    m:write("## Rows\n\n")
    m:write("| Severity | Stage | Status | Target | Detail |\n")
    m:write("| --- | --- | --- | --- | --- |\n")
    for _, row in ipairs(rows) do
      m:write("| " .. row.severity .. " | " .. row.stage .. " | " .. row.status .. " | `" .. row.target .. "` | " .. row.detail .. " |\n")
    end
    m:close()
  end
end

ensure_dir(reaper_dir)
ensure_dir(reports_dir)
reaper.Main_OnCommand(40023, 0)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "mesi_1 v12 Codex tune/EQ substitute. ReaTune and Codex JSFX inserted for vocal repair workflow. Do not claim vocal tuned until key/scale, correction settings, rendered before/after QC, and human A/B exist.", true)

local ref = new_track("01_REF_V11_CURRENT_FAVORITE_MUTED", -12, 0, true)
insert_media(ref, v11_ref)

local full = new_track("02_FULL_MIX_ORIGINAL_REF_MUTED", -14, 0, true)
insert_media(full, full_mix)

local raw = new_track("03_LEAD_VOCAL_RAW_MUTED", 0, 0, true)
insert_media(raw, lead_vocal)

local lead = new_track("04_LEAD_VOCAL_CODEX_TUNE_EQ_SUBSTITUTE", 0, 0, false)
insert_media(lead, lead_vocal)

local vocal_bus = new_track("05_VOCAL_BUS_CODEX", -1.5, 0, false)
local music = new_track("06_MUSIC_SUPPORT_LOW_MUTED", -18, 0, true)
insert_media(music, keyboard_b)
local drum = new_track("07_DRUMS_SUPPORT_MUTED", -18, 0, true)
insert_media(drum, drums)
local bass_track = new_track("08_BASS_SUPPORT_MUTED", -18, 0, true)
insert_media(bass_track, bass)
local print = new_track("09_PRINT_TARGET", 0, 0, true)

reaper.CreateTrackSend(lead, vocal_bus)

add_first(lead, {
  "JS: codex_fresh_mix/codex_vocal_pitch_monitor.jsfx",
  "codex_fresh_mix/codex_vocal_pitch_monitor.jsfx",
}, "pitch monitor", true)
add_first(lead, {
  "ReaTune",
  "VST: ReaTune (Cockos)",
  "VST: ReaTune",
}, "ReaTune pitch engine", true)
add_first(lead, {
  "JS: codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx",
  "codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx",
}, "dynamic M/S EQ", true)
add_first(lead, {
  "JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx",
  "codex_fresh_mix/codex_dynamic_eq_band.jsfx",
}, "extra resonance dynamic EQ", false)
add_first(lead, {
  "JS: codex_fresh_mix/codex_noise_floor_tamer.jsfx",
  "codex_fresh_mix/codex_noise_floor_tamer.jsfx",
}, "noise/fizz floor tamer", false)
add_first(vocal_bus, {
  "JS: codex_fresh_mix/codex_v20_channel_polish.jsfx",
  "codex_fresh_mix/codex_v20_channel_polish.jsfx",
}, "vocal bus polish", false)

local max_severity = "PASS"
for _, row in ipairs(rows) do
  if row.severity == "FAIL" then
    max_severity = "FAIL"
  elseif row.severity == "WARN" and max_severity ~= "FAIL" then
    max_severity = "WARN"
  end
end

reaper.GetSetProjectInfo_String(0, "RENDER_FILE", root .. "/renders/" .. slug, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "mesi_1_v12_vocal_chain_preview", true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 1, true)
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", 105.850688, true)

reaper.Main_SaveProjectEx(0, rpp, 0)
add_row("PASS", "project", "saved", rpp, "RPP contains ReaTune and Codex substitute JSFX chain.")
write_reports(max_severity)
reaper.ShowConsoleMsg("mesi_1 v12 Codex tune/EQ substitute build complete: " .. max_severity .. "\n")
