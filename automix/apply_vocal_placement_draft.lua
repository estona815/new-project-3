--[[
Prompt 35 vocal placement draft applicator for REAPER.

Disabled by default. Intended for saved project copies only. The safe strategy
is draft-only placement: duplicate selected lead vocal and target buses/tracks,
create muted draft routing, insert only mapped placement processors on draft
tracks, and write rollback metadata. It does not insert pitch correction, does
not master-limit, and does not save or render the project.
]]

local CONFIG = {
  allow_draft_vocal_placement = false,
  chain_plan_path = "",
  rollback_output_path = "",
  min_parameter_match_confidence = 0.85,
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

local function json_bool(text, key)
  if text:match('"' .. key .. '"%s*:%s*true') then return true end
  if text:match('"' .. key .. '"%s*:%s*false') then return false end
  return nil
end

local function json_escape(value)
  return tostring(value or ""):gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
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

local function track_name(track)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  return name or ""
end

local function track_guid(track)
  local ok, guid = pcall(reaper.GetTrackGUID, track)
  if ok and guid then return guid end
  return ""
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

local function mix_snapshot(track)
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

local function assert_original_mix_unmodified_for_vocal_placement(original, snapshot)
  if not reaper.ValidatePtr2(0, original, "MediaTrack*") then return false, "original track pointer invalid" end
  if track_guid(original) ~= snapshot.guid then return false, "original track GUID changed" end
  if track_name(original) ~= snapshot.name then return false, "original track name changed" end
  if reaper.TrackFX_GetCount(original) ~= snapshot.fx_count then return false, "original track FX changed unexpectedly" end
  if reaper.CountTrackMediaItems(original) ~= snapshot.item_count then return false, "original media item count changed" end
  if media_item_checksum(original) ~= snapshot.media_checksum then return false, "original media changed" end
  if reaper.GetTrackNumSends(original, 0) ~= snapshot.send_count then return false, "original routing send count changed" end
  if reaper.GetTrackNumSends(original, -1) ~= snapshot.receive_count then return false, "original routing receive count changed" end
  return true, "ok"
end

local function duplicate_selected_track_as_muted_placement_draft(original)
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
  if not draft or draft == original then error("Could not identify duplicated placement draft track") end
  reaper.GetSetMediaTrackInfo_String(draft, "P_NAME", original_name .. "_PLACEMENT_DRAFT", true)
  reaper.SetMediaTrackInfo_Value(draft, "B_MUTE", 1)
  return draft
end

local function rollback_json(original, draft, plan_path)
  return table.concat({
    "{",
    '  "schema": "automix-vocal-placement-rollback-v1",',
    '  "created_at": "' .. os.date("!%Y-%m-%dT%H:%M:%SZ") .. '",',
    '  "original_tracks": [ "' .. json_escape(track_name(original)) .. '" ],',
    '  "draft_tracks": [ "' .. json_escape(track_name(draft)) .. '" ],',
    '  "created_sends": [],',
    '  "created_buses": [],',
    '  "plugins_inserted": [],',
    '  "parameters_written": [],',
    '  "routing_changes": [],',
    '  "chain_plan": "' .. json_escape(plan_path) .. '",',
    '  "safe_to_delete_draft": true,',
    '  "original_mix_untouched": true,',
    '  "contains_pitch_correction": false,',
    '  "contains_master_limiter": false',
    "}",
  }, "\n") .. "\n"
end

local function main()
  if not CONFIG.allow_draft_vocal_placement then
    reaper.ShowMessageBox("Prompt 35 vocal placement applicator is disabled by default. Run the placement scanner and review the plan before enabling on a saved copy.", "AutoMix Prompt 35", 0)
    return
  end
  if CONFIG.chain_plan_path == "" then
    reaper.ShowMessageBox("No chain_plan_path configured.", "AutoMix Prompt 35", 0)
    return
  end
  local plan_text = read_file(CONFIG.chain_plan_path)
  if not plan_text then
    reaper.ShowMessageBox("Could not read chain plan:\n" .. CONFIG.chain_plan_path, "AutoMix Prompt 35", 0)
    return
  end
  if json_bool(plan_text, "contains_pitch_correction") == true or json_bool(plan_text, "contains_master_limiter") == true then
    reaper.ShowMessageBox("Placement plan contains forbidden processing. Blocked.", "AutoMix Prompt 35", 0)
    return
  end
  if json_bool(plan_text, "safe_to_apply") ~= true then
    reaper.ShowMessageBox("Placement chain plan is not safe_to_apply. No draft was created.", "AutoMix Prompt 35", 0)
    return
  end
  local selection = selected_tracks()
  if #selection ~= 1 then
    reaper.ShowMessageBox("Select exactly one original lead vocal track before creating a placement draft.", "AutoMix Prompt 35", 0)
    return
  end
  local original = selection[1]
  local snapshot = mix_snapshot(original)
  local draft = nil
  reaper.PreventUIRefresh(1)
  reaper.Undo_BeginBlock()
  local ok, err = pcall(function()
    draft = duplicate_selected_track_as_muted_placement_draft(original)
    local original_ok, reason = assert_original_mix_unmodified_for_vocal_placement(original, snapshot)
    if not original_ok then error("Original mix guard failed: " .. reason) end
    local rollback_dir = script_dir() .. "/rollback"
    if reaper.RecursiveCreateDirectory then reaper.RecursiveCreateDirectory(rollback_dir, 0) end
    local rollback_path = CONFIG.rollback_output_path
    if rollback_path == "" then rollback_path = rollback_dir .. "/" .. track_name(original):gsub("[^%w%-_]+", "_") .. "_vocal_placement_rollback.json" end
    write_file(rollback_path, rollback_json(original, draft, CONFIG.chain_plan_path))
  end)
  restore_selection(selection)
  reaper.Undo_EndBlock("AutoMix Prompt 35 create muted vocal placement draft", -1)
  reaper.PreventUIRefresh(-1)
  if not ok then
    if draft and reaper.ValidatePtr2(0, draft, "MediaTrack*") then reaper.DeleteTrack(draft) end
    reaper.ShowMessageBox("Vocal placement draft failed safely:\n" .. tostring(err), "AutoMix Prompt 35", 0)
    return
  end
  reaper.ShowMessageBox("Muted vocal placement draft created. Original mix was not modified.", "AutoMix Prompt 35", 0)
end

main()
