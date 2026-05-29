-- Codex guarded render candidate preparer.
-- This script prepares deterministic candidate render paths and JSON reports.
-- Use REAPER command-line renderproject on each saved candidate project.

local CONFIG = {
  project_root = ".",
  song_slug = "music_pipeline_candidates",
}

local CANDIDATES = {
  { id = "A_safe", intent = "conservative cleanup and output guard" },
  { id = "B_more_deai", intent = "stronger DeAI attempt, blocked unless brightness/transient guards pass" },
  { id = "C_punch_preserve", intent = "transient-first punch preservation" },
  { id = "D_reference_match", intent = "advisory reference translation only" },
}

local function join_path(a, b)
  if a:sub(-1) == "/" or a:sub(-1) == "\\" then
    return a .. b
  end
  return a .. "/" .. b
end

local function ensure_dir(path)
  reaper.RecursiveCreateDirectory(path, 0)
end

local function file_exists(path)
  local handle = io.open(path, "rb")
  if handle then
    handle:close()
    return true
  end
  return false
end

local function write_report(path, lines)
  local handle = io.open(path, "w")
  if not handle then
    reaper.ShowConsoleMsg("WARN could not write report: " .. path .. "\n")
    return
  end
  for _, line in ipairs(lines) do
    handle:write(line .. "\n")
  end
  handle:close()
end

local function prepare_candidate(candidate, reaper_dir, render_dir, report_dir)
  local render_path = join_path(render_dir, candidate.id .. ".wav")
  local project_path = join_path(reaper_dir, candidate.id .. "_RENDER.rpp")
  local report_path = join_path(report_dir, candidate.id .. ".json")
  local severity = "PASS"
  local status = "prepared"
  if file_exists(render_path) then
    severity = "FAIL"
    status = "render_exists_refusing_overwrite"
  else
    reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
    reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", candidate.id, true)
    reaper.Main_SaveProject(0, false)
  end
  write_report(report_path, {
    "{",
    '  "candidate_id": "' .. candidate.id .. '",',
    '  "intent": "' .. candidate.intent .. '",',
    '  "severity": "' .. severity .. '",',
    '  "status": "' .. status .. '",',
    '  "render_wav": "' .. render_path:gsub("\\", "\\\\") .. '",',
    '  "project_path_requested": "' .. project_path:gsub("\\", "\\\\") .. '",',
    '  "save_note": "REAPER API save-as is intentionally not guessed here; save a copy to project_path_requested before renderproject.",',
    '  "command_to_render": "REAPER -newinst -nosplash -renderproject ' .. project_path:gsub("\\", "\\\\") .. '",',
    '  "qc_command": "python3 -m harness.audio_qc --before BEFORE.wav --after ' .. render_path:gsub("\\", "\\\\") .. ' --json"',
    "}",
  })
  return severity, status, render_path
end

local function main()
  local reaper_dir = join_path(join_path(CONFIG.project_root, "reaper"), CONFIG.song_slug)
  local render_dir = join_path(join_path(CONFIG.project_root, "renders"), CONFIG.song_slug)
  local report_dir = join_path(join_path(CONFIG.project_root, "reports"), CONFIG.song_slug)
  ensure_dir(reaper_dir)
  ensure_dir(render_dir)
  ensure_dir(report_dir)

  local summary = { "{", '  "script": "scripts/render_candidates.lua",', '  "candidates": [' }
  for index, candidate in ipairs(CANDIDATES) do
    local severity, status, render_path = prepare_candidate(candidate, reaper_dir, render_dir, report_dir)
    table.insert(summary, '    { "candidate_id": "' .. candidate.id .. '", "severity": "' .. severity .. '", "status": "' .. status .. '", "render_wav": "' .. render_path:gsub("\\", "\\\\") .. '" }' .. (index == #CANDIDATES and "" or ","))
  end
  table.insert(summary, "  ]")
  table.insert(summary, "}")
  write_report(join_path(report_dir, "render_candidates_summary.json"), summary)
  reaper.ShowConsoleMsg("render_candidates.lua prepared candidate projects. Render with REAPER -renderproject, then run audio QC.\n")
end

main()
