from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT
from reference_copying_policy import evaluate_copying_request
from reference_intent_parser import parse_reference_intent


MODE_ALIASES = {
    "instrumental beat only": "instrumental_beat",
    "instrumental_beat": "instrumental_beat",
    "instrumental beat": "instrumental_beat",
    "vocal + beat": "vocal_plus_beat",
    "vocal_plus_beat": "vocal_plus_beat",
    "vocal plus beat": "vocal_plus_beat",
    "full stereo song": "full_song_stereo",
    "full_song_stereo": "full_song_stereo",
    "stems": "stems",
}

LENGTH_ALIASES = {
    "keep original": "keep_original",
    "keep_original": "keep_original",
    "under 2 minutes": "under_2min",
    "under_2min": "under_2min",
    "15 sec reels": "15sec_reels",
    "15sec_reels": "15sec_reels",
    "30 sec short-form": "30sec_short_form",
    "30sec_short_form": "30sec_short_form",
    "specific section": "specific_section",
    "specific_section": "specific_section",
    "specific_section_only": "specific_section",
}

EXPORT_ALIASES = {
    "wav 24-bit 44.1khz": "wav24_44k",
    "wav24_44k": "wav24_44k",
    "wav 24-bit 48khz": "wav24_48k",
    "wav24_48k": "wav24_48k",
}

VOCAL_DIRECTION_ALIASES = {
    "rap upfront": "rap_forward",
    "hyperpop tuned": "hyperpop",
    "airy pop": "airy_pop",
    "intimate dry": "intimate",
    "aggressive distorted": "aggressive",
}

MASTER_DIRECTION_ALIASES = {
    "master-ready headroom": "master_ready_headroom",
    "master_ready_headroom": "master_ready_headroom",
    "streaming-safe": "streaming_safe",
    "streaming_safe": "streaming_safe",
    "loud demo": "loud_demo",
    "loud_demo": "loud_demo",
}


def normalize_mode(value: str | None) -> str:
    return MODE_ALIASES.get((value or "").strip().lower(), value or "instrumental_beat")


def normalize_length_mode(value: str | None) -> str:
    return LENGTH_ALIASES.get((value or "").strip().lower(), value or "under_2min")


def normalize_export_format(value: str | None) -> str:
    return EXPORT_ALIASES.get((value or "").strip().lower(), value or "wav24_48k")


def normalize_vocal_direction(value: str | None) -> str:
    text = (value or "").strip()
    return VOCAL_DIRECTION_ALIASES.get(text.lower(), text)


def normalize_master_direction(value: str | None) -> str:
    return MASTER_DIRECTION_ALIASES.get((value or "").strip().lower(), value or "master_ready_headroom")


def normalize_drum_808_direction(value: str | None) -> str:
    text = (value or "").strip()
    if text.lower() == "strong controlled":
        return "strong_controlled"
    if text.lower() == "reference-inspired energetic digital drums":
        return "reference_inspired_energetic_digital_drums"
    return text or "strong_controlled"


def split_avoid_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[,/;\n]+", value) if item.strip()]


def combine_request_text(*values: str | None) -> str:
    pieces: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            pieces.append(text)
            seen.add(text)
    return " ".join(pieces)


