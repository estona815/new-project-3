from __future__ import annotations

from dataclasses import asdict
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from completion_gate import check_completion_status
from config import load_defaults
from export_audio import ffmpeg_path, run_command
from final_verify import expected_final_name, expected_sample_rate, verify_final_export, write_verification_json
from humanization_rubric import expanded_qc_rubric, render_expanded_qc_rubric, render_style_match_qc
from paths import PROJECT_ROOT
from audio_render_manifest import build_audio_render_manifest, write_audio_render_manifest
from autopilot_qc_report import build_autopilot_qc, write_autopilot_qc_reports
from export_status import derive_render_status
from release_package_builder import build_and_write_release_package
from release_workflow_orchestrator import write_release_workflow_status


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def choose_final_source(project_root: Path = PROJECT_ROOT) -> tuple[Path, str]:
    master_source = project_root / "09_MIX_MASTER" / "final_mix_master.wav"
    logic_source = project_root / "03_LOGIC_PROJECT" / "logic_export.wav"
    fallback_source = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
    if master_source.exists():
        return master_source, "final_mix_master"
    if logic_source.exists():
        return logic_source, "logic_export"
    if fallback_source.exists():
        return fallback_source, "fallback_processed"
    raise FileNotFoundError("No final source found. Expected Logic export or fallback_processed.wav.")


def convert_final_wav(source: Path, destination: Path, export_format: str) -> tuple[list[str], str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = expected_sample_rate(export_format)
    ffmpeg = ffmpeg_path()
    if ffmpeg:
        command = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-ar",
            str(sample_rate),
            "-acodec",
            "pcm_s24le",
            str(destination),
        ]
        result = run_command(command)
        if result.returncode == 0:
            return command, "ffmpeg"

    afconvert = shutil.which("afconvert")
    if afconvert:
        command = [
            afconvert,
            "-f",
            "WAVE",
            "-d",
            f"LEI24@{sample_rate}",
            str(source),
            str(destination),
        ]
        result = run_command(command)
        if result.returncode == 0:
            return command, "afconvert"

    raise RuntimeError("Final WAV export requires ffmpeg or afconvert so the requested 24-bit output can be verified.")


def create_mp3_preview(final_wav: Path, project_root: Path = PROJECT_ROOT) -> tuple[Path | None, str]:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return None, "ffmpeg unavailable; MP3 preview skipped"
    preview_path = project_root / "05_FINAL_WAV" / "final_preview.mp3"
    command = [ffmpeg, "-hide_banner", "-y", "-i", str(final_wav), "-codec:a", "libmp3lame", "-b:a", "192k", str(preview_path)]
    result = run_command(command)
    if result.returncode != 0 or not preview_path.exists() or preview_path.stat().st_size <= 0:
        return None, "MP3 preview failed; final WAV remains valid if verification passed"
    return preview_path, "created with ffmpeg"


def original_filename(metadata: dict[str, Any]) -> str:
    original = metadata.get("original_path")
    return Path(original).name if original else "unknown"


def fmt_bool(value: bool) -> str:
    return "yes" if value else "no"


