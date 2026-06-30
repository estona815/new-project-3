--[[
Safe REAPER plugin inventory scanner.

This script is inventory-only:
- does not apply FX to user tracks
- does not change original track FX, parameters, volume, pan, sends, or items
- does not render or save the project
- uses one temporary muted test track for insertability probes, then deletes it
- does not assume plugin parameter indexes

Outputs:
- automix/plugin_inventory.json
- automix/plugin_inventory_report.md
]]

local SCRIPT_VERSION = "reaper-plugin-inventory-v1"

local function safe_call(fn, ...)
  if type(fn) ~= "function" then return false, nil end
  return pcall(fn, ...)
end

local function script_dir()
  local info = debug.getinfo(1, "S")
  local source = info and info.source or ""
  source = source:gsub("^@", "")
  return source:match("^(.*)[/\\]") or "."
end

local ROOT_DIR = script_dir()
local ALIAS_CONFIG_PATH = ROOT_DIR .. "/plugin_aliases.lua"
local OUTPUT_JSON_PATH = ROOT_DIR .. "/plugin_inventory.json"
local OUTPUT_MD_PATH = ROOT_DIR .. "/plugin_inventory_report.md"

local function ensure_dir(path)
  if reaper.RecursiveCreateDirectory then
    reaper.RecursiveCreateDirectory(path, 0)
  end
end

local function json_escape(value)
  local replacements = {
    ["\\"] = "\\\\",
    ["\""] = "\\\"",
    ["\b"] = "\\b",
    ["\f"] = "\\f",
    ["\n"] = "\\n",
    ["\r"] = "\\r",
    ["\t"] = "\\t",
  }
  return tostring(value):gsub('[%z\1-\31\\"]', function(c)
    return replacements[c] or string.format("\\u%04x", c:byte())
  end)
end

local function is_array(tbl)
  if type(tbl) ~= "table" then return false end
  local count = 0
  for k, _ in pairs(tbl) do
    if type(k) ~= "number" then return false end
    if k <= 0 or k % 1 ~= 0 then return false end
    count = count + 1
  end
  for i = 1, count do
    if tbl[i] == nil then return false end
  end
  return true
end

