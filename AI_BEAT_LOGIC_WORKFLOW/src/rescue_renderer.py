from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bad_song_diagnosis import build_bad_song_diagnosis, render_bad_song_diagnosis_markdown
from completion_gate import check_completion_status
from export_audio import verify_wav
from final_verify import verify_final_wav
from lead_melody_generator import write_lead_melody_outputs
from paths import PROJECT_ROOT, ensure_folder_structure
from rescue_arrangement_planner import build_rescue_arrangement_plan, render_rescue_arrangement_plan_markdown
from rescue_mix_chain import build_rescue_mix, read_audio_file, write_wav24
from rescue_qc import build_rescue_qc, render_rescue_qc_markdown
from sample_motif_rebuild import write_sample_motif_rebuild_outputs
from vocal_texture_rescue import write_vocal_texture_rescue_outputs


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    resolved = Path(path).expanduser()
    if not resolved.exists():
        return None
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _sample_key_payload(sample_analysis: dict[str, Any] | None) -> dict[str, Any]:
    tonal = (sample_analysis or {}).get("tonal") or {}
    key = tonal.get("estimated_key") or tonal.get("estimated_tonic_or_pitch_center")
    return {
        "key": key or "F# minor",
        "confidence": tonal.get("confidence", "low"),
    }


def _song_key_bpm(diagnosis: dict[str, Any], sample_analysis: dict[str, Any] | None) -> dict[str, Any]:
    tempo = diagnosis.get("tempo") or {}
    candidates = tempo.get("bpm_candidates") or []
    bpm = candidates[0].get("bpm") if candidates and isinstance(candidates[0], dict) else None
    key = _sample_key_payload(sample_analysis)
    return {
        "bpm": bpm or 148,
        "tempo_bpm": bpm or 148,
        "tempo_confidence": tempo.get("confidence", "low"),
        "bpm_candidates": candidates,
        "key": key["key"],
        "key_confidence": key["confidence"],
    }


def _load_rendered_sample_demo(render_report: dict[str, Any]) -> tuple[Any, int]:
    if not render_report.get("created") or not render_report.get("path"):
        return None, 48_000
    metadata, audio = read_audio_file(render_report["path"])
    return audio, int(metadata["sample_rate"])


def _rendered_files(
    *,
    demo_path: Path,
    final_path: Path,
    render_audio: bool,
    final_mode: bool,
    lead_outputs: dict[str, Any],
    sample_outputs: dict[str, Any] | None,
) -> list[str]:
    files: list[str] = []
    if render_audio and demo_path.exists():
        files.append(str(demo_path))
    if final_mode and final_path.exists():
        files.append(str(final_path))
    for item in (lead_outputs.get("rendered") or {}).values():
        if isinstance(item, dict) and item.get("path"):
            path = Path(item["path"])
            if path.exists():
                files.append(str(path))
    sample_render = (sample_outputs or {}).get("render") or {}
    if sample_render.get("created") and sample_render.get("path"):
        path = Path(sample_render["path"])
        if path.exists():
            files.append(str(path))
    return list(dict.fromkeys(files))