def build_qc_report(
    input_metadata: dict[str, Any],
    analysis: dict[str, Any],
    verification: dict[str, Any],
    final_path: Path,
    mp3_path: Path | None,
    source_type: str,
    conversion_tool: str,
    mp3_note: str,
    reference_profile: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
    qc_report_exists: bool = True,
) -> str:
    vocal = analysis.get("vocal_like_texture_candidates", [])
    low_end = analysis.get("low_end_excess_candidates", [])
    melody_buried = analysis.get("melody_buried_candidates", [])
    arrangement = analysis.get("arrangement_candidates", {})
    glitches = arrangement.get("ai_random_transition_or_glitch_candidates", [])
    repeated = arrangement.get("repeated_loop_blocks", [])
    warnings = verification.get("warnings", [])
    processing_truth = (
        "fallback stereo processing was used"
        if source_type == "fallback_processed"
        else "mix/master stage output was used"
        if source_type == "final_mix_master"
        else "Logic export source was used"
    )
    brief = (options or {}).get("creative_brief") or {}
    avoid = brief.get("avoid", [])
    length = brief.get("length", {})
    reference_source = (reference_profile or {}).get("source", {})
    web_research = (reference_profile or {}).get("web_reference_research", {})
    reference_support = (
        reference_source.get("support")
        or "audio-informed"
        if reference_source.get("reference_audio_path")
        else "web-informed"
        if web_research.get("sources") and web_research.get("trait_inference_allowed")
        else "web-metadata-only"
        if web_research.get("sources")
        else "text-only"
        if reference_source.get("reference_text") or brief.get("creative_target") or (options or {}).get("creative_target")
        else "not provided"
    )
    brief_section = "\n".join(
        [
            "## Creative Target Review",
            "",
            f"- User creative target: {brief.get('creative_target') or (options or {}).get('creative_target') or reference_source.get('reference_text') or 'not provided'}",
            f"- Priority element: {brief.get('priority') or (options or {}).get('priority') or 'not provided'}",
            f"- avoid list: {', '.join(avoid) if avoid else (options or {}).get('avoid_list') or 'not provided'}",
            f"- target support: {reference_support}",
            f"- vocal direction: {brief.get('vocal_direction') or (options or {}).get('vocal_direction') or 'not provided'}",
            f"- drum/808 direction: {brief.get('drum_808_direction') or (options or {}).get('drum_808_direction') or 'not provided'}",
            f"- master direction: {brief.get('master_direction') or (options or {}).get('master_direction') or 'not provided'}",
            f"- requested length: {length.get('mode') or (options or {}).get('length_mode') or 'not provided'}",
            f"- requested section: {length.get('start') or 'not provided'} to {length.get('end') or 'not provided'}",
            "",
        ]
    )
    report_project_root = final_path.parents[1] if len(final_path.parents) > 1 else PROJECT_ROOT
    master_qc_candidate = (options or {}).get("master_qc_report_path")
    master_qc_report_exists = (
        Path(master_qc_candidate).exists()
        if master_qc_candidate
        else (report_project_root / "09_MIX_MASTER" / "master_qc_report.md").exists()
    )
    expected_completion_ready = bool(
        verification.get("passed", verification.get("ok", False))
        and final_path.exists()
        and qc_report_exists
        and master_qc_report_exists
    )
    style_match = render_style_match_qc(
        reference_profile,
        stereo_only=source_type == "fallback_processed",
        vocal_mode=(options or {}).get("vocal_mode", "suppress"),
        verification=verification,
        options=options or {},
        source_type=source_type,
        completion_gate_complete=expected_completion_ready,
        qc_report_exists=qc_report_exists,
        master_qc_report_exists=bool(master_qc_report_exists),
        enforce_completion=True,
    ) if reference_profile else "## Style Match QC\n\n- reference target profile: not provided\n"
    parsed_reference = (reference_profile or {}).get("parsed_intent", {})
    reference_traits = (reference_profile or {}).get("reference_traits", {})
    copying_policy = (reference_profile or {}).get("copying_policy", {})
    autopilot = (reference_profile or {}).get("commercial_digicore_autopilot") or reference_traits.get("commercial_digicore_autopilot", {})
    autopilot_summary = ""
    if autopilot.get("active"):
        arrangement_defaults = autopilot.get("arrangement_defaults", {})
        mix_targets = autopilot.get("mix_targets", {})
        autopilot_summary = "\n".join(
            [
                "## Commercial Digicore Autopilot QC",
                "",
                f"- active: {str(bool(autopilot.get('active'))).lower()}",
                f"- commercial requested: {str(bool(autopilot.get('commercial_requested'))).lower()}",
                f"- humanize Suno/AI feel requested: {str(bool(autopilot.get('humanize_suno_requested'))).lower()}",
                f"- hook target seconds: {arrangement_defaults.get('target_hook_seconds') or 'not fixed'}",
                f"- variation frequency bars: {arrangement_defaults.get('variation_frequency_bars')}",
                f"- mix target: {mix_targets.get('target')}",
                f"- promise limit: {mix_targets.get('promise_limit')}",
                "- scope: technical readiness, mix clarity, arrangement intentionality, and QC discipline only.",
                "- no chart-level success promise is made.",
                "",
            ]
        )
    reference_summary = "\n".join(
        [
            "## Reference Intent Summary",
            "",
            f"- original phrase: {parsed_reference.get('raw_text') or (reference_profile or {}).get('source', {}).get('reference_text', 'not provided')}",
            f"- target elements: {', '.join(parsed_reference.get('target_elements', [])) or 'not provided'}",
            f"- trait target elements: {', '.join(reference_traits.get('target_elements', [])) or 'not provided'}",
            f"- reference titles: {', '.join(parsed_reference.get('reference_titles', [])) or 'not provided'}",
            f"- priority: {parsed_reference.get('priority', 'not provided')}",
            f"- confidence: {(reference_profile or {}).get('source', {}).get('confidence', 'not provided')}",
            f"- evidence: {'; '.join(reference_traits.get('evidence_summary', [])) or 'not provided'}",
            f"- support class: {reference_source.get('support', reference_support)}",
            f"- web trait inference allowed: {str(bool(web_research.get('trait_inference_allowed'))).lower()}",
            f"- source limitations: {'; '.join(reference_traits.get('source_limitations', []) or web_research.get('source_limitations', [])) or 'not provided'}",
            f"- vocal identity clone allowed: {str(reference_traits.get('vocal', {}).get('identity_clone_allowed', False)).lower()}",
            f"- mono sub required: {str(reference_traits.get('bass_808', {}).get('mono_sub_required', True)).lower()}",
            f"- avoid: {', '.join((reference_profile or {}).get('avoid', [])) or 'not provided'}",
            "- exact copying: not performed or claimed",
            f"- copying policy: {copying_policy.get('report_note', 'No exact copying is performed or claimed.')}",
            f"- exact copy allowed: {str(bool(copying_policy.get('exact_copy_allowed'))).lower()}",
            f"- disallowed actions: {', '.join(copying_policy.get('disallowed_actions', [])) or 'not provided'}",
            "",
        ]
    )
    expanded_rubric = expanded_qc_rubric(
        analysis=analysis,
        verification=verification,
        reference_profile=reference_profile,
        options=options or {},
        source_type=source_type,
        qc_report_exists=qc_report_exists,
        master_qc_report_exists=bool(master_qc_report_exists),
        final_wav_exists=final_path.exists(),
        completion_gate_complete=expected_completion_ready,
    )
    expanded_rubric_text = render_expanded_qc_rubric(expanded_rubric)

    return f"""# QC Report

## 1. Input File
- original filename: {original_filename(input_metadata)}
- copied input path: {input_metadata.get('copied_path', 'unknown')}
- working wav path: {input_metadata.get('working_wav_path', 'unknown')}

## 2. Final Export
- final WAV path: {final_path}
- MP3 preview path: {mp3_path if mp3_path else 'not created'} ({mp3_note})
- sample rate: {verification.get('sample_rate')}
- bit depth: {verification.get('bit_depth')}
- channels: {verification.get('channels')}
- duration: {verification.get('duration_seconds'):.3f}s
- file size: {verification.get('file_size')} bytes

## 3. Completed Processing Summary
- Source used for final export: {source_type}
- Conversion tool used: {conversion_tool}
- What actually happened: {processing_truth}. This report does not claim Logic mixing if fallback was used.
- Final verification passed: {fmt_bool(bool(verification.get('passed')))}

## 4. Melody Preservation
- Main melody centrality is estimated from analysis, not human listening.
- Melody-buried candidate count: {len(melody_buried)}
- Risk: {'melody may still be buried in flagged sections' if melody_buried else 'no strong melody-buried heuristic warning remained in analysis'}
- Fallback processing is broad stereo processing, so it protects melody mainly by conservative gain/fade/EQ choices rather than stem-level remixing.

## 5. Vocal Chop / AI Texture Suppression
- Detected vocal-like heuristic regions: {len(vocal)}
- What was done: stereo-only fallback may apply conservative global EQ/level treatment; no real vocal removal is claimed.
- What remains: fake voice textures may remain because this pipeline has not used stem separation or manual Logic region editing.

## 6. Drum / 808 Balance
- Low-end warning count: {len(low_end)}
- Kick/808 dominance risk: {'review flagged low-end sections manually' if low_end else 'no strong low-end dominance warning from heuristic analysis'}
- Melody coverage risk: {'possible in melody-buried sections' if melody_buried else 'not strongly flagged by current heuristics'}

## 7. Clipping / Loudness
- peak: {verification.get('peak_dbfs'):.3f} dBFS
- RMS: {verification.get('rms_dbfs'):.3f} dBFS
- clipping count: {verification.get('clipping_count')}
- warning if too loud: {'; '.join(warnings) if warnings else 'none'}
- headroom note: final peak should stay around -1.0 dBFS/dBTP approximation or safer.

## 8. AI-Generated Feel Reduction
- Intro cleanup: handled by fallback trim/fade if analysis or mode selected a shortened section.
- Transition smoothing: fallback can smooth edges with fades, but not detailed region crossfades.
- Random glitch/riser candidates: {len(glitches)}
- Repetition candidates: {len(repeated)}

## 9. Remaining Problems
- Single stereo file limits stem-level control.
- Vocal-like texture could not be fully removed without stem separation or manual editing.
- True drum/808 rearrangement requires stems or manual Logic editing.
- Logic automation may be unavailable, partial, or not used.
- This QC does not replace a human listening pass.

## 10. Next Improvement Options
- Provide stems.
- Run stem separation.
- Manual Logic region editing.
- Create 15-sec reels cut.
- Make alternate version with softer drums.
- Make alternate version with stronger 808.
- Master louder after final arrangement is finished.

{brief_section}

{reference_summary}

{autopilot_summary}

{style_match}

{expanded_rubric_text}
"""


