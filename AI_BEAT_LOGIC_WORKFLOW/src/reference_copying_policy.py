from __future__ import annotations

from pathlib import Path
from typing import Any


COPYING_TERMS = ("따와", "가져와", "똑같이", "그대로", "copy", "same exact")
SAMPLING_TARGET_TERMS = ("킥", "kick", "베이스", "808", "드럼", "패턴", "샘플", "sample", "bassline")

DEFAULT_ALLOWED = [
    "high_level_trait_match",
    "broad_audio_analysis",
    "manual_logic_recreate_from_scratch",
]

DEFAULT_DISALLOWED = [
    "download_reference_audio",
    "extract_kick_sample",
    "extract_bassline",
    "copy_exact_pattern",
]

BLOCKED_NOTE = (
    "사용자가 '따와라'라고 요청했지만, 제공/소유 확인된 샘플이 없으므로 정확한 킥/베이스 샘플 복사가 아니라 "
    "질감, 어택, 저역 무게감, saturation, groove density 같은 고수준 특성으로 변환합니다."
)

ALLOWED_NOTE = (
    "사용자가 소유/라이선스/클리어 확인된 로컬 샘플 또는 스템을 제공했으므로, 직접 추출이나 다운로드 없이 "
    "제공 파일 안에서만 보수적인 sample_layering을 계획할 수 있습니다."
)


def _as_text(parsed_intent: dict[str, Any]) -> str:
    pieces = [
        str(parsed_intent.get("raw_text") or ""),
        " ".join(str(item) for item in parsed_intent.get("actions", [])),
        " ".join(str(item) for item in parsed_intent.get("avoid", [])),
    ]
    for request in parsed_intent.get("reference_requests", []):
        pieces.extend(str(request.get(key, "")) for key in ("action", "target_element", "reference_title"))
    return " ".join(pieces).lower()


def _copying_requested(parsed_intent: dict[str, Any]) -> bool:
    traits = parsed_intent.get("production_traits", {})
    if traits.get("user_requested_copying") or parsed_intent.get("copying_risk") in {"medium", "high"}:
        return True
    text = _as_text(parsed_intent)
    return any(term in text for term in COPYING_TERMS) and any(term in text for term in SAMPLING_TARGET_TERMS)


def _iter_file_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        return [str(value)]
    if isinstance(value, dict):
        paths: list[str] = []
        for item in value.values():
            paths.extend(_iter_file_values(item))
        return paths
    if isinstance(value, (list, tuple, set)):
        paths = []
        for item in value:
            paths.extend(_iter_file_values(item))
        return paths
    return []


def _existing_local_files(provided_files: Any) -> list[str]:
    existing: list[str] = []
    for item in _iter_file_values(provided_files):
        if not item:
            continue
        path = Path(item).expanduser()
        if path.exists() and path.is_file():
            existing.append(str(path))
    return existing


def _ownership_confirmed(ownership_flags: dict[str, Any] | None) -> bool:
    flags = ownership_flags or {}
    return any(
        bool(flags.get(key))
        for key in (
            "user_owned_sample",
            "user_owned_stem",
            "owned",
            "licensed",
            "cleared",
            "user_confirms_owned_or_licensed",
            "sample_cleared",
            "stem_cleared",
        )
    )


def evaluate_copying_request(
    parsed_intent: dict[str, Any],
    provided_files: Any,
    ownership_flags: dict[str, Any] | None,
) -> dict[str, Any]:
    copying_requested = _copying_requested(parsed_intent)
    existing_files = _existing_local_files(provided_files)
    ownership_ok = _ownership_confirmed(ownership_flags)
    exact_copy_allowed = bool(copying_requested and existing_files and ownership_ok)

    allowed_actions = list(DEFAULT_ALLOWED)
    disallowed_actions = list(DEFAULT_DISALLOWED)
    if exact_copy_allowed:
        allowed_actions.append("sample_layering")
        reason = "owned/licensed local source was provided and explicitly confirmed"
        report_note = ALLOWED_NOTE
    elif copying_requested:
        reason = "exact copying blocked because no owned/licensed local source was confirmed"
        report_note = BLOCKED_NOTE
    else:
        reason = "no exact copying or sampling request detected"
        report_note = "No exact sample, stem, pattern, bassline, melody, or sound-recording copying request was detected."

    if exact_copy_allowed:
        disallowed_actions = [
            action
            for action in disallowed_actions
            if action not in {"extract_kick_sample", "extract_bassline"}
        ]
    requires_user_owned_source = bool(copying_requested and not exact_copy_allowed)

    return {
        "copying_requested": copying_requested,
        "exact_copy_allowed": exact_copy_allowed,
        "reason": reason,
        "allowed_actions": allowed_actions,
        "disallowed_actions": disallowed_actions,
        "requires_user_owned_source": requires_user_owned_source,
        "report_note": report_note,
        "provided_local_files": existing_files,
        "ownership_confirmed": ownership_ok,
    }