def render_logic_rescue_plan_markdown(
    *,
    arrangement_plan: dict[str, Any],
    lead_plan: dict[str, Any],
    hook_plan: dict[str, Any],
    vocal_texture_plan: dict[str, Any],
    sample_motif_plan: dict[str, Any],
) -> str:
    sections = arrangement_plan.get("sections") or []
    lead_summary = lead_plan.get("hook_motif_summary") or {}
    vocal_actions = vocal_texture_plan.get("actions") or []
    selected_samples = sample_motif_plan.get("selected_samples") or []
    section_usage = sample_motif_plan.get("section_usage") or []
    marker_lines: list[str] = []
    for section in sections:
        start = float(section.get("start_time", section.get("start", 0.0)) or 0.0)
        duration = float(section.get("duration", 0.0) or 0.0)
        marker_lines.append(f"- create marker `{section.get('name', 'section')}` at {start:.1f}s; end {start + duration:.1f}s")
    sample_lines = [
        f"- {item.get('role')}: {item.get('sample_id')} {item.get('start', 0.0)}-{item.get('end', 0.0)}s; {item.get('reason', 'role assignment')}"
        for item in selected_samples
    ] or ["- no owned sample motif selected; create synth/sample-style motif manually if needed"]
    usage_lines = [
        f"- {item.get('section')}: {item.get('sample_role')} / density {item.get('density')}"
        for item in section_usage
    ] or ["- no sample section usage; keep hook identity on generated lead"]
    return "\n".join(
        [
            "# Logic Rescue Plan",
            "",
            "- status: RESCUE_PLAN_READY",
            "- execution: manual Logic Pro plan only",
            "- verified Logic automation success: false",
            "",
            "## Marker Pass",
            *marker_lines,
            "",
            "## Lead / Hook Pass",
            f"- primary lead motif: {lead_summary.get('primary_motif_id', hook_plan.get('main_hook_motif_id', 'lead_A'))}",
            f"- response motif: {hook_plan.get('call_response_motif_id', 'response_B')}",
            f"- hook return strategy: {hook_plan.get('hook_return_strategy', 'repeat the main motif with controlled variation')}",
            "- keep the core melody centered; use width only on support layers",
            "- do not copy exact reference melodies or artist vocal identity",
            "",
            "## Vocal Texture Pass",
            *[
                f"- {action.get('type')}: {action.get('method')} on {action.get('target')}; manual_logic_required={str(bool(action.get('manual_logic_required'))).lower()}"
                for action in vocal_actions
            ],
            "",
            "## Sample / Synth Motif Pass",
            *sample_lines,
            "",
            "## Section Usage",
            *usage_lines,
            "",
            "## Mix Handoff",
            "- start mix/master only after the lead and hook identity survive a mute test",
            "- stereo-only source may be ducked or demoted, but is not stem-level remixing",
            "- no vocal removal, kick replacement, 808 rewrite, drum rewrite, plugin insertion, or Logic automation success is claimed",
            "",
        ]
    )