def build_creative_brief(
    *,
    mode: str,
    main_input: str | None,
    beat_file: str | None,
    lead_vocal_file: str | None,
    adlibs_file: str | None,
    backing_vocal_file: str | None,
    stems_folder: str | None,
    reference_audio: str | None,
    length_mode: str,
    length_start: str | None,
    length_end: str | None,
    creative_target: str,
    priority: str,
    avoid: str | list[str] | None,
    vocal_direction: str,
    drum_808_direction: str,
    master_direction: str,
    export_format: str,
    save_logic_project: bool,
    raw_full_korean_request: str | None = None,
    creative_target_text: str | None = None,
    vocal_fx_text: str | None = None,
    drum_bass_request_text: str | None = None,
    style_cluster_text: str | None = None,
    owned_reference_sample: bool = False,
    owned_reference_stems: bool = False,
    owned_samples: bool = False,
    owned_stems: bool = False,
    owned_vocals: bool = False,
    release_metadata: dict[str, Any] | None = None,
    release_rights: dict[str, Any] | None = None,
    rough_request: str | None = None,
    release_ready: bool = False,
    target_deliverable: str = "demo",
    zero_clarification: bool = False,
    assumptions: list[str] | None = None,
    style_cluster: str = "custom",
    workflow: str = "plan_only",
    safety_blocks: list[str] | None = None,
    manual_logic_required: list[str] | None = None,
    deliverables_requested: list[str] | None = None,
) -> dict[str, Any]:
    full_request = (
        str(raw_full_korean_request).strip()
        if raw_full_korean_request is not None
        else combine_request_text(
            creative_target_text,
            creative_target,
            vocal_fx_text,
            drum_bass_request_text,
            style_cluster_text,
        )
    )
    target_text = creative_target_text or creative_target or full_request
    resolved_rough_request = rough_request or full_request or target_text
    return {
        "mode": normalize_mode(mode),
        "rough_request": resolved_rough_request,
        "release_ready": bool(release_ready),
        "target_deliverable": target_deliverable,
        "zero_clarification": bool(zero_clarification),
        "assumptions": list(assumptions or []),
        "style_cluster": style_cluster,
        "workflow": workflow,
        "safety_blocks": list(safety_blocks or []),
        "manual_logic_required": list(manual_logic_required or []),
        "deliverables_requested": list(deliverables_requested or []),
        "input_files": {
            "main_input": main_input,
            "beat_file": beat_file,
            "lead_vocal_file": lead_vocal_file,
            "adlibs_file": adlibs_file,
            "backing_vocal_file": backing_vocal_file,
            "stems_folder": stems_folder,
            "reference_audio": reference_audio,
        },
        "raw_full_korean_request": full_request,
        "creative_target_text": target_text,
        "vocal_fx_text": vocal_fx_text or "",
        "drum_bass_request_text": drum_bass_request_text or "",
        "style_cluster_text": style_cluster_text or "",
        "reference_audio": reference_audio,
        "owned_reference_sample": bool(owned_reference_sample),
        "owned_reference_stems": bool(owned_reference_stems),
        "owned_samples": bool(owned_samples),
        "owned_stems": bool(owned_stems),
        "owned_vocals": bool(owned_vocals),
        "release_metadata": dict(release_metadata or {}),
        "release_rights": dict(release_rights or {}),
        "ownership_flags": {
            "user_owned_sample": bool(owned_reference_sample or owned_samples),
            "user_owned_stem": bool(owned_reference_stems or owned_stems),
            "user_owned_vocal": bool(owned_vocals),
            "user_confirms_owned_or_licensed": bool(owned_reference_sample or owned_reference_stems or owned_samples or owned_stems or owned_vocals),
        },
        "length": {
            "mode": normalize_length_mode(length_mode),
            "start": length_start or None,
            "end": length_end or None,
        },
        "creative_target": target_text,
        "raw_user_phrase": full_request or target_text,
        "priority": priority,
        "avoid": split_avoid_list(avoid),
        "vocal_direction": normalize_vocal_direction(vocal_direction),
        "drum_808_direction": normalize_drum_808_direction(drum_808_direction),
        "master_direction": normalize_master_direction(master_direction),
        "export_format": normalize_export_format(export_format),
        "save_logic_project": bool(save_logic_project),
    }


def reference_text_from_brief(brief: dict[str, Any]) -> str:
    return brief.get("raw_full_korean_request") or brief.get("creative_target_text") or brief.get("creative_target", "")


def avoid_text_from_brief(brief: dict[str, Any]) -> str:
    return ", ".join(brief.get("avoid", []))


