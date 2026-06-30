--[[
Prompt 34 vocal recovery draft applicator for REAPER.

Default behavior is no-op. It never processes the original track. If explicitly
enabled on a saved project copy, it duplicates exactly one selected track,
renames the duplicate with _RECOVERY_DRAFT, mutes the draft by default, inserts
only mapped recovery processors on the draft, and writes only high-confidence
semantic parameters discovered by name. It does not use fixed parameter indexes
and it does not insert pitch correction.
]]

local CONFIG = {
  allow_draft_vocal_recovery = false,
  chain_plan_path = "",
  rollback_output_path = "",
  min_parameter_match_confidence = 0.85,
  plugin_candidates = {
    "VST3: ReaEQ",
    "VST: ReaEQ (Cockos)",
    "ReaEQ",
    "VST3: ReaXcomp",
    "VST: ReaXcomp (Cockos)",
    "ReaXcomp",
    "JS: Volume/Pan Smoother v5",
    "JS: Utility/volume_pan",
  },
}

local SEMANTIC_ALIASES = {
  utility_gain_db = { "gain", "volume", "trim" },
  low_cut_hz = { "frequency", "freq", "low cut", "high pass" },
  mud_dynamic_cut_amount = { "mud", "low mid", "threshold", "ratio", "gain" },
  nasal_dynamic_cut_amount = { "nasal", "mid", "threshold", "ratio", "gain" },
  harshness_dynamic_cut_amount = { "harsh", "presence", "threshold", "ratio", "gain" },
  sibilance_control_amount = { "sibilance", "de ess", "de-ess", "threshold" },
  high_fizz_control_amount = { "fizz", "air", "high", "threshold", "gain" },
  side_noise_reduction_amount = { "side", "width", "stereo", "gain" },
  output_gain_db = { "output", "gain", "volume" },
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

local function json_number(text, key)
  local value = text:match('"' .. key .. '"%s*:%s*([%-%.%d]+)')
  return value and tonumber(value) or nil
end

local function json_escape(value)
  return tostring(value or ""):gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
end

local function normalize_name(name)
  local s = tostring(name or ""):lower()
  s = s:gsub("^[%w%s%-%+_]*:%s*", "")
  s = s:gsub("[^%w]+", " ")
  s = s:gsub("%s+", " ")
  return s:gsub("^%s+", ""):gsub("%s+$", "")
end

local function compact_name(name)
  return normalize_name(name):gsub("%s+", "")
end

local function score_param_name(param_name, alias)
  local p = normalize_name(param_name)
  local a = normalize_name(alias)
  if p == "" or a == "" then return 0.0 end
  if p == a then return 0.98 end
  if (" " .. p .. " "):find(" " .. a .. " ", 1, true) then return 0.90 end
  local pc = compact_name(param_name)
  local ac = compact_name(alias)
  if pc == ac then return 0.95 end
  if #ac >= 5 and pc:find(ac, 1, true) then return 0.86 end
  return 0.0
end

local function discover_semantic_parameter(track, fx_index, semantic)
  local aliases = SEMANTIC_ALIASES[semantic]
  if not aliases then return nil, 0.0, nil end
  local count = reaper.TrackFX_GetNumParams(track, fx_index)
  local best_index = nil
  local best_score = 0.0
  local best_name = nil
  for param = 0, count - 1 do
    local _, param_name = reaper.TrackFX_GetParamName(track, fx_index, param, "")
    for _, alias in ipairs(aliases) do
      local score = score_param_name(param_name, alias)
      if score > best_score then
        best_score = score
        best_index = param
        best_name = param_name
      end
    end
  end
  if best_score >= CONFIG.min_parameter_match_confidence then
    return best_index, best_score, best_name
  end
  return nil, best_score, best_name
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

local function track_snapshot(track)
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

local function assert_original_track_unmodified_for_vocal_recovery(original, snapshot)
  if not reaper.ValidatePtr2(0, original, "MediaTrack*") then return false, "original track pointer invalid" end
  if track_guid(original) ~= snapshot.guid then return false, "original track GUID changed" end
  if track_name(original) ~= snapshot.name then return false, "original track name changed" end
  if reaper.TrackFX_GetCount(original) ~= snapshot.fx_count then return false, "original track FX count changed" end
  if reaper.CountTrackMediaItems(original) ~= snapshot.item_count then return false, "original media item count changed" end
  if media_item_checksum(original) ~= snapshot.media_checksum then return false, "original media changed" end
  if reaper.GetTrackNumSends(original, 0) ~= snapshot.send_count then return false, "original send count changed" end
  if reaper.GetTrackNumSends(original, -1) ~= snapshot.receive_count then return false, "original receive count changed" end
  return true, "ok"
end

local function duplicate_selected_track_as_muted_recovery_draft(original)
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
  if not draft or draft == original then error("Could not identify duplicated recovery draft track") end
  reaper.GetSetMediaTrackInfo_String(draft, "P_NAME", original_name .. "_RECOVERY_DRAFT", true)
  reaper.SetMediaTrackInfo_Value(draft, "B_MUTE", 1)
  return draft
end

local function insert_first_available_recovery_plugin(track)
  for _, candidate in ipairs(CONFIG.plugin_candidates) do
    local before = reaper.TrackFX_GetCount(track)
    local fx_index = reaper.TrackFX_AddByName(track, candidate, false, 1)
    local after = reaper.TrackFX_GetCount(track)
    if fx_index >= 0 and after > before then
      local _, actual_name = reaper.TrackFX_GetFXName(track, fx_index, "")
      return fx_index, actual_name or candidate
    end
  end
  return nil, nil
end

local function semantic_settings_from_plan(plan_text)
  local settings = {}
  for semantic, _ in pairs(SEMANTIC_ALIASES) do
    local value = json_number(plan_text, semantic)
    if value ~= nil then settings[semantic] = value end
  end
  return settings
end

local function apply_semantic_settings(track, fx_index, settings)
  local applied = {}
  local skipped = {}
  for semantic, value in pairs(settings) do
    local param_index, confidence, param_name = discover_semantic_parameter(track, fx_index, semantic)
    if param_index ~= nil then
      local normalized = value
      if semantic:find("_db", 1, true) then normalized = math.max(0.0, math.min(1.0, (value + 24.0) / 48.0)) end
      reaper.TrackFX_SetParamNormalized(track, fx_index, param_index, math.max(0.0, math.min(1.0, normalized)))
      applied[#applied + 1] = { semantic = semantic, param_name = param_name, confidence = confidence, value = value }
    else
      skipped[#skipped + 1] = { semantic = semantic, best_param_name = param_name, confidence = confidence, reason = "no high-confidence semantic parameter match" }
    end
  end
  return applied, skipped
end

local function table_to_json_array(items)
  local lines = {}
  for _, item in ipairs(items) do
    local parts = {}
    for key, value in pairs(item) do
      local rendered = type(value) == "number" and tostring(value) or '"' .. json_escape(value) .. '"'
      parts[#parts + 1] = '"' .. json_escape(key) .. '": ' .. rendered
    end
    lines[#lines + 1] = "    { " .. table.concat(parts, ", ") .. " }"
  end
  return "[\n" .. table.concat(lines, ",\n") .. "\n  ]"
end

local function rollback_json(original, draft, plugin_name, applied, skipped, plan_path)
  return table.concat({
    "{",
    '  "schema": "automix-vocal-recovery-rollback-v1",',
    '  "created_at": "' .. os.date("!%Y-%m-%dT%H:%M:%SZ") .. '",',
    '  "original_track_guid": "' .. json_escape(track_guid(original)) .. '",',
    '  "draft_track_guid": "' .. json_escape(track_guid(draft)) .. '",',
    '  "original_track_name": "' .. json_escape(track_name(original)) .. '",',
    '  "draft_track": "' .. json_escape(track_name(draft)) .. '",',
    '  "plugins_inserted": [ "' .. json_escape(plugin_name or "") .. '" ],',
    '  "parameters_written": ' .. table_to_json_array(applied) .. ",",
    '  "parameters_skipped": ' .. table_to_json_array(skipped) .. ",",
    '  "chain_plan": "' .. json_escape(plan_path) .. '",',
    '  "safe_to_delete_draft": true,',
    '  "original_track_untouched": true,',
    '  "draft_track_muted_by_default": true,',
    '  "contains_pitch_correction": false,',
    '  "fixed_parameter_indexes_used": false',
    "}",
  }, "\n") .. "\n"
end

local function main()
  if not CONFIG.allow_draft_vocal_recovery then
    reaper.ShowMessageBox("Prompt 34 vocal recovery applicator is disabled by default. Run batch triage, review the recovery chain plan, then enable on a saved project copy.", "AutoMix Prompt 34", 0)
    return
  end
  if CONFIG.chain_plan_path == "" then
    reaper.ShowMessageBox("No chain_plan_path configured.", "AutoMix Prompt 34", 0)
    return
  end
  local plan_text = read_file(CONFIG.chain_plan_path)
  if not plan_text then
    reaper.ShowMessageBox("Could not read chain plan:\n" .. CONFIG.chain_plan_path, "AutoMix Prompt 34", 0)
    return
  end
  if json_bool(plan_text, "contains_pitch_correction") == true then
    reaper.ShowMessageBox("Recovery plan contains pitch correction. Blocked.", "AutoMix Prompt 34", 0)
    return
  end
  if json_bool(plan_text, "safe_to_apply") ~= true then
    reaper.ShowMessageBox("Recovery chain plan is not safe_to_apply. No draft was created.", "AutoMix Prompt 34", 0)
    return
  end
  local original_selection = selected_tracks()
  if #original_selection ~= 1 then
    reaper.ShowMessageBox("Select exactly one original track before creating a recovery draft.", "AutoMix Prompt 34", 0)
    return
  end

  local original = original_selection[1]
  local snapshot = track_snapshot(original)
  local draft = nil
  local applied = {}
  local skipped = {}
  local plugin_name = nil

  reaper.PreventUIRefresh(1)
  reaper.Undo_BeginBlock()
  local ok, err = pcall(function()
    draft = duplicate_selected_track_as_muted_recovery_draft(original)
    local fx_index
    fx_index, plugin_name = insert_first_available_recovery_plugin(draft)
    if fx_index == nil then error("No configured recovery plugin could be inserted on draft track") end
    applied, skipped = apply_semantic_settings(draft, fx_index, semantic_settings_from_plan(plan_text))
    if #applied == 0 then error("No high-confidence recovery parameters were mapped; draft is unsafe") end
    local original_ok, reason = assert_original_track_unmodified_for_vocal_recovery(original, snapshot)
    if not original_ok then error("Original track modification guard failed: " .. reason) end
    local rollback_dir = script_dir() .. "/rollback"
    if reaper.RecursiveCreateDirectory then reaper.RecursiveCreateDirectory(rollback_dir, 0) end
    local rollback_path = CONFIG.rollback_output_path
    if rollback_path == "" then rollback_path = rollback_dir .. "/" .. track_name(original):gsub("[^%w%-_]+", "_") .. "_vocal_recovery_rollback.json" end
    write_file(rollback_path, rollback_json(original, draft, plugin_name, applied, skipped, CONFIG.chain_plan_path))
  end)
  restore_selection(original_selection)
  reaper.Undo_EndBlock("AutoMix Prompt 34 create muted vocal recovery draft", -1)
  reaper.PreventUIRefresh(-1)

  if not ok then
    if draft and reaper.ValidatePtr2(0, draft, "MediaTrack*") then reaper.DeleteTrack(draft) end
    reaper.ShowMessageBox("Vocal recovery draft failed safely:\n" .. tostring(err), "AutoMix Prompt 34", 0)
    return
  end

  reaper.ShowMessageBox("Muted vocal recovery draft created. Original track was not modified.\nApplied semantic controls: " .. tostring(#applied) .. "\nSkipped unknown controls: " .. tostring(#skipped), "AutoMix Prompt 34", 0)
end

main()
