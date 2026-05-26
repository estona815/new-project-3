from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bassline_idea_generator import build_bassline_guide
from chord_progression_engine import build_chord_progression_guide, normalize_key_payload
from drum_pattern_idea_generator import build_drum_pattern_guide
from melody_idea_generator import build_melody_idea_guide, choose_main_hook_source, infer_emotional_direction
from paths import PROJECT_ROOT
from release_intent_resolver import build_release_intent
from topline_guide_generator import build_topline_guide


COMPOSITION_STATUS = "COMPOSITION_GUIDE_READY"
STYLE_ALIASES = {
    "commercial_digicore": "commercial_digicore_hyperpop",
    "commercial_digicore_hyperpop": "commercial_digicore_hyperpop",
    "digicore": "commercial_digicore_hyperpop",
    "hyperpop": "hyperpop",
    "hip_hop": "hip_hop",
    "internet_underground": "internet_underground",
    "system_seoul_adjacent": "system_seoul_adjacent",
    "custom": "custom",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def load_composition_inputs(project_root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    root = Path(project_root)
    return {
        "creative_brief": _read_json(root / "02_EDIT_PLAN" / "creative_brief.json"),
        "production_intent": _read_json(root / "02_EDIT_PLAN" / "production_intent.json"),
        "sample_analysis": _read_json(root / "01_ANALYSIS" / "sample_analysis.json"),
        "vocal_to_code": _read_json(root / "01_ANALYSIS" / "vocal_to_code.json"),
        "song_structure_analysis": _read_json(root / "01_ANALYSIS" / "song_structure_analysis.json"),
    }


def normalize_style_target(style_cluster: str | None, rough_request: str = "") -> str:
    if style_cluster in STYLE_ALIASES:
        return STYLE_ALIASES[str(style_cluster)]
    inferred = build_release_intent(rough_request=rough_request).get("style_cluster")
    return STYLE_ALIASES.get(str(inferred), "commercial_digicore_hyperpop")


def infer_tempo(sample_analysis: dict[str, Any] | None = None, vocal_to_code: dict[str, Any] | None = None) -> dict[str, Any]:
    timing = (sample_analysis or {}).get("timing") or {}
    vocal_global = (vocal_to_code or {}).get("global") or {}
    bpm = timing.get("bpm") or vocal_global.get("estimated_bpm")
    confidence = timing.get("confidence") or vocal_global.get("bpm_confidence") or "low"
    alternatives = timing.get("bpm_candidates") or []
    if bpm and bpm not in alternatives:
        alternatives = [bpm, *alternatives]
    return {
        "bpm": bpm,
        "confidence": confidence if confidence in {"low", "medium", "high"} else "low",
        "alternatives": list(dict.fromkeys(alternatives))[:4],
    }


def infer_key(sample_analysis: dict[str, Any] | None = None, vocal_to_code: dict[str, Any] | None = None) -> dict[str, Any]:
    sample_key = normalize_key_payload(sample_analysis=sample_analysis)
    if sample_key["estimated_key"] or sample_key["alternatives"]:
        return sample_key
    vocal_global = (vocal_to_code or {}).get("global") or {}
    return normalize_key_payload(
        {
            "estimated_key": vocal_global.get("estimated_key"),
            "confidence": vocal_global.get("key_confidence", "low"),
            "alternatives": [],
        }
    )


def infer_energy_curve(rough_request: str = "", song_structure_analysis: dict[str, Any] | None = None) -> str:
    text = rough_request.lower()
    if any(item in text for item in ("drop first", "드랍 먼저", "바로 드랍")):
        return "drop_first"
    if any(item in text for item in ("slow build", "천천히", "빌드")):
        return "slow_build"
    if any(item in text for item in ("verse", "벌스")):
        return "verse_hook"
    if (song_structure_analysis or {}).get("reels_hook_region") or any(item in text for item in ("릴스", "15", "훅", "hook")):
        return "fast_hook"
    return "fast_hook"


def sample_use_allowed(sample_analysis: dict[str, Any] | None = None, creative_brief: dict[str, Any] | None = None) -> bool:
    safety = (sample_analysis or {}).get("sample_usage_safety") or {}
    ownership = (creative_brief or {}).get("ownership_flags") or {}
    return bool(safety.get("direct_sample_use_allowed") or ownership.get("user_confirms_owned_or_licensed"))


def build_composition_guide(
    *,
    rough_request: str = "",
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    song_structure_analysis: dict[str, Any] | None = None,
    style_cluster: str | None = None,
    creative_brief: dict[str, Any] | None = None,
    production_intent: dict[str, Any] | None = None,
    user_owned_sample_or_stem: bool | None = None,
) -> dict[str, Any]:
    resolved_request = rough_request or (creative_brief or {}).get("rough_request") or (creative_brief or {}).get("raw_full_korean_request") or ""
    resolved_style = normalize_style_target(style_cluster or (creative_brief or {}).get("style_cluster") or (production_intent or {}).get("style_cluster"), resolved_request)
    tempo = infer_tempo(sample_analysis, vocal_to_code)
    key = infer_key(sample_analysis, vocal_to_code)
    chord_guide = build_chord_progression_guide(key=key, sample_analysis=sample_analysis, style_target=resolved_style)
    melody_guide = build_melody_idea_guide(
        rough_request=resolved_request,
        style_target=resolved_style,
        sample_analysis=sample_analysis,
        vocal_to_code=vocal_to_code,
        key=key,
    )
    bassline_guide = build_bassline_guide(
        rough_request=resolved_request,
        style_target=resolved_style,
        chord_options=chord_guide["options"],
        key=key,
    )
    drum_guide = build_drum_pattern_guide(
        rough_request=resolved_request,
        style_target=resolved_style,
        sample_analysis=sample_analysis,
        tempo=tempo,
    )
    topline_guide = build_topline_guide(
        rough_request=resolved_request,
        vocal_to_code=vocal_to_code,
        style_target=resolved_style,
        key=key,
    )
    direct_sample_allowed = sample_use_allowed(sample_analysis, creative_brief) or bool(user_owned_sample_or_stem)
    notes = [
        "Guide-only composition stage; no final WAV, MIDI import, Logic automation, or generated audio is claimed.",
        "Do not copy exact reference melodies, progressions, basslines, drum patterns, lyrics, samples, or recordings.",
    ]
    if key["confidence"] == "low":
        notes.append("Key confidence is low; multiple chord options are provided and must be confirmed by ear.")
    if (vocal_to_code or {}).get("phrases"):
        notes.append("Vocal_to_code supports topline placement only and is not exact transcription.")
    if not direct_sample_allowed:
        notes.append("Sample/stem ownership is unconfirmed; direct sample use is blocked and traits must be recreated.")
    return {
        "schema_version": "composition_guide.v1",
        "status": COMPOSITION_STATUS,
        "complete": False,
        "style_target": resolved_style,
        "rough_request": resolved_request,
        "tempo": tempo,
        "key": key,
        "composition_strategy": {
            "main_hook": choose_main_hook_source(
                sample_analysis=sample_analysis,
                vocal_to_code=vocal_to_code,
                rough_request=resolved_request,
            ),
            "emotional_direction": infer_emotional_direction(resolved_request, resolved_style),
            "energy_curve": infer_energy_curve(resolved_request, song_structure_analysis),
        },
        "chord_options": chord_guide["options"],
        "melody_ideas": melody_guide["ideas"],
        "bassline_ideas": bassline_guide["ideas"],
        "drum_ideas": drum_guide["ideas"],
        "topline_ideas": topline_guide["ideas"],
        "child_guides": {
            "chord_progression_guide": chord_guide,
            "melody_idea_guide": melody_guide,
            "bassline_guide": bassline_guide,
            "drum_pattern_guide": drum_guide,
            "topline_guide": topline_guide,
        },
        "safety": {
            "exact_reference_copy": False,
            "voice_clone": False,
            "sample_use_allowed": direct_sample_allowed,
            "notes": notes,
        },
        "manual_logic_required": [
            "Create MIDI regions manually from these guide notes or use a later verified MIDI export step.",
            "Confirm key, chord roots, topline placement, and bass/sub interaction by ear.",
            "Logic import, plugin insertion, automation, and bounce are not claimed until verified.",
        ],
        "limitations": [
            "COMPOSITION_GUIDE_READY is not COMPLETE.",
            "No final WAV is generated by composition autopilot.",
            "MIDI guide content may be generated later, but Logic import must not be claimed without verification.",
        ],
    }


def render_composition_guide_markdown(guide: dict[str, Any]) -> str:
    lines = [
        "# Composition Autopilot Guide",
        "",
        f"- status: {guide['status']}",
        f"- complete: {str(bool(guide.get('complete'))).lower()}",
        f"- style target: {guide['style_target']}",
        f"- rough request: {guide.get('rough_request') or 'not provided'}",
        f"- tempo: {guide['tempo'].get('bpm') or 'unknown'} ({guide['tempo'].get('confidence')})",
        f"- key: {guide['key'].get('estimated_key') or 'unknown'} ({guide['key'].get('confidence')})",
        f"- hook source: {guide['composition_strategy']['main_hook']}",
        f"- energy curve: {guide['composition_strategy']['energy_curve']}",
        "",
        "## Chord Options",
        *[
            f"- {item['name']}: {'-'.join(item.get('roman', []))} ({item.get('confidence')}) - {item.get('feel')}"
            for item in guide.get("chord_options", [])
        ],
        "",
        "## Melody Ideas",
        *[f"- {item['idea_id']}: {item['shape']} ({item['confidence']})" for item in guide.get("melody_ideas", [])],
        "",
        "## Bassline Ideas",
        *[f"- {item['idea_id']}: {item['pattern']} ({item['confidence']})" for item in guide.get("bassline_ideas", [])],
        "",
        "## Drum Ideas",
        *[f"- {item['idea_id']}: {item['feel']} / {item['variation']} ({item['confidence']})" for item in guide.get("drum_ideas", [])],
        "",
        "## Topline Ideas",
        *[f"- {item['idea_id']}: {item['placement']} ({item['confidence']})" for item in guide.get("topline_ideas", [])],
        "",
        "## Safety",
        f"- exact reference copy: {str(bool(guide['safety']['exact_reference_copy'])).lower()}",
        f"- voice clone: {str(bool(guide['safety']['voice_clone'])).lower()}",
        f"- sample use allowed: {str(bool(guide['safety']['sample_use_allowed'])).lower()}",
        *[f"- {item}" for item in guide["safety"].get("notes", [])],
        "",
        "## Manual Logic Required",
        *[f"- {item}" for item in guide.get("manual_logic_required", [])],
        "",
        "## Limitations",
        *[f"- {item}" for item in guide.get("limitations", [])],
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_composition_guide(project_root: str | Path, guide: dict[str, Any]) -> dict[str, Path]:
    root = Path(project_root)
    edit_dir = root / "02_EDIT_PLAN"
    edit_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "composition_guide": edit_dir / "composition_guide.json",
        "composition_markdown": edit_dir / "composition_guide.md",
        "chord_progression_guide": edit_dir / "chord_progression_guide.json",
        "topline_guide": edit_dir / "topline_guide.json",
        "bassline_guide": edit_dir / "bassline_guide.json",
        "drum_pattern_guide": edit_dir / "drum_pattern_guide.json",
    }
    paths["composition_guide"].write_text(json.dumps(guide, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["composition_markdown"].write_text(render_composition_guide_markdown(guide), encoding="utf-8")
    child = guide.get("child_guides", {})
    paths["chord_progression_guide"].write_text(json.dumps(child["chord_progression_guide"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["topline_guide"].write_text(json.dumps(child["topline_guide"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["bassline_guide"].write_text(json.dumps(child["bassline_guide"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["drum_pattern_guide"].write_text(json.dumps(child["drum_pattern_guide"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return paths


def run_composition_autopilot(
    *,
    project_root: str | Path = PROJECT_ROOT,
    rough_request: str = "",
    style_cluster: str | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    song_structure_analysis: dict[str, Any] | None = None,
    user_owned_sample_or_stem: bool | None = None,
) -> dict[str, Any]:
    inputs = load_composition_inputs(project_root)
    guide = build_composition_guide(
        rough_request=rough_request,
        sample_analysis=sample_analysis or inputs.get("sample_analysis"),
        vocal_to_code=vocal_to_code or inputs.get("vocal_to_code"),
        song_structure_analysis=song_structure_analysis or inputs.get("song_structure_analysis"),
        style_cluster=style_cluster,
        creative_brief=inputs.get("creative_brief"),
        production_intent=inputs.get("production_intent"),
        user_owned_sample_or_stem=user_owned_sample_or_stem,
    )
    paths = write_composition_guide(project_root, guide)
    return {"guide": guide, "paths": paths, "json_path": str(paths["composition_guide"]), "markdown_path": str(paths["composition_markdown"])}