def render_rescue_qc_report(
    *,
    diagnosis: dict[str, Any],
    arrangement_plan: dict[str, Any],
    lead_plan: dict[str, Any],
    hook_plan: dict[str, Any],
    vocal_texture_plan: dict[str, Any],
    sample_motif_plan: dict[str, Any] | None,
    mix_report: dict[str, Any] | None,
    rendered_files: list[str],
    demo_verification: dict[str, Any] | None,
    final_verification: dict[str, Any] | None,
    completion_gate: Any | None,
    final_mode: bool,
) -> str:
    rescue = diagnosis.get("rescue_decision") or {}
    source_problem = arrangement_plan.get("source_problem") or {}
    mix_only = bool(rescue.get("mix_only_not_enough") or diagnosis.get("MIX_ONLY_NOT_ENOUGH"))
    lead_summary = lead_plan.get("hook_motif_summary") or {}
    bus_reports = (mix_report or {}).get("bus_reports") or {}
    final_lines: list[str] = []
    if final_verification:
        final_lines = [
            "",
            "## Final Verification",
            f"- final WAV verified: {str(bool(final_verification.get('ok'))).lower()}",
            f"- format verified: {str(bool(final_verification.get('format_verified'))).lower()}",
            f"- sample rate: {final_verification.get('sample_rate')}",
            f"- bit depth: {final_verification.get('bit_depth')}",
            f"- peak: {final_verification.get('peak_dbfs')}",
            f"- RMS: {final_verification.get('rms_dbfs')}",
            f"- clipping count: {final_verification.get('clipping_count')}",
        ]
    gate_lines: list[str] = []
    if completion_gate is not None:
        gate_lines = [
            "",
            "## Completion Gate",
            f"- complete: {str(bool(completion_gate.complete)).lower()}",
            f"- blocking reasons: {'; '.join(completion_gate.blocking_reasons) or 'none'}",
        ]
    rendered_file_lines = [f"- {path}" for path in rendered_files] if rendered_files else ["- no audio was rendered; plan only"]
    sample_status = "not available"
    if sample_motif_plan:
        sample_status = (
            "main motif returns in hook"
            if (sample_motif_plan.get("quality_gates") or {}).get("main_motif_returns_in_hook")
            else "sample motif plan needs manual review"
        )
    return "\n".join(
        [
            "# Rescue QC Report",
            "",
            "## Source Problems",
            *[f"- {key}: {str(bool(value)).lower()}" for key, value in source_problem.items()],
            f"- mix_only_not_enough: {str(mix_only).lower()}",
            f"- decision: {diagnosis.get('decision') or ('ARRANGEMENT_REBUILD_REQUIRED' if mix_only else 'MIX_REPAIR_CAN_FOLLOW_RESCUE_PLAN')}",
            "",
            "## Why Mix-Only Was Not Enough",
            (
                "- Mix/master alone is insufficient because lead melody, hook identity, and arrangement coherence were weak."
                if mix_only
                else "- Diagnosis did not require full arrangement rebuild; rescue render still stays conservative."
            ),
            "",
            "## New Lead / Hook Plan",
            f"- lead plan status: {lead_plan.get('status')}",
            f"- hook plan status: {hook_plan.get('status')}",
            f"- primary motif: {lead_summary.get('primary_motif_id', 'lead_A')}",
            f"- repetition with variation: {str(bool((lead_summary.get('repetition') or {}).get('has_repetition'))).lower()} / {str(bool((lead_summary.get('repetition') or {}).get('has_variation'))).lower()}",
            "",
            "## Arrangement Rebuild Summary",
            f"- length mode: {arrangement_plan.get('length_mode')}",
            f"- target duration: {arrangement_plan.get('target_duration_seconds')}s",
            f"- hook appears by: {arrangement_plan.get('hook_appears_by_seconds')}s",
            f"- section count: {len(arrangement_plan.get('sections', []))}",
            "",
            "## Sample Motif Rebuild",
            f"- status: {sample_motif_plan.get('status') if sample_motif_plan else 'not rendered'}",
            f"- quality: {sample_status}",
            "",
            "## What Was Actually Rendered",
            *rendered_file_lines,
            f"- source restructure: {str(bool((bus_reports.get('source_music_bus') or {}).get('restructure_applied'))).lower()}",
            f"- generated lead bus: {str(bool((bus_reports.get('generated_lead_bus') or {}).get('new_lead_hook_rendered'))).lower()}",
            f"- sample motif bus: {str(bool((bus_reports.get('sample_motif_bus') or {}).get('created'))).lower()}",
            f"- vocal texture demotion: {str(bool((bus_reports.get('vocal_texture_bus') or {}).get('created'))).lower()}",
            "",
            "## Manual Logic Required",
            *[f"- {item}" for item in arrangement_plan.get("manual_logic_required", [])],
            "- Fine-tune generated lead register, synth patch, and hook voicing by ear.",
            "- True stem-level vocal cleanup requires stems.",
            "",
            "## Stereo-Only Limitations",
            "- Stereo-only source cannot fully isolate stems.",
            "- No vocal removal is claimed.",
            "- No kick replacement, 808 rewrite, drum rewrite, plugin insertion, or Logic automation success is claimed unless separately verified.",
            "",
            "## Claim Guard",
            f"- stem-level remix claimed: {str(bool(((mix_report or {}).get('claim_guard') or {}).get('stem_level_remix_claimed'))).lower()}",
            f"- vocal removal claimed: {str(bool(((mix_report or {}).get('claim_guard') or {}).get('vocal_removal_claimed'))).lower()}",
            f"- plugin insertion claimed: {str(bool(((mix_report or {}).get('claim_guard') or {}).get('plugin_insertion_claimed'))).lower()}",
            "",
            "## Demo Verification",
            f"- demo created: {str(bool(demo_verification)).lower()}",
            f"- demo peak: {(demo_verification or {}).get('peak_dbfs', 'n/a')}",
            f"- demo clipping count: {(demo_verification or {}).get('clipping_count', 'n/a')}",
            *final_lines,
            *gate_lines,
            "",
            f"- final mode requested: {str(bool(final_mode)).lower()}",
        ]
    )


