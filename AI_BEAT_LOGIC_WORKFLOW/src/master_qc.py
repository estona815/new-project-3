from __future__ import annotations

from pathlib import Path
from typing import Any

from audio_analysis import flatten_channels, mono_mix, read_wav_float
from final_verify import expected_sample_rate, verify_final_wav
from humanization_rubric import (
    expanded_qc_rubric,
    korean_request_interpretation_qc,
    render_expanded_qc_rubric,
    render_style_match_qc,
)
from loudness_estimation import estimate_integrated_loudness_dbfs, linear_to_db, rms_db
from vocal_fx_intent import build_vocal_fx_intent
from release_master_targets import release_master_verified


def _clipping_count(samples: list[float]) -> int:
    return sum(1 for sample in samples if abs(sample) >= 0.999969)


def analyze_master_wav(path: Path) -> dict[str, Any]:
    metadata, channels = read_wav_float(path)
    samples = flatten_channels(channels)
    mono = mono_mix(channels)
    peak = max((abs(sample) for sample in samples), default=0.0)
    low_energy = 0.0
    total_energy = 0.0
    if len(mono) > 1:
        for left, right in zip(mono, mono[1:]):
            delta = abs(right - left)
            total_energy += abs(right)
            if delta < 0.01:
                low_energy += abs(right)
    low_ratio = low_energy / total_energy if total_energy > 0 else 0.0
    return {
        "path": str(path),
        "exists": path.exists(),
        "file_size": path.stat().st_size,
        "duration_seconds": metadata["duration_seconds"],
        "sample_rate": metadata["sample_rate"],
        "channels": metadata["channels"],
        "bit_depth": metadata["bit_depth"],
        "peak_dbfs": linear_to_db(peak),
        "rms_dbfs": rms_db(samples),
        "estimated_lufs": estimate_integrated_loudness_dbfs(samples),
        "clipping_count": _clipping_count(samples),
        "low_end_control_ratio": round(low_ratio, 4),
    }


def _render_korean_request_summary(natural_qc: dict[str, Any]) -> list[str]:
    return [
        "",
        "## Korean Request Interpretation QC",
        f"- Raw request: {natural_qc.get('raw_request', 'not provided')}",
        f"- Parsed targets: {', '.join(natural_qc.get('parsed_targets', [])) or 'not provided'}",
        f"- Copying risk: {natural_qc.get('copying_risk', 'none')}",
        f"- Exact-copy blocked or allowed: {natural_qc.get('exact_copy_status', 'blocked')}",
        f"- Ownership/sample status: {natural_qc.get('ownership_sample_status', 'not required')}",
        f"- Reference evidence mode: {natural_qc.get('evidence_mode', 'text_only')}",
        f"- Confidence level: {natural_qc.get('confidence', 'low')}",
        f"- Policy note: {natural_qc.get('copying_policy_note', 'No exact copying is performed or claimed.')}",
    ]


