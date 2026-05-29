-- Smoke-test Codex no-paid-plugin tune/EQ substitute FX in a new REAPER project.

local report_path = "reports/codex_tune_eq_substitute_reaper_smoke.json"

local function ensure_parent(path)
  local parent = path:match("^(.*)[/\\][^/\\]+$")
  if parent and parent ~= "" then
    reaper.RecursiveCreateDirectory(parent, 0)
  end
end

local function esc(value)
  value = tostring(value or "")
  value = value:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n")
  return value
end

local function add_first(track, candidates)
  for _, name in ipairs(candidates) do
    local fx = reaper.TrackFX_AddByName(track, name, false, -1)
    if fx and fx >= 0 then
      return true, name, fx
    end
  end
  return false, candidates[1] or "", -1
end

local rows = {}
local function add_row(severity, stage, status, plugin, fx_index)
  table.insert(rows, {
    severity = severity,
    stage = stage,
    status = status,
    plugin = plugin,
    fx_index = fx_index,
  })
end

reaper.InsertTrackAtIndex(0, true)
local track = reaper.GetTrack(0, 0)
reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "CODEX_TUNE_EQ_SUBSTITUTE_SMOKE_VOCAL", true)

local ok, plugin, fx = add_first(track, {
  "JS: codex_fresh_mix/codex_vocal_pitch_monitor.jsfx",
  "codex_fresh_mix/codex_vocal_pitch_monitor.jsfx",
})
add_row(ok and "PASS" or "FAIL", "pitch_monitor_jsfx", ok and "loaded" or "missing", plugin, fx)

ok, plugin, fx = add_first(track, {
  "ReaTune",
  "VST: ReaTune (Cockos)",
  "VST: ReaTune",
})
add_row(ok and "PASS" or "WARN", "reatune_stock_engine", ok and "loaded" or "missing", plugin, fx)

ok, plugin, fx = add_first(track, {
  "JS: codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx",
  "codex_fresh_mix/codex_pro_dynamic_ms_eq.jsfx",
})
add_row(ok and "PASS" or "FAIL", "pro_dynamic_ms_eq_jsfx", ok and "loaded" or "missing", plugin, fx)

ok, plugin, fx = add_first(track, {
  "JS: codex_fresh_mix/codex_dynamic_eq_band.jsfx",
  "codex_fresh_mix/codex_dynamic_eq_band.jsfx",
})
add_row(ok and "PASS" or "WARN", "single_dynamic_eq_band_jsfx", ok and "loaded" or "missing", plugin, fx)

local max_severity = "PASS"
for _, row in ipairs(rows) do
  if row.severity == "FAIL" then
    max_severity = "FAIL"
  elseif row.severity == "WARN" and max_severity ~= "FAIL" then
    max_severity = "WARN"
  end
end

ensure_parent(report_path)
local f = io.open(report_path, "w")
if f then
  f:write("{\n")
  f:write('  "script": "scripts/smoke_codex_tune_eq_substitute.lua",\n')
  f:write('  "max_severity": "' .. esc(max_severity) .. '",\n')
  f:write('  "rows": [\n')
  for i, row in ipairs(rows) do
    f:write("    {\n")
    f:write('      "severity": "' .. esc(row.severity) .. '",\n')
    f:write('      "stage": "' .. esc(row.stage) .. '",\n')
    f:write('      "status": "' .. esc(row.status) .. '",\n')
    f:write('      "plugin": "' .. esc(row.plugin) .. '",\n')
    f:write('      "fx_index": ' .. tostring(row.fx_index) .. "\n")
    f:write("    }" .. (i == #rows and "\n" or ",\n"))
  end
  f:write("  ]\n")
  f:write("}\n")
  f:close()
end

reaper.ShowConsoleMsg("Codex tune/EQ substitute smoke: " .. max_severity .. "\n")
