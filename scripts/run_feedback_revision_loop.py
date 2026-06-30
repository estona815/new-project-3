#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.feedback.revision_memory import (
    append_revision_memory,
    initialize_revision_memory_baseline,
    resolve_feedback_items,
    summarize_feedback_memory,
)
from automix.feedback.feedback_qc_integration import build_feedback_qc_integration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record user mix/master feedback and create a dry-run revision action plan.")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--pass-id", default="")
    parser.add_argument("--track-name", default="")
    parser.add_argument("--stage", default="feedback_intake")
    parser.add_argument("--source", default="user")
    parser.add_argument("--feedback", action="append", default=[])
    parser.add_argument("--feedback-file", type=Path, default=None)
    parser.add_argument("--initialize-baseline", action="store_true", help="Write an explicit no-feedback-yet baseline without inventing user feedback.")
    parser.add_argument("--resolve-feedback-id", action="append", default=[])
    parser.add_argument("--resolution-notes", default="")
    parser.add_argument("--reviewer", default="user")
    parser.add_argument("--evidence-path", action="append", default=[])
    parser.add_argument("--human-reviewed", action="store_true")
    parser.add_argument("--measured-qc-passed", action="store_true")
    parser.add_argument("--loudness-matched-ab-reviewed", action="store_true")
    parser.add_argument("--remaining-risk", action="append", default=[])
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def _feedback_from_file(path: Path | None) -> list[str]:
    if not path:
        return []
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def main() -> int:
    args = parse_args()
    if args.initialize_baseline and args.resolve_feedback_id:
        print(json.dumps({"status": "blocked", "reason": "initialize_baseline_cannot_resolve_feedback"}, indent=2))
        return 2
    if args.initialize_baseline and (args.feedback or args.feedback_file):
        print(json.dumps({"status": "blocked", "reason": "initialize_baseline_cannot_record_feedback"}, indent=2))
        return 2
    if args.initialize_baseline:
        memory = initialize_revision_memory_baseline(output_dir=args.output_dir, project_name=args.project_name)
        summary = summarize_feedback_memory(args.output_dir)
        feedback_qc = build_feedback_qc_integration(project_name=args.project_name, output_dir=args.output_dir)
        result = {
            "status": "feedback_revision_baseline_ready",
            "memory": str(args.output_dir / "review" / "user_feedback_revision_memory.json"),
            "action_plan": str(args.output_dir / "eval_reports" / "user_feedback_action_plan.json"),
            "report": str(args.output_dir / "eval_reports" / "user_feedback_revision_report.md"),
            "qc_integration": str(args.output_dir / "eval_reports" / "user_feedback_qc_integration.json"),
            "qc_integration_report": str(args.output_dir / "eval_reports" / "user_feedback_qc_integration.md"),
            "total_entries": summary.get("total_entries", 0),
            "pending_unresolved_count": summary.get("pending_unresolved_count", 0),
            "requires_human_review": summary.get("requires_human_review", False),
            "baseline_status": summary.get("baseline_status", ""),
            "no_feedback_fabricated": summary.get("no_feedback_fabricated", False),
            "dry_run_only": True,
        }
        if args.verbose:
            result["summary"] = summary
            result["feedback_qc_integration_summary"] = feedback_qc.get("summary", {})
            result["memory_summary"] = {
                "entries": len(memory.get("entries", [])),
                "baseline_status": memory.get("baseline_status", ""),
                "no_feedback_fabricated": memory.get("no_feedback_fabricated", False),
            }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.resolve_feedback_id:
        memory = resolve_feedback_items(
            output_dir=args.output_dir,
            project_name=args.project_name,
            pass_id=args.pass_id,
            feedback_ids=args.resolve_feedback_id,
            reviewer=args.reviewer,
            resolution_notes=args.resolution_notes,
            evidence_paths=args.evidence_path,
            human_reviewed=args.human_reviewed,
            measured_qc_passed=args.measured_qc_passed,
            loudness_matched_ab_reviewed=args.loudness_matched_ab_reviewed,
            remaining_risks=args.remaining_risk,
        )
        summary = summarize_feedback_memory(args.output_dir)
        feedback_qc = build_feedback_qc_integration(project_name=args.project_name, output_dir=args.output_dir)
        latest_record = memory.get("resolution_records", [])[-1] if memory.get("resolution_records") else {}
        accepted = bool(latest_record.get("accepted_for_resolution"))
        result = {
            "status": "feedback_resolution_accepted" if accepted else "feedback_resolution_blocked",
            "memory": str(args.output_dir / "review" / "user_feedback_revision_memory.json"),
            "action_plan": str(args.output_dir / "eval_reports" / "user_feedback_action_plan.json"),
            "report": str(args.output_dir / "eval_reports" / "user_feedback_revision_report.md"),
            "qc_integration": str(args.output_dir / "eval_reports" / "user_feedback_qc_integration.json"),
            "qc_integration_report": str(args.output_dir / "eval_reports" / "user_feedback_qc_integration.md"),
            "pending_unresolved_count": summary.get("pending_unresolved_count", 0),
            "resolved_feedback_count": summary.get("resolved_feedback_count", 0),
            "missing_requirements": latest_record.get("missing_requirements", []),
            "requires_human_review": summary.get("requires_human_review", False),
        }
        if args.verbose:
            result["summary"] = summary
            result["feedback_qc_integration_summary"] = feedback_qc.get("summary", {})
            result["latest_resolution_record"] = latest_record
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if accepted else 2

    feedback = [item for item in args.feedback if item.strip()]
    feedback.extend(_feedback_from_file(args.feedback_file))
    if not feedback:
        print(json.dumps({"status": "blocked", "reason": "feedback_required"}, indent=2))
        return 2
    memory = append_revision_memory(
        output_dir=args.output_dir,
        project_name=args.project_name,
        pass_id=args.pass_id,
        feedback_texts=feedback,
        track_name=args.track_name,
        source=args.source,
        stage=args.stage,
    )
    summary = summarize_feedback_memory(args.output_dir)
    feedback_qc = build_feedback_qc_integration(project_name=args.project_name, output_dir=args.output_dir)
    result = {
        "status": "feedback_revision_plan_created",
        "memory": str(args.output_dir / "review" / "user_feedback_revision_memory.json"),
        "action_plan": str(args.output_dir / "eval_reports" / "user_feedback_action_plan.json"),
        "report": str(args.output_dir / "eval_reports" / "user_feedback_revision_report.md"),
        "qc_integration": str(args.output_dir / "eval_reports" / "user_feedback_qc_integration.json"),
        "qc_integration_report": str(args.output_dir / "eval_reports" / "user_feedback_qc_integration.md"),
        "pending_unresolved_count": summary.get("pending_unresolved_count", 0),
        "requires_human_review": summary.get("requires_human_review", False),
        "dry_run_only": True,
    }
    if args.verbose:
        result["summary"] = summary
        result["feedback_qc_integration_summary"] = feedback_qc.get("summary", {})
        result["latest_entry"] = memory.get("entries", [])[-1] if memory.get("entries") else {}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
