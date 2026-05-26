from __future__ import annotations

from typing import Any


def _motif_count(sample_analysis: dict[str, Any] | None) -> int:
    return len(((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates", []))


def infer_emotional_direction(rough_request: str = "", style_target: str = "commercial_digicore_hyperpop") -> str:
    text = rough_request.lower()
    if any(item in text for item in ("dark", "어둡", "다크")):
        return "dark"
    if any(item in text for item in ("dream", "몽환", "꿈")):
        return "dreamy"
    if any(item in text for item in ("aggressive", "세게", "빡", "rage")):
        return "aggressive"
    if any(item in text for item in ("playful", "장난", "게임", "game")) or style_target == "system_seoul_adjacent":
        return "playful"
    return "bright_melancholic"


def choose_main_hook_source(
    *,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    rough_request: str = "",
) -> str:
    text = rough_request.lower()
    if _motif_count(sample_analysis) and any(item in text for item in ("샘플", "sample", "motif", "모티프")):
        return "sample_motif"
    if (vocal_to_code or {}).get("phrases") and any(item in text for item in ("보컬", "vocal", "topline", "탑라인")):
        return "vocal_phrase"
    if _motif_count(sample_analysis):
        return "sample_motif"
    if (vocal_to_code or {}).get("phrases"):
        return "vocal_phrase"
    if any(item in text for item in ("신스", "신디", "synth", "lead")):
        return "synth_lead"
    return "new_melody_guide"


def generate_melody_ideas(
    *,
    rough_request: str = "",
    style_target: str = "commercial_digicore_hyperpop",
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    key: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    key_confidence = (key or {}).get("confidence", "low")
    hook_source = choose_main_hook_source(sample_analysis=sample_analysis, vocal_to_code=vocal_to_code, rough_request=rough_request)
    phrase_count = len((vocal_to_code or {}).get("phrases", []))
    return [
        {
            "idea_id": "melody_01",
            "role": "main_hook",
            "source": hook_source,
            "shape": "short bright motif with one memorable landing note",
            "range_hint": "mid-high lead register; avoid masking lead vocal",
            "rhythm_hint": "front-load hook within first 15 seconds when short-form is requested",
            "confidence": "medium" if _motif_count(sample_analysis) or phrase_count else "low",
            "safety_notes": [
                "Create a new melody contour; do not copy exact reference melodies.",
                "If vocal_to_code exists, use phrase placement cues only, not exact transcription.",
            ],
        },
        {
            "idea_id": "melody_02",
            "role": "counter_melody",
            "source": "new_melody_guide",
            "shape": "two-note answer phrase after the vocal or hook call",
            "range_hint": "above bass and below vocal air band",
            "rhythm_hint": "answer on empty beats, not over every vocal syllable",
            "confidence": "low" if key_confidence == "low" else "medium",
            "safety_notes": ["Confirm against the estimated key by ear before committing."],
        },
    ]


def build_melody_idea_guide(**kwargs: Any) -> dict[str, Any]:
    return {
        "schema_version": "melody_idea_guide.v1",
        "status": "COMPOSITION_GUIDE_READY",
        "ideas": generate_melody_ideas(**kwargs),
        "safety": {
            "exact_reference_copy": False,
            "notes": ["Melody ideas are original guide shapes; no exact melody, lyric, or recording copying is allowed."],
        },
        "limitations": ["Guide-only melody plan; no generated audio or MIDI import is claimed."],
    }
