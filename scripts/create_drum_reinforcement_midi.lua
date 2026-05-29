-- Create drum reinforcement MIDI from a simple TSV/CSV event file.
-- Expected columns: time_sec,note,velocity,length_sec,label
-- This creates auditable MIDI items; audible rebeat still requires instruments/samples and bus renders.

local function ext(key, fallback)
  local value = reaper.GetExtState("codex_rebeat", key)
  if value == nil or value == "" then return fallback end
  return value
end

local function find_or_create_track(name)
  for i = 0, reaper.CountTracks(0) - 1 do
    local track = reaper.GetTrack(0, i)
    local _, track_name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
    if track_name == name then return track end
  end
  local index = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(index, true)
  local track = reaper.GetTrack(0, index)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", name, true)
  return track
end

local function parse_line(line)
  if line:match("^%s*time_sec") then return nil end
  local parts = {}
  for field in line:gmatch("[^,\t]+") do
    parts[#parts + 1] = field
  end
  if #parts < 3 then return nil end
  return {
    time = tonumber(parts[1]),
    note = tonumber(parts[2]),
    velocity = tonumber(parts[3]),
    length = tonumber(parts[4]) or 0.08,
    label = parts[5] or "drum"
  }
end

local events_path = ext("drum_events_tsv", "")
if events_path == "" then
  reaper.ShowMessageBox("codex_rebeat drum_events_tsv extstate is missing.", "Drum reinforcement MIDI", 0)
  return
end

local file = io.open(events_path, "r")
if file == nil then
  reaper.ShowMessageBox("Could not open drum events file: " .. events_path, "Drum reinforcement MIDI", 0)
  return
end

reaper.Undo_BeginBlock()
local kick = find_or_create_track("04_KICK_REBUILD_MIDI")
local snare = find_or_create_track("05_SNARE_CLAP_REBUILD_MIDI")
local hat = find_or_create_track("06_HAT_PERC_REBUILD_MIDI")

for line in file:lines() do
  local event = parse_line(line)
  if event ~= nil and event.time ~= nil and event.note ~= nil then
    local track = kick
    if event.note == 38 or event.note == 40 then track = snare end
    if event.note == 42 or event.note == 46 or event.note == 39 or event.note == 51 then track = hat end
    local item = reaper.CreateNewMIDIItemInProj(track, event.time, event.time + event.length, false)
    local take = reaper.GetActiveTake(item)
    local ppq_start = reaper.MIDI_GetPPQPosFromProjTime(take, event.time)
    local ppq_end = reaper.MIDI_GetPPQPosFromProjTime(take, event.time + event.length)
    local velocity = math.max(1, math.min(127, event.velocity))
    reaper.MIDI_InsertNote(take, false, false, ppq_start, ppq_end, 0, event.note, velocity, false)
    reaper.MIDI_Sort(take)
    reaper.GetSetMediaItemInfo_String(item, "P_NOTES", "Codex drum reinforcement: " .. event.label, true)
  end
end
file:close()

reaper.Undo_EndBlock("Create drum reinforcement MIDI", -1)
