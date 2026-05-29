-- Applies a no-paid-plugin vocal tune/EQ substitute chain.
-- This is an Antares/FabFilter substitute route, not a clone.

local CONFIG = {
  project_root = ".",
  report_path = "reports/codex_tune_eq_substitute_chain.json",
}

local function json_escape(value)
  value = tostring(value or "")
  value = value:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
  return value
end

local function ensure_parent(path)
  local parent = path:match("^(.*)[/\\][^/\\]+$")
  if parent and parent ~= "" then
    reaper.RecursiveCreateDirectory(parent, 0)
  end
end

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function is_vocal_track(track)
  local name = track_name(track):lower()
  return name:find("vocal", 1, true) or name:find("vox", 1, true) or name:find("lead", 1, true)
end

local function selected_or_vocal_tracks()
  local tracks = {}
  local selected_count = reaper.CountSelectedTracks(0)
  if selected_count > 0 then
    for i = 0, selected_count - 1 do
      table.insert(tracks, reaper.GetSelectedTrack(0, i))
    end
    return tracks, "selected_tracks"
  end

  local total = reaper.CountTracks(0)
  for i = 0, total - 1 do
    local track = reaper.GetTrack(0, i)
    if is_vocal_track(track) then
      table.insert(tracks, track)
    end
  end
  return tracks, "name_matched_vocal_tracks"
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

local function set_params(track, fx_index, params)
  for index, value in pairs(params or {}) do
    reaper.TrackFX_SetParam(track, fx_index, index - 1, value)
  end
end

local function add_row(rows, severity, track, stage, status, plugin, fx_index, note)
  table.insert(rows, {
    severity = severity,
    track = track_name(track),
    stage = stage,
    status = status,
    plugin = plugin,
    fx_index = fx_index,
    note = note or "",
  })
end

local function write_report(rows, source)
  ensure_parent(CONFIG.report_path)
  local handle = io.open(CONFIG.report_path, "w")
  if not handle then
    reaper.ShowConsoleMsg("WARN could not write report: " .. CONFIG.report_path .. "\n")
    return
  end
  handle:write("{\n")
  handle:write('  "script": "scripts/apply_codex_tune_eq_substitute.lua",\n')
  handle:write('  "source": "' .. json_escape(source) .. '",\n')
  handle:write('  "claim_policy": "Do not claim Antares-quality tuning, FabFilter clone EQ, or vocal tuned without pitch/QC evidence.",\n')
  handle:write('  "rows": [\n')
  for i, row in ipairs(rows) do
    handle:write("    {\n")
    handle:write('      "severity": "' .. json_escape(row.severity) .. '",\n')
    handle:write('      "track": "' .. json_escape(row.track) .. '",\n')
    handle:write('      "stage": "' .. json_escape(row.stage) .. '",\n')
    handle:write('      "status": "' .. json_escape(row.status) .. '",\n')
    handle:write('      "plugin": "' .. json_escape(row.plugin) .. '",\n')
    handle:write('      "fx_index": ' .. tostring(row.fx_index or -1) .. ',\n')
    handle:write('      "note": "' .. json_escape(row.note) .. '"\n')
    handle:write("    }" .. (i == #rows and "\n" or ",\n"))
  end
  handle:write("  ]\n")
  handle:write("}\n")
  handle:close()
end

local function main()
  local rows = {}
  local tracks, source = selected_or_vocal_tracks()
  if #tracks == 0 then
    reaper.ShowConsoleMsg("No selected or vocal-named tracks found. Select a vocal track and rerun.\n")
    write_report(rows, source .. "_none_found")
    return
  end

  reaper.Undo_BeginBlock()
  for _, track in ipairs(tracks) do
    local ok, plugin, fx = add_first_available(track, {
      "JS: codex_fresh_mix/codex_vocal_pitch_monitor.jsfx",
      "codex_fresh_mix/codex_vocal_pitch_monitor.jsfx",
    })
    add_row(rows, ok and "PASS" or "WARN", track, "pitch monitor", ok and "loaded" or "missing_plugin", plugin, fx, "Dry-through pitch/key/cents monitor before ReaTune.")

    ok, plugin, fx = add_first_available(track, {
      "ReaTune",
      "VST: ReaTune (Cockos)",
      "VST: ReaTune",
    })
    add_row(rows, ok and "PASS" or "FAIL", track, "pitch correction engine", ok and "loaded" or "missing_plugin", plugin, fx, "ReaTune is the actual free pitch-correction engine; parameters are not guessed by this script.")

    ok, plugin, fx = add_first_available(track, {
      "JS: codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx",
      "codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx",
    })
    add_row(rows, ok and "PASS" or "FAIL", track, "dynamic M/S EQ", ok and "loaded" or "missing_plugin", plugin, fx, "FabFilter-style substitute for mud/harsh/sibilance/fizz control.")
    if ok then
      set_params(track, fx, {
        [2] = 0.206,  -- band 1 freq around 280 Hz
        [5] = 0.222,
        [8] = 0.385,  -- band 2 freq around 3.6 kHz
        [11] = 0.267,
        [14] = 0.489, -- band 3 freq around 6.8 kHz
        [17] = 0.289,
        [20] = 0.514, -- band 4 freq around 11.2 kHz
        [23] = 0.222,
        [24] = 1.0,   -- side mode for air/fizz by default
      })
    end

    ok, plugin, fx = add_first_available(track, {
      "JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx",
      "codex_fresh_mix/codex_dynamic_eq_band.jsfx",
    })
    add_row(rows, ok and "PASS" or "WARN", track, "extra narrow resonance band", ok and "loaded" or "missing_plugin", plugin, fx, "Optional single-band dynamic notch for obvious ringing.")

    ok, plugin, fx = add_first_available(track, {
      "JS: codex_fresh_mix/codex_noise_floor_tamer.jsfx",
      "codex_fresh_mix/codex_noise_floor_tamer.jsfx",
    })
    add_row(rows, ok and "PASS" or "WARN", track, "noise/fizz floor tamer", ok and "loaded" or "missing_plugin", plugin, fx, "Light high-band gating only; do not over-clean.")
  end
  reaper.Undo_EndBlock("Codex apply tune/EQ substitute chain", -1)
  write_report(rows, source)
  reaper.ShowConsoleMsg("Codex tune/EQ substitute chain applied. Inspect " .. CONFIG.report_path .. " before making claims.\n")
end

main()
