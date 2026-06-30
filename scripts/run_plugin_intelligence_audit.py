#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automix.plugins.plugin_inventory_audit import audit_plugin_inventory, load_adapters, load_inventory, write_plugin_capability_report
from automix.plugins.plugin_parameter_learner import learn_adapter_from_parameter_list, write_learned_adapter
from automix.plugins.plugin_parameter_validator import validate_adapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt39 plugin intelligence inventory and adapter safety audit.")
    parser.add_argument("--scan", action="store_true", help="Read the existing safe REAPER inventory JSON and write an audit.")
    parser.add_argument("--learn", action="store_true", help="Create a provisional learned adapter for --plugin.")
    parser.add_argument("--validate", action="store_true", help="Validate learned/builtin adapters when observations are available.")
    parser.add_argument("--plugin", help="Plugin name for --learn or focused --validate.")
    parser.add_argument("--all", action="store_true", help="Apply validation to all discovered adapter JSON files.")
    parser.add_argument("--report", action="store_true", help="Write automix/eval_reports/plugin_capability_report.md.")
    parser.add_argument("--dry-run", action="store_true", help="Do not attempt live REAPER validation; fail closed.")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"), help="Automix output directory.")
    parser.add_argument("--inventory", type=Path, help="Optional inventory JSON path.")
    parser.add_argument("--parameters-json", type=Path, help="Optional parameter list JSON for --learn.")
    return parser.parse_args()


def load_parameters(path: Path | None) -> list[Any]:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("parameters", [])
    return []


def main() -> int:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    audit = None
    if args.learn:
        plugin_name = args.plugin or "unknown plugin"
        adapter = learn_adapter_from_parameter_list(
            plugin_name,
            load_parameters(args.parameters_json),
            output_dir=output_dir,
        )
        if not args.parameters_json:
            adapter.setdefault("warnings", []).append("parameter_list_unavailable_dry_run")
            write_learned_adapter(adapter, output_dir)

    if args.validate:
        adapter_dirs = [output_dir / "plugins" / "builtin_adapters", output_dir / "plugins" / "learned_adapters"]
        adapters = load_adapters(adapter_dirs)
        for adapter in adapters:
            names = adapter.get("plugin_name_patterns", [])
            if args.plugin and args.plugin not in names and args.plugin != adapter.get("adapter_id"):
                continue
            if args.all or args.plugin:
                validate_adapter(
                    adapter,
                    output_dir=output_dir,
                    plugin_available=False if args.dry_run else False,
                    validation_observations=None,
                )

    if args.scan or args.report or not (args.learn or args.validate):
        inventory = load_inventory(args.inventory or output_dir / "plugin_inventory.json")
        audit = audit_plugin_inventory(inventory, output_dir=output_dir)

    if args.report:
        if audit is None:
            inventory = load_inventory(args.inventory or output_dir / "plugin_inventory.json")
            audit = audit_plugin_inventory(inventory, output_dir=output_dir)
        write_plugin_capability_report(audit, output_dir)

    print(json.dumps({"status": "ok", "output_dir": str(output_dir), "audit_written": bool(audit)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
