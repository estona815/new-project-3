#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
APPROVED_SLUG = "mwolla_v14_no_chop_max_clarity_hook_reprise_master"
APPROVED_SCRIPT = ROOT / "tools" / "mwolla_v14_no_chop_vocal_clarity_lift_master.py"
MANIFEST = ROOT / "reports" / APPROVED_SLUG / "approved_baseline_manifest.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def verify_existing() -> dict[str, Any]:
    errors: list[str] = []
    require(MANIFEST.exists(), f"missing manifest: {rel(MANIFEST)}", errors)
    manifest = read_json(MANIFEST) if MANIFEST.exists() else {}

    for item in manifest.get("required_files", []):
        path = ROOT / item["path"]
        require(path.exists(), f"missing required file: {item['path']}", errors)

    qc_path = ROOT / manifest.get("qc_summary", "reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/qc_summary.json")
    hook_qc_path = ROOT / manifest.get("hook_reprise_qc", "reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/hook_reprise_qc.json")
    no_loudness_path = ROOT / manifest.get(
        "no_loudness_push_report",
        "reports/mwolla_v14_no_chop_max_clarity_hook_reprise_master/no_loudness_push_final_master_report.json",
    )
    deliverable_zip = ROOT / manifest.get(
        "deliverable_zip",
        "renders/mwolla_v14_no_chop_max_clarity_hook_reprise_master/mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER_DELIVERABLE.zip",
    )

    qc = read_json(qc_path) if qc_path.exists() else {}
    hook_qc = read_json(hook_qc_path) if hook_qc_path.exists() else {}
    no_loudness = read_json(no_loudness_path) if no_loudness_path.exists() else {}

    require(bool(qc.get("passed")), "qc_summary.passed is not true", errors)
    require(bool(qc.get("gate", {}).get("passed")), "vocal chain gate did not pass", errors)
    require(bool(qc.get("no_chop_timestamp_qc", {}).get("passed")), "no-chop timestamp QC did not pass", errors)
    require(bool(qc.get("hook_reprise", {}).get("passed")), "hook reprise QC summary did not pass", errors)
    require(bool(hook_qc.get("passed")), "hook_reprise_qc.passed is not true", errors)
    require(no_loudness.get("loudnorm_used") is False, "loudnorm_used is not false", errors)
    require(no_loudness.get("limiter_push_used") is False, "limiter_push_used is not false", errors)
    require(no_loudness.get("peak_guard_only") is True, "peak_guard_only is not true", errors)

    zip_status = "not_checked"
    if deliverable_zip.exists():
        with zipfile.ZipFile(deliverable_zip) as archive:
            bad_member = archive.testzip()
        require(bad_member is None, f"deliverable zip failed at member: {bad_member}", errors)
        zip_status = "ok" if bad_member is None else "failed"
    else:
        require(False, f"missing deliverable zip: {rel(deliverable_zip)}", errors)
        zip_status = "missing"

    return {
        "schema": "mwolla-approved-baseline-verification-v1",
        "slug": APPROVED_SLUG,
        "manifest": rel(MANIFEST),
        "passed": not errors,
        "errors": errors,
        "zip_status": zip_status,
        "final_lufs": qc.get("final_lufs"),
        "final_true_peak_dbfs": qc.get("final_true_peak_dbfs"),
        "mp3_true_peak_dbfs": qc.get("mp3_true_peak_dbfs"),
        "hook_reprise": qc.get("hook_reprise"),
        "no_chop_timestamp_qc": qc.get("no_chop_timestamp_qc"),
    }


def render_approved() -> int:
    spec = importlib.util.spec_from_file_location("mwolla_v14_no_chop_vocal_clarity_lift_master", APPROVED_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load approved script: {APPROVED_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main())


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or rerender the current user-approved Mwolla mix/master baseline.")
    parser.add_argument("--render", action="store_true", help="Rerun the approved v14 render harness before verification.")
    parser.add_argument("--verify-existing", action="store_true", help="Verify the existing approved v14 files without rerendering.")
    args = parser.parse_args()

    if args.render:
        code = render_approved()
        if code != 0:
            return code

    result = verify_existing()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
