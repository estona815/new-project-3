from __future__ import annotations

import argparse
import json
from pathlib import Path

from arrangement_autopilot import run_arrangement_autopilot
from audio_analysis import analyze_working_wav
from config import load_defaults
from composition_autopilot import run_composition_autopilot
from creative_brief import write_creative_brief_files
from dependency_capabilities import write_dependency_capabilities
from edit_plan_generator import write_edit_plan
from fallback_processing import run_fallback_processing
from ingest_convert import ConversionError, ingest_and_convert, write_conversion_error
from logic_integration import attempt_logic_project
from logging_utils import print_configuration_summary
from mastering import run_mastering_stage
from mix_master_autopilot import build_mix_master_plan, write_mix_master_plan
from paths import PROJECT_ROOT, ensure_folder_structure
from production_intent_resolver import write_production_intent_files
from qc_report import run_final_export_and_qc
from release_workflow_orchestrator import write_release_workflow_status
from release_status import COMPLETE, DEMO_RENDERED_VERIFIED, FINAL_MASTER_EXPORTED_UNVERIFIED, RESCUE_PLAN_READY, build_release_status, write_release_status
from rescue_renderer import run_bad_ai_song_rescue_render
from sample_analysis import write_sample_analysis
from song_arrangement_analyzer import write_song_structure_analysis
from style_translation import run_reference_targeting
from user_options import options_from_args, options_from_questionnaire
from vocal_mix_master import run_vocal_mix_master_extension
from vocal_to_code import write_vocal_to_code


RELEASE_COMPOSITION_WORKFLOWS = {"bad_ai_song_rescue", "song_to_release", "sample_to_release", "vocal_to_release", "stems_to_release", "plan_only"}


def _load_json(path: str | Path) -> dict:
    resolved = Path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def _text_option(options: object, name: str) -> str:
    value = getattr(options, name, "")
    return value if isinstance(value, str) else ""


def _composition_requested(options: object) -> bool:
    workflow = getattr(options, "workflow", None)
    target_deliverable = getattr(options, "target_deliverable", "demo")
    return bool(
        _text_option(options, "rough_request")
        or getattr(options, "release_ready", False) is True
        or (isinstance(target_deliverable, str) and target_deliverable != "demo")
        or workflow in RELEASE_COMPOSITION_WORKFLOWS
    )


