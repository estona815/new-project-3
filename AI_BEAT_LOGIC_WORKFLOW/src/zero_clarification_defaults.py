from __future__ import annotations

from typing import Any


ZERO_CLARIFICATION_TRIGGERS = ("마음대로", "제로 판단", "알아서", "상업 음악 퀄", "상업음악 퀄", "상업 퀄")

SAFE_COMMERCIAL_DEFAULTS = {
    "hook": "hook appears early",
    "melody": "original melody/vibe preserved",
    "vocal": "vocal/melody forward",
    "808": "808 strong but controlled",
    "mono_low_end": "sub/kick/808 mono-centered",
    "synth_width": "synth width on high-passed upper layers",
    "ai_artifacts": "random AI glitch reduced",
    "clipping": "no cheap rage clipping and no clipping in final",
    "master": "streaming_safe unless user says headroom or loud demo",
    "export": "final WAV 24-bit 48k by default",
    "release_package": "release package includes metadata/checklists/QC",
}


def zero_clarification_requested(text: str | None) -> bool:
    normalized = (text or "").lower()
    return any(trigger in normalized for trigger in ZERO_CLARIFICATION_TRIGGERS)


def safe_commercial_assumptions(text: str | None, *, target_deliverable: str = "release_package") -> list[str]:
    assumptions = [
        SAFE_COMMERCIAL_DEFAULTS["hook"],
        SAFE_COMMERCIAL_DEFAULTS["melody"],
        SAFE_COMMERCIAL_DEFAULTS["vocal"],
        SAFE_COMMERCIAL_DEFAULTS["808"],
        SAFE_COMMERCIAL_DEFAULTS["mono_low_end"],
        SAFE_COMMERCIAL_DEFAULTS["synth_width"],
        SAFE_COMMERCIAL_DEFAULTS["ai_artifacts"],
        SAFE_COMMERCIAL_DEFAULTS["clipping"],
    ]
    normalized = (text or "").lower()
    if "headroom" in normalized or "헤드룸" in normalized:
        assumptions.append("master target set to master-ready headroom because headroom was requested")
    elif "loud demo" in normalized or "라우드" in normalized:
        assumptions.append("master target set to loud demo because loud demo was requested")
    else:
        assumptions.append(SAFE_COMMERCIAL_DEFAULTS["master"])
    if target_deliverable in {"final_master", "release_package"}:
        assumptions.append(SAFE_COMMERCIAL_DEFAULTS["export"])
    if target_deliverable == "release_package":
        assumptions.append(SAFE_COMMERCIAL_DEFAULTS["release_package"])
    return assumptions


def apply_zero_clarification_defaults(intent: dict[str, Any]) -> dict[str, Any]:
    text = intent.get("rough_request") or ""
    target = intent.get("target_deliverable") or "release_package"
    assumptions = list(intent.get("assumptions", []))
    if intent.get("zero_clarification") or zero_clarification_requested(text):
        for item in safe_commercial_assumptions(text, target_deliverable=target):
            if item not in assumptions:
                assumptions.append(item)
    return {**intent, "assumptions": assumptions}