def release_package_required(options: dict[str, Any]) -> bool:
    workflow = options.get("workflow")
    return bool(
        options.get("release_ready")
        or options.get("target_deliverable") == "release_package"
        or workflow in {"song_to_release", "sample_to_release", "vocal_to_release", "stems_to_release"}
    )


def release_metadata_from_options(options: dict[str, Any]) -> dict[str, Any]:
    metadata = options.get("release_metadata") if isinstance(options.get("release_metadata"), dict) else {}
    return {
        "title": metadata.get("title") or options.get("metadata_title") or options.get("release_title") or "",
        "artist": metadata.get("artist") or options.get("metadata_artist") or options.get("release_artist") or "",
        "version": metadata.get("version") or options.get("metadata_version") or options.get("release_version") or "",
        "genre": metadata.get("genre") or options.get("metadata_genre") or options.get("release_genre") or options.get("release_profile") or "",
        "language": metadata.get("language") or options.get("metadata_language") or options.get("release_language") or "",
        "explicit": metadata.get("explicit") if metadata.get("explicit") in {True, False} else options.get("metadata_explicit", options.get("explicit")),
        "isrc": metadata.get("isrc") or options.get("isrc") or "",
        "upc": metadata.get("upc") or options.get("upc") or "",
        "copyright_year": metadata.get("copyright_year") or options.get("metadata_copyright_year") or options.get("copyright_year") or "",
        "copyright_owner": metadata.get("copyright_owner") or options.get("metadata_copyright_owner") or options.get("copyright_owner") or "",
        "producer": metadata.get("producer") or options.get("metadata_producer") or options.get("producer") or "",
        "composer": metadata.get("composer") or options.get("metadata_composer") or options.get("composer") or "",
        "lyricist": metadata.get("lyricist") or options.get("metadata_lyricist") or options.get("lyricist") or "",
        "featured_artists": metadata.get("featured_artists") or options.get("featured_artists") or [],
    }


