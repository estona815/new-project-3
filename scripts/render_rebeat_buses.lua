-- Render role-specific rebeat buses. This script assumes tracks/buses are named with role tokens.
-- Required true_rebeat bus renders: drums, bass, music/support, mix, master.

local function ext(key, fallback)
  local value = reaper.GetExtState("codex_rebeat", key)
  if value == nil or value == "" then return fallback end
  return value
end

local out_dir = ext("render_dir", "")
local slug = ext("slug", "song_vNEXT")
if out_dir == "" then
  reaper.ShowMessageBox("codex_rebeat render_dir extstate is missing.", "Render rebeat buses", 0)
  return
end

local roles = {
  {key = "drums", token = "DRUM"},
  {key = "bass", token = "BASS"},
  {key = "music", token = "MUSIC"},
  {key = "mix", token = "MIX_BUS"},
  {key = "master", token = "MASTER_BUS"}
}

local function set_all_mute(mute)
  for i = 0, reaper.CountTracks(0) - 1 do
    reaper.SetMediaTrackInfo_Value(reaper.GetTrack(0, i), "B_MUTE", mute and 1 or 0)
  end
end

local function unmute_role(token)
  for i = 0, reaper.CountTracks(0) - 1 do
    local track = reaper.GetTrack(0, i)
    local _, name = reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "", false)
    if string.find(string.upper(name), token, 1, true) then
      reaper.SetMediaTrackInfo_Value(track, "B_MUTE", 0)
    end
  end
end

reaper.Undo_BeginBlock()
for _, role in ipairs(roles) do
  set_all_mute(true)
  unmute_role(role.token)
  local out = out_dir .. "/" .. slug .. "_" .. role.key .. "_bus.wav"
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", out_dir, true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", slug .. "_" .. role.key .. "_bus", true)
  reaper.Main_OnCommand(41824, 0) -- File: Render project, using the most recent render settings
end
set_all_mute(false)
reaper.Undo_EndBlock("Render rebeat buses", -1)