local function json_encode(value, indent)
  indent = indent or 0
  local t = type(value)
  if t == "nil" then return "null" end
  if t == "boolean" then return value and "true" or "false" end
  if t == "number" then
    if value ~= value or value == math.huge or value == -math.huge then return "null" end
    return string.format("%.12g", value)
  end
  if t == "string" then return '"' .. json_escape(value) .. '"' end
  if t ~= "table" then return '"' .. json_escape(tostring(value)) .. '"' end

  local pad = string.rep("  ", indent)
  local child_pad = string.rep("  ", indent + 1)
  local parts = {}
  if is_array(value) then
    for i = 1, #value do
      parts[#parts + 1] = child_pad .. json_encode(value[i], indent + 1)
    end
    if #parts == 0 then return "[]" end
    return "[\n" .. table.concat(parts, ",\n") .. "\n" .. pad .. "]"
  end

  local keys = {}
  for k, _ in pairs(value) do keys[#keys + 1] = tostring(k) end
  table.sort(keys)
  for _, k in ipairs(keys) do
    parts[#parts + 1] = child_pad .. '"' .. json_escape(k) .. '": ' .. json_encode(value[k], indent + 1)
  end
  if #parts == 0 then return "{}" end
  return "{\n" .. table.concat(parts, ",\n") .. "\n" .. pad .. "}"
end

local function write_text(path, text)
  local f, err = io.open(path, "w")
  if not f then error("Cannot write " .. path .. ": " .. tostring(err)) end
  f:write(text)
  f:close()
end

local function normalize_name(name)
  local s = tostring(name or ""):lower()
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  s = s:gsub("^[%w%s%-%+_]*:%s*", "")
  s = s:gsub("%b()", " ")
  s = s:gsub("[%[%]{}]", " ")
  s = s:gsub("[^%w]+", " ")
  s = s:gsub("%s+", " ")
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return s
end

local function compact_name(name)
  return normalize_name(name):gsub("%s+", "")
end

local function contains_wordish(haystack, needle)
  if needle == "" then return false end
  return (" " .. haystack .. " "):find(" " .. needle .. " ", 1, true) ~= nil
end

local DEFAULT_PLUGIN_FAMILIES = {
  {
    id = "mautopitch",
    display_name = "MAutoPitch",
    capabilities = { "pitch_correction" },
    aliases = { "MAutoPitch", "MeldaProduction MAutoPitch", "VST3: MAutoPitch" },
    probe_names = { "VST3: MAutoPitch", "VST: MAutoPitch", "MAutoPitch" },
    fallback = "ReaPitch",
  },
  {
    id = "reapitch",
    display_name = "ReaPitch",
    capabilities = { "pitch_correction", "utility" },
    aliases = { "ReaPitch", "Cockos ReaPitch" },
    probe_names = { "ReaPitch (Cockos)", "VST: ReaPitch (Cockos)", "ReaPitch" },
    fallback = "manual pitch correction",
  },
  {
    id = "autotune_type",
    display_name = "Auto-Tune Type",
    capabilities = { "pitch_correction" },
    aliases = { "Auto-Tune", "Autotune", "Antares Auto-Tune", "Auto Tune" },
    probe_names = { "VST3: Auto-Tune", "VST3: Auto-Tune Pro", "Auto-Tune" },
    manual_only = true,
    fallback = "MAutoPitch or ReaPitch",
  },
  {
    id = "melodyne_type",
    display_name = "Melodyne Type",
    capabilities = { "pitch_correction" },
    aliases = { "Melodyne", "Celemony Melodyne" },
    probe_names = { "VST3: Melodyne", "Melodyne" },
    manual_only = true,
    fallback = "manual-only correction; do not automate unless validated",
  },
  {
    id = "reaeq",
    display_name = "ReaEQ",
    capabilities = { "static_eq" },
    aliases = { "ReaEQ", "Cockos ReaEQ" },
    probe_names = { "ReaEQ (Cockos)", "VST: ReaEQ (Cockos)", "ReaEQ" },
    fallback = "JS: 3-Band EQ",
  },
  {
    id = "tdr_nova",
    display_name = "TDR Nova",
    capabilities = { "static_eq", "dynamic_eq", "resonance_suppressor", "deesser" },
    aliases = { "TDR Nova", "Nova", "Tokyo Dawn Nova" },
    probe_names = { "VST3: TDR Nova", "VST: TDR Nova", "TDR Nova" },
    fallback = "ReaEQ plus ReaXcomp",
  },
  {
    id = "mequalizer",
    display_name = "MEqualizer",
    capabilities = { "static_eq" },
    aliases = { "MEqualizer", "MeldaProduction MEqualizer" },
    probe_names = { "VST3: MEqualizer", "VST: MEqualizer", "MEqualizer" },
    fallback = "ReaEQ",
  },
  {
    id = "melda_dynamic_eq",
    display_name = "Melda Dynamic EQ",
    capabilities = { "dynamic_eq", "resonance_suppressor", "deesser" },
    aliases = { "MAutoDynamicEQ", "MDynamicEQ", "MeldaProduction MAutoDynamicEQ", "MeldaProduction MDynamicEQ" },
    probe_names = { "VST3: MAutoDynamicEQ", "VST3: MDynamicEQ", "MAutoDynamicEQ", "MDynamicEQ" },
    fallback = "TDR Nova or ReaXcomp",
  },
  {
    id = "soothe_type",
    display_name = "Soothe-like Resonance Suppressor",
    capabilities = { "dynamic_eq", "resonance_suppressor", "deesser" },
    aliases = { "Soothe", "soothe2", "oeksound soothe" },
    probe_names = { "VST3: soothe2", "VST3: soothe", "soothe2" },
    manual_only = true,
    fallback = "TDR Nova",
  },
  {
    id = "dseq_type",
    display_name = "DSEQ-like Resonance Suppressor",
    capabilities = { "dynamic_eq", "resonance_suppressor", "deesser" },
    aliases = { "DSEQ", "TBProAudio DSEQ" },
    probe_names = { "VST3: DSEQ", "DSEQ" },
    manual_only = true,
    fallback = "TDR Nova",
  },
  {
    id = "decapitator",
    display_name = "Decapitator",
    capabilities = { "saturator" },
    aliases = { "Decapitator", "Soundtoys Decapitator" },
    probe_names = { "VST3: Decapitator", "VST: Decapitator", "Decapitator" },
    fallback = "JS saturation fallback",
  },
  {
    id = "saturn_type",
    display_name = "Saturn-type Saturator",
    capabilities = { "saturator", "multiband_compressor" },
    aliases = { "Saturn", "FabFilter Saturn", "Saturn 2" },
    probe_names = { "VST3: Saturn 2", "VST3: FabFilter Saturn 2", "Saturn" },
    fallback = "JS saturation fallback",
  },
  {
    id = "rea_comp",
    display_name = "ReaComp",
    capabilities = { "compressor" },
    aliases = { "ReaComp", "Cockos ReaComp" },
    probe_names = { "ReaComp (Cockos)", "VST: ReaComp (Cockos)", "ReaComp" },
    fallback = "JS compressor",
  },
  {
    id = "reaxcomp",
    display_name = "ReaXcomp",
    capabilities = { "multiband_compressor", "compressor", "deesser" },
    aliases = { "ReaXcomp", "Cockos ReaXcomp", "ReaXComp" },
    probe_names = { "ReaXcomp (Cockos)", "VST: ReaXcomp (Cockos)", "ReaXcomp" },
    fallback = "ReaComp",
  },
  {
    id = "la2a_type",
    display_name = "LA-2A / Opto Compressor Type",
    capabilities = { "compressor" },
    aliases = { "LA-2A", "LA2A", "LA-2A Gray", "opto", "Opto Compressor" },
    probe_names = { "VST3: LA-2A", "LA-2A", "LA2A" },
    manual_only = true,
    fallback = "ReaComp",
  },
  {
    id = "1176_type",
    display_name = "1176 Compressor Type",
    capabilities = { "compressor" },
    aliases = { "1176", "FET Compressor", "Black 76", "Blue Stripe" },
    probe_names = { "VST3: 1176", "1176" },
    manual_only = true,
    fallback = "ReaComp",
  },
  {
    id = "ott",
    display_name = "OTT",
    capabilities = { "multiband_compressor", "compressor" },
    aliases = { "OTT", "Xfer OTT", "Xfer Records OTT" },
    probe_names = { "VST3: OTT", "VST: OTT", "OTT" },
    fallback = "ReaXcomp",
  },
  {
    id = "valhalla",
    display_name = "Valhalla Reverb/Space",
    capabilities = { "reverb", "delay" },
    aliases = { "Valhalla", "ValhallaVintageVerb", "Valhalla Room", "ValhallaPlate" },
    probe_names = { "VST3: ValhallaVintageVerb", "VST3: ValhallaRoom", "Valhalla" },
    fallback = "ReaVerbate or ReaDelay",
  },
  {
    id = "valhalla_supermassive",
    display_name = "Valhalla Supermassive",
    capabilities = { "reverb", "delay" },
    aliases = { "Valhalla Supermassive", "ValhallaSupermassive", "Supermassive" },
    probe_names = { "VST3: ValhallaSupermassive", "ValhallaSupermassive", "Valhalla Supermassive" },
    fallback = "ReaDelay",
  },
  {
    id = "reaverbate",
    display_name = "ReaVerbate",
    capabilities = { "reverb" },
    aliases = { "ReaVerbate", "Cockos ReaVerbate" },
    probe_names = { "ReaVerbate (Cockos)", "VST: ReaVerbate (Cockos)", "ReaVerbate" },
    fallback = "JS reverb fallback",
  },
  {
    id = "readelay",
    display_name = "ReaDelay",
    capabilities = { "delay" },
    aliases = { "ReaDelay", "Cockos ReaDelay" },
    probe_names = { "ReaDelay (Cockos)", "VST: ReaDelay (Cockos)", "ReaDelay" },
    fallback = "JS delay fallback",
  },
  {
    id = "utility_gain",
    display_name = "Gain / Utility",
    capabilities = { "utility" },
    aliases = { "Volume Adjustment", "Gain", "Utility", "JS Volume", "JS: Volume" },
    probe_names = { "JS: Volume Adjustment", "JS: Utility/Volume", "Volume Adjustment" },
    fallback = "track volume envelope",
  },
  {
    id = "stereo_width",
    display_name = "Stereo Width Utility",
    capabilities = { "stereo_width", "utility" },
    aliases = { "Stereo Width", "Width", "M/S", "Mid Side", "JS: Stereo Width" },
    probe_names = { "JS: Stereo Width", "Stereo Width" },
    fallback = "pan and routing only",
  },
  {
    id = "analyzer",
    display_name = "Analyzer / Meter",
    capabilities = { "analyzer", "utility" },
    aliases = { "Spectrum Analyzer", "SPAN", "Loudness Meter", "Youlean", "JS: Frequency Spectrum Analyzer Meter" },
    probe_names = { "JS: Frequency Spectrum Analyzer Meter", "VST3: SPAN", "SPAN" },
    fallback = "REAPER meters",
  },
  {
    id = "limiter",
    display_name = "Limiter",
    capabilities = { "limiter" },
    aliases = { "Limiter", "ReaLimit", "Event Horizon", "LoudMax" },
    probe_names = { "ReaLimit (Cockos)", "VST: ReaLimit (Cockos)", "ReaLimit", "JS: Event Horizon Limiter/Clipper" },
    fallback = "JS limiter fallback",
  },
}

local REQUIRED_CAPABILITIES = {
  "pitch_correction",
  "static_eq",
  "dynamic_eq",
  "resonance_suppressor",
  "compressor",
  "limiter",
  "saturator",
  "multiband_compressor",
  "deesser",
  "reverb",
  "delay",
  "stereo_width",
  "noise_reduction",
  "analyzer",
  "utility",
}

local CAPABILITY_FALLBACKS = {
  pitch_correction = { "ReaPitch", "MAutoPitch if installed", "manual pitch editing" },
  static_eq = { "ReaEQ" },
  dynamic_eq = { "TDR Nova if installed", "ReaXcomp as coarse fallback" },
  resonance_suppressor = { "TDR Nova if installed", "manual ReaEQ notches after analysis" },
  compressor = { "ReaComp" },
  limiter = { "ReaLimit", "JS Event Horizon Limiter/Clipper" },
  saturator = { "JS saturation fallback", "defer saturation" },
  multiband_compressor = { "ReaXcomp" },
  deesser = { "TDR Nova if installed", "ReaXcomp de-ess band" },
  reverb = { "ReaVerbate", "stock/JS reverb fallback" },
  delay = { "ReaDelay" },
  stereo_width = { "pan/routing only", "JS Stereo Width if installed" },
  noise_reduction = { "manual/offline only unless a validated plugin is present" },
  analyzer = { "REAPER meters", "JS analyzer if installed" },
  utility = { "track controls", "JS utility plugins" },
}

local function load_user_aliases()
  local f = io.open(ALIAS_CONFIG_PATH, "r")
  if not f then return {} end
  f:close()
  local ok, loaded = pcall(dofile, ALIAS_CONFIG_PATH)
  if ok and type(loaded) == "table" then return loaded end
  return {}
end

local function merge_families()
  local out = {}
  for _, family in ipairs(DEFAULT_PLUGIN_FAMILIES) do out[#out + 1] = family end
  for _, family in ipairs(load_user_aliases()) do
    if type(family) == "table" and family.id and family.aliases then
      family.user_defined = true
      out[#out + 1] = family
    end
  end
  return out
end

local function score_alias(name, alias)
  local n = normalize_name(name)
  local a = normalize_name(alias)
  if n == "" or a == "" then return 0.0, "none" end
  if n == a then return 0.98, "exact_normalized" end
  if contains_wordish(n, a) then return 0.86, "word_match" end
  local nc = compact_name(name)
  local ac = compact_name(alias)
  if nc == ac then return 0.94, "exact_compact" end
  if nc:find(ac, 1, true) or ac:find(nc, 1, true) then
    local score = 0.72
    if #ac <= 4 then score = 0.52 end
    return score, "compact_substring"
  end
  return 0.0, "none"
end

local function classify_plugin(name, families)
  local matches = {}
  for _, family in ipairs(families) do
    local best_score = 0.0
    local best_alias = nil
    local best_method = "none"
    for _, alias in ipairs(family.aliases or {}) do
      local score, method = score_alias(name, alias)
      if score > best_score then
        best_score = score
        best_alias = alias
        best_method = method
      end
    end
    if best_score > 0.0 then
      matches[#matches + 1] = {
        family_id = family.id,
        display_name = family.display_name or family.id,
        capabilities = family.capabilities or { "unknown" },
        confidence = best_score,
        matched_alias = best_alias,
        match_method = best_method,
        manual_only = family.manual_only or false,
        user_defined = family.user_defined or false,
      }
    end
  end
  table.sort(matches, function(a, b) return a.confidence > b.confidence end)
  local primary = matches[1]
  local ambiguous = false
  if matches[2] and primary and matches[2].confidence >= primary.confidence - 0.08 then
    ambiguous = true
  end
  return primary, matches, ambiguous
end

local function plugin_format_from_name(name)
  local prefix = tostring(name or ""):match("^%s*([^:]+):")
  if prefix then return prefix end
  return "unknown"
end

local function track_id(track)
  if not track then return nil end
  local ok, id = safe_call(reaper.CSurf_TrackToID, track, false)
  if ok and type(id) == "number" then return id end
  return nil
end

local function track_name(track)
  if not track then return "" end
  local ok, _, name = safe_call(reaper.GetSetMediaTrackInfo_String, track, "P_NAME", "", false)
  if ok then return name or "" end
  return ""
end

local function get_fx_guid(track, fx_index)
  local ok, guid = safe_call(reaper.TrackFX_GetFXGUID, track, fx_index)
  if ok and guid then return guid end
  return nil
end

local function get_fx_state(track, fx_index)
  local enabled = nil
  local offline = nil
  local ok_enabled, val_enabled = safe_call(reaper.TrackFX_GetEnabled, track, fx_index)
  if ok_enabled then enabled = val_enabled and true or false end
  local ok_offline, val_offline = safe_call(reaper.TrackFX_GetOffline, track, fx_index)
  if ok_offline then offline = val_offline and true or false end
  return enabled, offline
end

local function inspect_track(track, index, selected_set, families)
  local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
  local fx_count = reaper.TrackFX_GetCount(track)
  local fx_entries = {}
  for fx = 0, fx_count - 1 do
    local _, fx_name = reaper.TrackFX_GetFXName(track, fx, "")
    local primary, matches, ambiguous = classify_plugin(fx_name or "", families)
    local enabled, offline = get_fx_state(track, fx)
    local category = "unknown"
    local capabilities = { "unknown" }
    local confidence = 0.0
    if primary then
      capabilities = primary.capabilities
      category = capabilities[1] or "unknown"
      confidence = primary.confidence
    end
    fx_entries[#fx_entries + 1] = {
      position = fx + 1,
      fx_index_zero_based = fx,
      name = fx_name or "",
      normalized_name = normalize_name(fx_name or ""),
      plugin_format = plugin_format_from_name(fx_name or ""),
      enabled = enabled,
      offline = offline,
      plugin_guid = get_fx_guid(track, fx),
      category = category,
      capabilities = capabilities,
      confidence = confidence,
      ambiguous = ambiguous,
      matches = matches,
      note = ambiguous and "fuzzy match is ambiguous; verify manually" or nil,
    }
  end

  local sends = {}
  local send_count = reaper.GetTrackNumSends(track, 0)
  for i = 0, send_count - 1 do
    local dest = reaper.GetTrackSendInfo_Value(track, 0, i, "P_DESTTRACK")
    sends[#sends + 1] = {
      index = i + 1,
      destination_track_index = track_id(dest),
      destination_track_name = track_name(dest),
      volume = reaper.GetTrackSendInfo_Value(track, 0, i, "D_VOL"),
      pan = reaper.GetTrackSendInfo_Value(track, 0, i, "D_PAN"),
      mute = reaper.GetTrackSendInfo_Value(track, 0, i, "B_MUTE") == 1,
    }
  end

  local receives = {}
  local receive_count = reaper.GetTrackNumSends(track, -1)
  for i = 0, receive_count - 1 do
    local src = reaper.GetTrackSendInfo_Value(track, -1, i, "P_SRCTRACK")
    receives[#receives + 1] = {
      index = i + 1,
      source_track_index = track_id(src),
      source_track_name = track_name(src),
      volume = reaper.GetTrackSendInfo_Value(track, -1, i, "D_VOL"),
      pan = reaper.GetTrackSendInfo_Value(track, -1, i, "D_PAN"),
      mute = reaper.GetTrackSendInfo_Value(track, -1, i, "B_MUTE") == 1,
    }
  end

  return {
    track_index = index + 1,
    track_index_zero_based = index,
    track_id = track_id(track),
    selected = selected_set[track] == true,
    name = name or "",
    fx_count = fx_count,
    fx = fx_entries,
    channel_count = reaper.GetMediaTrackInfo_Value(track, "I_NCHAN"),
    volume = reaper.GetMediaTrackInfo_Value(track, "D_VOL"),
    pan = reaper.GetMediaTrackInfo_Value(track, "D_PAN"),
    mute = reaper.GetMediaTrackInfo_Value(track, "B_MUTE") == 1,
    solo = reaper.GetMediaTrackInfo_Value(track, "I_SOLO"),
    sends = sends,
    receives = receives,
  }
end

local function selected_track_set()
  local set = {}
  local count = reaper.CountSelectedTracks(0)
  for i = 0, count - 1 do
    local tr = reaper.GetSelectedTrack(0, i)
    if tr then set[tr] = true end
  end
  return set
end

local function collect_existing_plugins(track_entries)
  local by_name = {}
  local out = {}
  for _, tr in ipairs(track_entries) do
    for _, fx in ipairs(tr.fx or {}) do
      local key = fx.normalized_name
      if key ~= "" then
        if not by_name[key] then
          by_name[key] = {
            name = fx.name,
            normalized_name = fx.normalized_name,
            plugin_format = fx.plugin_format,
            category = fx.category,
            capabilities = fx.capabilities,
            confidence = fx.confidence,
            ambiguous = fx.ambiguous,
            instances = {},
          }
          out[#out + 1] = by_name[key]
        end
        by_name[key].instances[#by_name[key].instances + 1] = {
          track_index = tr.track_index,
          track_name = tr.name,
          position = fx.position,
          enabled = fx.enabled,
          offline = fx.offline,
        }
      end
    end
  end
  return out
end

local function restore_track_selection(selected_tracks)
  reaper.Main_OnCommand(40297, 0) -- Unselect all tracks.
  for _, tr in ipairs(selected_tracks) do
    if reaper.ValidatePtr2(0, tr, "MediaTrack*") then
      reaper.SetTrackSelected(tr, true)
    end
  end
end

local function create_temp_probe_track()
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, false)
  local tr = reaper.GetTrack(0, idx)
  if not tr then error("Could not create temporary plugin probe track") end
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "__AUTOMIX_PLUGIN_INVENTORY_TEMP_DO_NOT_USE__", true)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", 0)
  reaper.SetMediaTrackInfo_Value(tr, "I_NCHAN", 2)
  reaper.SetMediaTrackInfo_Value(tr, "B_SHOWINTCP", 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_SHOWINMIXER", 0)
  return tr
end

local function delete_temp_probe_track(track)
  if track and reaper.ValidatePtr2(0, track, "MediaTrack*") then
    reaper.DeleteTrack(track)
  end
end

local function probe_plugin_family(track, family)
  local tried = {}
  local ok_any = false
  local found_name = nil
  local inserted_index = nil
  for _, candidate in ipairs(family.probe_names or family.aliases or {}) do
    local before = reaper.TrackFX_GetCount(track)
    local idx = reaper.TrackFX_AddByName(track, candidate, false, 1)
    local after = reaper.TrackFX_GetCount(track)
    local inserted = idx >= 0 and after > before
    tried[#tried + 1] = {
      query = candidate,
      success = inserted,
      returned_index = idx,
    }
    if inserted then
      local _, actual_name = reaper.TrackFX_GetFXName(track, idx, "")
      ok_any = true
      found_name = actual_name or candidate
      inserted_index = idx
      reaper.TrackFX_Delete(track, idx)
      break
    elseif after > before and idx >= 0 then
      reaper.TrackFX_Delete(track, idx)
    end
  end
  return {
    family_id = family.id,
    display_name = family.display_name or family.id,
    capabilities = family.capabilities or { "unknown" },
    insertable = ok_any,
    detected_name = found_name,
    inserted_index = inserted_index,
    confidence = ok_any and 0.90 or 0.0,
    manual_only = family.manual_only or false,
    user_defined = family.user_defined or false,
    fallback = family.fallback,
    tried = tried,
  }
end

local function probe_insertable_plugins(families)
  local selected_tracks = {}
  for i = 0, reaper.CountSelectedTracks(0) - 1 do
    selected_tracks[#selected_tracks + 1] = reaper.GetSelectedTrack(0, i)
  end

  local temp = nil
  local results = {}
  local ok, err = pcall(function()
    temp = create_temp_probe_track()
    for _, family in ipairs(families) do
      results[#results + 1] = probe_plugin_family(temp, family)
    end
  end)

  delete_temp_probe_track(temp)
  restore_track_selection(selected_tracks)

  if not ok then
    error(err)
  end

  return results
end

local function capability_summary(existing_plugins, insertable_plugins)
  local caps = {}
  for _, cap in ipairs(REQUIRED_CAPABILITIES) do
    caps[cap] = {
      capability = cap,
      existing_on_tracks = {},
      insertable = {},
      fallback_options = CAPABILITY_FALLBACKS[cap] or {},
      status = "missing",
    }
  end

  for _, plugin in ipairs(existing_plugins) do
    for _, cap in ipairs(plugin.capabilities or {}) do
      if caps[cap] then
        caps[cap].existing_on_tracks[#caps[cap].existing_on_tracks + 1] = plugin.name
        caps[cap].status = "present_on_track"
      end
    end
  end

  for _, plugin in ipairs(insertable_plugins) do
    if plugin.insertable then
      for _, cap in ipairs(plugin.capabilities or {}) do
        if caps[cap] then
          caps[cap].insertable[#caps[cap].insertable + 1] = plugin.detected_name or plugin.display_name
          if caps[cap].status == "missing" then caps[cap].status = "insertable" end
        end
      end
    end
  end

  local out = {}
  for _, cap in ipairs(REQUIRED_CAPABILITIES) do
    out[#out + 1] = caps[cap]
  end
  return out
end

local function missing_recommended(capabilities)
  local out = {}
  for _, entry in ipairs(capabilities) do
    if entry.status == "missing" then
      out[#out + 1] = {
        capability = entry.capability,
        fallback_options = entry.fallback_options,
      }
    end
  end
  return out
end

local function ambiguous_plugins(track_entries, existing_plugins)
  local out = {}
  for _, tr in ipairs(track_entries) do
    for _, fx in ipairs(tr.fx or {}) do
      if fx.ambiguous or (fx.confidence > 0 and fx.confidence < 0.80) then
        out[#out + 1] = {
          track_index = tr.track_index,
          track_name = tr.name,
          fx_position = fx.position,
          fx_name = fx.name,
          confidence = fx.confidence,
          matches = fx.matches,
          note = "Verify manually before automation uses this plugin.",
        }
      end
    end
  end
  for _, plugin in ipairs(existing_plugins) do
    if plugin.ambiguous then
      -- Track-level entries above are more actionable; keep existing list compact.
    end
  end
  return out
end

local function project_name()
  local ok, path = safe_call(reaper.GetProjectPath, "")
  local _, project_file = reaper.EnumProjects(-1, "")
  local name = tostring(project_file or ""):match("([^/\\]+)$") or ""
  return name, ok and path or ""
end

local function reaper_version()
  local ok, version = safe_call(reaper.GetAppVersion)
  if ok then return version end
  return "unknown"
end

local function scan_inventory()
  local families = merge_families()
  local selected_set = selected_track_set()
  local track_entries = {}
  for i = 0, reaper.CountTracks(0) - 1 do
    local tr = reaper.GetTrack(0, i)
    track_entries[#track_entries + 1] = inspect_track(tr, i, selected_set, families)
  end

  local existing_plugins = collect_existing_plugins(track_entries)
  local insertable_plugins = probe_insertable_plugins(families)
  local caps = capability_summary(existing_plugins, insertable_plugins)
  local name, project_path = project_name()
  local ambiguous = ambiguous_plugins(track_entries, existing_plugins)

  return {
    schema = "automix-reaper-plugin-inventory-v1",
    script_version = SCRIPT_VERSION,
    scan_date_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
    safety = {
      inventory_only = true,
      no_audio_changes = true,
      no_original_track_fx_insertion = true,
      temporary_probe_track_used = true,
      temporary_probe_track_deleted = true,
      no_parameter_changes = true,
      no_render = true,
      no_project_save = true,
      parameter_indexes_assumed = false,
    },
    reaper = {
      version = reaper_version(),
      project_name = name,
      project_path = project_path,
      track_count = reaper.CountTracks(0),
      selected_track_count = reaper.CountSelectedTracks(0),
    },
    tracks = track_entries,
    detected_plugins = existing_plugins,
    insertable_plugins = insertable_plugins,
    capability_inventory = caps,
    missing_recommended_plugins = missing_recommended(caps),
    ambiguous_plugins = ambiguous,
    fallback_options = CAPABILITY_FALLBACKS,
    notes = {
      "Fuzzy matches are suggestions, not proof of exact product identity.",
      "Manual-only plugins such as Melodyne-type and Auto-Tune-type entries must not be automatically controlled until separately validated.",
      "No plugin parameter indexes were queried or assumed in this inventory scan.",
    },
  }
end

local function write_markdown_report(path, inventory)
  local lines = {}
  lines[#lines + 1] = "# REAPER Plugin Inventory"
  lines[#lines + 1] = ""
  lines[#lines + 1] = "- Scan date UTC: `" .. inventory.scan_date_utc .. "`"
  lines[#lines + 1] = "- REAPER version: `" .. tostring(inventory.reaper.version) .. "`"
  lines[#lines + 1] = "- Project: `" .. tostring(inventory.reaper.project_name) .. "`"
  lines[#lines + 1] = "- Tracks scanned: `" .. tostring(inventory.reaper.track_count) .. "`"
  lines[#lines + 1] = "- Selected tracks: `" .. tostring(inventory.reaper.selected_track_count) .. "`"
  lines[#lines + 1] = "- Safety: inventory-only, no original track FX insertion, no parameter changes, no render, no save."
  lines[#lines + 1] = ""
  lines[#lines + 1] = "## Capability Summary"
  lines[#lines + 1] = ""
  lines[#lines + 1] = "| Capability | Status | Existing | Insertable | Fallback |"
  lines[#lines + 1] = "| --- | --- | --- | --- | --- |"
  for _, cap in ipairs(inventory.capability_inventory) do
    lines[#lines + 1] = "| " .. cap.capability
      .. " | " .. cap.status
      .. " | " .. table.concat(cap.existing_on_tracks or {}, ", ")
      .. " | " .. table.concat(cap.insertable or {}, ", ")
      .. " | " .. table.concat(cap.fallback_options or {}, ", ")
      .. " |"
  end

  lines[#lines + 1] = ""
  lines[#lines + 1] = "## Existing FX On Tracks"
  lines[#lines + 1] = ""
  for _, tr in ipairs(inventory.tracks) do
    lines[#lines + 1] = "### Track " .. tr.track_index .. ": " .. (tr.name ~= "" and tr.name or "(unnamed)")
    lines[#lines + 1] = ""
    if #tr.fx == 0 then
      lines[#lines + 1] = "- no FX"
    else
      for _, fx in ipairs(tr.fx) do
        lines[#lines + 1] = "- slot " .. fx.position .. ": `" .. fx.name .. "`"
          .. " / " .. table.concat(fx.capabilities or {}, ", ")
          .. " / confidence " .. string.format("%.2f", fx.confidence or 0)
          .. (fx.ambiguous and " / ambiguous" or "")
      end
    end
    lines[#lines + 1] = ""
  end

  lines[#lines + 1] = "## Ambiguous Matches"
  lines[#lines + 1] = ""
  if #inventory.ambiguous_plugins == 0 then
    lines[#lines + 1] = "- none"
  else
    for _, item in ipairs(inventory.ambiguous_plugins) do
      lines[#lines + 1] = "- Track " .. item.track_index .. " `" .. item.track_name .. "` slot "
        .. item.fx_position .. ": `" .. item.fx_name .. "` confidence "
        .. string.format("%.2f", item.confidence or 0)
    end
  end

  lines[#lines + 1] = ""
  lines[#lines + 1] = "## Missing Recommended Capabilities"
  lines[#lines + 1] = ""
  if #inventory.missing_recommended_plugins == 0 then
    lines[#lines + 1] = "- none"
  else
    for _, item in ipairs(inventory.missing_recommended_plugins) do
      lines[#lines + 1] = "- `" .. item.capability .. "` fallback: " .. table.concat(item.fallback_options or {}, ", ")
    end
  end

  write_text(path, table.concat(lines, "\n") .. "\n")
end

local function main()
  ensure_dir(ROOT_DIR)
  reaper.PreventUIRefresh(1)
  reaper.Undo_BeginBlock()
  local ok, inventory_or_error = pcall(scan_inventory)
  reaper.Undo_EndBlock("AutoMix plugin inventory scan (temporary probe track only)", -1)
  reaper.PreventUIRefresh(-1)

  if not ok then
    reaper.ShowMessageBox("Plugin inventory scan failed:\n" .. tostring(inventory_or_error), "AutoMix Inventory", 0)
    return
  end

  write_text(OUTPUT_JSON_PATH, json_encode(inventory_or_error, 0) .. "\n")
  write_markdown_report(OUTPUT_MD_PATH, inventory_or_error)
  reaper.ShowMessageBox(
    "Plugin inventory written:\n" .. OUTPUT_JSON_PATH .. "\n" .. OUTPUT_MD_PATH,
    "AutoMix Inventory",
    0
  )
end

main()