def release_rights_from_options(options: dict[str, Any], production_intent: dict[str, Any] | None = None) -> dict[str, Any]:
    rights = options.get("release_rights") if isinstance(options.get("release_rights"), dict) else {}
    safety = (production_intent or {}).get("safety") or {}
    owned_samples = bool(options.get("owned_samples") or options.get("owned_reference_sample"))
    owned_stems = bool(options.get("owned_stems") or options.get("owned_reference_stems"))
    owned_vocals = bool(options.get("owned_vocals"))
    contains_samples = bool(rights.get("contains_samples", options.get("contains_samples", False)))
    return {
        "contains_samples": contains_samples,
        "all_samples_owned_or_cleared": rights.get("all_samples_owned_or_cleared", True if owned_samples else options.get("all_samples_owned_or_cleared")),
        "source_ownership_confirmed": rights.get("source_ownership_confirmed", True if owned_samples or owned_stems or owned_vocals else options.get("source_ownership_confirmed")),
        "vocal_performer_consent": rights.get("vocal_performer_consent", True if owned_vocals else options.get("vocal_performer_consent")),
        "featured_artist_metadata_complete": rights.get("featured_artist_metadata_complete", options.get("featured_artist_metadata_complete")),
        "explicit_content_flag_set": rights.get("explicit_content_flag_set", options.get("explicit") in {True, False}),
        "exact_copy_risk_unresolved": bool(
            rights.get("exact_copy_risk_unresolved")
            or safety.get("exact_copy_allowed")
            or safety.get("copying_risk") == "high"
        ),
    }


