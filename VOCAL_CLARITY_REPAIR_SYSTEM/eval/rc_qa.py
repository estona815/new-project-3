from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any

from .audio_metrics import save_json
from .evaluation_harness import preset_slug, run_evaluation
from .preset_policy import load_factory_presets, load_release_policy, parameter_definitions, validate_factory_presets
from .release_gate import evaluate_release_candidate, write_markdown_report
from .synthetic_assets import generate_synthetic_suite


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
JSFX = ROOT / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
INSTALLED_JSFX = Path.home() / "Library/Application Support/REAPER/Effects/Codex Vocal/vocal_ai_artifact_split_tamer.jsfx"
RC_METADATA = ROOT / "release" / "rc_metadata.json"
JSON_FILES = [
    ROOT / "presets" / "factory_presets_safe_defaults.json",
    ROOT / "presets" / "release_candidate_policy.json",
    ROOT / "presets" / "model_output_contract_default.json",
    ROOT / "audio_tests" / "manifest.json",
    RC_METADATA,
]
PYTHON_FILES = [
    ROOT / "eval" / "audio_metrics.py",
    ROOT / "eval" / "evaluation_harness.py",
    ROOT / "eval" / "preset_policy.py",
    ROOT / "eval" / "release_gate.py",
    ROOT / "eval" / "rc_qa.py",
    ROOT / "eval" / "synthetic_assets.py",
    ROOT / "ml" / "model_output_contract.py",
    ROOT / "scripts" / "plugin_eval.py",
    REPO_ROOT / "tests" / "test_vocal_ai_artifact_split_tamer_jsfx.py",
    REPO_ROOT / "tests" / "test_reaper_multiband_prototype_assets.py",
    REPO_ROOT / "tests" / "test_model_output_contract.py",
    REPO_ROOT / "tests" / "test_ab_quality_harness.py",
    REPO_ROOT / "tests" / "test_prompt8_preset_release_policy.py",
    REPO_ROOT / "tests" / "test_prompt9_rc_qa_lock.py",
    REPO_ROOT / "tests" / "test_prompt10_developer_handoff.py",
    REPO_ROOT / "tests" / "test_prompt11_signal_path_audit.py",
    REPO_ROOT / "tests" / "test_prompt12_first_safety_patch.py",
    REPO_ROOT / "tests" / "test_prompt13_stft_mask_model_safety.py",
    REPO_ROOT / "tests" / "test_prompt14_conservative_soft_mask.py",
    REPO_ROOT / "tests" / "test_prompt15_source_preserve_guards.py",
    REPO_ROOT / "tests" / "test_prompt16_residual_eval_foundation.py",
]
TEST_FILES = [path for path in PYTHON_FILES if path.name.startswith("test_")]
DEFAULT_BLOCK_SIZES = [1, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 333]
DEFAULT_SAMPLE_RATES = [44100, 48000, 88200, 96000]
REALTIME_FORBIDDEN_PATTERNS = [
    r"\bnew\b",
    r"\bdelete\b",
    r"\bresize\b",
    r"\bmalloc\b",
    r"\bfree\b",
    r"\bfopen\b",
    r"\bprintf\b",
    r"\bmutex\b",
    r"\block\b",
    r"\bhttp\b",
    r"\btcp\b",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rc_metadata(path: Path = RC_METADATA) -> dict[str, Any]:
    return load_json(path)


def git_text(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def validate_version_metadata(metadata: dict[str, Any] | None = None) -> list[str]:
    metadata = metadata or load_rc_metadata()
    errors: list[str] = []
    required = [
        "schema",
        "plugin_name",
        "plugin_version",
        "build_number",
        "rc_build_date",
        "dsp_engine_version",
        "parameter_schema_version",
        "factory_preset_version",
        "release_policy_version",
        "test_report_version",
        "plugin_entry_point",
        "supported_plugin_formats",
        "model",
        "latency",
        "commit",
    ]
    for key in required:
        if key not in metadata:
            errors.append(f"missing_metadata:{key}")
    if metadata.get("schema") != "codex-vocal-rc-metadata-v1":
        errors.append("bad_metadata_schema")
    if "REAPER JSFX" not in metadata.get("supported_plugin_formats", []):
        errors.append("missing_supported_format_reaper_jsfx")
    model = metadata.get("model", {})
    if model.get("model_version") != "none" and model.get("model_output_type") == "none":
        errors.append("model_version_output_type_mismatch")
    if metadata.get("release_candidate_policy", {}).get("manual_listening_signoff_required") is not True:
        errors.append("manual_signoff_not_required")
    return errors


def validate_json_files(paths: list[Path] = JSON_FILES) -> list[str]:
    errors: list[str] = []
    for path in paths:
        try:
            load_json(path)
        except Exception as exc:  # noqa: BLE001 - report all JSON failures in QA summary.
            errors.append(f"{path}: {exc}")
    return errors


def compile_python_files(paths: list[Path] = PYTHON_FILES) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.exists():
            errors.append(f"missing_python_file:{path}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{path}: {exc.msg}")
    return errors


def run_direct_tests(test_files: list[Path] = TEST_FILES) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    pass_count = 0
    for path in test_files:
        if not path.exists():
            failures.append({"test": str(path), "error": "missing test file"})
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            failures.append({"test": str(path), "error": "cannot load test module"})
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, fn in sorted(vars(module).items()):
            if not name.startswith("test_") or not callable(fn):
                continue
            tmp: tempfile.TemporaryDirectory[str] | None = None
            kwargs: dict[str, Any] = {}
            if "tmp_path" in inspect.signature(fn).parameters:
                tmp = tempfile.TemporaryDirectory()
                kwargs["tmp_path"] = Path(tmp.name)
            try:
                fn(**kwargs)
                pass_count += 1
            except Exception:  # noqa: BLE001 - test runner records the traceback.
                failures.append({"test": f"{path.name}::{name}", "error": traceback.format_exc(limit=6)})
            finally:
                if tmp is not None:
                    tmp.cleanup()
    return {"pass_count": pass_count, "fail_count": len(failures), "failures": failures}


def jsfx_slider_defaults() -> dict[str, float]:
    defaults: dict[str, float] = {}
    pattern = re.compile(r"^slider(\d+):(-?\d+(?:\.\d+)?)<")
    for line in JSFX.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            defaults[f"slider{match.group(1)}"] = float(match.group(2))
    return defaults


def parameter_freeze_rows() -> list[dict[str, Any]]:
    policy = load_factory_presets()
    defaults = jsfx_slider_defaults()
    rows: list[dict[str, Any]] = []
    for key, definition in sorted(parameter_definitions(policy).items(), key=lambda item: int(item[0].replace("slider", ""))):
        parameter_id = definition["id"]
        rows.append(
            {
                "slider": key,
                "id": parameter_id,
                "display_name": definition["label"],
                "range": [definition["min"], definition["max"]],
                "default": definition["default"],
                "jsfx_default": defaults.get(key),
                "automation_safe": parameter_id
                in set(load_release_policy()["automation_safety"]["continuous_parameters_to_smooth"])
                or parameter_id in set(load_release_policy()["automation_safety"]["mode_parameters"])
                or parameter_id in {"Bypass", "OutputTrimDb"},
                "preset_safe": True,
                "mapping": definition.get("mapping", "linear/clamped"),
                "risk": "developer" if definition.get("ui_group") == "developer" else "bounded",
            }
        )
    rows.append(
        {
            "slider": "internal",
            "id": "HarmonicPreserve",
            "display_name": "Harmonic Preserve",
            "range": [0.0, 1.0],
            "default": 0.75,
            "jsfx_default": 0.75,
            "automation_safe": False,
            "preset_safe": True,
            "mapping": "internal constant",
            "risk": "internal source-preservation guard only",
        }
    )
    return rows


def validate_parameter_freeze() -> list[str]:
    errors: list[str] = []
    rows = parameter_freeze_rows()
    for row in rows:
        default = row["default"]
        lo, hi = row["range"]
        if not isinstance(default, (int, float)) or not math.isfinite(float(default)):
            errors.append(f"{row['id']}: nonfinite default")
        elif not (float(lo) <= float(default) <= float(hi)):
            errors.append(f"{row['id']}: default outside range")
        jsfx_default = row["jsfx_default"]
        if row["slider"] != "internal" and jsfx_default != default:
            errors.append(f"{row['id']}: policy default {default} != JSFX default {jsfx_default}")
    return errors


def installed_jsfx_check() -> dict[str, Any]:
    if not INSTALLED_JSFX.exists():
        return {"status": "warning", "message": "installed REAPER JSFX copy not found"}
    same = JSFX.read_text(encoding="utf-8") == INSTALLED_JSFX.read_text(encoding="utf-8")
    return {"status": "pass" if same else "fail", "message": "installed JSFX matches repo" if same else "installed JSFX differs from repo"}


def realtime_static_audit() -> dict[str, Any]:
    text = JSFX.read_text(encoding="utf-8")
    sample = text.split("@sample", 1)[1] if "@sample" in text else text
    hits: list[str] = []
    for pattern in REALTIME_FORBIDDEN_PATTERNS:
        if re.search(pattern, sample, re.IGNORECASE):
            hits.append(pattern)
    required_safety_tokens = [
        "bad_input",
        "bad_proc",
        "bad_out",
        "wet_state",
        "suspicious_drop",
        "full_band_collapse",
        "residual_monitor",
    ]
    missing = [token for token in required_safety_tokens if token not in sample]
    status = "pass" if not hits and not missing else "fail"
    return {"status": status, "forbidden_hits": hits, "missing_safety_tokens": missing}


def run_synthetic_release_matrix(output_dir: Path, *, quick: bool = False) -> dict[str, Any]:
    assets_dir = output_dir / "assets_48000"
    generate_synthetic_suite(assets_dir, sample_rate=48000)
    manifest_path = assets_dir / "manifest.synthetic.json"
    policy = load_release_policy()
    reports = []
    start = time.perf_counter()
    for preset in policy["release_presets"]:
        reports.append(run_evaluation(manifest_path, preset=preset, output_dir=output_dir / "preset_eval", renderer="passthrough", block_size=256))
    reports.append(run_evaluation(manifest_path, preset=policy["strong_preset"], output_dir=output_dir / "preset_eval", renderer="passthrough", block_size=256))
    gate = evaluate_release_candidate(reports, policy)
    save_json(output_dir / "release_gate_result.json", gate)
    write_markdown_report(output_dir / "release_gate_result.md", gate)

    block_sizes = [1, 256, 4096] if quick else DEFAULT_BLOCK_SIZES
    block_results = []
    for block_size in block_sizes:
        report = run_evaluation(
            manifest_path,
            preset="Preserve",
            output_dir=output_dir / "block_size_eval" / f"block_{block_size}",
            renderer="passthrough",
            block_size=block_size,
        )
        block_results.append({"block_size": block_size, "summary": report["summary"]})

    sample_rates = [44100, 48000] if quick else DEFAULT_SAMPLE_RATES
    sample_rate_results = []
    for sample_rate in sample_rates:
        sr_assets = output_dir / f"assets_{sample_rate}"
        generate_synthetic_suite(sr_assets, sample_rate=sample_rate)
        report = run_evaluation(
            sr_assets / "manifest.synthetic.json",
            preset="Preserve",
            output_dir=output_dir / "sample_rate_eval" / f"sr_{sample_rate}",
            renderer="passthrough",
            block_size=256,
        )
        sample_rate_results.append({"sample_rate": sample_rate, "summary": report["summary"]})

    elapsed = time.perf_counter() - start
    return {
        "release_gate": gate,
        "preset_reports": [str(output_dir / "preset_eval" / preset_slug(report["preset"]) / "run_metrics.json") for report in reports],
        "block_size_results": block_results,
        "sample_rate_results": sample_rate_results,
        "elapsed_sec": elapsed,
    }


def write_markdown_summary(path: Path, summary: dict[str, Any]) -> None:
    gate = summary["synthetic_matrix"]["release_gate"]
    lines = [
        "# RC QA Automated Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Plugin version: `{summary['metadata']['plugin_version']}`",
        f"- Build number: `{summary['metadata']['build_number']}`",
        f"- Commit: `{summary['git']['commit_hash']}`",
        f"- Dirty worktree: `{summary['git']['dirty_worktree']}`",
        f"- Release gate: `{gate['status']}`",
        "",
        "## Checks",
        "",
        f"- JSON validation errors: `{len(summary['json_errors'])}`",
        f"- Python compile errors: `{len(summary['compile_errors'])}`",
        f"- Direct tests: `{summary['direct_tests']['pass_count']} passed, {summary['direct_tests']['fail_count']} failed`",
        f"- Factory preset errors: `{len(summary['factory_preset_errors'])}`",
        f"- Version metadata errors: `{len(summary['metadata_errors'])}`",
        f"- Parameter freeze errors: `{len(summary['parameter_errors'])}`",
        f"- Real-time static audit: `{summary['realtime_static_audit']['status']}`",
        f"- Installed REAPER JSFX: `{summary['installed_jsfx']['status']}`",
        "",
        "## Release Gate Blockers",
        "",
    ]
    blockers = gate.get("blockers", [])
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- none in automated synthetic/passthrough gate")
    lines.extend(
        [
            "",
            "## Manual And DAW Status",
            "",
            "- Automated QA can lock regressions, but it does not approve the release candidate by itself.",
            "- Real REAPER processed renders, manual residual listening, host reopen/freeze/bounce checks, and packaging validation remain required before shipping.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_rc_qa(output_dir: Path, *, quick: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = load_rc_metadata()
    git_status = git_text("status", "--short")
    summary: dict[str, Any] = {
        "schema": "codex-vocal-rc-qa-summary-v1",
        "metadata": metadata,
        "git": {
            "commit_hash": git_text("rev-parse", "HEAD"),
            "branch": git_text("branch", "--show-current"),
            "dirty_worktree": bool(git_status),
            "dirty_status_short": git_status.splitlines()[:80],
        },
        "json_errors": validate_json_files(),
        "compile_errors": compile_python_files(),
        "direct_tests": run_direct_tests(),
        "factory_preset_errors": validate_factory_presets(load_factory_presets()),
        "metadata_errors": validate_version_metadata(metadata),
        "parameter_errors": validate_parameter_freeze(),
        "realtime_static_audit": realtime_static_audit(),
        "installed_jsfx": installed_jsfx_check(),
    }
    summary["synthetic_matrix"] = run_synthetic_release_matrix(output_dir, quick=quick)

    blockers: list[str] = []
    for key in ("json_errors", "compile_errors", "factory_preset_errors", "metadata_errors", "parameter_errors"):
        if summary[key]:
            blockers.append(key)
    if summary["direct_tests"]["fail_count"]:
        blockers.append("direct_tests_failed")
    if summary["realtime_static_audit"]["status"] == "fail":
        blockers.append("realtime_static_audit_failed")
    if summary["installed_jsfx"]["status"] == "fail":
        blockers.append("installed_jsfx_mismatch")
    if summary["synthetic_matrix"]["release_gate"]["status"] != "pass":
        blockers.append("synthetic_release_gate_failed")
    summary["automated_blockers"] = blockers
    summary["status"] = "pass" if not blockers else "fail"
    save_json(output_dir / "rc_qa_summary.json", summary)
    write_markdown_summary(output_dir / "rc_qa_summary.md", summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Prompt 9 release-candidate QA lock checks.")
    parser.add_argument("--output-dir", type=Path, default=Path(os.environ.get("CODEX_VOCAL_RC_QA_DIR", "/tmp/codex_vocal_rc_qa")))
    parser.add_argument("--quick", action="store_true", help="Use a smaller block-size/sample-rate matrix.")
    parser.add_argument("--allow-fail", action="store_true", help="Write reports but return success even if automated blockers exist.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary = run_rc_qa(args.output_dir, quick=args.quick)
    print(json.dumps({"status": summary["status"], "output_dir": str(args.output_dir), "automated_blockers": summary["automated_blockers"]}, indent=2))
    if summary["status"] == "pass" or args.allow_fail:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
