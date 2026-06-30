#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_gate import build_plugin_semantic_validation_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit plugin semantic parameter validation reports.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--validation-reports-dir", type=Path, default=None)
    parser.add_argument("--preflight", type=Path, default=None)
    parser.add_argument("--plugin-readiness", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_semantic_validation_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        validation_reports_dir=args.validation_reports_dir,
        preflight_path=args.preflight,
        plugin_readiness_path=args.plugin_readiness,
    )
    summary = {
        "status": "ready" if gate.get("semantic_validation_ready") else "blocked",
        "semantic_validation_ready": gate.get("semantic_validation_ready"),
        "required_plugins_total": gate.get("required_plugins_total"),
        "validation_reports_total": gate.get("validation_reports_total"),
        "safe_controls_total": gate.get("safe_controls_total"),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_gate.md"),
        "template_json": str(args.output_dir / "review/plugin_semantic_validation_manifest_template.json"),
        "request_md": str(args.output_dir / "review/plugin_semantic_validation_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("semantic_validation_ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
