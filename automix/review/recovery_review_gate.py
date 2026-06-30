from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.review.recovery_ab_review_policy import build_recovery_ab_review_status, policy_for_decision
from automix.review.recovery_review_form_generator import write_recovery_review_form
from automix.review.recovery_review_importer import (
    decision_from_cli,
    load_review_decisions_json,
    parse_markdown_review_form,
    validate_import_payload,
)
from automix.review.recovery_review_schema import (
    default_recovery_review_decision,
    finalized_review_decision,
)


REQUIRED_PROMPT43_OUTPUTS = {
    "pilot_report": "eval_reports/recovery_only_pilot_report.md",
    "track_selection": "eval_reports/recovery_only_track_selection.json",
    "rollback_registry": "rollback/recovery_only_rollback_registry.json",
    "original_protection": "eval_reports/recovery_only_original_protection_report.json",
    "pitch_block": "eval_reports/recovery_only_pitch_block_report.json",
    "ab_render_plan": "eval_reports/recovery_only_ab_render_plan.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_prompt43_outputs(output_dir: Path) -> dict[str, Any]:
    paths = {key: output_dir / rel for key, rel in REQUIRED_PROMPT43_OUTPUTS.items()}
    missing = [f"{key}:{path}" for key, path in paths.items() if not path.exists()]
    data = {
        "paths": {key: str(path) for key, path in paths.items()},
        "missing": missing,
        "track_selection": _read_json(paths["track_selection"]),
        "rollback_registry": _read_json(paths["rollback_registry"]),
        "original_protection": _read_json(paths["original_protection"]),
        "pitch_block": _read_json(paths["pitch_block"]),
        "ab_render_plan": _read_json(paths["ab_render_plan"]),
    }
    blockers = []
    if missing:
        blockers.append("PROMPT43_OUTPUTS_MISSING")
    if data["original_protection"] and not data["original_protection"].get("safe", False):
        blockers.append("ORIGINAL_PROTECTION_FAILED")
    if data["pitch_block"] and not data["pitch_block"].get("pitch_stage_blocked", False):
        blockers.append("PITCH_BLOCK_FAILED")
    if data["pitch_block"] and (data["pitch_block"].get("pitch_plugins_inserted") or data["pitch_block"].get("pitch_parameters_written")):
        blockers.append("PITCH_BLOCK_FAILED")
    data["precondition"] = {
        "ok": not blockers,
        "blockers": sorted(set(blockers)),
        "warnings": missing,
    }
    return data


def drafts_from_rollback_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    drafts = []
    for entry in registry.get("entries", []) or []:
        drafts.append(
            {
                "original_track_name": entry.get("original_track_name", entry.get("track_name", "")),
                "original_track_guid": entry.get("original_track_guid", ""),
                "draft_track_name": entry.get("draft_track_name", ""),
                "draft_track_guid": entry.get("draft_track_guid", ""),
                "rollback_file": entry.get("rollback_file", ""),
                "safe_to_delete": bool(entry.get("safe_to_rollback", True)),
            }
        )
    return drafts


def default_review_state(project_name: str, drafts: list[dict[str, Any]], ab_status: dict[str, Any]) -> dict[str, Any]:
    ab_by_draft = {item.get("draft_track_name"): item for item in ab_status.get("tracks", [])}
    decisions = []
    for draft in drafts:
        ab = ab_by_draft.get(draft.get("draft_track_name"), {})
        decisions.append(
            default_recovery_review_decision(
                track_name=str(draft.get("original_track_name", "")),
                original_track_guid=str(draft.get("original_track_guid", "")),
                draft_track_name=str(draft.get("draft_track_name", "")),
                draft_track_guid=str(draft.get("draft_track_guid", "")),
                warnings=list(ab.get("warnings", [])),
            )
        )
    return {
        "schema": "automix-recovery-review-state-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "review_status": "pending" if drafts else "completed",
        "drafts": decisions,
        "accepted_drafts": [],
        "rejected_drafts": [],
        "needs_revision": [],
        "stem_required": [],
        "manual_cleanup_required": [],
        "global_downstream_allowed": False,
        "warnings": [] if drafts else ["no_recovery_drafts_to_review"],
    }


def _state_status(decisions: list[dict[str, Any]], precondition_blocked: bool = False) -> str:
    if precondition_blocked:
        return "blocked"
    if not decisions:
        return "completed"
    values = [item.get("decision") for item in decisions]
    if all(value == "needs_review" for value in values):
        return "pending"
    if any(value == "needs_revision" for value in values):
        return "needs_revision"
    if any(value == "stem_required" for value in values):
        return "stem_required"
    if all(value == "rejected" for value in values):
        return "all_rejected"
    if any(value in {"accepted", "accepted_light"} for value in values):
        return "accepted_some" if any(value == "needs_review" for value in values) else "completed"
    return "partially_reviewed"


def _group_decisions(decisions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "accepted_drafts": [item for item in decisions if item.get("decision") in {"accepted", "accepted_light"}],
        "rejected_drafts": [item for item in decisions if item.get("decision") == "rejected"],
        "needs_revision": [item for item in decisions if item.get("decision") == "needs_revision"],
        "stem_required": [item for item in decisions if item.get("decision") == "stem_required"],
        "manual_cleanup_required": [item for item in decisions if item.get("decision") == "manual_cleanup_required"],
    }


def _apply_imported_decisions(
    *,
    state: dict[str, Any],
    payload: dict[str, Any],
    ab_status: dict[str, Any],
    update: bool,
    acknowledge_warnings: bool,
    allow_provisional_without_ab: bool,
) -> tuple[dict[str, Any], list[str], int]:
    errors = validate_import_payload(payload)
    imported = 0
    decisions = list(state.get("drafts", []))
    by_draft = {item.get("draft_track_name"): item for item in decisions}
    ab_by_draft = {item.get("draft_track_name"): item for item in ab_status.get("tracks", [])}
    for item in payload.get("decisions", []) or []:
        draft_name = item.get("draft_track_name")
        if draft_name not in by_draft:
            errors.append(f"unknown_draft:{draft_name}")
            continue
        existing = by_draft[draft_name]
        if existing.get("decision") != "needs_review" and not update:
            errors.append(f"decision_exists_requires_update:{draft_name}")
            continue
        decision = item.get("decision", "needs_review")
        warnings_ack = list(item.get("warnings_acknowledged", []))
        if acknowledge_warnings and not warnings_ack:
            warnings_ack.append("cli_acknowledged")
        policy = policy_for_decision(
            ab_status=ab_by_draft.get(draft_name, {}),
            decision=decision,
            allow_provisional_without_ab=allow_provisional_without_ab,
        )
        if decision in {"accepted", "accepted_light"} and not warnings_ack:
            errors.append(f"warnings_not_acknowledged:{draft_name}")
            continue
        if not policy.get("allowed"):
            errors.append(f"ab_policy_block:{draft_name}:{','.join(policy.get('blockers', []))}")
            continue
        finalized = finalized_review_decision(
            existing,
            decision=decision,
            reviewer=str(payload.get("reviewer", "user")),
            notes=str(item.get("notes", "")),
            warnings_acknowledged=warnings_ack,
            ab_files_reviewed=bool(item.get("ab_files_reviewed") or ab_by_draft.get(draft_name, {}).get("ab_complete")),
            loudness_matched_reviewed=bool(item.get("loudness_matched_reviewed") or "loudness_matched_render_missing" not in ab_by_draft.get(draft_name, {}).get("warnings", [])),
            difference_file_reviewed=bool(item.get("difference_file_reviewed") or "difference_render_missing" not in ab_by_draft.get(draft_name, {}).get("warnings", [])),
            provisional_acceptance=bool(policy.get("provisional_acceptance")),
        )
        finalized["warnings"] = sorted(set(existing.get("warnings", []) + policy.get("warnings", [])))
        by_draft[draft_name] = finalized
        imported += 1
    state["drafts"] = [by_draft.get(item.get("draft_track_name"), item) for item in decisions]
    return state, errors, imported


def write_accepted_sources(project_name: str, decisions: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    accepted = []
    blocked = []
    for item in decisions:
        if item.get("decision") in {"accepted", "accepted_light"}:
            accepted.append(
                {
                    "original_track_name": item.get("track_name"),
                    "original_track_guid": item.get("original_track_guid", ""),
                    "accepted_draft_track_name": item.get("draft_track_name"),
                    "accepted_draft_track_guid": item.get("draft_track_guid", ""),
                    "decision": item.get("decision"),
                    "fragile_source": bool(item.get("fragile_source") or item.get("decision") == "accepted_light" or item.get("provisional_acceptance")),
                    "allowed_for_placement": "placement" in item.get("allowed_downstream_stages", []),
                    "allowed_for_pitch_triage": "pitch" in item.get("allowed_downstream_stages", []),
                    "pitch_extra_caution": bool(item.get("pitch_extra_caution") or item.get("decision") == "accepted_light"),
                    "allowed_for_final_export": False,
                    "provisional_acceptance": bool(item.get("provisional_acceptance")),
                    "notes": item.get("notes", ""),
                    "warnings": item.get("warnings", []),
                }
            )
        else:
            blocked.append(
                {
                    "original_track_name": item.get("track_name"),
                    "draft_track_name": item.get("draft_track_name"),
                    "decision": item.get("decision"),
                    "blocked_downstream_stages": item.get("blocked_downstream_stages", []),
                    "notes": item.get("notes", ""),
                }
            )
    data = {"schema": "automix-accepted-recovery-sources-v1", "project_name": project_name, "accepted_sources": accepted, "blocked_sources": blocked, "warnings": []}
    write_json(output_dir / "review" / "accepted_recovery_sources.json", data)
    return data


def write_rejected_recovery_drafts(project_name: str, decisions: list[dict[str, Any]], rollback_registry: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    rollback_by_draft = {item.get("draft_track_name"): item.get("rollback_file") for item in rollback_registry.get("entries", [])}
    data = {
        "schema": "automix-rejected-recovery-drafts-v1",
        "project_name": project_name,
        "rejected": [],
        "needs_revision": [],
        "stem_required": [],
        "manual_cleanup_required": [],
    }
    for item in decisions:
        entry = {
            "draft_track_name": item.get("draft_track_name"),
            "reason": item.get("notes", "") or item.get("decision"),
            "recommended_action": "rollback_or_keep_muted",
            "rollback_file": rollback_by_draft.get(item.get("draft_track_name"), ""),
            "safe_to_delete": True,
        }
        if item.get("decision") == "rejected":
            data["rejected"].append(entry)
        elif item.get("decision") == "needs_revision":
            data["needs_revision"].append(entry)
        elif item.get("decision") == "stem_required":
            data["stem_required"].append(entry)
        elif item.get("decision") == "manual_cleanup_required":
            data["manual_cleanup_required"].append(entry)
    write_json(output_dir / "review" / "rejected_recovery_drafts.json", data)
    return data


def write_revision_request(project_name: str, decisions: list[dict[str, Any]], output_dir: Path) -> Path:
    lines = ["# Recovery Revision Request", "", f"- Project: `{project_name}`", ""]
    needs = [item for item in decisions if item.get("decision") == "needs_revision"]
    if not needs:
        lines.append("No recovery revisions requested.")
    for item in needs:
        lines.extend(
            [
                f"## {item.get('draft_track_name')}",
                "",
                f"- Problem heard: `{item.get('notes', 'not specified')}`",
                "- Recommended adjustment: `reduce processing and preserve body`",
                "- Safer profile: `minimal_cleanup`",
                "- Controls to reduce: `high_fizz_control_amount`, `sibilance_control_amount`, `harshness_dynamic_cut_amount`",
                "- Controls to disable: `saturation`, `side_cleanup if phasey`",
                "- Switch to minimal cleanup: `yes if damage persists`",
                "- Better stem needed: `yes if source artifacts dominate`",
                "",
            ]
        )
    path = output_dir / "review" / "recovery_revision_request.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_downstream_gate(project_name: str, state: dict[str, Any], accepted_sources: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    accepted = accepted_sources.get("accepted_sources", [])
    allowed = []
    if accepted:
        allowed = ["vocal_placement_scan", "pitch_triage"]
    blocked = []
    if not accepted:
        blocked = ["pitch", "placement", "premaster", "final_export", "reference_matching"]
    else:
        blocked = ["premaster", "final_export"]
    gate = {
        "schema": "automix-downstream-recovery-gate-v1",
        "project_name": project_name,
        "recovery_review_required": True,
        "review_status": state.get("review_status", "pending"),
        "accepted_sources_available": bool(accepted),
        "blocked_downstream_stages": blocked,
        "allowed_downstream_stages": allowed,
        "warnings": ["final_export_still_blocked_after_recovery_review"] if accepted else ["recovery_review_incomplete_or_no_acceptance"],
    }
    write_json(output_dir / "orchestrator" / "downstream_recovery_gate.json", gate)
    return gate


def write_review_report(
    *,
    project_name: str,
    state: dict[str, Any],
    accepted_sources: dict[str, Any],
    rejected: dict[str, Any],
    downstream_gate: dict[str, Any],
    ab_status: dict[str, Any],
    precondition: dict[str, Any],
    output_dir: Path,
    final_recommendation: str,
) -> Path:
    decisions = state.get("drafts", [])
    ab_by_draft = {item.get("draft_track_name"): item for item in ab_status.get("tracks", [])}
    lines = [
        "# Recovery Draft Human Review Report",
        "",
        "## Summary",
        "",
        f"- Project: `{project_name}`",
        f"- Review status: `{state.get('review_status')}`",
        f"- Accepted drafts: `{len([d for d in decisions if d.get('decision') == 'accepted'])}`",
        f"- Accepted light drafts: `{len([d for d in decisions if d.get('decision') == 'accepted_light'])}`",
        f"- Rejected drafts: `{len(rejected.get('rejected', []))}`",
        f"- Needs revision: `{len(rejected.get('needs_revision', []))}`",
        f"- Stem required: `{len(rejected.get('stem_required', []))}`",
        f"- Manual cleanup required: `{len(rejected.get('manual_cleanup_required', []))}`",
        f"- Downstream allowed: `{downstream_gate.get('allowed_downstream_stages', [])}`",
        "",
        "## Preconditions",
        "",
        f"- Prompt 43 report: `{not bool(precondition.get('missing'))}`",
        f"- Original protection: `{precondition.get('original_protection_safe')}`",
        f"- Pitch block: `{precondition.get('pitch_block_ok')}`",
        f"- Rollback registry: `{precondition.get('rollback_registry_ok')}`",
        f"- A/B availability: `{len([t for t in ab_status.get('tracks', []) if t.get('ab_complete')])}`",
        "",
        "## Review Decisions",
        "",
        "| Original Track | Draft Track | A/B Complete | Evaluation Passed | Decision | Downstream Allowed | Notes |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for item in decisions:
        ab = ab_by_draft.get(item.get("draft_track_name"), {})
        lines.append(
            f"| `{item.get('track_name')}` | `{item.get('draft_track_name')}` | `{ab.get('ab_complete', False)}` | `{ab.get('evaluation_passed', False)}` | `{item.get('decision')}` | `{', '.join(item.get('allowed_downstream_stages', []))}` | {item.get('notes', '')} |"
        )
    lines.extend(["", "## Accepted Sources", ""])
    if not accepted_sources.get("accepted_sources"):
        lines.append("- none")
    for item in accepted_sources.get("accepted_sources", []):
        lines.append(f"- `{item.get('accepted_draft_track_name')}` fragile `{item.get('fragile_source')}`, placement `{item.get('allowed_for_placement')}`, pitch triage `{item.get('allowed_for_pitch_triage')}`, final export `{item.get('allowed_for_final_export')}`")
    lines.extend(["", "## Rejected / Blocked Sources", ""])
    for key in ("rejected", "needs_revision", "stem_required", "manual_cleanup_required"):
        for item in rejected.get(key, []):
            lines.append(f"- `{item.get('draft_track_name')}`: `{key}`, rollback `{item.get('rollback_file')}`, action `{item.get('recommended_action')}`")
    if not any(rejected.get(key) for key in ("rejected", "needs_revision", "stem_required", "manual_cleanup_required")):
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Revision Requests",
            "",
            "- See `automix/review/recovery_revision_request.md`.",
            "",
            "## Stem Requests",
            "",
            f"- Stem-required decisions: `{len(rejected.get('stem_required', []))}`",
            "",
            "## Downstream Gate",
            "",
            f"- placement allowed: `{'vocal_placement_scan' in downstream_gate.get('allowed_downstream_stages', [])}`",
            f"- pitch triage allowed: `{'pitch_triage' in downstream_gate.get('allowed_downstream_stages', [])}`",
            "- premaster allowed: `False`",
            "- final export allowed: `False`",
            "",
            "## Manual Listening Checklist",
            "",
            "- vocal is not duller",
            "- vocal is not thinner",
            "- consonants are not smeared",
            "- sibilance is not lispy",
            "- stereo image is stable",
            "- emotional tone is preserved",
            "- AI artifacts are reduced, not hidden",
            "- draft is better at matched loudness",
            "",
            "## Final Recommendation",
            "",
            f"`{final_recommendation}`",
            "",
        ]
    )
    path = output_dir / "eval_reports" / "recovery_review_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_recovery_review_gate(
    *,
    project_path: str | Path | None = None,
    output_dir: str | Path = "automix",
    generate_form: bool = False,
    input_decisions: str | Path | None = None,
    markdown_form: str | Path | None = None,
    accept_draft: str | None = None,
    decision: str | None = None,
    notes: str = "",
    acknowledge_warnings: bool = False,
    allow_provisional_without_ab: bool = False,
    update: bool = False,
    mute_rejected: bool = False,
    interactive: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    prompt43 = load_prompt43_outputs(output)
    project_name = prompt43.get("track_selection", {}).get("project_name") or prompt43.get("rollback_registry", {}).get("project_name") or (Path(project_path).stem if project_path else "project")
    drafts = drafts_from_rollback_registry(prompt43.get("rollback_registry", {}))
    ab_status = build_recovery_ab_review_status(project_name=project_name, drafts=drafts, output_dir=output)
    existing_state = _read_json(output / "review" / "recovery_review_state.json")
    if existing_state and existing_state.get("drafts"):
        state = existing_state
        state["updated_at"] = now_utc()
    else:
        state = default_review_state(project_name, drafts, ab_status)
    blocker_errors = []
    imported_count = 0
    if generate_form or True:
        form_path = write_recovery_review_form(project_name=project_name, drafts=drafts, ab_status=ab_status, output_dir=output)
    payloads = []
    if input_decisions:
        payloads.append(load_review_decisions_json(Path(input_decisions)))
    if markdown_form:
        payloads.append(parse_markdown_review_form(Path(markdown_form)))
    cli_payload = decision_from_cli(draft_track_name=accept_draft, decision=decision, notes=notes, acknowledge_warnings=acknowledge_warnings)
    if cli_payload.get("decisions"):
        payloads.append(cli_payload)
    if interactive:
        blocker_errors.append("interactive_mode_not_available_in_non_tty_runner")
    if prompt43.get("precondition", {}).get("blockers"):
        blocker_errors.extend(prompt43["precondition"]["blockers"])
    if prompt43.get("precondition", {}).get("ok", True):
        for payload in payloads:
            state, errors, count = _apply_imported_decisions(
                state=state,
                payload=payload,
                ab_status=ab_status,
                update=update,
                acknowledge_warnings=acknowledge_warnings,
                allow_provisional_without_ab=allow_provisional_without_ab,
            )
            blocker_errors.extend(errors)
            imported_count += count
    elif payloads:
        blocker_errors.append("precondition_failed_decisions_not_imported")
    groups = _group_decisions(state.get("drafts", []))
    state.update(groups)
    state["review_status"] = _state_status(state.get("drafts", []), precondition_blocked=bool(prompt43.get("precondition", {}).get("blockers")))
    state["global_downstream_allowed"] = bool(groups["accepted_drafts"] and not prompt43.get("precondition", {}).get("blockers"))
    state["warnings"] = sorted(set(state.get("warnings", []) + ab_status.get("warnings", []) + blocker_errors))
    write_json(output / "review" / "recovery_review_state.json", state)
    accepted_sources = write_accepted_sources(project_name, state.get("drafts", []), output)
    rejected = write_rejected_recovery_drafts(project_name, state.get("drafts", []), prompt43.get("rollback_registry", {}), output)
    revision_path = write_revision_request(project_name, state.get("drafts", []), output)
    downstream_gate = write_downstream_gate(project_name, state, accepted_sources, output)
    if not drafts:
        final_recommendation = "no_recovery_drafts_to_review"
    elif blocker_errors:
        final_recommendation = "review_incomplete_do_not_continue"
    elif rejected.get("stem_required"):
        final_recommendation = "provide_better_stems"
    elif rejected.get("manual_cleanup_required"):
        final_recommendation = "manual_cleanup_required"
    elif rejected.get("needs_revision"):
        final_recommendation = "rerun_recovery_revision"
    elif accepted_sources.get("accepted_sources"):
        if any(item.get("decision") == "accepted_light" or item.get("provisional_acceptance") for item in accepted_sources.get("accepted_sources", [])):
            final_recommendation = "proceed_to_pitch_triage_with_caution"
        else:
            final_recommendation = "proceed_to_vocal_placement_scan"
    else:
        final_recommendation = "review_incomplete_do_not_continue"
    report_path = write_review_report(
        project_name=project_name,
        state=state,
        accepted_sources=accepted_sources,
        rejected=rejected,
        downstream_gate=downstream_gate,
        ab_status=ab_status,
        precondition={
            "missing": prompt43.get("missing", []),
            "original_protection_safe": prompt43.get("original_protection", {}).get("safe", False),
            "pitch_block_ok": prompt43.get("pitch_block", {}).get("pitch_stage_blocked", False),
            "rollback_registry_ok": bool(prompt43.get("rollback_registry")),
        },
        output_dir=output,
        final_recommendation=final_recommendation,
    )
    blocker_report = {}
    if prompt43.get("precondition", {}).get("blockers"):
        blocker_report = {
            "schema": "automix-recovery-review-blocker-report-v1",
            "project_name": project_name,
            "blockers": prompt43["precondition"]["blockers"],
            "recommended_action": "run_prompt43_first" if "PROMPT43_OUTPUTS_MISSING" in prompt43["precondition"]["blockers"] else "manual_inspection_required",
        }
        write_json(output / "review" / "recovery_review_blocker_report.json", blocker_report)
    summary = {
        "schema": "automix-recovery-review-gate-summary-v1",
        "project_name": project_name,
        "project_path": str(project_path or ""),
        "review_status": state.get("review_status"),
        "prompt43_precondition_ok": prompt43.get("precondition", {}).get("ok", False),
        "prompt43_blockers": prompt43.get("precondition", {}).get("blockers", []),
        "drafts_to_review": len(drafts),
        "decisions_imported": imported_count,
        "accepted_drafts": len(groups["accepted_drafts"]),
        "rejected_drafts": len(groups["rejected_drafts"]),
        "revision_requests": len(groups["needs_revision"]),
        "stem_requests": len(groups["stem_required"]),
        "manual_cleanup_required": len(groups["manual_cleanup_required"]),
        "downstream_gate_status": downstream_gate.get("review_status"),
        "downstream_allowed": downstream_gate.get("allowed_downstream_stages", []),
        "ab_review_tracks": len(ab_status.get("tracks", [])),
        "ab_complete_tracks": len([item for item in ab_status.get("tracks", []) if item.get("ab_complete")]),
        "form": str(form_path),
        "reports": {
            "review_state": str(output / "review" / "recovery_review_state.json"),
            "accepted_sources": str(output / "review" / "accepted_recovery_sources.json"),
            "ab_review_status": str(output / "review" / "recovery_ab_review_status.json"),
            "downstream_gate": str(output / "orchestrator" / "downstream_recovery_gate.json"),
            "rejected_drafts": str(output / "review" / "rejected_recovery_drafts.json"),
            "revision_request": str(revision_path),
            "review_report": str(report_path),
        },
        "final_recommendation": final_recommendation,
        "warnings": sorted(set(state.get("warnings", []) + prompt43.get("precondition", {}).get("warnings", []))),
        "errors": sorted(set(blocker_errors)),
    }
    if verbose:
        summary["drafts"] = drafts
        summary["blocker_report"] = blocker_report
    write_json(output / "review" / "recovery_review_gate_summary.json", summary)
    return summary
