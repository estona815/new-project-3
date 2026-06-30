-- AutoMix plugin semantic validation runtime collector.
--
-- Run this only in a saved test copy or temporary muted REAPER test context.
-- This collector writes raw observations only. It does not create validation
-- reports, render audio, save the project, or grant parameter write safety.

local SCRIPT_VERSION = "prompt78-runtime-collector-v1"
local PROJECT_NAME = "project"
local QUEUE_PAYLOAD_PATH = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/plugin_semantic_validation_runtime_queue.json"
local SUMMARY_OUTPUT_PATH = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/plugin_semantic_validation_runtime_observation_summary.json"
local JOBS = {{["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "jsfx", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx", ["plugin_name"] = "Codex Vocal/vocal_ai_artifact_split_tamer.jsfx", ["priority"] = 20, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_01_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_codex_vocal_vocal_ai_artifact_split_tamer.jsfx_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "stock", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_02_reaverbate_cockos", ["plugin_name"] = "ReaVerbate (Cockos)", ["priority"] = 20, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_02_reaverbate_cockos_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_02_reaverbate_cockos_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reaverbate_cockos_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "jsfx", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx", ["plugin_name"] = "Vocal Clarity Repair/vocal_air_guard.jsfx", ["priority"] = 20, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_03_vocal_clarity_repair_vocal_air_guard.jsfx_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_air_guard.jsfx_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "jsfx", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx", ["plugin_name"] = "Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx", ["priority"] = 20, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_04_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_demud_dynamic_eq.jsfx_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "jsfx", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx", ["plugin_name"] = "Vocal Clarity Repair/vocal_output_guard.jsfx", ["priority"] = 20, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_05_vocal_clarity_repair_vocal_output_guard.jsfx_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_output_guard.jsfx_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "jsfx", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx", ["plugin_name"] = "Vocal Clarity Repair/vocal_presence_enhancer.jsfx", ["priority"] = 20, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_06_vocal_clarity_repair_vocal_presence_enhancer.jsfx_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_vocal_clarity_repair_vocal_presence_enhancer.jsfx_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "stock", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_07_reacomp_cockos", ["plugin_name"] = "ReaComp (Cockos)", ["priority"] = 30, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_07_reacomp_cockos_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_07_reacomp_cockos_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reacomp_cockos_rerun_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "stock", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_08_readelay_cockos", ["plugin_name"] = "ReaDelay (Cockos)", ["priority"] = 30, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_08_readelay_cockos_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_08_readelay_cockos_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_readelay_cockos_rerun_reaper_observed.json"}, {["acceptance_criteria"] = {"report schema is automix-plugin-parameter-validation-report-v1", "status=passed", "safe_for_automix=true", "no_fake_success=true", "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name"}, ["category"] = "stock", ["disallowed_actions"] = {"do not mark a report passed from plugin availability alone", "do not use fixed parameter indexes unless observed in the target REAPER runtime", "do not validate on a production track without a saved test copy or temporary muted test context", "do not write parameters to the user's mix from this queue"}, ["job_id"] = "semantic_validation_09_reaeq_cockos", ["plugin_name"] = "ReaEQ (Cockos)", ["priority"] = 30, ["raw_observation_output_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/reaper_scripts/observations/semantic_validation_09_reaeq_cockos_observation.json", ["report_template_path"] = "automix/review/plugin_semantic_validation_runtime_report_templates/semantic_validation_09_reaeq_cockos_validation_report_template.json", ["required_observations"] = {"REAPER runtime observed the exact plugin or accepted installed substitute", "semantic parameter response observed by name or verified helper, not guessed from index order", "status=passed only when the report has at least one validated write-safe semantic control", "safe_for_automix=true and no_fake_success=true only after observed response evidence", "safe min/max bounds recorded for every write_allowed semantic control"}, ["requires_reaper_runtime"] = true, ["requires_saved_test_copy_or_temporary_muted_context"] = true, ["semantic_controls_to_observe"] = {}, ["source_job_status"] = "awaiting_reaper_runtime_collection", ["target_report_path"] = "/Users/hantaeheuk/Documents/New project 3/automix/analysis_reports/plugin_parameter_validation_reaeq_cockos_rerun_reaper_observed.json"}}

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

local function ensure_parent_dir(path)
  local dir = tostring(path or ""):match("^(.*)[/\\][^/\\]+$")
  if dir and dir ~= "" and reaper.RecursiveCreateDirectory then
    reaper.RecursiveCreateDirectory(dir, 0)
  end
end

local function write_text(path, text)
  ensure_parent_dir(path)
  local f, err = io.open(path, "w")
  if not f then error("Cannot write " .. tostring(path) .. ": " .. tostring(err)) end
  f:write(text)
  f:close()
end

local function create_temp_probe_track(job)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, false)
  local tr = reaper.GetTrack(0, idx)
  if not tr then error("Could not create temporary semantic validation probe track") end
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", "__AUTOMIX_SEMANTIC_VALIDATION_TEMP_DO_NOT_USE__", true)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
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

local function collect_job(job)
  local result = {
    schema = "automix-plugin-semantic-validation-runtime-observation-v1",
    script_version = SCRIPT_VERSION,
    project_name = PROJECT_NAME,
    job_id = job.job_id or "",
    plugin_name = job.plugin_name or "",
    target_report_path = job.target_report_path or "",
    raw_observation_output_path = job.raw_observation_output_path or "",
    queue_payload_path = QUEUE_PAYLOAD_PATH,
    created_at_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
    safe_to_write_parameters = false,
    creates_validation_reports = false,
    writes_parameters = false,
    renders_audio = false,
    saves_project = false,
    temporary_muted_probe_track_used = true,
    temporary_muted_probe_track_deleted = false,
    parameter_indexes_assumed = false,
    add_result = {},
    parameters = {},
    errors = {},
    warnings = {},
    limits = {
      "Raw observations are not passing semantic validation reports.",
      "Parameter names and indexes require human review before write-safe mappings.",
      "This collector never calls parameter-write APIs.",
    },
  }
  local temp = nil
  local ok, err = pcall(function()
    temp = create_temp_probe_track(job)
    local before = reaper.TrackFX_GetCount(temp)
    local fx_index = reaper.TrackFX_AddByName(temp, job.plugin_name or "", false, 1)
    local after = reaper.TrackFX_GetCount(temp)
    local inserted = fx_index >= 0 and after > before
    result.add_result = {
      query = job.plugin_name or "",
      returned_index = fx_index,
      fx_count_before = before,
      fx_count_after = after,
      inserted = inserted,
    }
    if not inserted then
      result.errors[#result.errors + 1] = "plugin_insert_failed"
      return
    end
    local _, actual_name = reaper.TrackFX_GetFXName(temp, fx_index, "")
    result.actual_fx_name = actual_name or ""
    local param_count = reaper.TrackFX_GetNumParams(temp, fx_index)
    result.param_count = param_count
    for i = 0, param_count - 1 do
      local _, param_name = reaper.TrackFX_GetParamName(temp, fx_index, i, "")
      result.parameters[#result.parameters + 1] = {
        index = i,
        name = param_name or "",
        observed_by = "TrackFX_GetParamName",
        write_allowed = false,
        semantic_validated = false,
      }
    end
    reaper.TrackFX_Delete(temp, fx_index)
  end)
  if not ok then
    result.errors[#result.errors + 1] = tostring(err)
  end
  delete_temp_probe_track(temp)
  result.temporary_muted_probe_track_deleted = true
  result.status = (#result.errors == 0) and "raw_observation_collected" or "raw_observation_failed"
  write_text(result.raw_observation_output_path, json_encode(result, 0) .. "\n")
  return result
end

local function main()
  reaper.PreventUIRefresh(1)
  reaper.Undo_BeginBlock()
  local results = {}
  local ok, err = pcall(function()
    for _, job in ipairs(JOBS) do
      results[#results + 1] = collect_job(job)
    end
  end)
  reaper.Undo_EndBlock("AutoMix collect plugin semantic validation raw observations", -1)
  reaper.PreventUIRefresh(-1)
  local summary = {
    schema = "automix-plugin-semantic-validation-runtime-observation-summary-v1",
    script_version = SCRIPT_VERSION,
    project_name = PROJECT_NAME,
    created_at_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
    safe_to_write_parameters = false,
    creates_validation_reports = false,
    queue_payload_path = QUEUE_PAYLOAD_PATH,
    jobs_total = #JOBS,
    observations_total = #results,
    results = results,
    errors = {},
  }
  if not ok then
    summary.errors[#summary.errors + 1] = tostring(err)
  end
  if SUMMARY_OUTPUT_PATH ~= "" then
    write_text(SUMMARY_OUTPUT_PATH, json_encode(summary, 0) .. "\n")
  end
  reaper.ShowMessageBox(
    "AutoMix raw runtime observations written: " .. tostring(#results) .. "\n" .. tostring(SUMMARY_OUTPUT_PATH),
    "AutoMix Semantic Validation Collector",
    0
  )
end

main()
