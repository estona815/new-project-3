--[[
Final vocal-space placement draft applicator for REAPER.

Disabled by default. Use only on a saved copy after
automix/eval_reports/final_placement_adapter_mapping_report.json says
apply_allowed=true. This script creates muted draft-only tracks/buses, inserts
validated placement FX on the muted draft bus, writes parameters only by
parameter-name lookup with normalized 0-1 values, and writes rollback metadata.

It never edits original tracks, never edits the original master, never inserts
pitch correction, never saves, never renders, and never creates final delivery.
]]

local CONFIG = {
  allow_final_vocal_space_placement = false,
  lua_plan_path = "",
  require_selected_accepted_recovery_draft = true,
}

local function script_dir()
  local info = debug.getinfo(1, "S")
  local source = info and info.source or ""
  source = source:gsub("^@", "")
  return source:match("^(.*)[/\\]") or "."
end

local function read_file(path)
  local f = io.open(path, "r")
  if not f then return nil end
  local text = f:read("*a")
  f:close()
  return text
end

local function write_file(path, text)
  local f, err = io.open(path, "w")
  if not f then error("Cannot write " .. path .. ": " .. tostring(err)) end
  f:write(text)
  f:close()
end

local function json_escape(value)
  return tostring(value or ""):gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
end

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function track_guid(track)
  local ok, guid = pcall(reaper.GetTrackGUID, track)
  if ok and guid then return guid end
  return ""
end