def run_final_export_and_qc(options: dict[str, Any] | None = None, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    resolved_options = options or load_defaults()
    export_format = resolved_options.get("export_format", "wav24_48k")
    length_mode = resolved_options.get("length_mode", "under_2min")
    final_path = project_root / "05_FINAL_WAV" / expected_final_name(export_format)
    source, source_type = choose_final_source(project_root)
    command, conversion_tool = convert_final_wav(source, final_path, export_format)
    mp3_path, mp3_note = create_mp3_preview(final_path, project_root)
    verification = verify_final_export(final_path, export_format, length_mode)
    verification_path = project_root / "06_QC_REPORT" / "final_verification.json"
    write_verification_json(verification, verification_path)

    input_metadata = load_json(project_root / "01_ANALYSIS" / "input_metadata.json")
    analysis = load_json(project_root / "01_ANALYSIS" / "analysis.json")
    reference_profile = load_json(project_root / "08_REFERENCE_MATCH" / "reference_target_profile.json")
    report = build_qc_report(
        input_metadata,
        analysis,
        verification,
        final_path,
        mp3_path,
        source_type,
        conversion_tool,
        mp3_note,
        reference_profile or None,
        resolved_options,
        True,
    )
    report_path = project_root / "06_QC_REPORT" / "qc_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    completion_status = check_completion_status(
        final_wav_path=final_path,
        qc_report_path=report_path,
        requested_format=export_format,
        final_verify_result=verification,
        require_master_qc=True,
        master_qc_report_path=project_root / "09_MIX_MASTER" / "master_qc_report.md",
    )
    render_status = derive_render_status(
        final_wav_exists=final_path.exists(),
        final_wav_verified=bool(verification.get("ok") or verification.get("passed")),
        completion_complete=completion_status.complete,
    )
    render_manifest = build_audio_render_manifest(
        status=render_status,
        source_files=[str(source)],
        rendered_files=[str(final_path), str(mp3_path)] if mp3_path else [str(final_path)],
        final_verify_result=verification,
        qc_report_path=report_path,
        master_qc_report_path=project_root / "09_MIX_MASTER" / "master_qc_report.md",
        completion_gate=completion_status,
    )
    manifest_path = project_root / "06_QC_REPORT" / "audio_render_manifest.json"
    write_audio_render_manifest(manifest_path, render_manifest)
    arrangement_plan = load_json(project_root / "02_EDIT_PLAN" / "arrangement_plan.json")
    mix_master_plan = load_json(project_root / "09_MIX_MASTER" / "mix_master_plan.json")
    sample_analysis = load_json(project_root / "01_ANALYSIS" / "sample_analysis.json")
    vocal_to_code = load_json(project_root / "01_ANALYSIS" / "vocal_to_code.json")
    song_structure = load_json(project_root / "01_ANALYSIS" / "song_structure_analysis.json")
    autopilot_qc = build_autopilot_qc(
        arrangement_plan=arrangement_plan or None,
        mix_master_plan=mix_master_plan or None,
        reference_profile=reference_profile or None,
        sample_analysis=sample_analysis or None,
        vocal_to_code=vocal_to_code or None,
        song_structure=song_structure or None,
        render_manifest=render_manifest,
        completion_gate=asdict(completion_status),
        input_mode=resolved_options.get("mode", "instrumental_beat"),
    )
    autopilot_qc_paths = write_autopilot_qc_reports(project_root, autopilot_qc)
    release_package_paths: dict[str, Path] = {}
    if release_package_required(resolved_options):
        production_intent = load_json(project_root / "02_EDIT_PLAN" / "production_intent.json")
        package_result = build_and_write_release_package(
            project_root,
            final_master_path=final_path,
            requested_format=export_format,
            metadata=release_metadata_from_options(resolved_options),
            rights=release_rights_from_options(resolved_options, production_intent or None),
            optional_deliverables={"mp3_preview": mp3_path},
            artwork_required=bool(resolved_options.get("artwork_required")),
            mix_master=mix_master_plan or None,
            arrangement=autopilot_qc.get("arrangement_qc"),
            reference_profile=reference_profile or None,
            requested_deliverables=(resolved_options.get("release_intent") or {}).get("deliverables_requested", []),
            completion_gate=asdict(completion_status),
            qc_report_path=report_path,
            master_qc_report_path=project_root / "09_MIX_MASTER" / "master_qc_report.md",
            false_claim_risk=(autopilot_qc.get("commercial_readiness_qc") or {}).get("false_claim_risk"),
        )
        release_package_paths = package_result["paths"]
        completion_status = check_completion_status(
            final_wav_path=final_path,
            qc_report_path=report_path,
            requested_format=export_format,
            final_verify_result=verification,
            require_master_qc=True,
            master_qc_report_path=project_root / "09_MIX_MASTER" / "master_qc_report.md",
            require_release_package=True,
            release_package_manifest_path=release_package_paths["manifest"],
            release_qc_report_path=release_package_paths["release_qc_report"],
        )
    render_status = derive_render_status(
        final_wav_exists=final_path.exists(),
        final_wav_verified=bool(verification.get("ok") or verification.get("passed")),
        completion_complete=completion_status.complete,
    )
    render_manifest = build_audio_render_manifest(
        status=render_status,
        source_files=[str(source)],
        rendered_files=[str(final_path), str(mp3_path)] if mp3_path else [str(final_path)],
        final_verify_result=verification,
        qc_report_path=report_path,
        master_qc_report_path=project_root / "09_MIX_MASTER" / "master_qc_report.md",
        completion_gate=completion_status,
    )
    write_audio_render_manifest(manifest_path, render_manifest)
    release_status = write_release_workflow_status(
        project_root=project_root,
        workflow=resolved_options.get("workflow"),
        mode=resolved_options.get("mode"),
        completion_gate=completion_status,
        final_audio_verified=bool(verification.get("ok") or verification.get("passed")),
        release_package_manifest_path=release_package_paths.get("manifest"),
        release_qc_report_path=release_package_paths.get("release_qc_report"),
    )
    return {
        "final_path": final_path,
        "mp3_path": mp3_path,
        "qc_report": report_path,
        "verification": verification,
        "source_type": source_type,
        "conversion_tool": conversion_tool,
        "command": command,
        "completion_gate": completion_status,
        "completion_gate_summary": asdict(completion_status),
        "render_status": render_status,
        "audio_render_manifest": manifest_path,
        "autopilot_qc": autopilot_qc,
        "autopilot_qc_reports": autopilot_qc_paths,
        "release_package": release_package_paths.get("manifest"),
        "release_package_reports": release_package_paths,
        "release_status": release_status["path"],
        "release_status_summary": release_status["status"],
        "complete": completion_status.complete,
    }


def main() -> int:
    result = run_final_export_and_qc()
    print(f"Final WAV: {result['final_path']}")
    print(f"QC report: {result['qc_report']}")
    if result["complete"]:
        print("Final output passed completion gate.")
        return 0
    print("Final output is not complete.")
    for reason in result["completion_gate"].blocking_reasons:
        print(f"- {reason}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
