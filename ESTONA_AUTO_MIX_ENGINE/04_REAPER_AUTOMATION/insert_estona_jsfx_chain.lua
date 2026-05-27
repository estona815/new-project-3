-- Insert ESTONA JSFX chain on selected tracks.
local jsfx = {
  "estona_Vocal_AntiAI_Harsh",
  "estona_Vocal_Beat_Glue",
  "estona_DigiClip",
  "estona_MonoSub_Guard"
}

reaper.Undo_BeginBlock()
for i = 0, reaper.CountSelectedTracks(0)-1 do
  local tr = reaper.GetSelectedTrack(0, i)
  for _, name in ipairs(jsfx) do
    reaper.TrackFX_AddByName(tr, name, false, -1)
  end
end
reaper.Undo_EndBlock("Insert ESTONA JSFX chain", -1)
