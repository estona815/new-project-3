-- Codex REAPER music pipeline session builder.
-- Run from REAPER after editing CONFIG.project_root/source_dir if needed.

local CONFIG = {
  project_root = ".",
  source_dir = "input_stems",
  song_slug = "music_pipeline_candidates",
  project_name = "music_pipeline_candidates.rpp",
}

local TRACKS = {
  { name = "01_REF_ORIGINAL", role = "reference" },
  { name = "02_DRUMS", role = "drums" },
  { name = "03_BASS", role = "bass" },
  { name = "04_MUSIC", role = "music" },
  { name = "05_VOCAL", role = "vocal" },
  { name = "06_FX", role = "fx" },
  { name = "07_PARALLEL_COMP", role = "parallel" },
  { name = "08_DEAI_BUS", role = "deai_bus" },
  { name = "09_MIX_BUS", role = "mix_bus" },
  { name = "10_MASTER_PRINT", role = "master_print" },
}

local ROLE_TOKENS = {
  reference = { "fullmix", "full_mix", "full mix", "2track", "master", "original", "reference" },
  drums = { "drum", "kick", "snare", "hat", "perc", "beat" },
  bass = { "bass", "808", "sub" },
  music = { "music", "synth", "key", "piano", "guitar", "melody", "instrumental", "inst" },
  vocal = { "vocal", "vox", "lead", "voice", "adlib", "bgv" },
  fx = { "fx", "sfx", "riser", "impact", "texture" },
}

local AUDIO_EXT = {
  wav = true,
  aif = true,
  aiff = true,
  flac = true,
  mp3 = true,
  m4a = true,
  ogg = true,
}

local function join_path(a, b)
  if a:sub(-1) == "/" or a:sub(-1) == "\\" then
    return a .. b
  end
  return a .. "/" .. b
end

local function basename(path)
  return path:match("([^/\\]+)$") or path
end

local function stem_lower(path)
  local name = basename(path):lower()
  return name:gsub("%.[^.]+$", "")
end

local function extension(path)
  return (path:match("%.([^.]+)$") or ""):lower()
end

local function contains_any(text, tokens)
  local lower = text:lower()
  for _, token in ipairs(tokens) do
    if lower:find(token, 1, true) then
      return true
    end
  end
  return false
end

local function classify_file(path)
  local text = stem_lower(path)
  for role, tokens in pairs(ROLE_TOKENS) do
    if contains_any(text, tokens) then
      return role
    end
  end
  return "unclassified"
end

local function scan_audio_files(dir)
  local files = {}
  local index = 0
  while true do
    local file = reaper.EnumerateFiles(dir, index)
    if not file then
      break
    end
    if AUDIO_EXT[extension(file)] then
      local path = join_path(dir, file)
      local role = classify_file(path)
      if not files[role] then
        files[role] = {}
      end
      table.insert(files[role], path)
    end
    index = index + 1
  end
  return files
end

local function ensure_dir(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

local function write_report(path, payload_lines)
  local handle = io.open(path, "w")
  if not handle then
    reaper.ShowConsoleMsg("WARN could not write report: " .. path .. "\n")
    return
  end
  for _, line in ipairs(payload_lines) do
    handle:write(line .. "\n")
  end
  handle:close()
end

local function create_track(index, name)
  reaper.InsertTrackAtIndex(index - 1, true)
  local track = reaper.GetTrack(0, index - 1)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
  return track
end

local function add_media_item(track, path)
  local source = reaper.PCM_Source_CreateFromFile(path)
  if not source then
    return false, "PCM_Source_CreateFromFile failed"
  end
  local item = reaper.AddMediaItemToTrack(track)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, source)
  local length = reaper.GetMediaSourceLength(source)
  if length and length > 0 then
    reaper.SetMediaItemInfo_Value(item, "D_LENGTH", length)
  end
  return true, "ok"
end

local function main()
  local source_dir = CONFIG.source_dir
  if not source_dir:match("^/") and not source_dir:match("^%a:[/\\]") then
    source_dir = join_path(CONFIG.project_root, source_dir)
  end
  local reaper_dir = join_path(join_path(CONFIG.project_root, "reaper"), CONFIG.song_slug)
  local reports_dir = join_path(join_path(CONFIG.project_root, "reports"), CONFIG.song_slug)
  ensure_dir(reaper_dir)
  ensure_dir(reports_dir)

  reaper.Undo_BeginBlock()
  local files_by_role = scan_audio_files(source_dir)
  local report = {
    "{",
    '  "script": "scripts/create_reaper_mix_session.lua",',
    '  "source_dir": "' .. source_dir:gsub("\\", "\\\\") .. '",',
    '  "created_tracks": [',
  }
  local tracks_by_role = {}
  for index, spec in ipairs(TRACKS) do
    local track = create_track(index, spec.name)
    tracks_by_role[spec.role] = track
    if spec.role == "reference" then
      reaper.SetMediaTrackInfo_Value(track, "B_MUTE", 1)
    end
    table.insert(report, '    "' .. spec.name .. '"' .. (index == #TRACKS and "" or ","))
  end
  table.insert(report, "  ],")
  table.insert(report, '  "imports": [')

  local import_rows = {}
  local unavailable = {}
  for role, track in pairs(tracks_by_role) do
    if role ~= "parallel" and role ~= "deai_bus" and role ~= "mix_bus" and role ~= "master_print" then
      local files = files_by_role[role] or {}
      if #files == 0 then
        table.insert(unavailable, role)
      end
      for _, path in ipairs(files) do
        local ok, message = add_media_item(track, path)
        table.insert(import_rows, '    { "role": "' .. role .. '", "file": "' .. path:gsub("\\", "\\\\") .. '", "status": "' .. (ok and "imported" or "failed") .. '", "message": "' .. message .. '" }')
      end
    end
  end
  for index, row in ipairs(import_rows) do
    table.insert(report, row .. (index == #import_rows and "" or ","))
  end
  table.insert(report, "  ],")
  table.insert(report, '  "unavailable_stems": [')
  for index, role in ipairs(unavailable) do
    table.insert(report, '    "' .. role .. '"' .. (index == #unavailable and "" or ","))
  end
  local project_path = join_path(reaper_dir, CONFIG.project_name)
  table.insert(report, "  ],")
  table.insert(report, '  "project_path_requested": "' .. project_path:gsub("\\", "\\\\") .. '",')
  table.insert(report, '  "save_note": "REAPER API save-as is intentionally not guessed here; save the session to project_path_requested before render claims."')
  table.insert(report, "}")
  reaper.Main_SaveProject(0, false)
  write_report(join_path(reports_dir, "create_reaper_mix_session.json"), report)
  reaper.Undo_EndBlock("Codex create guarded music pipeline session", -1)
  reaper.ShowConsoleMsg("create_reaper_mix_session.lua complete: " .. project_path .. "\n")
end

main()