def run_bad_ai_song_rescue_render(
    input_path: str | Path,
    *,
    project_root: str | Path = PROJECT_ROOT,
    final_mode: bool = False,
    render_audio: bool = True,
    render_generated_lead: bool = True,
    render_sample_motif: bool = True,
    demote_vocal_texture: bool = True,
    sample_folder: str | Path | None = None,
    sample_analysis: dict[str, Any] | None = None,
    sample_analysis_path: str | Path | None = None,
    creative_brief: dict[str, Any] | None = None,
    creative_brief_path: str | Path | None = None,
    style_cluster: str | None = "system_seoul_adjacent",
    length_mode: str | None = "under_2min",
) -> dict[str, Any]:
    root = Path(project_root)
    ensure_folder_structure(root)
    source = Path(input_path).expanduser()
    analysis_dir = root / "01_ANALYSIS"
    edit_dir = root / "02_EDIT_PLAN"
    processed_dir = root / "04_PROCESSED_AUDIO"
    final_dir = root / "05_FINAL_WAV"
    qc_dir = root / "06_QC_REPORT"
    for folder in (analysis_dir, edit_dir, processed_dir, final_dir, qc_dir):
        folder.mkdir(parents=True, exist_ok=True)

    loaded_sample_analysis = sample_analysis or _read_json(sample_analysis_path) or _read_json(analysis_dir / "sample_analysis.json")
    loaded_creative_brief = creative_brief or _read_json(creative_brief_path) or _read_json(edit_dir / "creative_brief.json")

    diagnosis = build_bad_song_diagnosis(source, mode="full_song_stereo")
    diagnosis_json = analysis_dir / "bad_song_diagnosis.json"
    diagnosis_md = analysis_dir / "bad_song_diagnosis.md"
    _write_json(diagnosis_json, diagnosis)
    diagnosis_md.write_text(render_bad_song_diagnosis_markdown(diagnosis), encoding="utf-8")

    arrangement_plan = build_rescue_arrangement_plan(
        bad_song_diagnosis=diagnosis,
        sample_analysis=loaded_sample_analysis,
        creative_brief=loaded_creative_brief,
        style_cluster=style_cluster,
        length_mode=length_mode,
    )
    arrangement_json = edit_dir / "rescue_arrangement_plan.json"
    arrangement_md = edit_dir / "rescue_arrangement_plan.md"
    _write_json(arrangement_json, arrangement_plan)
    arrangement_md.write_text(render_rescue_arrangement_plan_markdown(arrangement_plan), encoding="utf-8")

    song_context = _song_key_bpm(diagnosis, loaded_sample_analysis)
    lead_outputs = write_lead_melody_outputs(
        project_root=root,
        tempo=diagnosis.get("tempo"),
        key={"key": song_context["key"], "confidence": song_context["key_confidence"]},
        style_cluster=style_cluster,
        sample_analysis=loaded_sample_analysis,
        section_plan=arrangement_plan,
        render=render_generated_lead,
    )
    lead_plan = lead_outputs["lead_melody_plan"]
    hook_plan = lead_outputs["hook_identity_plan"]

    vocal_outputs = write_vocal_texture_rescue_outputs(
        project_root=root,
        input_path=source,
        vocal_like_texture_candidates=(diagnosis.get("vocal_texture") or {}).get("candidate_regions", []),
        creative_brief=loaded_creative_brief,
        rescue_diagnosis=diagnosis,
        mode="full_song_stereo",
        process=False,
        new_lead_available=render_generated_lead,
    )
    vocal_plan = vocal_outputs["vocal_texture_rescue_plan"]

    sample_audio = None
    sample_audio_rate = 48_000
    sample_motif_analysis = None if sample_folder else loaded_sample_analysis
    sample_outputs = write_sample_motif_rebuild_outputs(
        project_root=root,
        sample_folder=sample_folder,
        sample_analysis=sample_motif_analysis,
        song_key_bpm=song_context,
        rescue_arrangement_plan=arrangement_plan,
        render=bool(render_sample_motif and (sample_folder or loaded_sample_analysis)),
    )
    sample_plan = sample_outputs["sample_motif_rebuild_plan"]
    sample_audio, sample_audio_rate = _load_rendered_sample_demo(sample_outputs.get("render") or {})

    logic_plan_path = edit_dir / "logic_rescue_plan.md"
    logic_plan_path.write_text(
        render_logic_rescue_plan_markdown(
            arrangement_plan=arrangement_plan,
            lead_plan=lead_plan,
            hook_plan=hook_plan,
            vocal_texture_plan=vocal_plan,
            sample_motif_plan=sample_plan,
        ),
        encoding="utf-8",
    )

    demo_path = processed_dir / "rescue_demo.wav"
    final_path = final_dir / "final_bad_ai_song_rescue_24bit_48k.wav"
    qc_path = qc_dir / "rescue_qc_report.md"
    mix_report: dict[str, Any] | None = None
    demo_verification: dict[str, Any] | None = None
    final_verification: dict[str, Any] | None = None
    completion_gate = None
    rescue_qc: dict[str, Any] | None = None

    if render_audio:
        metadata, source_audio = read_audio_file(source)
        mix_report = build_rescue_mix(
            source_audio=source_audio,
            source_sample_rate=int(metadata["sample_rate"]),
            arrangement_plan=arrangement_plan,
            lead_plan=lead_plan if render_generated_lead else None,
            sample_motif_audio=sample_audio,
            sample_motif_sample_rate=sample_audio_rate,
            vocal_texture_plan=vocal_plan if demote_vocal_texture else None,
            final_mode=final_mode,
        )
        write_wav24(demo_path, mix_report["audio"], mix_report["sample_rate"])
        demo_verification = verify_wav(demo_path)
        if final_mode:
            write_wav24(final_path, mix_report["audio"], mix_report["sample_rate"])
            final_verification = verify_final_wav(final_path, "wav24_48k")

    rendered_files = _rendered_files(
        demo_path=demo_path,
        final_path=final_path,
        render_audio=render_audio,
        final_mode=final_mode,
        lead_outputs=lead_outputs,
        sample_outputs=sample_outputs,
    )
    detailed_report = render_rescue_qc_report(
        diagnosis=diagnosis,
        arrangement_plan=arrangement_plan,
        lead_plan=lead_plan,
        hook_plan=hook_plan,
        vocal_texture_plan=vocal_plan,
        sample_motif_plan=sample_plan,
        mix_report=mix_report,
        rendered_files=rendered_files,
        demo_verification=demo_verification,
        final_verification=final_verification,
        completion_gate=None,
        final_mode=final_mode,
    )
    rescue_qc = build_rescue_qc(
        diagnosis=diagnosis,
        arrangement_plan=arrangement_plan,
        lead_plan=lead_plan,
        hook_plan=hook_plan,
        vocal_texture_plan=vocal_plan,
        sample_motif_plan=sample_plan,
        mix_report=mix_report,
        demo_verification=demo_verification,
        final_verification=final_verification,
        completion_gate=None,
        qc_report_exists=True,
        demo_wav_path=demo_path,
        final_wav_path=final_path if final_mode else None,
    )
    report = render_rescue_qc_markdown(rescue_qc, rendered_files=rendered_files) + "\n\n---\n\n" + detailed_report
    qc_path.write_text(report, encoding="utf-8")
    _write_json(qc_dir / "rescue_qc_score.json", rescue_qc)

    if final_mode:
        completion_gate = check_completion_status(
            final_wav_path=final_path,
            qc_report_path=qc_path,
            requested_format="wav24_48k",
            final_verify_result=final_verification,
        )
        detailed_report = render_rescue_qc_report(
            diagnosis=diagnosis,
            arrangement_plan=arrangement_plan,
            lead_plan=lead_plan,
            hook_plan=hook_plan,
            vocal_texture_plan=vocal_plan,
            sample_motif_plan=sample_plan,
            mix_report=mix_report,
            rendered_files=rendered_files,
            demo_verification=demo_verification,
            final_verification=final_verification,
            completion_gate=completion_gate,
            final_mode=final_mode,
        )
        rescue_qc = build_rescue_qc(
            diagnosis=diagnosis,
            arrangement_plan=arrangement_plan,
            lead_plan=lead_plan,
            hook_plan=hook_plan,
            vocal_texture_plan=vocal_plan,
            sample_motif_plan=sample_plan,
            mix_report=mix_report,
            demo_verification=demo_verification,
            final_verification=final_verification,
            completion_gate=completion_gate,
            qc_report_exists=True,
            demo_wav_path=demo_path,
            final_wav_path=final_path,
        )
        report = render_rescue_qc_markdown(rescue_qc, rendered_files=rendered_files) + "\n\n---\n\n" + detailed_report
        qc_path.write_text(report, encoding="utf-8")
        _write_json(qc_dir / "rescue_qc_score.json", rescue_qc)

    if not render_audio:
        status = "RESCUE_PLAN_READY"
    elif final_mode:
        status = "COMPLETE" if completion_gate and completion_gate.complete and rescue_qc and rescue_qc.get("verdict") == "FINAL_RESCUE_PASS" else "FINAL_RENDER_NEEDS_QC"
    else:
        status = "DEMO_RENDERED_NOT_COMPLETE"

    return {
        "schema_version": "bad_ai_song_rescue_render.v1",
        "status": status,
        "complete": status == "COMPLETE",
        "paths": {
            "bad_song_diagnosis_json": diagnosis_json,
            "bad_song_diagnosis_md": diagnosis_md,
            "rescue_arrangement_plan_json": arrangement_json,
            "rescue_arrangement_plan_md": arrangement_md,
            "lead_melody_plan": lead_outputs["paths"]["lead_melody_plan"],
            "hook_identity_plan": lead_outputs["paths"]["hook_identity_plan"],
            "vocal_texture_rescue_plan": vocal_outputs["paths"]["vocal_texture_rescue_plan"],
            "sample_motif_rebuild_plan": sample_outputs["paths"]["sample_motif_rebuild_plan"],
            "logic_rescue_plan": logic_plan_path,
            "rescue_demo": demo_path,
            "final_wav": final_path if final_mode else None,
            "rescue_qc_report": qc_path,
        },
        "diagnosis": diagnosis,
        "arrangement_plan": arrangement_plan,
        "lead_melody_plan": lead_plan,
        "hook_identity_plan": hook_plan,
        "vocal_texture_rescue_plan": vocal_plan,
        "sample_motif_rebuild_plan": sample_plan,
        "mix": mix_report,
        "rescue_qc": rescue_qc,
        "demo_verification": demo_verification,
        "final_verification": final_verification,
        "completion_gate": completion_gate,
        "claim_guard": (mix_report or {}).get(
            "claim_guard",
            {
                "stem_level_remix_claimed": False,
                "vocal_removal_claimed": False,
                "plugin_insertion_claimed": False,
            },
        ),
    }
