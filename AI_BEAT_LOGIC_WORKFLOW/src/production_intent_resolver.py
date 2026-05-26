from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from creative_brief import avoid_text_from_brief, reference_text_from_brief
from paths import PROJECT_ROOT
from reference_copying_policy import evaluate_copying_request
from reference_intent_parser import parse_reference_intent
from release_intent_resolver import build_release_intent


RELEASE_READY_LIMITATION = (
    "Release-ready means verified local audio deliverables, metadata/checklist files, safety notes, QC reports, "
    "and clear remaining limitations; it does not guarantee distribution approval or commercial success."
)


def _combined_request(options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") if isinstance(options.get("creative_brief"), dict) else {}
    pieces = [
        options.get("rough_request"),
        options.get("raw_full_korean_request"),
        reference_text_from_brief(brief) if brief else "",
        options.get("creative_target_text"),
        options.get("creative_target"),
        options.get("reference_text"),
        options.get("vocal_fx_text"),
        options.get("drum_bass_request_text"),
        options.get("style_cluster_text"),
    ]
    seen: set[str] = set()
    clean: list[str] = []
    for piece in pieces:
        text = str(piece or "").strip()
        if text and text not in seen:
            clean.append(text)
            seen.add(text)
    return " ".join(clean)


def _intent_stage_actions(parsed: dict[str, Any], mode: str) -> list[str]:
    actions = list(parsed.get("actions", []))
    elements = set(parsed.get("target_elements", []))
    if "arrangement" in elements or "commercial_digicore_autopilot" in actions:
        actions.append("composition_idea_generation")
        actions.append("arrangement_autopilot")
    if {"vocal", "bass_808", "drums", "synth_width"} & elements:
        actions.append("mix_master_autopilot")
    if mode in {"full_song_stereo", "vocal_plus_beat", "stems"}:
        actions.append("audio_analysis")
    return sorted(set(actions))


def _composition_ideas(parsed: dict[str, Any]) -> list[dict[str, str]]:
    explicit = parsed.get("explicit_targets") or {}
    arrangement = explicit.get("arrangement") or {}
    bass = explicit.get("bass_808") or {}
    synth = explicit.get("synth_width") or {}
    vocal = explicit.get("vocal") or {}
    hook = "first_15_seconds" if arrangement.get("target_hook_seconds") == 15 else "early_hook"
    return [
        {
            "name": "hook_first_arrangement",
            "instruction": f"Build a {hook} with the strongest motif, then vary drums/bass every 4-8 bars.",
        },
        {
            "name": "melody_safe_low_end",
            "instruction": f"Keep sub centered, use {bass.get('tone', 'controlled')} 808/bass, and duck or simplify when it masks melody/vocal.",
        },
        {
            "name": "wide_top_mono_bottom",
            "instruction": f"Widen only high-passed synth or upper harmonics; keep low end mono below {synth.get('low_frequency_mono_cutoff_hz', 120)} Hz.",
        },
        {
            "name": "vocal_identity_safe_fx",
            "instruction": f"Use {vocal.get('tuning', 'subtle')} pitch-correction guidance and saturation as production traits only; preserve user voice identity.",
        },
    ]


def resolve_production_intent(options: dict[str, Any]) -> dict[str, Any]:
    brief = options.get("creative_brief") if isinstance(options.get("creative_brief"), dict) else {}
    files = brief.get("input_files", {}) if brief else {}
    request_text = _combined_request(options)
    parsed = parse_reference_intent(
        request_text,
        avoid_text=avoid_text_from_brief(brief) if brief else options.get("avoid_list"),
        priority=options.get("priority"),
        drum_direction=options.get("drum_808_direction") or options.get("drum_808"),
        vocal_direction=options.get("vocal_direction") or options.get("vocal_style"),
        master_direction=options.get("master_direction") or options.get("master_loudness"),
        reference_audio_available=bool(options.get("reference_audio") or files.get("reference_audio")),
    )
    ownership_flags = brief.get("ownership_flags", {}) if brief else {
        "user_owned_sample": bool(options.get("owned_reference_sample")),
        "user_owned_stem": bool(options.get("owned_reference_stems")),
        "user_confirms_owned_or_licensed": bool(options.get("owned_reference_sample") or options.get("owned_reference_stems")),
    }
    copying_policy = evaluate_copying_request(parsed, files, ownership_flags)
    mode = str(options.get("mode") or brief.get("mode") or "instrumental_beat")
    workflow = options.get("workflow")
    release_intent = options.get("release_intent") if isinstance(options.get("release_intent"), dict) else build_release_intent(
        rough_request=request_text,
        workflow=workflow,
        mode=mode,
        release_ready=bool(options.get("release_ready") or brief.get("release_ready")),
        zero_clarification=bool(options.get("zero_clarification") or brief.get("zero_clarification")) if (options.get("zero_clarification") is not None or brief.get("zero_clarification") is not None) else None,
        target_deliverable=options.get("target_deliverable") or brief.get("target_deliverable"),
        release_profile=options.get("release_profile") or brief.get("style_cluster"),
        reference_audio_available=bool(options.get("reference_audio") or files.get("reference_audio")),
    )
    release_requested = bool(
        workflow in {"song_to_mix_master", "song_to_release"}
        or "발매" in request_text
        or "릴리즈" in request_text
        or "release" in request_text.lower()
        or "상업" in request_text
        or release_intent.get("release_ready")
    )
    return {
        "schema_version": "production_intent.v1",
        "raw_request": request_text,
        "workflow": release_intent.get("workflow") or workflow,
        "mode": mode,
        "language": parsed.get("language"),
        "target_elements": parsed.get("target_elements", []),
        "actions": _intent_stage_actions(parsed, mode),
        "composition_ideas": _composition_ideas(parsed),
        "release_ready_requested": release_requested,
        "release_intent": release_intent,
        "style_cluster": release_intent.get("style_cluster"),
        "final_length": release_intent.get("final_length"),
        "priority": release_intent.get("priority"),
        "target_deliverable": release_intent.get("target_deliverable"),
        "deliverables_requested": release_intent.get("deliverables_requested", []),
        "mix_master_target": release_intent.get("mix_master_target"),
        "assumptions": release_intent.get("assumptions", []),
        "release_ready_definition": RELEASE_READY_LIMITATION,
        "copying_policy": copying_policy,
        "safety": {
            "copying_risk": parsed.get("copying_risk"),
            "exact_copy_allowed": bool(copying_policy.get("exact_copy_allowed")),
            "requires_user_owned_source": bool(copying_policy.get("requires_user_owned_source")),
            "vocal_identity_clone_allowed": False,
            "reference_prompt_scope": "high_level_production_targets_only",
            "stereo_only_false_claims_blocked": True,
            "logic_plugin_success_requires_verified_artifacts": True,
            "blocks": release_intent.get("safety_blocks", []),
        },
        "parsed_intent": parsed,
        "limitations": [
            RELEASE_READY_LIMITATION,
            "Stereo-only sources cannot prove stem-level remixing, guaranteed vocal removal, true kick/bass replacement, true drum rewrite, true stem separation, or plugin insertion.",
            "Reference prompts are translated to traits; exact songs, samples, kick sounds, basslines, melodies, lyrics, drum patterns, sound recordings, and living artist vocal identity are not copied.",
        ],
    }


def render_production_intent_markdown(intent: dict[str, Any]) -> str:
    assumption_lines = [f"- {item}" for item in intent.get("assumptions", [])] or ["- none"]
    lines = [
        "# Production Intent",
        "",
        f"- workflow: {intent.get('workflow') or 'not provided'}",
        f"- mode: {intent.get('mode')}",
        f"- release-ready requested: {str(bool(intent.get('release_ready_requested'))).lower()}",
        f"- target deliverable: {intent.get('target_deliverable') or 'not provided'}",
        f"- style cluster: {intent.get('style_cluster') or 'not provided'}",
        f"- priority: {intent.get('priority') or 'not provided'}",
        f"- release-ready meaning: {intent.get('release_ready_definition')}",
        f"- raw request: {intent.get('raw_request') or 'not provided'}",
        "",
        "## Targets",
        f"- elements: {', '.join(intent.get('target_elements', [])) or 'not provided'}",
        f"- actions: {', '.join(intent.get('actions', [])) or 'not provided'}",
        "",
        "## Composition Ideas",
        *[f"- {item['name']}: {item['instruction']}" for item in intent.get("composition_ideas", [])],
        "",
        "## Safety",
        f"- copying risk: {intent.get('safety', {}).get('copying_risk')}",
        f"- exact copy allowed: {str(bool(intent.get('safety', {}).get('exact_copy_allowed'))).lower()}",
        f"- requires owned source: {str(bool(intent.get('safety', {}).get('requires_user_owned_source'))).lower()}",
        f"- vocal identity clone allowed: {str(bool(intent.get('safety', {}).get('vocal_identity_clone_allowed'))).lower()}",
        f"- safety blocks: {'; '.join(intent.get('safety', {}).get('blocks', [])) or 'not provided'}",
        "",
        "## Assumptions",
        *assumption_lines,
        "",
        "## Limitations",
        *[f"- {item}" for item in intent.get("limitations", [])],
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_production_intent_files(
    options: dict[str, Any],
    project_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = Path(project_root)
    output_dir = root / "02_EDIT_PLAN"
    output_dir.mkdir(parents=True, exist_ok=True)
    intent = resolve_production_intent(options)
    json_path = output_dir / "production_intent.json"
    markdown_path = output_dir / "production_intent.md"
    json_path.write_text(json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_production_intent_markdown(intent), encoding="utf-8")
    return {"intent": intent, "json": json_path, "markdown": markdown_path}
