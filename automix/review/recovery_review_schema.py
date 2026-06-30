from __future__ import annotations

from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc


ALLOWED_REVIEW_DECISIONS = {
    "needs_review",
    "accepted",
    "accepted_light",
    "rejected",
    "needs_revision",
    "stem_required",
    "manual_cleanup_required",
}

DOWNSTREAM_STAGES = ["pitch", "placement", "premaster", "final_export"]


def default_recovery_review_decision(
    *,
    track_name: str,
    original_track_guid: str = "",
    draft_track_name: str,
    draft_track_guid: str = "",
    reviewer: str = "user",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "automix-recovery-review-decision-v1",
        "track_name": track_name,
        "original_track_guid": original_track_guid,
        "draft_track_name": draft_track_name,
        "draft_track_guid": draft_track_guid,
        "decision": "needs_review",
        "reviewer": reviewer,
        "review_time": None,
        "ab_files_reviewed": False,
        "loudness_matched_reviewed": False,
        "difference_file_reviewed": False,
        "notes": "",
        "warnings_acknowledged": [],
        "allowed_downstream_stages": [],
        "blocked_downstream_stages": list(DOWNSTREAM_STAGES),
        "provisional_acceptance": False,
        "fragile_source": False,
        "warnings": warnings or [],
    }


def downstream_for_decision(
    decision: str,
    *,
    provisional_acceptance: bool = False,
) -> tuple[list[str], list[str], dict[str, Any]]:
    flags = {
        "fragile_source": False,
        "pitch_extra_caution": False,
        "final_export_blocked": True,
    }
    if decision == "accepted":
        allowed = ["placement", "pitch"]
        blocked = ["premaster", "final_export"]
    elif decision == "accepted_light":
        allowed = ["placement", "pitch"]
        blocked = ["premaster", "final_export"]
        flags["fragile_source"] = True
        flags["pitch_extra_caution"] = True
    else:
        allowed = []
        blocked = list(DOWNSTREAM_STAGES)
    if provisional_acceptance:
        flags["final_export_blocked"] = True
        if "final_export" not in blocked:
            blocked.append("final_export")
    return sorted(set(allowed)), sorted(set(blocked)), flags


def validate_review_decision(decision: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    value = str(decision.get("decision", ""))
    if value not in ALLOWED_REVIEW_DECISIONS:
        errors.append("INVALID_REVIEW_DECISION")
    if not decision.get("draft_track_name"):
        errors.append("DRAFT_TRACK_NAME_REQUIRED")
    if value in {"accepted", "accepted_light"} and not decision.get("warnings_acknowledged"):
        errors.append("WARNINGS_NOT_ACKNOWLEDGED")
    return errors


def finalized_review_decision(
    base: dict[str, Any],
    *,
    decision: str,
    reviewer: str = "user",
    notes: str = "",
    warnings_acknowledged: list[str] | None = None,
    ab_files_reviewed: bool = False,
    loudness_matched_reviewed: bool = False,
    difference_file_reviewed: bool = False,
    provisional_acceptance: bool = False,
) -> dict[str, Any]:
    out = dict(base)
    out["decision"] = decision
    out["reviewer"] = reviewer
    out["review_time"] = now_utc()
    out["notes"] = notes
    out["warnings_acknowledged"] = warnings_acknowledged or []
    out["ab_files_reviewed"] = bool(ab_files_reviewed)
    out["loudness_matched_reviewed"] = bool(loudness_matched_reviewed)
    out["difference_file_reviewed"] = bool(difference_file_reviewed)
    out["provisional_acceptance"] = bool(provisional_acceptance)
    allowed, blocked, flags = downstream_for_decision(decision, provisional_acceptance=provisional_acceptance)
    out["allowed_downstream_stages"] = allowed
    out["blocked_downstream_stages"] = blocked
    out.update(flags)
    out["validation_errors"] = validate_review_decision(out)
    return out

