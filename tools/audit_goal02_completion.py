#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_completion_audit"
REQUIRED_MAIN_VOCAL_PLUGIN = "JS: Codex Vocal AI Artifact Split Tamer"
MAIN_TRACK = "08 MALE_NONHOOK_CENTER"
AB_SEQUENCE_ORDER = (
    "Current target -> v04 candidate -> ref_06 -> v04 candidate -> "
    "ref_07 -> v04 candidate -> ref_03 -> v04 candidate"
)

TOP10_FIELDS = [
    "문제:",
    "원인 추정:",
    "레퍼런스와의 차이:",
    "수정 위치:",
    "사용할 플러그인:",
    "권장 시작값:",
    "A/B 확인법:",
    "실패 징후:",
]

CHAIN_HEADINGS = [
    "Lead Vocal Chain",
    "Lead Vocal Parallel Crush",
    "Doubles / Adlibs",
    "808 Chain",
    "Drum Bus",
    "Music Bus",
    "Mix Bus / Master Chain",
]

STARTING_PARAMETER_NEEDLES = [
    "Lead vocal:",
    "Parallel crush:",
    "Doubles/adlibs:",
    "808:",
    "Drums:",
    "Music:",
    "Master:",
]

REFERENCE_MIX_FEATURE_KEYS = [
    "overall_loudness_rms_lufs",
    "true_peak_peak_density",
    "vocal_position_thickness_brightness_proxy",
    "autotune_sibilance_proxy",
    "bass_808_character_proxy",
    "kick_808_relationship_proxy",
    "drum_hihat_proxy",
    "presence_harshness_air",
    "stereo_width_mono_compatibility",
    "reverb_delay_depth_proxy",
    "saturation_clipping_distortion_proxy",
    "master_compression_proxy",
    "core_mix_features_3",
]

PRIMARY_REFERENCE_TRANSLATION_FIELDS = [
    "why_reference",
    "target_lacks",
    "target_already_ok",
    "must_follow",
    "must_not_copy",
    "bus_translation_order",
    "plugin_scope",
    "ab_check",
    "failure_signs",
    "claim_limit",
]


