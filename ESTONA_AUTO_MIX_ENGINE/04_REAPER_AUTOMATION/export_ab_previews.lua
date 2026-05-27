-- Mark likely 15s A/B preview regions in REAPER. Rendering those regions can be
-- done with REAPER's region render matrix or the Python preview helper.

local ranges = {
  {"reference_15s", 0, 15},
  {"previous_approved_15s", 15, 30},
  {"current_render_15s", 30, 45},
  {"hook_section_15s", 45, 60},
  {"loudest_section_15s", 60, 75},
  {"vocal_exposed_15s", 75, 90}
}

reaper.Undo_BeginBlock()
reaper.PreventUIRefresh(1)
for _, r in ipairs(ranges) do
  reaper.AddProjectMarker2(0, true, r[2], r[3], "ESTONA_AB_" .. r[1], -1, 0)
end
reaper.SetProjExtState(0, "ESTONA_AUTO_MIX_ENGINE", "ab_preview_regions_created", os.date("%Y-%m-%d %H:%M:%S"))
reaper.PreventUIRefresh(-1)
reaper.Undo_EndBlock("Create ESTONA A/B preview regions", -1)
