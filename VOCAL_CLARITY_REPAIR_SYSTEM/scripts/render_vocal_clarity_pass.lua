local rpp = [[/Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v44_louder_more_audible_master/mesi_1_v44_LOUDER_MORE_AUDIBLE_MASTER.rpp]]
local render_dir = [[/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v44_louder_more_audible_master]]
local log_path = [[/Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v44_louder_more_audible_master/render_prepare.log]]
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\n"); f:close() end end
os.remove(log_path)
local ok,err=xpcall(function()
  reaper.Main_openProject(rpp)
  reaper.GetSetProjectInfo_String(0,"RENDER_FILE",render_dir,true)
  reaper.GetSetProjectInfo_String(0,"RENDER_PATTERN","mesi_1_v44_REAPERPRINT_louder_audible_24-48",true)
  reaper.Main_SaveProjectEx(0,rpp,0)
  log("wrapper ok")
end, debug.traceback)
if not ok then log("wrapper error: " .. tostring(err)) end
reaper.defer(function() reaper.Main_OnCommand(40004,0) end)
