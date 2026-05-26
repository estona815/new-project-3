from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT
from vocal_analysis import analyze_vocal_inputs, pitch_tool_status
from vocal_chain_planner import build_vocal_chain_plan
from vocal_mix_report import build_mix_session_plan, build_processing_log, build_reference_translation, limitations_for_mode, processing_scope
from vocal_processing import process_vocal_assets


def path_status(path_text: str | None) -> dict[str, Any]:
    if not path_text:
        return {"path": None, "exists": False}
    path = Path(path_text).expanduser()
    return {"path": str(path), "exists": path.exists(), "size": path.stat().st_size if path.exists() else 0}


def run_vocal_mix_master_extension(options: dict[str, Any], project_root: Path = PROJECT_ROOT) -> dict[str, Path]:
    vocal_dir = project_root / "07_VOCAL_PROCESSING"
    ref_dir = project_root / "08_REFERENCE_MATCH"
    mix_dir = project_root / "09_MIX_MASTER"
    for folder in (vocal_dir, ref_dir, mix_dir):
        folder.mkdir(parents=True, exist_ok=True)

    pitch_available, pitch_note = pitch_tool_status()
    vocal_analysis = analyze_vocal_inputs(options)
    vocal_analysis = {
        **vocal_analysis,
        "mode": options.get("mode", "instrumental_beat"),
        "processing_scope": processing_scope(options),
        "declared_files": {
            "vocal_file": path_status(options.get("vocal_file")),
            "beat_file": path_status(options.get("beat_file")),
            "lead_vocal_file": path_status(options.get("lead_vocal_file")),
            "adlib_file": path_status(options.get("adlib_file")),
            "backing_vocal_file": path_status(options.get("backing_vocal_file")),
        },
        "pitch_tool_available": pitch_available,
        "pitch_tool_note": pitch_note,
        "limitations": limitations_for_mode(options),
    }
    processing_result = process_vocal_assets(options, vocal_analysis, project_root)
    reference_analysis = {
        "reference_audio": path_status(options.get("reference_audio")),
        "reference_text": options.get("reference_text"),
        "copying_policy": "broad target only; no exact reference, artist, or producer clone",
    }
    reference_target = {
        "vocal_style": options.get("vocal_style", "polished"),
        "mix_intensity": options.get("mix_intensity", "standard"),
        "master_loudness": options.get("master_loudness", "master_ready_headroom"),
        "reverb_space": options.get("reverb_space", "plate"),
        "delay_style": options.get("delay_style", "throw_only"),
    }

    paths = {
        "vocal_analysis": vocal_dir / "vocal_analysis.json",
        "vocal_processing_log": vocal_dir / "vocal_processing_log.md",
        "vocal_chain_plan": vocal_dir / "vocal_chain_plan.md",
        "reference_analysis": ref_dir / "reference_analysis.json",
        "reference_target_profile": ref_dir / "reference_target_profile.json",
        "style_translation": ref_dir / "style_translation.md",
        "mix_session_plan": mix_dir / "mix_session_plan.md",
        "master_qc_report": mix_dir / "master_qc_report.md",
    }
    paths["vocal_analysis"].write_text(json.dumps(vocal_analysis, indent=2) + "\n", encoding="utf-8")
    paths["vocal_processing_log"].write_text(
        build_processing_log(options, pitch_available, pitch_note, vocal_analysis, processing_result),
        encoding="utf-8",
    )
    paths["vocal_chain_plan"].write_text(build_vocal_chain_plan(options, vocal_analysis, pitch_available, pitch_note), encoding="utf-8")
    paths["reference_analysis"].write_text(json.dumps(reference_analysis, indent=2) + "\n", encoding="utf-8")
    if not paths["reference_target_profile"].exists():
        paths["reference_target_profile"].write_text(json.dumps(reference_target, indent=2) + "\n", encoding="utf-8")
    if not paths["style_translation"].exists():
        paths["style_translation"].write_text(build_reference_translation(options), encoding="utf-8")
    paths["mix_session_plan"].write_text(build_mix_session_plan(options, processing_result), encoding="utf-8")
    paths["master_qc_report"].write_text(
        "# Master QC Report\n\n"
        "- status: planning only for mix/master extension\n"
        "- final_mix_master.wav exists: false\n"
        "- Completion must still be gated by final WAV verification and QC in the existing export stage.\n",
        encoding="utf-8",
    )
    return paths
