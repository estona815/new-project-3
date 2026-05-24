
-- Harness v0.5 render setup. Inspect the session before rendering.
local project_dir = reaper.GetProjectPath("")
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", project_dir .. "/renders", true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "PREMASTER_24bit_48k", true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.ShowMessageBox("Render premaster first, then duplicate settings for MASTER_24bit_48k after confirming the master chain. MP3 export is optional after WAV verification.", "Render targets prepared", 0)
