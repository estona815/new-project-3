-- Codex guarded FX-chain applier.
-- Applies stock/fallback stages and logs every loaded or missing plugin.

local CONFIG = {
  project_root = ".",
  song_slug = "music_pipeline_candidates",
}

local ROLE_FX = {
  ["02_DRUMS"] = {
    { stage = "cleanup EQ", names = { "ReaEQ (Cockos)", "VST: ReaEQ (Cockos)" }, required = true },
    { stage = "compressor", names = { "ReaComp (Cockos)", "VST: ReaComp (Cockos)" }, required = true },
  },
  ["03_BASS"] = {
    { stage = "cleanup EQ", names = { "ReaEQ (Cockos)", "VST: ReaEQ (Cockos)" }, required = true },
    { stage = "compressor", names = { "ReaComp (Cockos)", "VST: ReaComp (Cockos)" }, required = true },
  },
  ["04_MUSIC"] = {
    { stage = "resonance dynamic notch / M/S EQ stage", names = { "TDR Nova", "ReaEQ (Cockos)", "VST: ReaEQ (Cockos)" }, required = true },
  },
  ["05_VOCAL"] = {
    { stage = "cleanup EQ", names = { "ReaEQ (Cockos)", "VST: ReaEQ (Cockos)" }, required = true },
    { stage = "resonance dynamic notch", names = { "TDR Nova", "ReaXcomp (Cockos)", "VST: ReaXcomp (Cockos)" }, required = true },
    { stage = "compressor", names = { "ReaComp (Cockos)", "VST: ReaComp (Cockos)" }, required = true },
    { stage = "de-esser", names = { "TDR Nova", "ReaXcomp (Cockos)", "VST: ReaXcomp (Cockos)" }, required = false },
  },
  ["08_DEAI_BUS"] = {
    { stage = "Suno DeAI custom plugin stage", names = { "JS: codex_suno_deai", "JS: suno_deai", "JS: ai_vocal_artifact_reducer" }, required = false },
  },
  ["09_MIX_BUS"] = {
    { stage = "M/S EQ stage", names = { "TDR Nova", "ReaEQ (Cockos)", "VST: ReaEQ (Cockos)" }, required = true },
    { stage = "master dynamic EQ", names = { "TDR Nova", "ReaXcomp (Cockos)", "VST: ReaXcomp (Cockos)" }, required = true },
  },
  ["10_MASTER_PRINT"] = {
    { stage = "limiter/output guard", names = { "ReaLimit (Cockos)", "VST: ReaLimit (Cockos)" }, required = true },
  },
}

local function join_path(a, b)
  if a:sub(-1) == "/" or a:sub(-1) == "\\" then
    return a .. b
  end
  return a .. "/" .. b
end

local function ensure_dir(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

local function write_report(path, rows)
  local handle = io.open(path, "w")
  if not handle then
    reaper.ShowConsoleMsg("WARN could not write report: " .. path .. "\n")
    return
  end
  handle:write("{\n")
  handle:write('  "script": "scripts/apply_fx_chains.lua",\n')
  handle:write('  "rows": [\n')
  for index, row in ipairs(rows) do
    handle:write(row .. (index == #rows and "\n" or ",\n"))
  end
  handle:write("  ]\n")
  handle:write("}\n")
  handle:close()
end

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function find_track(prefix)
  local count = reaper.CountTracks(0)
  for index = 0, count - 1 do
    local track = reaper.GetTrack(0, index)
    local name = track_name(track)
    if name:find(prefix, 1, true) == 1 then
      return track
    end
  end
  return nil
end

local function add_first_available(track, candidates)
  for _, name in ipairs(candidates) do
    local fx_index = reaper.TrackFX_AddByName(track, name, false, -1)
    if fx_index and fx_index >= 0 then
      return true, name, fx_index
    end
  end
  return false, candidates[1] or "", -1
end

local function main()
  local reports_dir = join_path(join_path(CONFIG.project_root, "reports"), CONFIG.song_slug)
  ensure_dir(reports_dir)
  local rows = {}
  reaper.Undo_BeginBlock()
  for prefix, stages in pairs(ROLE_FX) do
    local track = find_track(prefix)
    if not track then
      table.insert(rows, '    { "severity": "WARN", "track": "' .. prefix .. '", "stage": "track lookup", "status": "missing_track" }')
    else
      for _, stage in ipairs(stages) do
        local ok, loaded_name, fx_index = add_first_available(track, stage.names)
        local severity = ok and "PASS" or (stage.required and "FAIL" or "WARN")
        local status = ok and "loaded" or "missing_plugin"
        table.insert(rows, '    { "severity": "' .. severity .. '", "track": "' .. prefix .. '", "stage": "' .. stage.stage .. '", "status": "' .. status .. '", "plugin": "' .. loaded_name .. '", "fx_index": ' .. tostring(fx_index) .. ' }')
      end
    end
  end
  reaper.Undo_EndBlock("Codex apply guarded FX chains", -1)
  write_report(join_path(reports_dir, "apply_fx_chains.json"), rows)
  reaper.ShowConsoleMsg("apply_fx_chains.lua complete; inspect reports before claiming success.\n")
end

main()

