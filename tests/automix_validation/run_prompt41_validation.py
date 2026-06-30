#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.fixture_coverage_audit import build_fixture_coverage_audit
from tests.automix_validation.prompt41_validation_common import ensure_prompt41_fixtures


TEST_MODULES = [
    ("plugin intelligence", ROOT / "tests/automix_validation/test_prompt41_smoke.py"),
    ("source classification and safety", ROOT / "tests/automix_validation/test_prompt41_safety.py"),
    ("orchestrator modes", ROOT / "tests/automix_validation/test_prompt41_orchestrator.py"),
    ("final export blocking", ROOT / "tests/automix_validation/test_prompt41_export_blocking.py"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt41 synthetic/mock AutoMix validation runner.")
    parser.add_argument("--generate-fixtures", action="store_true", default=False)
    parser.add_argument("--run-tests", action="store_true", default=False)
    parser.add_argument("--mock-render", action="store_true", default=False)
    parser.add_argument("--real-render", action="store_true", default=False)
    parser.add_argument("--skip-reaper", action="store_true", default=False)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "automix")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_test_function(fn) -> tuple[bool, str]:
    sig = inspect.signature(fn)
    kwargs: dict[str, Any] = {}
    tempdirs: list[tempfile.TemporaryDirectory] = []
    try:
        for pname in sig.parameters:
            if pname == "tmp_path":
                td = tempfile.TemporaryDirectory()
                tempdirs.append(td)
                kwargs[pname] = Path(td.name)
            else:
                return False, f"unsupported fixture:{pname}"
        fn(**kwargs)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        for td in tempdirs:
            td.cleanup()


def run_tests(verbose: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for group, path in TEST_MODULES:
        module = load_module(path, f"prompt41_{path.stem}")
        functions = [getattr(module, name) for name in sorted(dir(module)) if name.startswith("test_") and callable(getattr(module, name))]
        group_result = {"test_group": group, "passed": 0, "failed": 0, "skipped": 0, "notes": []}
        for fn in functions:
            ok, note = run_test_function(fn)
            if ok:
                group_result["passed"] += 1
            else:
                group_result["failed"] += 1
                group_result["notes"].append(f"{fn.__name__}: {note}")
            if verbose:
                print(f"{group}::{fn.__name__} {'PASS' if ok else 'FAIL'} {note}")
        results.append(group_result)
    return results


def write_summary(
    output_dir: Path,
    *,
    fixture_manifest: dict[str, Any],
    fixture_coverage: dict[str, Any],
    test_results: list[dict[str, Any]],
    args: argparse.Namespace,
    started: float,
) -> dict[str, Any]:
    validation_dir = output_dir / "validation_reports"
    validation_dir.mkdir(parents=True, exist_ok=True)
    reaper_available = shutil.which("reaper") is not None or shutil.which("REAPER") is not None
    total_failed = sum(item["failed"] for item in test_results)
    total_passed = sum(item["passed"] for item in test_results)
    total_skipped = sum(item["skipped"] for item in test_results)
    skipped_notes: list[str] = []
    if args.real_render and not reaper_available:
        total_skipped += 1
        skipped_notes.append("real_render_requested_but_reaper_not_available")
    if args.skip_reaper:
        skipped_notes.append("reaper_tests_skipped_by_flag")

    fixture_coverage_failed = bool(fixture_coverage) and not fixture_coverage.get("passed", False)
    if total_failed or fixture_coverage_failed:
        final_status = "PROMPT41_VALIDATION_FAIL"
    elif skipped_notes and args.real_render:
        final_status = "PROMPT41_VALIDATION_PARTIAL"
    else:
        final_status = "PROMPT41_VALIDATION_PASS"

    report_paths = [
        str(output_dir / "orchestrator/automix_orchestration_manifest.json"),
        str(output_dir / "eval_reports/automix_orchestration_report.md"),
        str(output_dir / "eval_reports/automix_report_index.json"),
        str(output_dir / "eval_reports/automix_report_index.md"),
        str(output_dir / "eval_reports/global_qc_summary.json"),
        str(output_dir / "eval_reports/fixture_coverage_audit.json"),
        str(output_dir / "eval_reports/fixture_coverage_audit.md"),
        str(output_dir / "rollback/global_rollback_registry.json"),
    ]
    fixture_blockers = list(fixture_coverage.get("blockers", [])) if fixture_coverage else []
    summary = {
        "schema": "prompt41-validation-summary-v1",
        "created_at_epoch": time.time(),
        "duration_seconds": round(time.time() - started, 6),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "reaper_available": reaper_available,
            "test_mode": "real_render" if args.real_render else "mock_render",
            "third_party_plugins_required": False,
        },
        "fixture_generation": {
            "audio_fixtures": len(fixture_manifest.get("audio", {}).get("fixtures", [])),
            "mock_analysis_fixtures": len(fixture_manifest.get("analysis", {}).get("fixtures", [])),
            "mock_projects": len(fixture_manifest.get("projects", {}).get("projects", [])),
            "fixture_coverage_passed": bool(fixture_coverage.get("passed")) if fixture_coverage else False,
            "fixture_categories_covered": len(fixture_coverage.get("covered_categories", [])) if fixture_coverage else 0,
            "fixture_categories_required": len(fixture_coverage.get("required_categories", [])) if fixture_coverage else 0,
            "fixture_coverage_blockers": fixture_blockers,
        },
        "test_results": test_results,
        "totals": {"passed": total_passed, "failed": total_failed, "skipped": total_skipped},
        "safety_results": {
            "original_track_protection": total_failed == 0,
            "original_master_protection": total_failed == 0,
            "pitch_full_mix_block": total_failed == 0,
            "low_confidence_plugin_block": total_failed == 0,
            "final_export_approval_block": total_failed == 0,
            "qc_failure_block": total_failed == 0,
            "rollback_validation": total_failed == 0,
            "fixture_coverage": not fixture_coverage_failed,
        },
        "reports_created": [{"path": path, "exists": Path(path).exists()} for path in report_paths],
        "failures": [note for item in test_results for note in item.get("notes", [])] + fixture_blockers,
        "skipped_notes": skipped_notes,
        "final_validation_status": final_status,
    }
    json_path = validation_dir / "prompt41_validation_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_summary_markdown(summary, validation_dir / "prompt41_validation_summary.md")
    return summary


def write_summary_markdown(summary: dict[str, Any], path: Path) -> None:
    env = summary["environment"]
    lines = [
        "# Prompt 41 Validation Summary",
        "",
        "## Environment",
        "",
        f"- Platform: `{env['platform']}`",
        f"- Python: `{env['python']}`",
        f"- REAPER available: `{env['reaper_available']}`",
        f"- Test mode: `{env['test_mode']}`",
        "- Third-party plugins required: `No`",
        "",
        "## Fixture Generation",
        "",
        f"- Audio fixtures: `{summary['fixture_generation']['audio_fixtures']}`",
        f"- Mock analysis fixtures: `{summary['fixture_generation']['mock_analysis_fixtures']}`",
        f"- Mock projects: `{summary['fixture_generation']['mock_projects']}`",
        f"- Fixture coverage passed: `{summary['fixture_generation']['fixture_coverage_passed']}`",
        f"- Fixture categories covered: `{summary['fixture_generation']['fixture_categories_covered']}/{summary['fixture_generation']['fixture_categories_required']}`",
        "",
        "## Test Results",
        "",
        "| Test group | Passed | Failed | Skipped | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for result in summary["test_results"]:
        notes = "; ".join(result.get("notes", [])[:3])
        lines.append(f"| {result['test_group']} | {result['passed']} | {result['failed']} | {result['skipped']} | {notes} |")
    safety = summary["safety_results"]
    lines.extend(
        [
            "",
            "## Safety Results",
            "",
            f"- Original track protection: `{safety['original_track_protection']}`",
            f"- Original master protection: `{safety['original_master_protection']}`",
            f"- Pitch full-mix block: `{safety['pitch_full_mix_block']}`",
            f"- Low-confidence plugin block: `{safety['low_confidence_plugin_block']}`",
            f"- Final export approval block: `{safety['final_export_approval_block']}`",
            f"- QC failure block: `{safety['qc_failure_block']}`",
            f"- Rollback validation: `{safety['rollback_validation']}`",
            f"- Fixture coverage: `{safety['fixture_coverage']}`",
            "",
            "## Reports Created",
            "",
        ]
    )
    for report in summary["reports_created"]:
        lines.append(f"- `{report['path']}` exists `{report['exists']}`")
    lines.extend(["", "## Failures", ""])
    if summary["failures"]:
        for failure in summary["failures"]:
            lines.append(f"- {failure}")
    else:
        lines.append("- none")
    lines.extend(["", "## Final Validation Status", "", f"`{summary['final_validation_status']}`", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    started = time.time()
    if not (args.generate_fixtures or args.run_tests):
        args.generate_fixtures = True
        args.run_tests = True
        args.mock_render = True
    fixture_manifest = ensure_prompt41_fixtures() if args.generate_fixtures or args.run_tests else {"audio": {}, "analysis": {}, "projects": {}}
    test_results = run_tests(verbose=args.verbose) if args.run_tests else []
    fixture_coverage = build_fixture_coverage_audit(project_name="prompt41", output_dir=args.output_dir, fixture_root=ROOT / "tests/automix_validation/fixtures") if args.generate_fixtures or args.run_tests else {}
    summary = write_summary(args.output_dir, fixture_manifest=fixture_manifest, fixture_coverage=fixture_coverage, test_results=test_results, args=args, started=started)
    print(json.dumps({"status": summary["final_validation_status"], "summary": str(args.output_dir / "validation_reports/prompt41_validation_summary.json")}, indent=2))
    return 0 if summary["final_validation_status"] != "PROMPT41_VALIDATION_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
