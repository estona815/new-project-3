from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from instrumental_mix_autopilot import build_instrumental_mix_chain
from master_targets import build_master_chain
from mix_targets import commercial_style_notes, default_mix_priorities, normalize_input_mode
from release_mix_master_autopilot import build_release_mix_master_plan
from stem_mix_autopilot import build_stem_mix_plan
from vocal_mix_autopilot import build_vocal_mix_chain


def build_mix_master_plan(
    *,
    input_mode: str = "instrumental_beat",
    style_target: str = "commercial_digicore_hyperpop",
    master_target_mode: str = "master_ready_headroom",
    dependency_capabilities: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    arrangement_plan: dict[str, Any] | None = None,
    final_verify_result: dict[str, Any] | None = None,
    release_ready: bool = False,
    requested_deliverables: list[str] | None = None,
) -> dict[str, Any]:
    mode = normalize_input_mode(input_mode)
    plugins = (dependency_capabilities or {}).get("plugins", {})
    stems_available = mode == "stems"
    pitch_guide = (vocal_to_code or {}).get("pitch_correction_guide")
    vocal_chain = build_vocal_mix_chain(
        input_mode=mode,
        pitch_guide=pitch_guide,
        plugin_capabilities=plugins,
        requested_style=style_target,
    )
    instrumental_chain = build_instrumental_mix_chain(mode, style_target=style_target)
    stem_plan = build_stem_mix_plan(stems_available)
    master_chain = build_master_chain(master_target_mode)
    fallback_possible = _fallback_possible(mode)
    manual_logic_required = _manual_logic_required(mode, vocal_chain, stem_plan)
    plan = {
        "schema_version": "mix_master_plan.v1",
        "input_mode": mode,
        "style_target": style_target,
        "mix_priorities": default_mix_priorities(style_target),
        "commercial_style_target": commercial_style_notes(),
        "vocal_chain": vocal_chain,
        "instrumental_chain": instrumental_chain,
        "stem_chain": stem_plan,
        "drum_808_plan": _drum_808_plan(mode, stems_available),
        "synth_width_plan": _synth_width_plan(),
        "master_chain": master_chain,
        "fallback_possible": fallback_possible,
        "manual_logic_required": manual_logic_required,
        "arrangement_context_available": bool(arrangement_plan),
        "false_claim_guards": {
            "auto_tune_applied": False,
            "decapitator_applied": False,
            "plugin_processing_verified": False,
            "stem_level_remix_claimed": False,
            "master_export_verified": False,
            "completion_claimed": False,
        },
        "limitations": _limitations(mode),
    }
    plan["release_mix_master_plan"] = build_release_mix_master_plan(
        input_mode=mode,
        master_target_mode=master_target_mode,
        release_ready=release_ready,
        requested_deliverables=requested_deliverables,
        dependency_capabilities=dependency_capabilities,
        final_verify_result=final_verify_result,
        final_format="wav24_44k" if master_target_mode == "wav24_44k" else "wav24_48k",
        qc_report_exists=False,
        release_checklist_exists=False,
        isolated_vocal_available=bool(vocal_to_code),
        stems_provided=stems_available,
    )
    return plan


def write_mix_master_plan(project_root: str | Path, plan: dict[str, Any]) -> dict[str, Path]:
    root = Path(project_root)
    output_dir = root / "09_MIX_MASTER"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "mix_master_plan.json"
    markdown_path = output_dir / "mix_master_plan.md"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_mix_master_plan_markdown(plan), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def render_mix_master_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Mix/Master Autopilot Plan",
        "",
        f"- schema: {plan['schema_version']}",
        f"- input mode: {plan['input_mode']}",
        f"- style target: {plan['style_target']}",
        f"- master target: {plan['master_chain']['target_mode']}",
        "",
        "## Priorities",
        *[f"- {item}" for item in plan["mix_priorities"]],
        "",
        "## Manual Logic Required",
        *[f"- {item}" for item in plan["manual_logic_required"]],
        "",
        "## Release Mix/Master",
        f"- final master verified: {str(bool(plan.get('release_mix_master_plan', {}).get('claim_guard', {}).get('final_master_verified'))).lower()}",
        f"- verification source: {plan.get('release_mix_master_plan', {}).get('final_verification_summary', {}).get('source', 'final_verify')}",
        "",
        "## False Claim Guards",
        *[f"- {key}: {str(value).lower()}" for key, value in plan["false_claim_guards"].items()],
        "",
        "## Limitations",
        *[f"- {item}" for item in plan["limitations"]],
    ]
    return "\n".join(lines).rstrip() + "\n"


def _fallback_possible(mode: str) -> list[str]:
    if mode == "sample_arrangement_plan_only":
        return ["plan_only_no_audio_processing"]
    if mode == "stems":
        return ["stem bus balance plan", "manual Logic stem processing", "mastering after verified pre-master"]
    return ["stereo trim/fade", "broad EQ", "gain staging", "conservative saturation", "mastering polish"]


def _manual_logic_required(mode: str, vocal_chain: dict[str, Any], stem_plan: dict[str, Any]) -> list[str]:
    required = [
        "plugin insertion unless verified",
        "automation writing unless verified",
        "final bounce/export verification",
    ]
    if vocal_chain.get("active"):
        required.extend(["pitch correction", "vocal delay throws", "clip gain rides"])
    if mode != "stems":
        required.extend(["true drum rewrite", "true kick/bass replacement", "true stem-level remixing"])
    if stem_plan.get("active"):
        required.append("stem bus balancing decisions by listening")
    return required


def _drum_808_plan(mode: str, stems_available: bool) -> dict[str, Any]:
    return {
        "kick": "short controlled transient; no extracted reference kick unless owned/cleared",
        "808": "mono sub, controlled saturation, movement supports hook",
        "sidechain": "use if melody/vocal masking occurs",
        "direct_control_allowed": stems_available,
        "true_rewrite_requires": "MIDI/stems/manual Logic",
        "false_claim_guard": {"true_kick_bass_replacement_claimed": False},
    }


def _synth_width_plan() -> dict[str, Any]:
    return {
        "upper_width": "allowed on high-passed synth/melody layers",
        "low_end": "mono",
        "phase_policy": "check mono compatibility before export",
        "automation": "widen hooks, narrow verses/bridges when useful",
    }


def _limitations(mode: str) -> list[str]:
    if mode == "stems":
        return ["Stems allow more direct balancing, but plugin processing and bounce/export still require verification."]
    if mode == "sample_arrangement_plan_only":
        return ["Plan-only mode has no audio processing or final WAV claim."]
    return [
        "Stereo-only processing cannot claim stem-level control.",
        "No guaranteed vocal removal, true kick/bass replacement, or true drum rewrite is claimed.",
        "Plugin-applied claims require verified processing artifacts.",
    ]
