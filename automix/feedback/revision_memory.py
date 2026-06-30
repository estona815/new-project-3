from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.feedback_action_mapping import map_feedback_to_actions
from automix.feedback.feedback_intake import classify_feedback_batch
from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json


REVISION_MEMORY_SCHEMA = "automix-user-feedback-revision-memory-v1"
FEEDBACK_SUMMARY_SCHEMA = "automix-user-feedback-summary-v1"

MEMORY_REL_PATH = Path("review/user_feedback_revision_memory.json")
ACTION_PLAN_REL_PATH = Path("eval_reports/user_feedback_action_plan.json")
REPORT_REL_PATH = Path("eval_reports/user_feedback_revision_report.md")


def _empty_memory(project_name: str = "") -> dict[str, Any]:
    return {
        "schema": REVISION_MEMORY_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "entries": [],
        "resolution_records": [],
        "category_counts": {},
        "unresolved_feedback_ids": [],
        "resolved_feedback_ids": [],
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_revision_memory(output_dir: Path, *, project_name: str = "") -> dict[str, Any]:
    data = _load_json(output_dir / MEMORY_REL_PATH)
    if not data:
        return _empty_memory(project_name=project_name)
    data.setdefault("schema", REVISION_MEMORY_SCHEMA)
    data.setdefault("project_name", project_name or data.get("project_name", ""))
    data.setdefault("entries", [])
    data.setdefault("resolution_records", [])
    data.setdefault("category_counts", {})
    data.setdefault("unresolved_feedback_ids", [])
    data.setdefault("resolved_feedback_ids", [])
    return data


def _category_counts(memory: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in memory.get("entries", []):
        for feedback in entry.get("feedback_items", []):
            for category in feedback.get("categories", []):
                name = str(category.get("category", "general_mix_feedback"))
                counts[name] = counts.get(name, 0) + 1
    return counts


def _entry_id(pass_id: str, feedback_items: list[dict[str, Any]]) -> str:
    if pass_id:
        return f"revision_{slugify(pass_id)}"
    if feedback_items:
        return f"revision_{feedback_items[0].get('feedback_id', 'unknown')}"
    return f"revision_{slugify(now_utc())}"


def _all_feedback_ids(memory: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for entry in memory.get("entries", []):
        for feedback in entry.get("feedback_items", []):
            feedback_id = str(feedback.get("feedback_id", ""))
            if feedback_id:
                ids.add(feedback_id)
    return ids


def _recompute_memory_status(memory: dict[str, Any]) -> dict[str, Any]:
    all_ids = _all_feedback_ids(memory)
    resolved = {str(item) for item in memory.get("resolved_feedback_ids", []) if str(item)}
    memory["resolved_feedback_ids"] = sorted(all_ids & resolved)
    memory["unresolved_feedback_ids"] = sorted(all_ids - resolved)
    memory["category_counts"] = _category_counts(memory)
    memory["updated_at"] = now_utc()
    return memory


def build_revision_entry(
    *,
    project_name: str,
    pass_id: str,
    feedback_texts: list[str],
    previous_memory: dict[str, Any] | None = None,
    track_name: str = "",
    source: str = "user",
    stage: str = "feedback_intake",
    applied_actions: list[dict[str, Any]] | None = None,
    evidence_paths: list[str] | None = None,
) -> dict[str, Any]:
    previous_counts = dict((previous_memory or {}).get("category_counts", {}))
    feedback_items = classify_feedback_batch(
        feedback_texts,
        project_name=project_name,
        pass_id=pass_id,
        track_name=track_name,
        source=source,
    )
    action_plans = [map_feedback_to_actions(item, previous_categories=previous_counts) for item in feedback_items]
    categories = sorted({category for plan in action_plans for category in plan.get("categories", [])})
    repeated_categories = sorted(category for category in categories if previous_counts.get(category, 0) > 0)
    return {
        "entry_id": _entry_id(pass_id, feedback_items),
        "project_name": project_name,
        "pass_id": pass_id,
        "stage": stage,
        "track_name": track_name,
        "source": source,
        "created_at": now_utc(),
        "feedback_items": feedback_items,
        "action_plans": action_plans,
        "applied_actions": applied_actions or [],
        "evidence_paths": evidence_paths or [],
        "categories": categories,
        "repeated_categories": repeated_categories,
        "unresolved_feedback_ids": [item.get("feedback_id", "") for item in feedback_items],
        "resolution_status": "planned_review_required" if feedback_items else "no_feedback",
        "human_review_required": bool(feedback_items),
        "dry_run_only": True,
    }


def append_revision_memory(
    *,
    output_dir: Path,
    project_name: str,
    pass_id: str,
    feedback_texts: list[str],
    track_name: str = "",
    source: str = "user",
    stage: str = "feedback_intake",
    applied_actions: list[dict[str, Any]] | None = None,
    evidence_paths: list[str] | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    memory = load_revision_memory(output_dir, project_name=project_name)
    entry = build_revision_entry(
        project_name=project_name,
        pass_id=pass_id,
        feedback_texts=feedback_texts,
        previous_memory=memory,
        track_name=track_name,
        source=source,
        stage=stage,
        applied_actions=applied_actions,
        evidence_paths=evidence_paths,
    )
    memory["project_name"] = project_name or memory.get("project_name", "")
    memory["updated_at"] = now_utc()
    memory.setdefault("entries", []).append(entry)
    _recompute_memory_status(memory)
    write_json(output_dir / MEMORY_REL_PATH, memory)
    action_plan = build_current_action_plan(memory)
    write_json(output_dir / ACTION_PLAN_REL_PATH, action_plan)
    write_feedback_revision_report(memory, output_dir)
    return memory


def initialize_revision_memory_baseline(
    *,
    output_dir: Path,
    project_name: str,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    memory = load_revision_memory(output_dir, project_name=project_name)
    memory["project_name"] = project_name or memory.get("project_name", "")
    memory.setdefault("created_at", now_utc())
    memory.setdefault("entries", [])
    memory.setdefault("resolution_records", [])
    memory.setdefault("category_counts", {})
    memory.setdefault("unresolved_feedback_ids", [])
    memory.setdefault("resolved_feedback_ids", [])
    if memory.get("entries"):
        memory["baseline_status"] = "feedback_entries_present"
        memory["no_feedback_fabricated"] = False
    else:
        memory["baseline_status"] = "no_feedback_recorded"
        memory["no_feedback_fabricated"] = True
    _recompute_memory_status(memory)
    write_json(output_dir / MEMORY_REL_PATH, memory)
    action_plan = build_current_action_plan(memory)
    write_json(output_dir / ACTION_PLAN_REL_PATH, action_plan)
    write_feedback_revision_report(memory, output_dir)
    return memory


def _resolution_missing_requirements(
    *,
    feedback_ids: list[str],
    known_feedback_ids: set[str],
    evidence_paths: list[str],
    human_reviewed: bool,
    measured_qc_passed: bool,
    loudness_matched_ab_reviewed: bool,
) -> list[str]:
    missing = []
    if not feedback_ids:
        missing.append("feedback_id_required")
    missing.extend(f"{feedback_id}:feedback_id_not_found" for feedback_id in feedback_ids if feedback_id not in known_feedback_ids)
    if not evidence_paths:
        missing.append("evidence_path_required")
    else:
        missing.extend(f"evidence_path_missing:{path}" for path in evidence_paths if not Path(path).expanduser().exists())
    if not human_reviewed:
        missing.append("human_review_required")
    if not measured_qc_passed:
        missing.append("measured_qc_pass_required")
    if not loudness_matched_ab_reviewed:
        missing.append("loudness_matched_ab_review_required")
    return sorted(set(missing))


def resolve_feedback_items(
    *,
    output_dir: Path,
    feedback_ids: list[str],
    project_name: str = "",
    pass_id: str = "",
    reviewer: str = "user",
    resolution_notes: str = "",
    evidence_paths: list[str] | None = None,
    human_reviewed: bool = False,
    measured_qc_passed: bool = False,
    loudness_matched_ab_reviewed: bool = False,
    remaining_risks: list[str] | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    memory = load_revision_memory(output_dir, project_name=project_name)
    clean_ids = sorted({str(item).strip() for item in feedback_ids if str(item).strip()})
    evidence_paths = [str(path) for path in (evidence_paths or []) if str(path).strip()]
    known = _all_feedback_ids(memory)
    missing = _resolution_missing_requirements(
        feedback_ids=clean_ids,
        known_feedback_ids=known,
        evidence_paths=evidence_paths,
        human_reviewed=human_reviewed,
        measured_qc_passed=measured_qc_passed,
        loudness_matched_ab_reviewed=loudness_matched_ab_reviewed,
    )
    accepted = not missing
    record = {
        "schema": "automix-user-feedback-resolution-record-v1",
        "project_name": project_name or memory.get("project_name", ""),
        "pass_id": pass_id,
        "reviewer": reviewer,
        "created_at": now_utc(),
        "feedback_ids": clean_ids,
        "resolution_notes": resolution_notes,
        "evidence_paths": evidence_paths,
        "human_reviewed": bool(human_reviewed),
        "measured_qc_passed": bool(measured_qc_passed),
        "loudness_matched_ab_reviewed": bool(loudness_matched_ab_reviewed),
        "remaining_risks": remaining_risks or [],
        "accepted_for_resolution": accepted,
        "missing_requirements": missing,
        "resolution_status": "resolved_with_evidence" if accepted else "resolution_evidence_incomplete",
    }
    memory["project_name"] = project_name or memory.get("project_name", "")
    memory.setdefault("resolution_records", []).append(record)
    if accepted:
        resolved = set(memory.get("resolved_feedback_ids", []))
        resolved.update(clean_ids)
        memory["resolved_feedback_ids"] = sorted(resolved)
    _recompute_memory_status(memory)
    write_json(output_dir / MEMORY_REL_PATH, memory)
    action_plan = build_current_action_plan(memory)
    write_json(output_dir / ACTION_PLAN_REL_PATH, action_plan)
    write_feedback_revision_report(memory, output_dir)
    return memory


def build_current_action_plan(memory: dict[str, Any]) -> dict[str, Any]:
    entries = list(memory.get("entries", []))
    latest = entries[-1] if entries else {}
    plans = latest.get("action_plans", []) if latest else []
    unresolved = list(memory.get("unresolved_feedback_ids", []))
    return {
        "schema": "automix-current-user-feedback-action-plan-v1",
        "project_name": memory.get("project_name", ""),
        "created_at": now_utc(),
        "baseline_status": memory.get("baseline_status", ""),
        "no_feedback_fabricated": bool(memory.get("no_feedback_fabricated", False)),
        "latest_entry_id": latest.get("entry_id", ""),
        "latest_pass_id": latest.get("pass_id", ""),
        "planned_actions": [action for plan in plans for action in plan.get("planned_actions", [])],
        "blocked_auto_actions": [action for plan in plans for action in plan.get("blocked_auto_actions", [])],
        "safety_flags": sorted({flag for plan in plans for flag in plan.get("safety_flags", [])}),
        "unresolved_feedback_ids": unresolved,
        "resolved_feedback_ids": list(memory.get("resolved_feedback_ids", [])),
        "requires_human_review": bool(unresolved),
        "dry_run_only": True,
    }


def summarize_feedback_memory(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    memory_path = output_dir / MEMORY_REL_PATH
    memory = _load_json(memory_path)
    if not memory:
        return {
            "schema": FEEDBACK_SUMMARY_SCHEMA,
            "exists": False,
            "path": str(memory_path),
            "total_entries": 0,
            "pending_unresolved_count": 0,
            "repeated_categories": [],
            "latest_pass_id": "",
            "baseline_status": "not_initialized",
            "no_feedback_fabricated": False,
            "requires_human_review": False,
            "dry_run_only": True,
            "warnings": [],
        }
    entries = list(memory.get("entries", []))
    latest = entries[-1] if entries else {}
    repeated = sorted({category for entry in entries for category in entry.get("repeated_categories", [])})
    unresolved = list(memory.get("unresolved_feedback_ids", []))
    warnings = []
    if unresolved:
        warnings.append("user_feedback_unresolved")
    if repeated:
        warnings.append("repeated_feedback_category_requires_attention")
    return {
        "schema": FEEDBACK_SUMMARY_SCHEMA,
        "exists": True,
        "path": str(memory_path),
        "total_entries": len(entries),
        "resolution_records_count": len(memory.get("resolution_records", [])),
        "pending_unresolved_count": len(unresolved),
        "resolved_feedback_count": len(memory.get("resolved_feedback_ids", [])),
        "repeated_categories": repeated,
        "latest_pass_id": latest.get("pass_id", ""),
        "latest_entry_id": latest.get("entry_id", ""),
        "baseline_status": memory.get("baseline_status", ""),
        "no_feedback_fabricated": bool(memory.get("no_feedback_fabricated", False)),
        "category_counts": memory.get("category_counts", {}),
        "requires_human_review": bool(unresolved),
        "dry_run_only": True,
        "warnings": warnings,
    }


def write_feedback_revision_report(memory: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# User Feedback Revision Loop",
        "",
        f"- Project: `{memory.get('project_name', '')}`",
        f"- Updated UTC: `{memory.get('updated_at', '')}`",
        f"- Entries: `{len(memory.get('entries', []))}`",
        f"- Unresolved feedback items: `{len(memory.get('unresolved_feedback_ids', []))}`",
        f"- Resolved feedback items: `{len(memory.get('resolved_feedback_ids', []))}`",
        f"- Baseline status: `{memory.get('baseline_status', '')}`",
        f"- No feedback fabricated: `{bool(memory.get('no_feedback_fabricated', False))}`",
        "",
        "This report is evidence for planning and human review. It does not prove an audio improvement by itself.",
        "",
    ]
    if not memory.get("entries"):
        lines.extend(
            [
                "No user feedback has been recorded in this revision memory. This baseline is only an audit marker and does not invent a listening review.",
                "",
            ]
        )
    for entry in memory.get("entries", []):
        lines.extend(
            [
                f"## {entry.get('pass_id') or entry.get('entry_id')}",
                "",
                f"- Stage: `{entry.get('stage')}`",
                f"- Track: `{entry.get('track_name') or 'project'}`",
                f"- Resolution: `{entry.get('resolution_status')}`",
                f"- Repeated categories: `{', '.join(entry.get('repeated_categories', [])) or 'none'}`",
                "",
            ]
        )
        for feedback in entry.get("feedback_items", []):
            category_names = ", ".join(item.get("category", "") for item in feedback.get("categories", []))
            lines.append(f"- Feedback `{feedback.get('feedback_id')}`: {feedback.get('normalized_text')}")
            lines.append(f"  Categories: `{category_names or 'none'}`")
        lines.append("")
        for plan in entry.get("action_plans", []):
            for action in plan.get("planned_actions", []):
                lines.append(f"- Planned action `{action.get('action_id')}`: {action.get('planned_action')}")
        lines.append("")
    if memory.get("resolution_records"):
        lines.extend(["## Resolution Records", ""])
        for record in memory.get("resolution_records", []):
            lines.append(f"- `{record.get('resolution_status')}` for `{', '.join(record.get('feedback_ids', [])) or 'none'}`")
            lines.append(f"  Evidence: `{', '.join(record.get('evidence_paths', [])) or 'none'}`")
            if record.get("missing_requirements"):
                lines.append(f"  Missing: `{', '.join(record.get('missing_requirements', []))}`")
            if record.get("remaining_risks"):
                lines.append(f"  Remaining risks: `{', '.join(record.get('remaining_risks', []))}`")
        lines.append("")
    path = output_dir / REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