def render_creative_brief_markdown(brief: dict[str, Any]) -> str:
    files = brief.get("input_files", {})
    avoid = brief.get("avoid", [])
    length = brief.get("length", {})
    raw_request = reference_text_from_brief(brief)
    parsed = parse_reference_intent(raw_request, avoid_text=avoid_text_from_brief(brief), reference_audio_available=bool(files.get("reference_audio")))
    copying_policy = evaluate_copying_request(parsed, files, brief.get("ownership_flags", {}))
    confidence = parsed.get("confidence", "low")
    automatic = [
        "text parsing",
        "reference trait planning",
        "copy/sampling policy evaluation",
        "fallback-safe broad processing plan",
    ]
    manual = [
        "Logic listening decisions",
        "plugin insertion unless verified",
        "stem-level drum/bass/vocal edits without stems",
        "exact sample/layer use unless owned/licensed source is provided",
    ]
    lines = [
        "# Creative Brief",
        "",
        f"- mode: {brief.get('mode')}",
        f"- workflow: {brief.get('workflow', 'plan_only')}",
        f"- release ready: {str(bool(brief.get('release_ready'))).lower()}",
        f"- target deliverable: {brief.get('target_deliverable', 'demo')}",
        f"- zero clarification: {str(bool(brief.get('zero_clarification'))).lower()}",
        f"- style cluster: {brief.get('style_cluster', 'custom')}",
        "",
        "## Files",
        f"- main input: {files.get('main_input') or 'not provided'}",
        f"- beat file: {files.get('beat_file') or 'not provided'}",
        f"- lead vocal file: {files.get('lead_vocal_file') or 'not provided'}",
        f"- adlibs file: {files.get('adlibs_file') or 'not provided'}",
        f"- backing vocal file: {files.get('backing_vocal_file') or 'not provided'}",
        f"- stems folder: {files.get('stems_folder') or 'not provided'}",
        f"- reference audio: {files.get('reference_audio') or 'not provided'}",
        "",
        "## Direction",
        f"- raw request: {raw_request or 'not provided'}",
        f"- target feeling: {brief.get('creative_target') or 'not provided'}",
        f"- creative target text: {brief.get('creative_target_text') or 'not provided'}",
        f"- vocal FX text: {brief.get('vocal_fx_text') or 'not provided'}",
        f"- drum/bass request text: {brief.get('drum_bass_request_text') or 'not provided'}",
        f"- style cluster text: {brief.get('style_cluster_text') or 'not provided'}",
        f"- priority: {brief.get('priority') or 'not provided'}",
        f"- avoid list: {', '.join(avoid) if avoid else 'not provided'}",
        f"- vocal direction: {brief.get('vocal_direction') or 'not provided'}",
        f"- drum/808 direction: {brief.get('drum_808_direction') or 'not provided'}",
        f"- master direction: {brief.get('master_direction') or 'not provided'}",
        "",
        "## Delivery",
        f"- length: {length.get('mode')}",
        f"- section start: {length.get('start') or 'not provided'}",
        f"- section end: {length.get('end') or 'not provided'}",
        f"- export: {brief.get('export_format')}",
        f"- Logic project preference: {'save' if brief.get('save_logic_project') else 'skip'}",
        "",
        "## Parsed Interpretation",
        f"- language: {parsed.get('language', 'unknown')}",
        f"- target elements: {', '.join(parsed.get('target_elements', [])) or 'not provided'}",
        f"- actions: {', '.join(parsed.get('actions', [])) or 'not provided'}",
        f"- reference titles: {', '.join(parsed.get('reference_titles', [])) or 'not provided'}",
        f"- reference confidence: {confidence}",
        "",
        "## Copy / Sampling Policy",
        f"- copying requested: {str(bool(copying_policy.get('copying_requested'))).lower()}",
        f"- exact copy allowed: {str(bool(copying_policy.get('exact_copy_allowed'))).lower()}",
        f"- owned reference sample: {str(bool(brief.get('owned_reference_sample'))).lower()}",
        f"- owned reference stems: {str(bool(brief.get('owned_reference_stems'))).lower()}",
        f"- policy note: {copying_policy.get('report_note', 'No exact copying is performed or claimed.')}",
        f"- disallowed actions: {', '.join(copying_policy.get('disallowed_actions', [])) or 'not provided'}",
        "",
        "## Release Intent",
        f"- deliverables requested: {', '.join(brief.get('deliverables_requested', [])) or 'not provided'}",
        f"- assumptions: {'; '.join(brief.get('assumptions', [])) or 'not provided'}",
        f"- safety blocks: {'; '.join(brief.get('safety_blocks', [])) or 'not provided'}",
        f"- manual Logic required: {'; '.join(brief.get('manual_logic_required', [])) or 'not provided'}",
        "",
        "## Automation / Manual Scope",
        f"- what can be applied automatically: {', '.join(automatic)}",
        f"- what requires Logic/manual/stems: {', '.join(manual)}",
        "",
        "## Final Target Summary",
        f"- {raw_request or brief.get('creative_target') or 'Use conservative high-level production targets.'}",
    ]
    if brief.get("creative_target") and not files.get("reference_audio"):
        lines.extend(
            [
                "",
                "## Reference Safety",
                "- Text-only reference requests are treated as low-confidence, high-level production targets.",
                "- No exact bass sound, melody, mix, artist, producer, sample, or recording is inferred without reference audio.",
            ]
        )
    return "\n".join(lines) + "\n"


def write_creative_brief_files(brief: dict[str, Any], project_root: Path = PROJECT_ROOT) -> dict[str, Path]:
    plan_dir = project_root / "02_EDIT_PLAN"
    plan_dir.mkdir(parents=True, exist_ok=True)
    json_path = plan_dir / "creative_brief.json"
    md_path = plan_dir / "creative_brief.md"
    json_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_creative_brief_markdown(brief), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}
