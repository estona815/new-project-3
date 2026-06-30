#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.final_placement_adapter_mapping import validate_final_placement_adapters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate final vocal-space placement adapter mappings and generate a safe REAPER applicator plan.")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--chain-plan", type=Path, default=None)
    parser.add_argument("--inventory", type=Path, default=None)
    parser.add_argument("--adapter-dir", action="append", type=Path, default=[])
    parser.add_argument("--min-confidence", type=float, default=0.85)
    parser.add_argument("--allow-offline-validated-adapters", action="store_true")
    parser.add_argument("--generate-applicator-plan", action="store_true", default=True)
    parser.add_argument("--write-configured-applicator", action="store_true")
    parser.add_argument("--enable-configured-applicator", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def write_configured_applicator(output_dir: Path, lua_plan_path: str, *, enabled: bool) -> Path:
    source = ROOT / "automix" / "apply_final_vocal_space_placement_draft.lua"
    target = output_dir / "apply_final_vocal_space_placement_draft_configured.lua"
    text = source.read_text(encoding="utf-8")
    text = text.replace("allow_final_vocal_space_placement = false", f"allow_final_vocal_space_placement = {'true' if enabled else 'false'}", 1)
    text = text.replace('lua_plan_path = ""', f'lua_plan_path = "{lua_plan_path.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34))}"', 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def main() -> int:
    args = parse_args()
    report = validate_final_placement_adapters(
        output_dir=args.output_dir,
        chain_plan_path=args.chain_plan,
        inventory_path=args.inventory,
        adapter_dirs=args.adapter_dir,
        min_confidence=args.min_confidence,
        allow_offline_validated_adapters=args.allow_offline_validated_adapters,
        generate_applicator_plan=args.generate_applicator_plan,
    )
    configured_applicator = ""
    configured_enabled = False
    if args.write_configured_applicator:
        configured_enabled = bool(args.enable_configured_applicator and report.get("apply_allowed"))
        configured_applicator = str(write_configured_applicator(args.output_dir, report.get("applicator_plan_lua", ""), enabled=configured_enabled))

    payload = {
        "project_name": report.get("project_name"),
        "apply_allowed": report.get("apply_allowed"),
        "all_required_categories_safe": report.get("all_required_categories_safe"),
        "blocked_reasons": report.get("blocked_reasons", []),
        "mapping_report": str(args.output_dir / "eval_reports" / "final_placement_adapter_mapping_report.json"),
        "mapping_report_md": str(args.output_dir / "eval_reports" / "final_placement_adapter_mapping_report.md"),
        "applicator_plan_lua": report.get("applicator_plan_lua"),
        "applicator_plan_json": report.get("applicator_plan_json"),
        "configured_applicator": configured_applicator,
        "configured_applicator_enabled": configured_enabled,
    }
    if args.verbose:
        payload["category_results"] = report.get("category_results", [])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
