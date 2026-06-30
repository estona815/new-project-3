from __future__ import annotations

from enum import Enum


class StageStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    REQUIRES_STEM = "requires_stem"
    REQUIRES_PLUGIN_MAPPING = "requires_plugin_mapping"
    REQUIRES_APPROVAL = "requires_approval"


TERMINAL_UNSAFE_STATUSES = {
    StageStatus.BLOCKED.value,
    StageStatus.FAILED.value,
    StageStatus.REQUIRES_MANUAL_REVIEW.value,
    StageStatus.REQUIRES_STEM.value,
    StageStatus.REQUIRES_PLUGIN_MAPPING.value,
    StageStatus.REQUIRES_APPROVAL.value,
}


def normalize_status(status: str | StageStatus) -> str:
    value = status.value if isinstance(status, StageStatus) else str(status)
    allowed = {item.value for item in StageStatus}
    if value not in allowed:
        return StageStatus.FAILED.value
    return value