def _write_composition_if_requested(options: object) -> dict | None:
    if not _composition_requested(options):
        return None
    result = run_composition_autopilot(
        project_root=PROJECT_ROOT,
        rough_request=_text_option(options, "raw_full_korean_request") or _text_option(options, "rough_request") or _text_option(options, "creative_target"),
        style_cluster=(getattr(options, "release_intent", None) or {}).get("style_cluster") if getattr(options, "release_intent", None) else None,
        user_owned_sample_or_stem=bool(getattr(options, "owned_reference_sample", False) or getattr(options, "owned_reference_stems", False)),
    )
    print(f"Composition guide written: {result['json_path']}")
    print(f"Composition guide summary written: {result['markdown_path']}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold CLI for the AI_BEAT_LOGIC_WORKFLOW local AI producer autopilot."
    )
    parser.add_argument("--input", help="Path to the source Suno MP3/WAV file.")
    parser.add_argument(
        "--workflow",
        choices=[
            "song_to_mix_master",
            "bad_ai_song_rescue",
            "song_to_release",
            "sample_to_arrangement",
            "sample_to_release",
            "vocal_to_code",
            "vocal_to_release",
            "stems_to_production",
            "stems_to_release",
            "plan_only",
        ],
        help="Autopilot workflow shortcut.",
    )
    parser.add_argument("--rough-request", dest="rough_request", help="Natural-language production request, Korean or English.")
    parser.add_argument("--rescue-mode", choices=["plan", "demo", "final"], help="Bad AI song rescue output depth.")
    parser.add_argument("--generate-lead", choices=["false", "true"], help="Render/create a generated lead motif for bad AI song rescue.")
    parser.add_argument("--demote-vocal-texture", choices=["false", "true"], help="Demote weird vocal-like textures during rescue render.")
    parser.add_argument("--target-length", choices=["reels_15sec", "short_30sec", "under_2min", "full_song"], help="Bad AI song rescue target length.")
    parser.add_argument(
        "--style-cluster",
        choices=["commercial_digicore_hyperpop", "system_seoul_adjacent", "custom"],
        help="Broad bad AI song rescue style cluster; exact copying is prohibited.",
    )
    parser.add_argument("--length-mode", help="Final length mode, e.g. under_2min.")
    parser.add_argument("--vocal-mode", help="Vocal handling mode, e.g. suppress.")
    parser.add_argument("--melody-focus", help="Melody focus level, e.g. front.")
    parser.add_argument("--drum-808", help="Drum/808 intensity, e.g. strong_controlled.")
    parser.add_argument("--export-format", help="Export format, e.g. wav24_48k.")
    parser.add_argument("--save-logic-project", help="Whether to save a Logic project: true or false.")
    parser.add_argument("--mode", choices=["instrumental_beat", "vocal_plus_beat", "full_song_stereo", "stems"], help="Processing mode.")
    parser.add_argument("--vocal-file", help="Separate vocal file for vocal_plus_beat mode.")
    parser.add_argument("--beat-file", help="Separate beat/instrumental file.")
    parser.add_argument("--lead-vocal-file", help="Lead vocal stem file.")
    parser.add_argument("--adlib-file", help="Adlib vocal stem file.")
    parser.add_argument("--backing-vocal-file", help="Backing vocal stem file.")
    parser.add_argument("--stems-folder", help="Folder containing supplied stems.")
    parser.add_argument("--reference-audio", help="Reference audio for broad target analysis.")
    parser.add_argument("--sample-folder", help="Optional owned/cleared sample folder for rescue motif planning.")
    parser.add_argument("--reference-text", help="Text description of reference direction.")
    parser.add_argument("--creative-target-text", help="Full natural-language creative target, including messy Korean production requests.")
    parser.add_argument("--owned-reference-sample", choices=["false", "true"], help="Whether a provided reference sample is owned/licensed/cleared.")
    parser.add_argument("--owned-reference-stems", choices=["false", "true"], help="Whether provided reference stems are owned/licensed/cleared.")
    parser.add_argument("--owned-samples", choices=["false", "true"], help="Whether supplied samples are owned/licensed/cleared for release use.")
    parser.add_argument("--owned-stems", choices=["false", "true"], help="Whether supplied stems are owned/licensed/cleared for release use.")
    parser.add_argument("--owned-vocals", choices=["false", "true"], help="Whether supplied vocals have performer consent and release rights.")
    parser.add_argument("--vocal-fx-text", help="Natural-language vocal FX request, e.g. 오토튠 더, 디카페이터 살짝.")
    parser.add_argument("--drum-bass-request-text", help="Natural-language drum/bass/808 request.")
    parser.add_argument("--style-cluster-text", help="Natural-language style cluster request, e.g. 2hollis, ycs, SYSTEM SEOUL.")
    parser.add_argument("--vocal-style", choices=["natural", "polished", "hyperpop", "digicore", "rap_forward", "airy_pop", "intimate", "aggressive"])
    parser.add_argument("--mix-intensity", choices=["conservative", "standard", "bold"])
    parser.add_argument("--master-loudness", choices=["streaming_safe", "loud_demo", "master_ready_headroom", "release_master"])
    parser.add_argument("--autotune", choices=["none", "subtle", "medium", "hard_effect"])
    parser.add_argument("--deess", choices=["light", "medium", "strong"])
    parser.add_argument("--reverb-space", choices=["dry", "small_room", "plate", "wide_hall", "washed"])
    parser.add_argument("--delay-style", choices=["none", "slap", "quarter", "eighth", "pingpong", "throw_only"])
    parser.add_argument("--creative-target", help="Plain-language creative target for the edit/mix.")
    parser.add_argument("--priority", help="Most important outcome to prioritize.")
    parser.add_argument("--avoid-list", help="Comma-separated or plain-text list of things to avoid.")
    parser.add_argument("--vocal-direction", help="Plain-language vocal direction.")
    parser.add_argument("--drum-808-direction", help="Plain-language drum/808 direction.")
    parser.add_argument("--master-direction", help="Plain-language master/loudness direction.")
    parser.add_argument("--length-start", help="Start time for specific-section length mode.")
    parser.add_argument("--length-end", help="End time for specific-section length mode.")
    parser.add_argument(
        "--arrangement-autopilot",
        action="store_true",
        help="Write a sample/vocal-to-arrangement autopilot plan without claiming rendered audio.",
    )
    parser.add_argument("--arrangement-sample-file", help="Owned/cleared local sample WAV for arrangement autopilot analysis.")
    parser.add_argument("--arrangement-vocal-file", help="Local vocal WAV for guide-only phrase/melody coding.")
    parser.add_argument("--arrangement-genre", help="Arrangement autopilot genre target, e.g. digicore or SYSTEM SEOUL-adjacent.")
    parser.add_argument("--release-ready", choices=["false", "true"], help="Whether to run toward release package readiness.")
    parser.add_argument("--zero-clarification", choices=["false", "true"], help="Apply safe commercial defaults without asking follow-up questions.")
    parser.add_argument("--target-deliverable", choices=["demo", "final_master", "release_package"], help="Requested deliverable depth.")
    parser.add_argument(
        "--release-profile",
        choices=["commercial_digicore", "hip_hop", "hyperpop", "internet_underground", "system_seoul_adjacent", "custom"],
        help="Commercial release profile for safe defaults.",
    )
    parser.add_argument("--metadata-title", help="Release metadata title. Leave blank for draft package.")
    parser.add_argument("--metadata-artist", help="Release metadata primary artist. Leave blank for draft package.")
    parser.add_argument("--metadata-version", help="Release metadata version, e.g. single, radio edit, final.")
    parser.add_argument("--metadata-genre", help="Release metadata genre.")
    parser.add_argument("--metadata-language", help="Release metadata language.")
    parser.add_argument("--metadata-explicit", choices=["false", "true"], help="Release metadata explicit-content flag.")
    parser.add_argument("--metadata-isrc", help="Existing ISRC. The workflow never invents one.")
    parser.add_argument("--metadata-upc", help="Existing UPC. The workflow never invents one.")
    parser.add_argument("--metadata-copyright-year", help="Release metadata copyright year.")
    parser.add_argument("--metadata-copyright-owner", help="Release metadata copyright owner.")
    parser.add_argument("--metadata-producer", help="Release metadata producer.")
    parser.add_argument("--metadata-composer", help="Release metadata composer/songwriter.")
    parser.add_argument("--metadata-lyricist", help="Release metadata lyricist.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Ask the expanded setup questions and write 02_EDIT_PLAN/creative_brief.json/md.",
    )
    parser.add_argument(
        "--logic-only",
        action="store_true",
        help="Only check/attempt optional Logic Pro project automation and write status.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    ensure_folder_structure()
    capabilities_path = write_dependency_capabilities()
    print(f"Dependency capabilities written: {capabilities_path}")
    defaults = load_defaults()

    if args.logic_only:
        status = attempt_logic_project()
        print(f"Logic automation status: {status.status}")
        print(status.message)
        print("Status written: 03_LOGIC_PROJECT/logic_automation_status.md")
        return 0 if status.status in {"success", "partial_success", "unavailable"} else 2

    if args.interactive:
        options = options_from_questionnaire(defaults)
    else:
        options = options_from_args(args, defaults)

    if getattr(options, "creative_brief", None):
        write_creative_brief_files(options.creative_brief, PROJECT_ROOT)
    intent_paths = write_production_intent_files(vars(options), PROJECT_ROOT)
    print(f"Production intent written: {intent_paths['json']}")
    release_status = write_release_workflow_status(
        project_root=PROJECT_ROOT,
        workflow=getattr(options, "workflow", None),
        mode=getattr(options, "mode", None),
    )
    print(f"Release workflow status written: {release_status['path']}")

    print_configuration_summary(options)
    workflow = getattr(options, "workflow", None)
    if workflow in {"vocal_to_code", "vocal_to_release"}:
        vocal_source = getattr(options, "vocal_file", None) or getattr(options, "lead_vocal_file", None) or options.input_path
        if not vocal_source:
            print("Vocal-to-code requires --vocal-file or --input.")
            return 2
        try:
            vocal_code_paths = write_vocal_to_code(
                vocal_source,
                mode="separate_vocal",
                requested_pitch_mode=getattr(options, "autotune", "subtle"),
            )
        except (OSError, ValueError) as error:
            print(f"Vocal-to-code analysis failed: {error}")
            return 2
        print(f"Vocal-to-code analysis written: {vocal_code_paths['json']}")
        print(f"Vocal-to-code summary written: {vocal_code_paths['summary']}")
        print(f"Vocal pitch guide written: {vocal_code_paths['pitch_guide']}")
        _write_composition_if_requested(options)
        release_status = write_release_workflow_status(
            project_root=PROJECT_ROOT,
            workflow=workflow,
            mode=getattr(options, "mode", None),
        )
        print(f"Release workflow status written: {release_status['path']}")
        print("VOCAL_CODE_READY")
        print("Vocal guide generation complete. No final WAV or completion token is being claimed.")
        return 0

    if getattr(options, "arrangement_autopilot", False) is True and workflow not in {"song_to_mix_master", "song_to_release"}:
        sample_path = getattr(options, "arrangement_sample_file", None) or options.input_path or getattr(options, "beat_file", None)
        vocal_path = getattr(options, "arrangement_vocal_file", None) or getattr(options, "vocal_file", None) or getattr(options, "lead_vocal_file", None)
        try:
            autopilot = run_arrangement_autopilot(
                project_root=PROJECT_ROOT,
                sample_path=sample_path,
                vocal_path=vocal_path,
                genre=getattr(options, "arrangement_genre", "digicore"),
                request_text=options.reference_text or options.creative_target,
                length_mode=options.length_mode,
            )
        except (OSError, ValueError) as error:
            print(f"Arrangement autopilot failed: {error}")
            return 2
        print(f"Arrangement plan JSON written: {autopilot['json_path']}")
        print(f"Arrangement plan Markdown written: {autopilot['markdown_path']}")
        for name, path in autopilot.get("paths", {}).items():
            if name not in {"json", "markdown"}:
                print(f"Arrangement guide written: {path}")
        if workflow in {"sample_to_arrangement", "sample_to_release", "stems_to_production", "stems_to_release"} or not options.input_path:
            _write_composition_if_requested(options)
            release_status = write_release_workflow_status(
                project_root=PROJECT_ROOT,
                workflow=workflow,
                mode=getattr(options, "mode", None),
            )
            print(f"Release workflow status written: {release_status['path']}")
            print("ARRANGEMENT_PLAN_READY")
            print("Arrangement autopilot planning complete. No final WAV or completion token is being claimed.")
            return 0
    if options.reference_text or options.reference_audio or options.creative_brief:
        reference = run_reference_targeting(vars(options))
        print(f"Reference target profile written: {reference['reference_target_profile']}")
        print(f"Style translation written: {reference['style_translation']}")
    if not options.input_path:
        _write_composition_if_requested(options)
        release_status = write_release_workflow_status(
            project_root=PROJECT_ROOT,
            workflow=workflow,
            mode=getattr(options, "mode", None),
        )
        print(f"Release workflow status written: {release_status['path']}")
        print("Planned settings loaded. No input was provided, so conversion was not attempted.")
        return 0

    try:
        metadata = ingest_and_convert(options.input_path, options.export_format)
    except (ConversionError, FileNotFoundError, ValueError) as error:
        write_conversion_error(str(error))
        print(f"Conversion failed: {error}")
        print("No converted working WAV is being claimed.")
        return 2

    print("Input ingestion and working WAV conversion complete.")
    print(f"Copied input: {metadata.copied_path}")
    print(f"Working WAV: {metadata.working_wav_path}")
    print(f"Conversion tool: {metadata.conversion_tool_used}")
    try:
        sample_analysis_paths = write_sample_analysis(
            options.input_path,
            working_wav_path=metadata.working_wav_path,
            ownership_status="owned" if getattr(options, "owned_reference_sample", False) else "unknown",
        )
        print(f"Sample analysis written: {sample_analysis_paths['json']}")
        print(f"Sample analysis summary written: {sample_analysis_paths['summary']}")
    except (OSError, ValueError) as error:
        print(f"Sample analysis skipped: {error}")
    song_mode = "vocal_song" if getattr(options, "mode", "instrumental_beat") in {"vocal_plus_beat", "full_song_stereo"} else "stems" if getattr(options, "mode", "instrumental_beat") == "stems" else "instrumental"
    try:
        song_structure_paths = write_song_structure_analysis(metadata.working_wav_path, mode=song_mode)
        print(f"Song structure analysis written: {song_structure_paths['json']}")
        print(f"Song structure summary written: {song_structure_paths['summary']}")
    except (OSError, ValueError) as error:
        print(f"Song structure analysis skipped: {error}")
    vocal_code_source = None
    vocal_code_mode = None
    if getattr(options, "mode", "instrumental_beat") in {"vocal_plus_beat", "stems"} and (getattr(options, "lead_vocal_file", None) or getattr(options, "vocal_file", None)):
        vocal_code_source = options.lead_vocal_file or options.vocal_file
        vocal_code_mode = "vocal_plus_beat"
    elif getattr(options, "mode", "instrumental_beat") == "full_song_stereo":
        vocal_code_source = metadata.working_wav_path
        vocal_code_mode = "full_song_stereo"
    if vocal_code_source and vocal_code_mode:
        try:
            vocal_code_paths = write_vocal_to_code(
                vocal_code_source,
                mode=vocal_code_mode,
                requested_pitch_mode=getattr(options, "autotune", "subtle"),
            )
            print(f"Vocal-to-code analysis written: {vocal_code_paths['json']}")
            print(f"Vocal pitch guide written: {vocal_code_paths['pitch_guide']}")
        except (OSError, ValueError) as error:
            print(f"Vocal-to-code analysis skipped: {error}")
    _write_composition_if_requested(options)
    analysis = analyze_working_wav()
    print(f"Analysis written: 01_ANALYSIS/analysis.json")
    print(f"Analysis summary written: 01_ANALYSIS/analysis_summary.md")
    print(f"Analyzed duration: {analysis['metadata']['duration_seconds']:.2f}s")
    if workflow == "bad_ai_song_rescue":
        rescue_mode = getattr(options, "rescue_mode", "plan")
        render_audio = rescue_mode in {"demo", "final"}
        final_mode = rescue_mode == "final"
        rescue = run_bad_ai_song_rescue_render(
            metadata.working_wav_path,
            project_root=PROJECT_ROOT,
            final_mode=final_mode,
            render_audio=render_audio,
            render_generated_lead=bool(getattr(options, "generate_lead", True)),
            render_sample_motif=bool(getattr(options, "sample_folder", None)),
            demote_vocal_texture=bool(getattr(options, "demote_vocal_texture", True)),
            sample_folder=getattr(options, "sample_folder", None),
            creative_brief=getattr(options, "creative_brief", None),
            style_cluster=getattr(options, "style_cluster", "custom"),
            length_mode=getattr(options, "target_length", None) or getattr(options, "length_mode", "under_2min"),
        )
        for name, path in rescue["paths"].items():
            if path:
                print(f"Rescue output written: {name} -> {path}")
        generated = [str(path) for path in rescue["paths"].values() if path]
        final_verified = bool((rescue.get("final_verification") or {}).get("ok"))
        if rescue.get("status") == "COMPLETE":
            release_status_value = COMPLETE
        elif final_mode:
            release_status_value = FINAL_MASTER_EXPORTED_UNVERIFIED
        elif render_audio:
            release_status_value = DEMO_RENDERED_VERIFIED
        else:
            release_status_value = RESCUE_PLAN_READY
        rescue_status = build_release_status(
            workflow="bad_ai_song_rescue",
            status=release_status_value,
            completion_gate=rescue.get("completion_gate") or {"complete": False, "blocking_reasons": ["final rescued WAV was not rendered or verified"]},
            final_audio_verified=final_verified,
            release_package_ready=False,
            blocking_reasons=list((rescue.get("rescue_qc") or {}).get("blocking_reasons", [])),
            generated_deliverables=generated,
            manual_logic_required=["Logic rescue arrangement/export remains manual unless verified artifacts exist"],
            limitations=[
                "No final WAV, Logic automation success, plugin insertion, stem-level remix, vocal removal, kick replacement, 808 rewrite, or drum rewrite is claimed.",
            ],
        )
        status_path = write_release_status(PROJECT_ROOT / "06_QC_REPORT" / "release_status.json", rescue_status)
        print(f"Release status written: {status_path}")
        print(rescue["status"])
        if rescue["status"] == "COMPLETE":
            print("COMPLETE")
            return 0
        if rescue_mode == "plan":
            print("Bad AI song rescue plan is ready. No final WAV or completion token is being claimed.")
            return 0
        if rescue_mode == "demo":
            print("Bad AI song rescue demo is ready. Demo renders are not COMPLETE.")
            return 0
        print("Final bad AI song rescue render did not pass completion gate.")
        return 2
    if workflow == "song_to_mix_master" or getattr(options, "arrangement_autopilot", False) is True:
        sample_path = getattr(options, "arrangement_sample_file", None) or options.input_path or getattr(options, "beat_file", None)
        vocal_path = getattr(options, "arrangement_vocal_file", None) or getattr(options, "vocal_file", None) or getattr(options, "lead_vocal_file", None)
        try:
            autopilot = run_arrangement_autopilot(
                project_root=PROJECT_ROOT,
                sample_path=sample_path,
                vocal_path=vocal_path,
                genre=getattr(options, "arrangement_genre", "digicore"),
                request_text=options.reference_text or options.creative_target,
                length_mode=options.length_mode,
            )
        except (OSError, ValueError) as error:
            print(f"Arrangement autopilot skipped: {error}")
        else:
            print(f"Arrangement plan JSON written: {autopilot['json_path']}")
            print(f"Arrangement plan Markdown written: {autopilot['markdown_path']}")
    write_edit_plan(options=vars(options))
    print("Edit plan written: 02_EDIT_PLAN/edit_plan.md")
    dependency_capabilities = _load_json(capabilities_path)
    arrangement_plan = _load_json(PROJECT_ROOT / "02_EDIT_PLAN" / "arrangement_plan.json")
    vocal_to_code = _load_json(PROJECT_ROOT / "01_ANALYSIS" / "vocal_to_code.json")
    mix_master_plan = build_mix_master_plan(
        input_mode=getattr(options, "mode", "instrumental_beat"),
        style_target="commercial_digicore_hyperpop",
        master_target_mode=getattr(options, "master_loudness", "master_ready_headroom"),
        dependency_capabilities=dependency_capabilities,
        vocal_to_code=vocal_to_code or None,
        arrangement_plan=arrangement_plan or None,
    )
    mix_master_paths = write_mix_master_plan(PROJECT_ROOT, mix_master_plan)
    print(f"Mix/master autopilot plan written: {mix_master_paths['json']}")
    release_status = write_release_workflow_status(
        project_root=PROJECT_ROOT,
        workflow=workflow,
        mode=getattr(options, "mode", None),
    )
    print(f"Release workflow status written: {release_status['path']}")
    extension = run_vocal_mix_master_extension(vars(options))
    print(f"Mode-aware mix/master plan written: {extension['mix_session_plan']}")
    fallback = run_fallback_processing(options=vars(options))
    print(f"Fallback processed WAV written: {fallback['verification']['path']}")
    print("Processing log written: 04_PROCESSED_AUDIO/processing_log.md")
    master = run_mastering_stage(options=vars(options))
    print(f"Mix/master WAV written: {master['output_path']}")
    print(f"Master QC report written: {master['master_qc_report']}")
    final_result = run_final_export_and_qc(options=vars(options))
    print(f"Final WAV written: {final_result['final_path']}")
    print(f"QC report written: {final_result['qc_report']}")
    if final_result.get("release_package"):
        print(f"Release package written: {final_result['release_package']}")
    if final_result.get("release_status"):
        print(f"Release status written: {final_result['release_status']}")
    completion_status = final_result["completion_gate"]
    if completion_status.complete:
        print("COMPLETE")
        return 0
    print("Final output is not complete.")
    for reason in completion_status.blocking_reasons:
        print(f"- {reason}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