def _build_rendered_master_qc_report(
    final_path: Path,
    report_path: Path,
    options: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> str:
    status = verify_master_completion(final_path.parent.parent, options or {}, final_path, report_path)
    verification = status.get("verification", {})
    if verification:
        verification = {**verification, "passed": status.get("complete"), "warnings": status.get("blocking_reasons", [])}
    rubric = expanded_qc_rubric(
        analysis=analysis or {},
        verification=verification,
        reference_profile=reference_profile,
        options=options or {},
        source_type=(options or {}).get("source_type", "fallback_processed"),
        qc_report_exists=report_path.exists(),
        master_qc_report_exists=report_path.exists(),
        final_wav_exists=final_path.exists(),
        completion_gate_complete=bool(status.get("complete")),
    )
    brief = (options or {}).get("creative_brief") or {}
    avoid = brief.get("avoid", [])
    source = (reference_profile or {}).get("source", {})
    request_text = " ".join(
        str(item)
        for item in (
            (options or {}).get("vocal_fx_request"),
            (options or {}).get("reference_text"),
            (options or {}).get("creative_target"),
            (options or {}).get("vocal_direction"),
            brief.get("creative_target"),
            brief.get("vocal_direction"),
        )
        if item
    )
    vocal_fx = (options or {}).get("vocal_fx_intent") if isinstance((options or {}).get("vocal_fx_intent"), dict) else build_vocal_fx_intent(request_text)
    reference_support = "audio-supported" if source.get("reference_audio_path") else "text-only" if source.get("reference_text") or brief.get("creative_target") else "not provided"
    sections = [
        "# Master QC Report",
        "",
        "## Final WAV",
        f"- path: {final_path}",
        f"- verification passed: {str(bool(verification.get('passed'))).lower()}",
        f"- sample rate: {verification.get('sample_rate', 'unknown')}",
        f"- peak: {verification.get('peak_dbfs', 'unknown')}",
        f"- clipping count: {verification.get('clipping_count', 'unknown')}",
        "",
        "## Creative Target Review",
        f"- User creative target: {brief.get('creative_target') or (options or {}).get('creative_target') or source.get('reference_text') or 'not provided'}",
        f"- Priority element: {brief.get('priority') or (options or {}).get('priority') or 'not provided'}",
        f"- Avoid list: {', '.join(avoid) if avoid else (options or {}).get('avoid_list') or 'not provided'}",
        f"- Target support: {reference_support}",
    ]
    if rubric.get("vocal_context"):
        sections.extend(
            [
                "",
                "## Vocal QC",
                "- Lead vocal intelligibility, vocal tone control, vocal/beat blend, and adlib/backing control are scored below.",
                "- If only stereo processing was used, vocal scores are heuristic and limited.",
                f"- Plugin-aware FX intent: pitch {vocal_fx.get('pitch_correction', {}).get('intensity', 'none')}; saturation {vocal_fx.get('saturation', {}).get('intensity', 'none')}; plugin status {vocal_fx.get('plugin_application', {}).get('status', 'not_requested')}.",
                f"- Plugin claim rule: {vocal_fx.get('plugin_application', {}).get('claim_language', 'do not claim plugin application without verification')}.",
                "- QC must check harshness/sibilance risk when saturation, brightening, or stronger tuning was requested.",
            ]
        )
    if reference_profile:
        sections.extend(_render_korean_request_summary(korean_request_interpretation_qc(reference_profile, options or {})))
    if reference_profile:
        sections.extend(
            [
                "",
                render_style_match_qc(
                    reference_profile,
                    stereo_only=(options or {}).get("source_type", "fallback_processed") == "fallback_processed",
                    vocal_mode=(options or {}).get("vocal_mode", "suppress"),
                    verification=verification,
                    options=options or {},
                    source_type=(options or {}).get("source_type", "fallback_processed"),
                    completion_gate_complete=bool(status.get("complete")),
                    qc_report_exists=report_path.exists(),
                    master_qc_report_exists=report_path.exists(),
                    enforce_completion=True,
                ).rstrip(),
            ]
        )
    sections.extend(["", render_expanded_qc_rubric(rubric)])
    return "\n".join(sections)


def build_master_qc_report(
    options: dict[str, Any] | Path,
    source_path: Path,
    final_path: Path | dict[str, Any],
    final_info: dict[str, Any] | None = None,
    processing_notes: list[str] | dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> str:
    if isinstance(options, Path):
        # Compatibility path for feature/16 tests:
        # build_master_qc_report(final_path, report_path, options, reference_profile, analysis)
        return _build_rendered_master_qc_report(
            options,
            source_path,
            final_path if isinstance(final_path, dict) else {},
            final_info if isinstance(final_info, dict) else None,
            processing_notes if isinstance(processing_notes, dict) else None,
        )
    final_info = final_info or {}
    processing_notes = processing_notes if isinstance(processing_notes, list) else []
    warnings = warnings or []
    reference = options.get("reference_audio") or options.get("reference_text")
    reference_profile = options.get("reference_profile") if isinstance(options.get("reference_profile"), dict) else None
    reference_score = "not evaluated; no reference provided"
    if reference:
        reference_score = "broad target only: 0.50 heuristic placeholder, no exact copying claimed"
    vocal_mode = options.get("vocal_mode", "suppress")
    input_mode = options.get("mode", "instrumental_beat")
    brief = options.get("creative_brief") or {}
    avoid = brief.get("avoid", [])
    master_loudness = options.get("master_loudness", "master_ready_headroom")
    mix_plan = options.get("mix_master_plan") if isinstance(options.get("mix_master_plan"), dict) else None
    autopilot_qc = options.get("autopilot_qc") if isinstance(options.get("autopilot_qc"), dict) else None
    release_status = options.get("release_status") if isinstance(options.get("release_status"), dict) else None
    final_verify_result = options.get("final_verify_result") if isinstance(options.get("final_verify_result"), dict) else {}
    release_master_check = release_master_verified(
        final_verify_result=final_verify_result or {**final_info, "ok": not final_info.get("clipping_count"), "format_verified": final_info.get("bit_depth") == 24},
        qc_report_exists=True,
        release_checklist_exists=bool(options.get("release_checklist_exists")),
        require_release_checklist=options.get("master_loudness") == "release_master",
    )
    loud_demo_warning = ""
    if master_loudness == "loud_demo":
        loud_demo_warning = "\n- loud_demo warning: louder preview with reduced headroom; less master-ready."
    source = (reference_profile or {}).get("source", {})
    traits = (reference_profile or {}).get("reference_traits", {})
    request_text = " ".join(
        str(item)
        for item in (
            options.get("vocal_fx_request"),
            options.get("reference_text"),
            options.get("creative_target"),
            options.get("vocal_direction"),
            brief.get("creative_target"),
            brief.get("vocal_direction"),
        )
        if item
    )
    vocal_fx = options.get("vocal_fx_intent") if isinstance(options.get("vocal_fx_intent"), dict) else build_vocal_fx_intent(request_text)
    reference_support = "audio-supported" if source.get("reference_audio_path") or options.get("reference_audio") else "text-only" if source.get("reference_text") or reference or brief.get("creative_target") else "not provided"
    reference_qc = ""
    natural_qc_section = ""
    if reference_profile:
        natural_qc_section = "\n" + "\n".join(_render_korean_request_summary(korean_request_interpretation_qc(reference_profile, options)))
        reference_qc = "\n" + render_style_match_qc(
            reference_profile,
            stereo_only=options.get("source_type", "fallback_processed") == "fallback_processed",
            vocal_mode=options.get("vocal_mode", "suppress"),
            verification={**final_info, "passed": not final_info.get("clipping_count")},
            options=options,
            source_type=options.get("source_type", "fallback_processed"),
            completion_gate_complete=False,
            qc_report_exists=True,
            master_qc_report_exists=False,
            enforce_completion=True,
        )
    return f"""# Master QC Report

## 1. Input Mode
- input mode: {input_mode}
- vocal mode: {vocal_mode}

## 2. Files Used
- source file: {source_path}
- final mix/master WAV: {final_path}

## 3. Master Target
- target: {master_loudness}{loud_demo_warning}
- mix/master autopilot plan: {mix_plan.get('schema_version') if mix_plan else 'not attached'}
- autopilot QC status: {autopilot_qc.get('status') if autopilot_qc else 'not attached'}
- release workflow status: {release_status.get('status') if release_status else 'not attached'}
- release package ready: {str(bool(release_status.get('release_package_ready'))).lower() if release_status else 'false'}
- release master verified by final_verify/QC: {str(bool(release_master_check.get('verified'))).lower()}
- release master blocking reasons: {'; '.join(release_master_check.get('blocking_reasons', [])) or 'none'}
- commercial success claimed: false
- release scoring scope: local technical/package readiness only; not distributor approval or commercial success
- plan pass is complete: false
- plugin processing verified: {str(bool((mix_plan or {}).get('false_claim_guards', {}).get('plugin_processing_verified'))).lower()}
- stem-level remix claimed: {str(bool((mix_plan or {}).get('false_claim_guards', {}).get('stem_level_remix_claimed'))).lower()}
- creative target: {brief.get('creative_target') or options.get('creative_target') or 'not provided'}
- priority: {brief.get('priority') or options.get('priority') or 'not provided'}
- avoid list: {', '.join(avoid) if avoid else options.get('avoid_list') or 'not provided'}
- master direction: {brief.get('master_direction') or options.get('master_direction') or master_loudness}

## Creative Target Review
- User creative target: {brief.get('creative_target') or options.get('creative_target') or source.get('reference_text') or 'not provided'}
- Priority element: {brief.get('priority') or options.get('priority') or 'not provided'}
- Avoid list: {', '.join(avoid) if avoid else options.get('avoid_list') or 'not provided'}
- Target support: {reference_support}
- Trait target elements: {', '.join(traits.get('target_elements', [])) if traits else 'not provided'}
- Vocal identity clone allowed: {str(traits.get('vocal', {}).get('identity_clone_allowed', False)).lower() if traits else 'false'}
- Mono sub required: {str(traits.get('bass_808', {}).get('mono_sub_required', True)).lower() if traits else 'true'}
- Evidence: {'; '.join(traits.get('evidence_summary', [])) if traits else 'not provided'}
{natural_qc_section}

## 4. Final WAV Info
- sample rate: {final_info.get('sample_rate')}
- channels: {final_info.get('channels')}
- bit depth: {final_info.get('bit_depth')}
- duration: {final_info.get('duration_seconds'):.3f}s
- file size: {final_info.get('file_size')} bytes

## 5. Peak/RMS/LUFS Estimate
- peak: {final_info.get('peak_dbfs'):.3f} dBFS
- RMS: {final_info.get('rms_dbfs'):.3f} dBFS
- estimated LUFS: {final_info.get('estimated_lufs'):.3f}
- note: LUFS is RMS-based approximation, not gated K-weighted measurement.

## 6. Clipping
- clipping count: {final_info.get('clipping_count')}
- clipping status: {'blocked' if final_info.get('clipping_count') else 'clear'}

## 7. Vocal Intelligibility If Vocal Mode
- Vocal intelligibility was not isolated from a stereo master.
- If separate vocals were used upstream, check lead level and consonants manually in Logic.

## 8. Beat/Vocal Balance If Applicable
- Balance is a heuristic listening requirement, not guaranteed by this mastering stage.
- Avoid over-limiting the beat over the vocal.

## 9. Low-End Control
- low-end control ratio: {final_info.get('low_end_control_ratio')}
- sub cleanup below 20-30 Hz was applied conservatively.

## 10. Harshness/Sibilance Warning
- Harshness and sibilance are not fixed by mastering alone.
- Use vocal or mix-stage de-essing if flagged upstream.
- Plugin-aware vocal FX: pitch {vocal_fx.get('pitch_correction', {}).get('intensity', 'none')}; saturation {vocal_fx.get('saturation', {}).get('intensity', 'none')}; plugin status {vocal_fx.get('plugin_application', {}).get('status', 'not_requested')}.
- Plugin claim rule: {vocal_fx.get('plugin_application', {}).get('claim_language', 'do not claim plugin application without verification')}.
- If fallback saturation was used, QC wording must say generic saturation approximation, not Decapitator applied.

## 11. Reference Match Score If Reference Was Provided
- reference match: {reference_score}
- no exact reference song, artist, producer, melody, mix, or master copying is claimed.
{reference_qc}

## 12. Limitations
- Processing notes: {'; '.join(processing_notes) if processing_notes else 'none'}
- Warnings: {'; '.join(warnings) if warnings else 'none'}
- This QC does not replace a human listening pass.
"""


def verify_master_completion(
    project_root: Path,
    options: dict[str, Any] | None = None,
    final_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    resolved_options = options or {}
    export_format = resolved_options.get("export_format", "wav24_48k")
    expected_sr = expected_sample_rate(export_format)
    candidates = [
        final_path or project_root / "09_MIX_MASTER" / "final_mix_master.wav",
        project_root / "05_FINAL_WAV" / "final_suno_logic_processed_24bit_48k.wav",
        project_root / "05_FINAL_WAV" / "final_suno_logic_processed_24bit_44k.wav",
    ]
    existing = next((path for path in candidates if path.exists()), candidates[0])
    report = report_path or project_root / "09_MIX_MASTER" / "master_qc_report.md"
    blocking: list[str] = []
    info: dict[str, Any] = {}
    if not existing.exists():
        blocking.append(f"final WAV missing: {existing}")
    elif existing.stat().st_size <= 0:
        blocking.append(f"final WAV is empty: {existing}")
    else:
        verification = verify_final_wav(existing, export_format)
        info.update(verification)
        try:
            info.update(analyze_master_wav(existing))
        except Exception as error:  # noqa: BLE001 - master QC must fail closed.
            blocking.append(f"master WAV analysis failed: {error}")
        if info.get("sample_rate") is not None and int(info["sample_rate"]) != expected_sr:
            blocking.append(f"wrong sample rate: expected {expected_sr}, got {info['sample_rate']}")
        if not info.get("format_verified"):
            blocking.append("wrong bit depth/codec or unverified master WAV format")
        if int(info.get("clipping_count") or 0) > 0:
            blocking.append("clipping detected in final WAV")
        if verification.get("ok") is False:
            blocking.append("master final WAV verification did not pass")
        if verification.get("errors"):
            blocking.extend(str(error) for error in verification["errors"])
    if not report.exists():
        blocking.append(f"master QC report missing: {report}")
    blocking = list(dict.fromkeys(blocking))
    return {
        "complete": not blocking,
        "blocking_reasons": blocking,
        "final_path": str(existing),
        "report_path": str(report),
        "verification": info,
    }
