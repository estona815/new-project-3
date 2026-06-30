#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator, WORKFLOW_MODES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt40 end-to-end fail-closed AutoMix orchestrator.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--mode", default="scan_only", choices=sorted(WORKFLOW_MODES))
    parser.add_argument("--target-profile", default=None)
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--reference-role", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--allow-recovery-drafts", action="store_true")
    parser.add_argument("--allow-pitch", action="store_true")
    parser.add_argument("--no-pitch", action="store_true")
    parser.add_argument("--allow-placement-drafts", action="store_true")
    parser.add_argument("--allow-reference-match-draft", action="store_true")
    parser.add_argument("--allow-premaster-draft", action="store_true")
    parser.add_argument("--allow-final-export", action="store_true")
    parser.add_argument("--approve-final", action="store_true")
    parser.add_argument("--acknowledge-warnings", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--package-review", action="store_true")
    parser.add_argument("--deliverables-root", type=Path, default=Path("deliverables"))
    parser.add_argument("--accept-placement-review", action="store_true")
    parser.add_argument("--apply-safe-premaster-draft", action="store_true")
    parser.add_argument("--final-vocal-space-chain-plan", type=Path, default=None)
    parser.add_argument("--plugin-inventory", type=Path, default=None)
    parser.add_argument("--adapter-min-confidence", type=float, default=0.85)
    parser.add_argument("--allow-offline-validated-adapters", action="store_true")
    parser.add_argument("--diagnostic-continue", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = "diagnostic_continue" if args.diagnostic_continue else args.mode
    if args.diagnostic_continue and mode != "diagnostic_continue":
        mode = "diagnostic_continue"
    allow_pitch = True
    if args.no_pitch:
        allow_pitch = False
    elif args.allow_pitch:
        allow_pitch = True

    config = {
        "mode": mode,
        "project_path": str(args.project) if args.project else "",
        "output_dir": str(args.output_dir),
        "target_profile": args.target_profile,
        "references": [str(path) for path in args.reference],
        "reference_roles": list(args.reference_role),
        "allow_recovery_drafts": args.allow_recovery_drafts,
        "allow_pitch_correction": allow_pitch,
        "allow_placement_drafts": args.allow_placement_drafts,
        "allow_reference_match_draft": args.allow_reference_match_draft,
        "allow_premaster_draft": args.allow_premaster_draft,
        "allow_final_export": args.allow_final_export,
        "final_approval_explicit": args.approve_final,
        "warnings_acknowledged": args.acknowledge_warnings,
        "render_ab": args.render_ab,
        "package_review": args.package_review,
        "deliverables_root": str(args.deliverables_root),
        "accept_placement_review": args.accept_placement_review,
        "apply_safe_premaster_draft": args.apply_safe_premaster_draft,
        "final_vocal_space_chain_plan_path": str(args.final_vocal_space_chain_plan) if args.final_vocal_space_chain_plan else None,
        "plugin_inventory_path": str(args.plugin_inventory) if args.plugin_inventory else None,
        "adapter_min_confidence": args.adapter_min_confidence,
        "allow_offline_validated_adapters": args.allow_offline_validated_adapters,
        "diagnostic_continue": args.diagnostic_continue,
        "dry_run": args.dry_run,
        "verbose": args.verbose,
    }
    if args.no_pitch:
        config["allow_pitch_correction"] = False
    if mode == "diagnostic_continue":
        config["allow_recovery_drafts"] = False
        config["allow_pitch_correction"] = False
        config["allow_placement_drafts"] = False
        config["allow_reference_match_draft"] = False
        config["allow_premaster_draft"] = False
        config["allow_final_export"] = False
    if mode == "scan_only":
        config["dry_run"] = True
    if args.allow_final_export and not args.approve_final:
        # The orchestrator will report this as requires_approval; do not convert
        # the CLI flag into approval implicitly.
        config["final_approval_explicit"] = False

    orchestrator = AutoMixOrchestrator(config)
    manifest = orchestrator.run()
    summary = {
        "status": manifest.get("global_status"),
        "mode": manifest.get("mode"),
        "safe_to_export": manifest.get("safe_to_export"),
        "manifest": str(args.output_dir / "orchestrator" / "automix_orchestration_manifest.json"),
        "report": str(args.output_dir / "eval_reports" / "automix_orchestration_report.md"),
        "dry_run": bool(config.get("dry_run")),
        "final_export_blocked_without_approval": not bool(config.get("final_approval_explicit")) and manifest.get("mode") == "final_delivery",
    }
    print(json.dumps(summary if not args.verbose else {**summary, "next_required_actions": manifest.get("next_required_actions", [])}, indent=2))
    return 0 if manifest.get("global_status") not in {"failed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