PATHS = {
    "reference_match": Path("reports/goal02_8_reference_match/goal02_reference_match.json"),
    "reference_mix_features": Path("reports/goal02_8_reference_match/goal02_reference_8_track_mix_features.json"),
    "primary_reference_translation_pack": Path("reports/goal02_8_reference_match/goal02_primary_reference_translation_pack.json"),
    "objective_coverage_audit": Path("reports/goal02_objective_coverage/goal02_objective_coverage_audit.json"),
    "action_plan": Path("reports/goal02_8_reference_match/GOAL02_REAPER_ACTION_PLAN.md"),
    "decision_packet": Path("reports/goal02_candidate_decision_v04/goal02_candidate_decision.json"),
    "v04_trace": Path("reports/goal02_chorus_reaper_v04/actual_reaper_plugin_trace.json"),
    "fullsong_trace": Path("reports/goal02_fullsong_reaper_v04_draft/actual_reaper_plugin_trace.json"),
    "v04_lufs": Path("reports/goal02_chorus_lufs_target_v04/goal02_lufs_target_package.json"),
    "fullsong_lufs": Path("reports/goal02_fullsong_lufs_target_v04_draft/goal02_lufs_target_package.json"),
    "review_package": Path("reports/goal02_v04_user_ab_review/goal02_v04_review_package.json"),
    "user_decision": Path("reports/goal02_user_ab_decision/goal02_user_ab_decision.json"),
    "final_delivery": Path("reports/goal02_final_delivery/goal02_final_delivery_gate.json"),
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(root: Path, rel: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = root / rel
    if not path.exists():
        return None, f"missing:{rel}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"invalid_json:{rel}:{exc}"


def add_item(items: list[dict[str, Any]], item_id: str, requirement: str, status: str, evidence: str, notes: str = "") -> None:
    items.append(
        {
            "id": item_id,
            "requirement": requirement,
            "status": status,
            "evidence": evidence,
            "notes": notes,
        }
    )


def row_has_first_slot_plugin(trace: dict[str, Any], track_name: str = MAIN_TRACK) -> bool:
    for row in trace.get("rows", []):
        if (
            str(row.get("track", "")).lower() == track_name.lower()
            and row.get("fx_index") == 0
            and row.get("plugin") == REQUIRED_MAIN_VOCAL_PLUGIN
        ):
            return True
    return False


def route_muted_no_master(trace: dict[str, Any], track: str) -> bool:
    for row in trace.get("rows", []):
        if row.get("track") == track and row.get("stage") == "track config":
            plugin = str(row.get("plugin", ""))
            return "muted=true" in plugin and "master_send=false" in plugin
    return False


def lufs_targets_pass(package: dict[str, Any]) -> tuple[bool, str]:
    rows = package.get("loudness_rows", [])
    target_rows = [row for row in rows if row.get("target_pass") is not None]
    if not target_rows:
        return False, "no target-pass loudness rows"
    failed = [str(row.get("label")) for row in target_rows if row.get("target_pass") is not True]
    if failed:
        return False, "failed target rows: " + ", ".join(failed)
    return True, f"{len(target_rows)} target rows pass"


def review_package_passes(package: dict[str, Any]) -> tuple[bool, str]:
    if package.get("status") != "USER_AB_REVIEW_PACKAGE_READY_NOT_FINAL":
        return False, f"status={package.get('status')}"
    zip_path = Path(str(package.get("zip_path", "")))
    if not zip_path.exists():
        return False, f"review zip missing: {zip_path}"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
    except zipfile.BadZipFile:
        return False, "review zip invalid"
    if bad:
        return False, f"review zip bad member: {bad}"
    target_rows = [row for row in package.get("loudness_rows", []) if row.get("review_target_kind")]
    if not target_rows:
        return False, "review target rows missing"
    failed = [str(row.get("label")) for row in target_rows if row.get("review_target_pass") is not True]
    if failed:
        return False, "failed review target rows: " + ", ".join(failed)
    return True, f"review zip valid; {len(target_rows)} target rows pass"


def review_flow_controls_pass(package: dict[str, Any]) -> tuple[bool, str]:
    zip_path = Path(str(package.get("zip_path", "")))
    if not zip_path.exists():
        return False, f"review zip missing: {zip_path}"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            required = {"GOAL02_REVIEW_PLAYER.html", "GOAL02_USER_AB_REVIEW_CHECKLIST.md"}
            missing_files = sorted(required - names)
            if missing_files:
                return False, "missing review flow files: " + ", ".join(missing_files)
            html = archive.read("GOAL02_REVIEW_PLAYER.html").decode("utf-8")
            checklist = archive.read("GOAL02_USER_AB_REVIEW_CHECKLIST.md").decode("utf-8")
    except zipfile.BadZipFile:
        return False, "review zip invalid"
    except KeyError as exc:
        return False, f"review flow file missing:{exc}"

    checks = {
        "ab_order_in_html": AB_SEQUENCE_ORDER in html,
        "ab_order_in_checklist": AB_SEQUENCE_ORDER in checklist,
        "approval_command_in_html": "python3 tools/record_goal02_ab_decision.py --decision approve_v04_20s_then_extend_final" in html,
        "revision_command_in_checklist": "python3 tools/record_goal02_ab_decision.py --decision revise_v04_hat_sibilance" in checklist,
        "not_approval_warning_in_html": "does not approve audio" in html,
        "final_gate_warning_in_checklist": "does not replace the final WAV/MP3/ZIP delivery gate" in checklist,
    }
    failed = [key for key, ok in checks.items() if not ok]
    if failed:
        return False, "failed review flow checks: " + ", ".join(failed)
    return True, "review player/checklist include A/B order, decision commands, and final-gate warnings"


def reference_mix_feature_report_passes(report: dict[str, Any]) -> tuple[bool, str]:
    if report.get("status") != "REFERENCE_8_TRACK_MIX_FEATURE_REPORT_READY_METRIC_PROXIES":
        return False, f"status={report.get('status')}"
    refs = report.get("references", [])
    if len(refs) != 8:
        return False, f"reference_count={len(refs)}"
    primary_ids = report.get("primary_reference_ids", [])
    if len(primary_ids) < 2:
        return False, f"primary_reference_count={len(primary_ids)}"
    weak: list[str] = []
    for ref in refs:
        missing = [key for key in REFERENCE_MIX_FEATURE_KEYS if key not in ref]
        if missing:
            weak.append(f"{ref.get('id')}:missing:{','.join(missing)}")
        if len(ref.get("core_mix_features_3", [])) != 3:
            weak.append(f"{ref.get('id')}:core_mix_features_3_count")
        if "not listening claims" not in str(ref.get("claim_limit", "")):
            weak.append(f"{ref.get('id')}:claim_limit")
    if weak:
        return False, "; ".join(weak)
    return True, f"8 references covered; primary_reference_ids={','.join(primary_ids)}; proxy claim limits present"


def primary_reference_translation_pack_passes(pack: dict[str, Any]) -> tuple[bool, str]:
    if pack.get("status") != "PRIMARY_REFERENCE_TRANSLATION_PACK_READY":
        return False, f"status={pack.get('status')}"
    required_ids = {"ref_03", "ref_06", "ref_07"}
    entries = pack.get("entries", [])
    entry_ids = {str(entry.get("id")) for entry in entries if isinstance(entry, dict)}
    if entry_ids != required_ids:
        return False, f"primary_entry_ids={','.join(sorted(entry_ids))}"
    if pack.get("primary_reference_count") != 3:
        return False, f"primary_reference_count={pack.get('primary_reference_count')}"
    weak: list[str] = []
    for entry in entries:
        ref_id = str(entry.get("id"))
        for field in PRIMARY_REFERENCE_TRANSLATION_FIELDS:
            value = entry.get(field)
            if isinstance(value, list):
                if not value:
                    weak.append(f"{ref_id}:empty:{field}")
            elif not value:
                weak.append(f"{ref_id}:missing:{field}")
        if "not a listening claim" not in str(entry.get("claim_limit", "")):
            weak.append(f"{ref_id}:claim_limit")
    if weak:
        return False, "; ".join(weak)
    return True, "ref_03/ref_06/ref_07 translated into follow/avoid/bus/plugin/A-B controls"


def objective_coverage_audit_passes(audit: dict[str, Any]) -> tuple[bool, str]:
    if audit.get("status") not in {"OBJECTIVE_COVERAGE_READY_USER_AB_PENDING", "OBJECTIVE_COVERAGE_COMPLETE_VERIFIED"}:
        return False, f"status={audit.get('status')}"
    if audit.get("missing_count") != 0:
        return False, f"missing_count={audit.get('missing_count')}"
    if audit.get("non_user_requirements_passed") is not True:
        return False, f"non_user_requirements_passed={audit.get('non_user_requirements_passed')}"
    blocked_ids = sorted(str(item.get("id")) for item in audit.get("items", []) if item.get("status") == "BLOCKED")
    expected_blockers = ["approved_final_delivery_package", "user_ab_success_criteria"]
    if blocked_ids and blocked_ids != expected_blockers:
        return False, f"unexpected_blocked_ids={','.join(blocked_ids)}"
    return True, f"objective coverage non-user requirements pass; blocked_ids={','.join(blocked_ids) or 'none'}"


def audit_goal02(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    items: list[dict[str, Any]] = []

    reference, error = load_json(root, PATHS["reference_match"])
    if error:
        add_item(items, "reference_analysis", "Analyze target plus eight references from source files.", "MISSING", str(PATHS["reference_match"]), error)
    else:
        summary = reference.get("summary", {})
        refs_measured = int(summary.get("references_measured", 0) or 0)
        primary_count = len(reference.get("primary_references") or reference.get("closest_references") or [])
        status = "PASS" if refs_measured == 8 and primary_count >= 2 else "MISSING"
        notes = f"references_measured={refs_measured}; primary_or_closest_count={primary_count}"
        add_item(items, "reference_analysis", "Analyze target plus eight references from source files.", status, str(PATHS["reference_match"]), notes)

    reference_features, error = load_json(root, PATHS["reference_mix_features"])
    if error:
        add_item(
            items,
            "reference_8_track_feature_report",
            "Write per-reference mix feature coverage for all eight references using measured proxies and explicit claim limits.",
            "MISSING",
            str(PATHS["reference_mix_features"]),
            error,
        )
    else:
        ok, notes = reference_mix_feature_report_passes(reference_features)
        add_item(
            items,
            "reference_8_track_feature_report",
            "Write per-reference mix feature coverage for all eight references using measured proxies and explicit claim limits.",
            "PASS" if ok else "MISSING",
            str(PATHS["reference_mix_features"]),
            notes,
        )

    translation_pack, error = load_json(root, PATHS["primary_reference_translation_pack"])
    if error:
        add_item(
            items,
            "primary_reference_translation_pack",
            "Translate ref_03/ref_06/ref_07 into what to follow, what not to copy, bus order, plugin scope, and A/B checks.",
            "MISSING",
            str(PATHS["primary_reference_translation_pack"]),
            error,
        )
    else:
        ok, notes = primary_reference_translation_pack_passes(translation_pack)
        add_item(
            items,
            "primary_reference_translation_pack",
            "Translate ref_03/ref_06/ref_07 into what to follow, what not to copy, bus order, plugin scope, and A/B checks.",
            "PASS" if ok else "MISSING",
            str(PATHS["primary_reference_translation_pack"]),
            notes,
        )

    objective_coverage, error = load_json(root, PATHS["objective_coverage_audit"])
    if error:
        add_item(
            items,
            "objective_coverage_audit",
            "Audit the original Goal 02 objective item by item and prove all non-user requirements are covered.",
            "MISSING",
            str(PATHS["objective_coverage_audit"]),
            error,
        )
    else:
        ok, notes = objective_coverage_audit_passes(objective_coverage)
        add_item(
            items,
            "objective_coverage_audit",
            "Audit the original Goal 02 objective item by item and prove all non-user requirements are covered.",
            "PASS" if ok else "MISSING",
            str(PATHS["objective_coverage_audit"]),
            notes,
        )

    action_plan = root / PATHS["action_plan"]
    if not action_plan.exists():
        add_item(items, "required_written_plan", "Write primary refs, common traits, TOP 10, chains, A/B method, export targets, rollback, 30-minute plan.", "MISSING", str(PATHS["action_plan"]))
        for item_id, requirement in [
            ("reference_plan_sections", "Document primary references and shared reference mix traits separately."),
            ("top10_problem_format", "Document exactly ten target problems with cause, reference delta, fix location, plugins, starts, A/B check, and failure signs."),
            ("required_chain_coverage", "Document the required A-G REAPER FX chains."),
            ("starting_parameter_coverage", "Document starting parameter ranges for the required chains."),
            ("ab_export_rollback_workflow", "Document chorus-first order, loudness-matched A/B, master targets, rollback criteria, and 30-minute work table."),
        ]:
            add_item(items, item_id, requirement, "MISSING", str(PATHS["action_plan"]), "action plan missing")
    else:
        text = action_plan.read_text(encoding="utf-8")
        needles = [
            "Primary Reference Selection",
            "Reference Common Mix Features",
            "Target Top 10 Problems",
            "Chorus 20-Second Revision Order",
            "Lead Vocal Chain",
            "Loudness-Matched A/B Method",
            "Master Export Goals",
            "Rollback Criteria",
            "30-Minute Work Table",
            "User A/B Decision Intake",
            "Final Delivery Gate",
        ]
        missing = [needle for needle in needles if needle not in text]
        status = "PASS" if not missing else "MISSING"
        add_item(items, "required_written_plan", "Write primary refs, common traits, TOP 10, chains, A/B method, export targets, rollback, 30-minute plan.", status, str(PATHS["action_plan"]), "missing sections: " + ", ".join(missing) if missing else "required sections present")

        reference_needles = ["Primary Reference Selection", "Reference Common Mix Features", "| 1 | `ref_", "| 2 | `ref_"]
        missing_reference = [needle for needle in reference_needles if needle not in text]
        add_item(
            items,
            "reference_plan_sections",
            "Document primary references and shared reference mix traits separately.",
            "PASS" if not missing_reference else "MISSING",
            str(PATHS["action_plan"]),
            "missing: " + ", ".join(missing_reference) if missing_reference else "primary refs and shared traits present",
        )

        field_counts = {field: text.count(field) for field in TOP10_FIELDS}
        weak_fields = [f"{field}={count}" for field, count in field_counts.items() if count < 10]
        add_item(
            items,
            "top10_problem_format",
            "Document exactly ten target problems with cause, reference delta, fix location, plugins, starts, A/B check, and failure signs.",
            "PASS" if not weak_fields else "MISSING",
            str(PATHS["action_plan"]),
            "field counts all >=10" if not weak_fields else "weak fields: " + ", ".join(weak_fields),
        )

        missing_chains = [heading for heading in CHAIN_HEADINGS if heading not in text]
        add_item(
            items,
            "required_chain_coverage",
            "Document the required A-G REAPER FX chains.",
            "PASS" if not missing_chains else "MISSING",
            str(PATHS["action_plan"]),
            "all required chains present" if not missing_chains else "missing chains: " + ", ".join(missing_chains),
        )

        missing_starts = [needle for needle in STARTING_PARAMETER_NEEDLES if needle not in text]
        add_item(
            items,
            "starting_parameter_coverage",
            "Document starting parameter ranges for the required chains.",
            "PASS" if not missing_starts else "MISSING",
            str(PATHS["action_plan"]),
            "all starting parameter groups present" if not missing_starts else "missing starts: " + ", ".join(missing_starts),
        )

        workflow_needles = [
            "Chorus 20-Second Revision Order",
            "Loudness-Matched A/B Method",
            "Master Export Goals",
            "Rollback Criteria",
            "30-Minute Work Table",
            "-9.5 to -8.0 LUFS-I",
            "-14.5 to -12.5 LUFS-I",
        ]
        missing_workflow = [needle for needle in workflow_needles if needle not in text]
        add_item(
            items,
            "ab_export_rollback_workflow",
            "Document chorus-first order, loudness-matched A/B, master targets, rollback criteria, and 30-minute work table.",
            "PASS" if not missing_workflow else "MISSING",
            str(PATHS["action_plan"]),
            "A/B, export, rollback, and 30-minute workflow present" if not missing_workflow else "missing workflow: " + ", ".join(missing_workflow),
        )

    decision_packet, error = load_json(root, PATHS["decision_packet"])
    if error:
        add_item(items, "preferred_20s_candidate", "Prepare preferred 20-second v04 loudness-matched candidate and rollback candidate.", "MISSING", str(PATHS["decision_packet"]), error)
    else:
        status = "PASS" if decision_packet.get("status") == "PREFERRED_20S_CANDIDATE_READY_USER_AB_PENDING" else "MISSING"
        preferred = decision_packet.get("preferred")
        if isinstance(preferred, dict):
            preferred = preferred.get("version", "preferred_candidate_present")
        rollback = decision_packet.get("rollback_candidate")
        if isinstance(rollback, dict):
            rollback = rollback.get("version", "rollback_candidate_present")
        add_item(
            items,
            "preferred_20s_candidate",
            "Prepare preferred 20-second v04 loudness-matched candidate and rollback candidate.",
            status,
            str(PATHS["decision_packet"]),
            f"status={decision_packet.get('status')}; preferred={preferred}; rollback={rollback}",
        )

    for key, label in [("v04_trace", "20-second REAPER trace"), ("fullsong_trace", "full-song REAPER trace")]:
        trace, error = load_json(root, PATHS[key])
        if error:
            add_item(items, key, f"{label}: prove main vocal first-slot JSFX and muted reference/source routing.", "MISSING", str(PATHS[key]), error)
            continue
        first_slot = row_has_first_slot_plugin(trace)
        ref_ok = route_muted_no_master(trace, "REF BUS")
        source_ok = route_muted_no_master(trace, "SOURCE full mix reference muted - not in master")
        status = "PASS" if first_slot and ref_ok and source_ok else "MISSING"
        add_item(items, key, f"{label}: prove main vocal first-slot JSFX and muted reference/source routing.", status, str(PATHS[key]), f"first_slot={first_slot}; ref_bus_muted_no_master={ref_ok}; source_muted_no_master={source_ok}")

    for key, label in [("v04_lufs", "20-second v04 LUFS package"), ("fullsong_lufs", "full-song v04 draft LUFS package")]:
        package, error = load_json(root, PATHS[key])
        if error:
            add_item(items, key, f"{label}: safe/loud target rows pass.", "MISSING", str(PATHS[key]), error)
            continue
        ok, notes = lufs_targets_pass(package)
        add_item(items, key, f"{label}: safe/loud target rows pass.", "PASS" if ok else "MISSING", str(PATHS[key]), notes)

    review, error = load_json(root, PATHS["review_package"])
    if error:
        add_item(items, "review_package", "Build user A/B review ZIP with WAV/MP3 copies, checksums, and target-row evidence.", "MISSING", str(PATHS["review_package"]), error)
        add_item(items, "review_flow_controls", "Package an A/B review player/checklist with exact sequence order, decision commands, and final-gate warnings.", "MISSING", str(PATHS["review_package"]), error)
    else:
        ok, notes = review_package_passes(review)
        add_item(items, "review_package", "Build user A/B review ZIP with WAV/MP3 copies, checksums, and target-row evidence.", "PASS" if ok else "MISSING", str(PATHS["review_package"]), notes)
        flow_ok, flow_notes = review_flow_controls_pass(review)
        add_item(
            items,
            "review_flow_controls",
            "Package an A/B review player/checklist with exact sequence order, decision commands, and final-gate warnings.",
            "PASS" if flow_ok else "MISSING",
            str(PATHS["review_package"]),
            flow_notes,
        )

    user_decision, error = load_json(root, PATHS["user_decision"])
    if error:
        add_item(items, "user_ab_approval", "Record explicit user loudness-matched A/B approval or revision decision.", "BLOCKED", str(PATHS["user_decision"]), error)
    else:
        decision = user_decision.get("decision")
        ready = bool(user_decision.get("ready_for_final_export_prep"))
        if decision in {"approve_v04_20s_then_extend_final", "approve_safe_only"} and ready:
            status = "PASS"
        else:
            status = "BLOCKED"
        add_item(items, "user_ab_approval", "Record explicit user loudness-matched A/B approval or revision decision.", status, str(PATHS["user_decision"]), f"decision={decision}; ready_for_final_export_prep={ready}; blockers={user_decision.get('blockers')}")

    final_delivery, error = load_json(root, PATHS["final_delivery"])
    if error:
        add_item(items, "final_delivery_package", "Create approved-only final WAV/MP3 delivery ZIP and final gate evidence.", "BLOCKED", str(PATHS["final_delivery"]), error)
    else:
        zip_path = Path(str(final_delivery.get("zip_path", "")))
        safe = bool(final_delivery.get("safe_to_claim_final_delivery"))
        status = "PASS" if final_delivery.get("status") == "FINAL_DELIVERY_PACKAGE_READY" and safe and zip_path.exists() else "BLOCKED"
        add_item(items, "final_delivery_package", "Create approved-only final WAV/MP3 delivery ZIP and final gate evidence.", status, str(PATHS["final_delivery"]), f"status={final_delivery.get('status')}; safe_to_claim={safe}; zip_exists={zip_path.exists()}; blockers={final_delivery.get('blockers')}")

    pass_count = sum(1 for item in items if item["status"] == "PASS")
    blocked = [item for item in items if item["status"] == "BLOCKED"]
    missing = [item for item in items if item["status"] == "MISSING"]
    complete = pass_count == len(items)
    if complete:
        status = "GOAL02_COMPLETE_VERIFIED"
    elif blocked:
        status = "GOAL02_INCOMPLETE_BLOCKED_BY_USER_AB_OR_FINAL_DELIVERY"
    else:
        status = "GOAL02_INCOMPLETE_MISSING_EVIDENCE"
    return {
        "schema": "goal02-completion-audit-v1",
        "created_at": now_utc(),
        "root": str(root),
        "status": status,
        "complete": complete,
        "pass_count": pass_count,
        "total_count": len(items),
        "blocked_count": len(blocked),
        "missing_count": len(missing),
        "items": items,
        "claim_policy": "No finished master, reference-match success, or delivery claim unless complete=true.",
    }


def write_report(path: Path, audit: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 Completion Audit",
        "",
        f"- Created UTC: `{audit['created_at']}`",
        f"- Status: `{audit['status']}`",
        f"- Complete: `{audit['complete']}`",
        f"- Pass: `{audit['pass_count']}` / `{audit['total_count']}`",
        f"- Blocked: `{audit['blocked_count']}`",
        f"- Missing: `{audit['missing_count']}`",
        "- Claim policy: `No finished master, reference-match success, or delivery claim unless complete=true.`",
        "",
        "## Requirements",
        "",
        "| id | status | evidence | notes |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["items"]:
        notes = str(item.get("notes", "")).replace("|", "\\|")
        lines.append(f"| `{item['id']}` | `{item['status']}` | `{item['evidence']}` | {notes} |")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
        ]
    )
    if audit["complete"]:
        lines.append("- All audited Goal 02 gates pass.")
    else:
        blocked = [item for item in audit["items"] if item["status"] == "BLOCKED"]
        if blocked:
            lines.extend(f"- `{item['id']}`: {item['requirement']}" for item in blocked)
        else:
            lines.append("- Resolve missing evidence items before approval/final delivery.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    audit = audit_goal02(args.root)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / "goal02_completion_audit.json"
    md_path = args.report_dir / "goal02_completion_audit.md"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(md_path, audit)
    audit["json_path"] = str(json_path)
    audit["report_path"] = str(md_path)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Goal 02 completion requirement by requirement.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()
    audit = run(args)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "complete": audit["complete"],
                "pass_count": audit["pass_count"],
                "total_count": audit["total_count"],
                "blocked_count": audit["blocked_count"],
                "missing_count": audit["missing_count"],
                "report_path": audit["report_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if audit["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
