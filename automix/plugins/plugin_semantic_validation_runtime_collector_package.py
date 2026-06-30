from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA = (
    "automix-plugin-semantic-validation-runtime-collector-package-v1"
)
REAPER_RUNTIME_QUEUE_SCHEMA = "automix-plugin-semantic-validation-reaper-runtime-queue-v1"
RUNTIME_OBSERVATION_TEMPLATE_SCHEMA = "automix-plugin-semantic-validation-runtime-observation-template-v1"
RUNTIME_OBSERVATION_SCHEMA = "automix-plugin-semantic-validation-runtime-observation-v1"

COLLECTOR_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json")
COLLECTOR_PACKAGE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.md")
COLLECTION_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collection_package.json")
QUEUE_REL_PATH = Path("eval_reports/plugin_semantic_validation_queue.json")
REAPER_SCRIPT_REL_PATH = Path("reaper_scripts/collect_plugin_semantic_validation_runtime.lua")
REAPER_QUEUE_PAYLOAD_REL_PATH = Path("reaper_scripts/plugin_semantic_validation_runtime_queue.json")
OBSERVATION_TEMPLATE_REL_PATH = Path("reaper_scripts/plugin_semantic_validation_runtime_observations_template.json")
OBSERVATION_DIR_REL_PATH = Path("reaper_scripts/observations")
OPERATOR_RUNBOOK_REL_PATH = Path("review/plugin_semantic_validation_runtime_collector_operator_runbook.md")
SAFETY_AUDIT_REL_PATH = Path("eval_reports/reaper_runtime_collector_safety_audit.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _abs(path: Path) -> str:
    return str(path.resolve())


def _resolve_report_path(value: Any, output_dir: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _lua_literal(value: Any) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "{" + ", ".join(_lua_literal(item) for item in value) + "}"
    if isinstance(value, dict):
        parts = [f"[{json.dumps(str(key), ensure_ascii=False)}] = {_lua_literal(value[key])}" for key in sorted(value)]
        return "{" + ", ".join(parts) + "}"
    return json.dumps(str(value), ensure_ascii=False)


def _observation_path(job_id: str, plugin_name: str, output_dir: Path) -> Path:
    slug = slugify(job_id or plugin_name)
    return output_dir / OBSERVATION_DIR_REL_PATH / f"{slug}_observation.json"


def _collector_job_from_collection(job: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    plugin_name = str(job.get("plugin_name", "")).strip()
    target_report_path = _resolve_report_path(job.get("target_report_path", ""), output_dir)
    observation_path = _observation_path(job_id, plugin_name, output_dir)
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "category": str(job.get("category", "unknown")),
        "priority": int(job.get("priority", 999) or 999),
        "source_job_status": str(job.get("job_status", "")),
        "target_report_path": _abs(target_report_path),
        "report_template_path": str(job.get("report_template_path", "")),
        "raw_observation_output_path": _abs(observation_path),
        "requires_reaper_runtime": True,
        "requires_saved_test_copy_or_temporary_muted_context": True,
        "required_observations": _as_string_list(job.get("required_observations", [])),
        "acceptance_criteria": _as_string_list(job.get("acceptance_criteria", [])),
        "disallowed_actions": sorted(set(_as_string_list(job.get("disallowed_actions", [])))),
        "semantic_controls_to_observe": _as_string_list(job.get("semantic_controls_to_observe", [])),
    }


def _collector_job_from_queue(job: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    plugin_name = str(job.get("plugin_name", "")).strip()
    target_report_path = _resolve_report_path(job.get("target_report_path", ""), output_dir)
    observation_path = _observation_path(job_id, plugin_name, output_dir)
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "category": str(job.get("category", "unknown")),
        "priority": int(job.get("priority", 999) or 999),
        "source_job_status": "from_queue_without_collection_package",
        "target_report_path": _abs(target_report_path),
        "report_template_path": "",
        "raw_observation_output_path": _abs(observation_path),
        "requires_reaper_runtime": True,
        "requires_saved_test_copy_or_temporary_muted_context": True,
        "required_observations": _as_string_list(job.get("required_observations", [])),
        "acceptance_criteria": _as_string_list(job.get("acceptance_criteria", [])),
        "disallowed_actions": sorted(set(_as_string_list(job.get("disallowed_actions", [])))),
        "semantic_controls_to_observe": _as_string_list(job.get("semantic_controls_to_observe", [])),
    }


def _build_observation_template(project_name: str, output_dir: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": RUNTIME_OBSERVATION_TEMPLATE_SCHEMA,
        "target_runtime_observation_schema": RUNTIME_OBSERVATION_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "collector_jobs_total": len(jobs),
        "observation_paths": [job.get("raw_observation_output_path", "") for job in jobs],
        "required_follow_up": [
            "Operator converts raw observation JSON into real plugin_parameter_validation reports only after manual review.",
            "Runtime evidence gate must validate the accepted manifest and real reports.",
            "Semantic validation gate must pass before automatic parameter writes are considered.",
        ],
        "limits": [
            "This template is not a runtime observation.",
            "Raw observations are not passing validation reports.",
            "Parameter indexes remain non-authoritative until semantic controls are reviewed.",
        ],
    }


def _build_queue_payload(
    *,
    project_name: str,
    output_dir: Path,
    source_kind: str,
    source_path: Path,
    jobs: list[dict[str, Any]],
    blocked_queue_jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": REAPER_RUNTIME_QUEUE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": _abs(output_dir),
        "source_kind": source_kind,
        "source_path": _abs(source_path),
        "collector_script_path": _abs(output_dir / REAPER_SCRIPT_REL_PATH),
        "observation_template_path": _abs(output_dir / OBSERVATION_TEMPLATE_REL_PATH),
        "jobs_total": len(jobs),
        "jobs": jobs,
        "blocked_queue_jobs_total": len(blocked_queue_jobs),
        "blocked_queue_jobs": blocked_queue_jobs,
        "safety": {
            "requires_reaper_runtime": bool(jobs),
            "requires_saved_test_copy_or_temporary_muted_context": bool(jobs),
            "temporary_muted_probe_track_only": True,
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "renders_audio": False,
            "saves_project": False,
        },
        "limits": [
            "This queue payload is operator/reference material; the Lua script embeds the same jobs directly.",
            "The collector writes raw observations only, not passing semantic validation reports.",
        ],
    }


def _lua_script(*, project_name: str, queue_payload: dict[str, Any], jobs: list[dict[str, Any]]) -> str:
    jobs_literal = _lua_literal(jobs)
    queue_path = str(queue_payload.get("collector_script_path", "")).replace(
        "collect_plugin_semantic_validation_runtime.lua", "plugin_semantic_validation_runtime_queue.json"
    )
    summary_path = str(Path(jobs[0]["raw_observation_output_path"]).parent / "plugin_semantic_validation_runtime_observation_summary.json") if jobs else ""
    return f"""-- AutoMix plugin semantic validation runtime collector.
--
-- Run this only in a saved test copy or temporary muted REAPER test context.
-- This collector writes raw observations only. It does not create validation
-- reports, render audio, save the project, or grant parameter write safety.

local SCRIPT_VERSION = "prompt78-runtime-collector-v1"
local PROJECT_NAME = {_lua_literal(project_name)}
local QUEUE_PAYLOAD_PATH = {_lua_literal(queue_path)}
local SUMMARY_OUTPUT_PATH = {_lua_literal(summary_path)}
local JOBS = {jobs_literal}

local function json_escape(value)
  local replacements = {{
    ["\\\\"] = "\\\\\\\\",
    ["\\""] = "\\\\\\"",
    ["\\b"] = "\\\\b",
    ["\\f"] = "\\\\f",
    ["\\n"] = "\\\\n",
    ["\\r"] = "\\\\r",
    ["\\t"] = "\\\\t",
  }}
  return tostring(value):gsub('[%z\\1-\\31\\\\"]', function(c)
    return replacements[c] or string.format("\\\\u%04x", c:byte())
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
  local parts = {{}}
  if is_array(value) then
    for i = 1, #value do
      parts[#parts + 1] = child_pad .. json_encode(value[i], indent + 1)
    end
    if #parts == 0 then return "[]" end
    return "[\\n" .. table.concat(parts, ",\\n") .. "\\n" .. pad .. "]"
  end

  local keys = {{}}
  for k, _ in pairs(value) do keys[#keys + 1] = tostring(k) end
  table.sort(keys)
  for _, k in ipairs(keys) do
    parts[#parts + 1] = child_pad .. '"' .. json_escape(k) .. '": ' .. json_encode(value[k], indent + 1)
  end
  if #parts == 0 then return "{{}}" end
  return "{{\\n" .. table.concat(parts, ",\\n") .. "\\n" .. pad .. "}}"
end

local function ensure_parent_dir(path)
  local dir = tostring(path or ""):match("^(.*)[/\\\\][^/\\\\]+$")
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
  local result = {{
    schema = "{RUNTIME_OBSERVATION_SCHEMA}",
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
    add_result = {{}},
    parameters = {{}},
    errors = {{}},
    warnings = {{}},
    limits = {{
      "Raw observations are not passing semantic validation reports.",
      "Parameter names and indexes require human review before write-safe mappings.",
      "This collector never calls parameter-write APIs.",
    }},
  }}
  local temp = nil
  local ok, err = pcall(function()
    temp = create_temp_probe_track(job)
    local before = reaper.TrackFX_GetCount(temp)
    local fx_index = reaper.TrackFX_AddByName(temp, job.plugin_name or "", false, 1)
    local after = reaper.TrackFX_GetCount(temp)
    local inserted = fx_index >= 0 and after > before
    result.add_result = {{
      query = job.plugin_name or "",
      returned_index = fx_index,
      fx_count_before = before,
      fx_count_after = after,
      inserted = inserted,
    }}
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
      result.parameters[#result.parameters + 1] = {{
        index = i,
        name = param_name or "",
        observed_by = "TrackFX_GetParamName",
        write_allowed = false,
        semantic_validated = false,
      }}
    end
    reaper.TrackFX_Delete(temp, fx_index)
  end)
  if not ok then
    result.errors[#result.errors + 1] = tostring(err)
  end
  delete_temp_probe_track(temp)
  result.temporary_muted_probe_track_deleted = true
  result.status = (#result.errors == 0) and "raw_observation_collected" or "raw_observation_failed"
  write_text(result.raw_observation_output_path, json_encode(result, 0) .. "\\n")
  return result
end

local function main()
  reaper.PreventUIRefresh(1)
  reaper.Undo_BeginBlock()
  local results = {{}}
  local ok, err = pcall(function()
    for _, job in ipairs(JOBS) do
      results[#results + 1] = collect_job(job)
    end
  end)
  reaper.Undo_EndBlock("AutoMix collect plugin semantic validation raw observations", -1)
  reaper.PreventUIRefresh(-1)
  local summary = {{
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
    errors = {{}},
  }}
  if not ok then
    summary.errors[#summary.errors + 1] = tostring(err)
  end
  if SUMMARY_OUTPUT_PATH ~= "" then
    write_text(SUMMARY_OUTPUT_PATH, json_encode(summary, 0) .. "\\n")
  end
  reaper.ShowMessageBox(
    "AutoMix raw runtime observations written: " .. tostring(#results) .. "\\n" .. tostring(SUMMARY_OUTPUT_PATH),
    "AutoMix Semantic Validation Collector",
    0
  )
end

main()
"""


def write_lua_collector_script(project_name: str, output_dir: Path, queue_payload: dict[str, Any], jobs: list[dict[str, Any]]) -> Path:
    path = output_dir / REAPER_SCRIPT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_lua_script(project_name=project_name, queue_payload=queue_payload, jobs=jobs), encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_collector_report(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Collector Package",
        "",
        f"- Project: `{package.get('project_name')}`",
        f"- Created UTC: `{package.get('created_at')}`",
        f"- Status: `{package.get('status')}`",
        f"- Ready for REAPER runtime collection: `{package.get('ready_for_reaper_runtime_collection')}`",
        f"- Collector jobs: `{package.get('collector_jobs_total')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        f"- Creates validation reports: `{package.get('creates_validation_reports')}`",
        f"- Lua collector: `{package.get('lua_collector_script_path')}`",
        f"- Queue payload: `{package.get('queue_payload_path')}`",
        f"- Required safety audit: `{package.get('safety_audit_path')}`",
        "",
        "This collector writes raw observations only. It does not approve plugin write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in package.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in package.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Collector Jobs", ""])
    if not package.get("collector_jobs"):
        lines.append("- none")
    for job in package.get("collector_jobs", []):
        lines.extend(
            [
                f"### {job.get('job_id')}",
                "",
                f"- Plugin: `{job.get('plugin_name')}`",
                f"- Raw observation: `{job.get('raw_observation_output_path')}`",
                f"- Target validation report: `{job.get('target_report_path')}`",
                f"- Template: `{job.get('report_template_path') or 'none'}`",
                "",
            ]
        )
    path = output_dir / COLLECTOR_PACKAGE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_operator_runbook(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Collector Operator Runbook",
        "",
        "## Preconditions",
        "",
        "- Open a saved REAPER test copy or a temporary muted test context.",
        "- Do not run this against a production mix if you are not prepared to undo/remove the temporary probe track.",
        "- Confirm the collector is being used for raw observations only.",
        "- Confirm `reaper_runtime_collector_safety_audit.json` passed before running the Lua collector.",
        "- Keep `safe_to_write_parameters=false` until the semantic validation gate passes.",
        "",
        "## Run",
        "",
        "Inside REAPER, run:",
        "",
        f"`{package.get('lua_collector_script_path')}`",
        "",
        "## Expected Outputs",
        "",
        f"- `{package.get('queue_payload_path')}`",
        f"- `{package.get('observation_template_path')}`",
        f"- `{package.get('safety_audit_path')}`",
    ]
    for job in package.get("collector_jobs", []):
        lines.append(f"- `{job.get('raw_observation_output_path')}`")
    lines.extend(
        [
            "",
            "## Follow-Up",
            "",
            "- Review raw observation JSON manually.",
            "- Rerun `scripts/run_reaper_runtime_collector_safety_audit.py --require-passed` after regenerating the collector.",
            "- Write real `automix-plugin-parameter-validation-report-v1` reports only after confirming semantic controls by name.",
            "- Create/update `automix/review/plugin_semantic_validation_runtime_manifest.json` only after the reports exist.",
            "- Rerun the runtime evidence gate, then rerun the semantic validation gate before any parameter write decision.",
            "",
            "## Disallowed",
            "",
            "- Do not copy raw observation files into `automix/analysis_reports` as passing validation reports.",
            "- Do not infer write safety from plugin insertability.",
            "- Do not hard-code parameter indexes from this collector without semantic review.",
        ]
    )
    path = output_dir / OPERATOR_RUNBOOK_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def build_plugin_semantic_validation_runtime_collector_package(
    *,
    project_name: str,
    output_dir: Path,
    collection_package: dict[str, Any] | None = None,
    queue: dict[str, Any] | None = None,
    collection_package_path: Path | None = None,
    queue_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    collection_package_path = collection_package_path or output_dir / COLLECTION_PACKAGE_REL_PATH
    queue_path = queue_path or output_dir / QUEUE_REL_PATH
    collection_package = collection_package or _load_json(collection_package_path)
    queue = queue or _load_json(queue_path)

    blockers: list[str] = []
    warnings: list[str] = []
    source_kind = ""
    source_path = collection_package_path
    blocked_queue_jobs: list[dict[str, Any]] = []

    jobs: list[dict[str, Any]] = []
    if collection_package.get("schema") == "automix-plugin-semantic-validation-runtime-collection-package-v1":
        source_kind = "runtime_collection_package"
        source_path = collection_package_path
        source_jobs = [job for job in collection_package.get("collection_jobs", []) or [] if isinstance(job, dict)]
        blocked_queue_jobs = [job for job in collection_package.get("blocked_queue_jobs", []) or [] if isinstance(job, dict)]
        if collection_package.get("blockers"):
            warnings.append("source_runtime_collection_package_has_blockers")
        jobs = [_collector_job_from_collection(job, output_dir=output_dir) for job in source_jobs]
    elif queue.get("schema") == "automix-plugin-semantic-validation-queue-v1":
        source_kind = "semantic_validation_queue_fallback"
        source_path = queue_path
        source_jobs = [job for job in queue.get("queue_jobs", []) or [] if isinstance(job, dict)]
        blocked_queue_jobs = [job for job in queue.get("blocked_jobs", []) or [] if isinstance(job, dict)]
        warnings.append("runtime_collection_package_missing_using_queue_fallback")
        jobs = [_collector_job_from_queue(job, output_dir=output_dir) for job in source_jobs]
    else:
        blockers.append("runtime_collection_package_or_queue_missing_or_invalid")

    jobs = sorted(jobs, key=lambda item: (int(item.get("priority", 999) or 999), str(item.get("plugin_name", "")).lower()))
    if blocked_queue_jobs:
        warnings.append(f"blocked_queue_jobs_remain:{len(blocked_queue_jobs)}")

    if blockers:
        status = "runtime_collector_package_blocked"
    elif not jobs:
        status = "no_runtime_collector_jobs"
    else:
        status = "runtime_collector_package_ready"

    queue_payload = _build_queue_payload(
        project_name=project_name,
        output_dir=output_dir,
        source_kind=source_kind,
        source_path=source_path,
        jobs=jobs,
        blocked_queue_jobs=blocked_queue_jobs,
    )
    observation_template = _build_observation_template(project_name, output_dir, jobs)
    write_json(output_dir / REAPER_QUEUE_PAYLOAD_REL_PATH, queue_payload)
    write_json(output_dir / OBSERVATION_TEMPLATE_REL_PATH, observation_template)
    lua_path = write_lua_collector_script(project_name, output_dir, queue_payload, jobs)

    package = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_kind": source_kind,
        "source_path": str(source_path),
        "status": status,
        "ready_for_reaper_runtime_collection": bool(jobs and not blockers),
        "ready_for_runtime_evidence_gate": False,
        "requires_reaper_runtime": bool(jobs),
        "requires_saved_test_copy_or_temporary_muted_context": bool(jobs),
        "requires_operator_review": bool(jobs or blocked_queue_jobs),
        "requires_collector_safety_audit": True,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "collector_jobs_total": len(jobs),
        "blocked_queue_jobs_total": len(blocked_queue_jobs),
        "collector_jobs": jobs,
        "blocked_queue_jobs": blocked_queue_jobs,
        "lua_collector_script_path": str(lua_path),
        "queue_payload_path": str(output_dir / REAPER_QUEUE_PAYLOAD_REL_PATH),
        "observation_template_path": str(output_dir / OBSERVATION_TEMPLATE_REL_PATH),
        "operator_runbook_path": str(output_dir / OPERATOR_RUNBOOK_REL_PATH),
        "safety_audit_path": str(output_dir / SAFETY_AUDIT_REL_PATH),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This package writes a REAPER Lua collector and queue payload only.",
            "The generated Lua collector must pass reaper_runtime_collector_safety_audit before operator runtime collection.",
            "The collector creates raw observation files, not passing validation reports.",
            "safe_to_write_parameters remains false; runtime and semantic gates must pass later.",
        ],
    }
    target = output_path or output_dir / COLLECTOR_PACKAGE_REL_PATH
    write_json(target, package)
    write_plugin_semantic_validation_runtime_collector_report(package, output_dir)
    write_operator_runbook(package, output_dir)
    return package
