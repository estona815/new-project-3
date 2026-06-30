#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .schemas import (
        ASSET_MANIFEST_PATH,
        PLUGIN_TRACE_PATH,
        PROJECT_PATH,
        build_plugin_trace,
        detect_environment,
        discover_assets,
        ensure_harness_dirs,
        package_delivery,
        write_asset_report,
        write_final_delivery_report,
        write_json,
        write_plugin_trace_summary,
        write_reaper_project_skeleton,
        write_validation_report,
    )
except ImportError:
    from schemas import (
        ASSET_MANIFEST_PATH,
        PLUGIN_TRACE_PATH,
        PROJECT_PATH,
        build_plugin_trace,
        detect_environment,
        discover_assets,
        ensure_harness_dirs,
        package_delivery,
        write_asset_report,
        write_final_delivery_report,
        write_json,
        write_plugin_trace_summary,
        write_reaper_project_skeleton,
        write_validation_report,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the REAPER mix/master automation harness.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--prepare", action="store_true", help="Prepare project, manifest, trace, and reports.")
    parser.add_argument("--runtime-verified", action="store_true", help="Mark trace as collected from an actual REAPER runtime.")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    env = detect_environment(root)
    manifest = discover_assets(root)
    write_json(root / ASSET_MANIFEST_PATH.relative_to(Path(__file__).resolve().parents[1]), manifest)
    write_asset_report(manifest, root)
    project_path = write_reaper_project_skeleton(root)
    trace = build_plugin_trace(manifest, env, root, runtime_verified=args.runtime_verified)
    write_json(root / PLUGIN_TRACE_PATH.relative_to(Path(__file__).resolve().parents[1]), trace)
    write_plugin_trace_summary(trace)
    validation = write_validation_report(trace, root)
    qc_report = None
    qc_path = root / "work" / "qc" / "qc_report.json"
    if qc_path.exists():
        qc_report = json.loads(qc_path.read_text(encoding="utf-8"))
    package_manifest = package_delivery(root)
    write_final_delivery_report(env, manifest, trace, qc_report, package_manifest, root)
    package_manifest = package_delivery(root)
    write_final_delivery_report(env, manifest, trace, qc_report, package_manifest, root)
    result = {
        "status": "PASS" if validation["gate_checks"]["overall_pass"] else "BLOCKED",
        "project_path": str(project_path),
        "plugin_trace_path": str(root / PLUGIN_TRACE_PATH.relative_to(Path(__file__).resolve().parents[1])),
        "validation": validation,
        "package": package_manifest,
        "notes": [
            "REAPER project skeleton and trace plan are generated.",
            "Actual renders remain blocked until source stems/reference and a runtime render pass are available.",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