local function selected_tracks()
  local tracks = {}
  for i = 0, reaper.CountSelectedTracks(0) - 1 do
    tracks[#tracks + 1] = reaper.GetSelectedTrack(0, i)
  end
  return tracks
end

local function restore_selection(tracks)
  reaper.Main_OnCommand(40297, 0)
  for _, track in ipairs(tracks) do
    if reaper.ValidatePtr2(0, track, "MediaTrack*") then
      reaper.SetTrackSelected(track, true)
    end
  end
end

local function media_item_checksum(track)
  local parts = {}
  for i = 0, reaper.CountTrackMediaItems(track) - 1 do
    local item = reaper.GetTrackMediaItem(track, i)
    local position = reaper.GetMediaItemInfo_Value(item, "D_POSITION")
    local length = reaper.GetMediaItemInfo_Value(item, "D_LENGTH")
    parts[#parts + 1] = string.format("%.9f:%.9f", position, length)
  end
  return table.concat(parts, "|")
end

local function source_snapshot(track)
  return {
    guid = track_guid(track),
    name = track_name(track),
    fx_count = reaper.TrackFX_GetCount(track),
    item_count = reaper.CountTrackMediaItems(track),
    send_count = reaper.GetTrackNumSends(track, 0),
    receive_count = reaper.GetTrackNumSends(track, -1),
    media_checksum = media_item_checksum(track),
  }
end

local function master_snapshot()
  local master = reaper.GetMasterTrack(0)
  return {
    fx_count = reaper.TrackFX_GetCount(master),
    volume = reaper.GetMediaTrackInfo_Value(master, "D_VOL"),
    pan = reaper.GetMediaTrackInfo_Value(master, "D_PAN"),
  }
end

local function assert_source_unchanged(track, snapshot)
  if not reaper.ValidatePtr2(0, track, "MediaTrack*") then return false, "source pointer invalid" end
  if track_guid(track) ~= snapshot.guid then return false, "source GUID changed" end
  if track_name(track) ~= snapshot.name then return false, "source name changed" end
  if reaper.TrackFX_GetCount(track) ~= snapshot.fx_count then return false, "source FX count changed" end
  if reaper.CountTrackMediaItems(track) ~= snapshot.item_count then return false, "source item count changed" end
  if reaper.GetTrackNumSends(track, 0) ~= snapshot.send_count then return false, "source send count changed" end
  if reaper.GetTrackNumSends(track, -1) ~= snapshot.receive_count then return false, "source receive count changed" end
  if media_item_checksum(track) ~= snapshot.media_checksum then return false, "source media changed" end
  return true, "ok"
end

local function assert_master_unchanged(snapshot)
  local master = reaper.GetMasterTrack(0)
  if reaper.TrackFX_GetCount(master) ~= snapshot.fx_count then return false, "master FX changed" end
  if reaper.GetMediaTrackInfo_Value(master, "D_VOL") ~= snapshot.volume then return false, "master volume changed" end
  if reaper.GetMediaTrackInfo_Value(master, "D_PAN") ~= snapshot.pan then return false, "master pan changed" end
  return true, "ok"
end

local function duplicate_selected_track_as_muted_draft(original)
  local original_name = track_name(original)
  local original_number = math.floor(reaper.GetMediaTrackInfo_Value(original, "IP_TRACKNUMBER"))
  local before_count = reaper.CountTracks(0)
  reaper.Main_OnCommand(40297, 0)
  reaper.SetTrackSelected(original, true)
  reaper.Main_OnCommand(40062, 0)
  local draft = nil
  for i = 0, reaper.CountSelectedTracks(0) - 1 do
    local candidate = reaper.GetSelectedTrack(0, i)
    if candidate ~= original then draft = candidate end
  end
  if not draft and reaper.CountTracks(0) > before_count then
    draft = reaper.GetTrack(0, original_number)
  end
  if not draft or draft == original then error("Could not identify duplicated draft track") end
  reaper.GetSetMediaTrackInfo_String(draft, "P_NAME", original_name .. "_FINAL_VOCAL_SPACE_DRAFT", true)
  reaper.SetMediaTrackInfo_Value(draft, "B_MUTE", 1)
  reaper.SetMediaTrackInfo_Value(draft, "B_MAINSEND", 0)
  return draft
end

local function create_muted_bus()
  local index = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(index, true)
  local bus = reaper.GetTrack(0, index)
  if not bus then error("Could not create final vocal space bus") end
  reaper.GetSetMediaTrackInfo_String(bus, "P_NAME", "FINAL VOCAL SPACE BUS", true)
  reaper.SetMediaTrackInfo_Value(bus, "B_MUTE", 1)
  reaper.SetMediaTrackInfo_Value(bus, "B_MAINSEND", 1)
  return bus
end

local function normalize_name(value)
  return tostring(value or ""):lower():gsub("[^%w]+", "")
end

local function set_param_by_name(track, fx_index, target_name, normalized_value)
  if type(normalized_value) ~= "number" or normalized_value < 0 or normalized_value > 1 then
    return false, "normalized value outside 0..1"
  end
  local desired = normalize_name(target_name)
  if desired == "" then return false, "empty target parameter name" end
  local count = reaper.TrackFX_GetNumParams(track, fx_index)
  for i = 0, count - 1 do
    local _, name = reaper.TrackFX_GetParamName(track, fx_index, i, "")
    if normalize_name(name) == desired then
      reaper.TrackFX_SetParam(track, fx_index, i, normalized_value)
      return true, name
    end
  end
  return false, "parameter not found: " .. tostring(target_name)
end

local function plan_has_disallowed_plugins(plan)
  local terms = { "mautopitch", "autotune", "auto-tune", "melodyne", "reapitch", "reatune", "graillon", "ott", "ozone", "decapitator", "saturn", "valhalla" }
  for _, fx in ipairs(plan.fx_to_insert or {}) do
    local lower = tostring(fx.plugin_name_for_reaper or ""):lower()
    for _, term in ipairs(terms) do
      if lower:find(term, 1, true) then return true, fx.plugin_name_for_reaper end
    end
  end
  return false, ""
end

local function rollback_json(original, draft, bus, send_index, inserted, parameter_writes, plan)
  local plugin_lines = {}
  for _, plugin in ipairs(inserted) do
    plugin_lines[#plugin_lines + 1] = '    { "track": "' .. json_escape(plugin.track) .. '", "plugin": "' .. json_escape(plugin.plugin) .. '", "fx_index": ' .. tostring(plugin.fx_index) .. ' }'
  end
  local param_lines = {}
  for _, param in ipairs(parameter_writes) do
    param_lines[#param_lines + 1] = '    { "plugin": "' .. json_escape(param.plugin) .. '", "target_name": "' .. json_escape(param.target_name) .. '", "normalized_value": ' .. tostring(param.normalized_value) .. ' }'
  end
  return table.concat({
    "{",
    '  "schema": "automix-final-vocal-space-reaper-applicator-rollback-v1",',
    '  "created_at": "' .. os.date("!%Y-%m-%dT%H:%M:%SZ") .. '",',
    '  "original_track": "' .. json_escape(track_name(original)) .. '",',
    '  "original_track_guid": "' .. json_escape(track_guid(original)) .. '",',
    '  "draft_tracks": [ "' .. json_escape(track_name(draft)) .. '" ],',
    '  "draft_buses": [ "' .. json_escape(track_name(bus)) .. '" ],',
    '  "created_sends": [ { "source": "' .. json_escape(track_name(draft)) .. '", "destination": "' .. json_escape(track_name(bus)) .. '", "send_index": ' .. tostring(send_index) .. ' } ],',
    '  "plugins_inserted": [',
    table.concat(plugin_lines, ",\n"),
    '  ],',
    '  "parameters_written": [',
    table.concat(param_lines, ",\n"),
    '  ],',
    '  "safe_to_delete_draft": true,',
    '  "original_tracks_untouched": true,',
    '  "original_master_untouched": true,',
    '  "pitch_plugins_inserted": false,',
    '  "final_export_created": false,',
    '  "lua_plan_path": "' .. json_escape(CONFIG.lua_plan_path) .. '"',
    "}",
  }, "\n") .. "\n"
end

local function main()
  if not CONFIG.allow_final_vocal_space_placement then
    reaper.ShowMessageBox("Final vocal-space applicator is disabled. Run adapter validation first and use a configured copy only on a saved project copy.", "AutoMix Final Vocal Space", 0)
    return
  end
  if CONFIG.lua_plan_path == "" then
    reaper.ShowMessageBox("No lua_plan_path configured.", "AutoMix Final Vocal Space", 0)
    return
  end
  local plan_ok, plan = pcall(dofile, CONFIG.lua_plan_path)
  if not plan_ok or type(plan) ~= "table" then
    reaper.ShowMessageBox("Could not load Lua applicator plan:\n" .. tostring(plan), "AutoMix Final Vocal Space", 0)
    return
  end
  if plan.apply_allowed ~= true then
    reaper.ShowMessageBox("Applicator plan is not apply_allowed. No draft was created.", "AutoMix Final Vocal Space", 0)
    return
  end
  if plan.pitch_correction_blocked ~= true or plan.master_modification_blocked ~= true or plan.final_export_blocked ~= true then
    reaper.ShowMessageBox("Applicator plan does not preserve required hard blocks. No draft was created.", "AutoMix Final Vocal Space", 0)
    return
  end
  local disallowed, plugin_name = plan_has_disallowed_plugins(plan)
  if disallowed then
    reaper.ShowMessageBox("Applicator plan contains disallowed plugin: " .. tostring(plugin_name), "AutoMix Final Vocal Space", 0)
    return
  end
  local selection = selected_tracks()
  if #selection ~= 1 then
    reaper.ShowMessageBox("Select exactly one accepted recovery vocal draft before running the final vocal-space applicator.", "AutoMix Final Vocal Space", 0)
    return
  end
  local original = selection[1]
  local source_before = source_snapshot(original)
  local master_before = master_snapshot()
  local draft = nil
  local bus = nil
  local send_index = -1
  local inserted = {}
  local parameter_writes = {}

  reaper.PreventUIRefresh(1)
  reaper.Undo_BeginBlock()
  local ok, err = pcall(function()
    draft = duplicate_selected_track_as_muted_draft(original)
    bus = create_muted_bus()
    send_index = reaper.CreateTrackSend(draft, bus)
    if send_index < 0 then error("Could not create draft send to final vocal space bus") end
    for _, fx in ipairs(plan.fx_to_insert or {}) do
      local plugin = tostring(fx.plugin_name_for_reaper or "")
      if plugin ~= "" then
        local fx_index = reaper.TrackFX_AddByName(bus, plugin, false, -1)
        if fx_index < 0 then error("Could not insert mapped plugin: " .. plugin) end
        inserted[#inserted + 1] = { track = track_name(bus), plugin = plugin, fx_index = fx_index }
        for _, param in ipairs(fx.parameter_writes or {}) do
          local param_ok, param_reason = set_param_by_name(bus, fx_index, param.target_name, param.normalized_value)
          if not param_ok then error("Parameter write failed for " .. plugin .. ": " .. tostring(param_reason)) end
          parameter_writes[#parameter_writes + 1] = {
            plugin = plugin,
            target_name = param.target_name,
            normalized_value = param.normalized_value,
          }
        end
      end
    end
    local source_ok, source_reason = assert_source_unchanged(original, source_before)
    if not source_ok then error("Original source protection failed: " .. source_reason) end
    local master_ok, master_reason = assert_master_unchanged(master_before)
    if not master_ok then error("Original master protection failed: " .. master_reason) end
    local rollback_path = tostring(plan.rollback_output_path or "")
    if rollback_path == "" then rollback_path = script_dir() .. "/rollback/final_vocal_space_reaper_applicator_rollback.json" end
    write_file(rollback_path, rollback_json(original, draft, bus, send_index, inserted, parameter_writes, plan))
  end)
  restore_selection(selection)
  reaper.Undo_EndBlock("AutoMix create muted final vocal-space placement draft", -1)
  reaper.PreventUIRefresh(-1)
  if not ok then
    if draft and reaper.ValidatePtr2(0, draft, "MediaTrack*") then reaper.DeleteTrack(draft) end
    if bus and reaper.ValidatePtr2(0, bus, "MediaTrack*") then reaper.DeleteTrack(bus) end
    reaper.ShowMessageBox("Final vocal-space applicator failed safely:\n" .. tostring(err), "AutoMix Final Vocal Space", 0)
    return
  end
  reaper.ShowMessageBox("Muted final vocal-space placement draft scaffold created. Original track and master were not modified.", "AutoMix Final Vocal Space", 0)
end

main()
