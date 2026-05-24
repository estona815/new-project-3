from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import signal
from scipy.io import wavfile

from audio_metrics import (
    bandpass,
    clipping_count,
    harshness_score,
    mono,
    mono_compatibility,
    peak_db,
    rms,
    rms_db,
    side_mid_db,
    sibilance_score,
    to_stereo,
)
from suno_source_classifier import (
    BASS_OR_808,
    FEMALE_BGV,
    FX,
    MALE_LEAD_VOCAL,
    MUSIC_OR_SYNTH,
    PROBLEM_REFERENCE,
    REFERENCE_ONLY,
    TECHNICAL_MIX_REFERENCE,
    VOCAL_ARTIFACT_QUARANTINE,
    classify_source_file,
)


@dataclass(frozen=True)
class AudioQCIssue:
    source: str
    issue_type: str
    timestamp: float
    severity: str
    likely_cause: str
    suggested_action: str
    quarantine_related_stem: bool
    reaper_marker: bool


def read_wav(path: str | Path) -> tuple[int, np.ndarray]:
    sample_rate, data = wavfile.read(Path(path))
    samples = data.astype(np.float32, copy=False)
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        samples = samples / max(abs(info.min), info.max)
    return int(sample_rate), to_stereo(np.nan_to_num(samples))


def _frame_rms_db(audio: np.ndarray, sample_rate: int, window_ms: float = 80.0, hop_ms: float = 40.0) -> tuple[np.ndarray, np.ndarray]:
    samples = mono(audio)
    window = max(8, int(sample_rate * window_ms / 1000.0))
    hop = max(1, int(sample_rate * hop_ms / 1000.0))
    if samples.shape[0] < window:
        value = 20.0 * np.log10(float(rms(samples)) + 1e-12)
        return np.array([value], dtype=np.float32), np.array([0.0], dtype=np.float32)
    count = 1 + (samples.shape[0] - window) // hop
    values = np.empty(count, dtype=np.float32)
    times = np.empty(count, dtype=np.float32)
    for index in range(count):
        start = index * hop
        frame = samples[start : start + window]
        values[index] = 20.0 * math.log10(float(np.sqrt(np.mean(frame * frame))) + 1e-12)
        times[index] = start / sample_rate
    return values, times


def _add_issue(
    issues: list[AudioQCIssue],
    *,
    source: str,
    issue_type: str,
    timestamp: float,
    severity: str,
    likely_cause: str,
    suggested_action: str,
    quarantine_related_stem: bool = False,
    reaper_marker: bool | None = None,
) -> None:
    marker = severity in {"high", "critical"} if reaper_marker is None else bool(reaper_marker)
    issues.append(
        AudioQCIssue(
            source=source,
            issue_type=issue_type,
            timestamp=round(max(0.0, float(timestamp)), 3),
            severity=severity,
            likely_cause=likely_cause,
            suggested_action=suggested_action,
            quarantine_related_stem=quarantine_related_stem,
            reaper_marker=marker,
        )
    )


def _severity_from_margin(value: float, medium: float, high: float, critical: float) -> str:
    if value >= critical:
        return "critical"
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


def _detect_dropouts_and_splices(
    issues: list[AudioQCIssue],
    audio: np.ndarray,
    sample_rate: int,
    source: str,
    category: str,
) -> None:
    values, times = _frame_rms_db(audio, sample_rate, window_ms=40.0, hop_ms=20.0)
    if values.size < 5:
        return
    active = values[values > -90.0]
    if active.size == 0:
        return
    median = float(np.median(active))
    low_threshold = min(-58.0, median - 32.0)
    near_silent = values < low_threshold
    delta = np.diff(values)
    quarantine_cut = category in {FX, VOCAL_ARTIFACT_QUARANTINE}

    hole_start: int | None = None
    hole_count = 0
    for index, is_low in enumerate(np.concatenate([near_silent, np.array([False])])):
        if is_low and hole_start is None:
            hole_start = index
        if not is_low and hole_start is not None:
            duration = (index - hole_start) * 0.02
            if duration >= 0.10:
                before = values[max(0, hole_start - 2) : hole_start]
                after = values[index : min(values.size, index + 2)]
                if before.size and after.size and max(float(np.max(before)), float(np.max(after))) > median - 9.0:
                    _add_issue(
                        issues,
                        source=source,
                        issue_type="near_silence_hole",
                        timestamp=float(times[hole_start]),
                        severity="high" if duration > 0.25 else "medium",
                        likely_cause="local dropout, bad splice, or abrupt AI render cut",
                        suggested_action="quarantine or manually repair this section before REAPER production",
                        quarantine_related_stem=quarantine_cut,
                    )
                    hole_count += 1
                    if hole_count >= 6:
                        break
            hole_start = None

    abrupt_indexes = np.where(np.abs(delta) > 18.0)[0]
    last_time = -999.0
    emitted = 0
    for index in abrupt_indexes[:12]:
        timestamp = float(times[index + 1])
        if timestamp - last_time < 0.45:
            continue
        last_time = timestamp
        change = abs(float(delta[index]))
        severity = "critical" if change > 34.0 else "high" if change > 26.0 else "medium"
        _add_issue(
            issues,
            source=source,
            issue_type="local_dropout_or_abrupt_cut",
            timestamp=timestamp,
            severity=severity,
            likely_cause="hard splice, sudden gate, or generated stem boundary artifact",
            suggested_action="send the related stem to ARTIFACT_QUARANTINE and review the edit point",
            quarantine_related_stem=quarantine_cut,
        )
        emitted += 1
        if emitted >= 6:
            break


def _detect_energy_spikes_and_sections(
    issues: list[AudioQCIssue],
    audio: np.ndarray,
    sample_rate: int,
    source: str,
    category: str,
) -> None:
    values, times = _frame_rms_db(audio, sample_rate, window_ms=160.0, hop_ms=80.0)
    if values.size < 8:
        return
    median = float(np.median(values))
    jumps = np.diff(values)
    spike_indexes = np.where(jumps > 13.0)[0]
    for index in spike_indexes[:6]:
        _add_issue(
            issues,
            source=source,
            issue_type="sudden_energy_spike",
            timestamp=float(times[index + 1]),
            severity="medium" if jumps[index] < 20.0 else "high",
            likely_cause="random transition impact, glitch burst, or unbalanced section entry",
            suggested_action="lower/trim FX or quarantine the transient source before arranging",
            quarantine_related_stem=category in {FX, VOCAL_ARTIFACT_QUARANTINE} and bool(jumps[index] > 20.0),
        )

    one_sec, sec_times = _frame_rms_db(audio, sample_rate, window_ms=1000.0, hop_ms=1000.0)
    if one_sec.size < 4:
        return
    section_delta = np.abs(np.diff(one_sec))
    unstable = np.where((section_delta > 9.0) & (one_sec[:-1] > median - 16.0))[0]
    for index in unstable[:6]:
        _add_issue(
            issues,
            source=source,
            issue_type="unstable_section_transition",
            timestamp=float(sec_times[index + 1]),
            severity="medium",
            likely_cause="AI arrangement jumped sections without a producer-style transition",
            suggested_action="add a manual fill, riser, drum edit, or reject this generation section",
            quarantine_related_stem=False,
        )


def _detect_vocal_chop_artifacts(
    issues: list[AudioQCIssue],
    audio: np.ndarray,
    sample_rate: int,
    source: str,
    category: str,
) -> None:
    source_text = Path(source).stem.lower()
    keyword_hit = any(token in source_text for token in ("vocal_chop", "vox_chop", "ahh", "ooh", "yeah", "moan", "random"))
    if category == VOCAL_ARTIFACT_QUARANTINE or keyword_hit:
        _add_issue(
            issues,
            source=source,
            issue_type="suspicious_vocal_chop_artifact",
            timestamp=0.0,
            severity="high",
            likely_cause="filename indicates random vocal chop/adlib/moan artifact",
            suggested_action="route to ARTIFACT_QUARANTINE muted by default",
            quarantine_related_stem=True,
        )
        return

    if "vocal" not in source_text and "vox" not in source_text and "bgv" not in source_text:
        return
    values, times = _frame_rms_db(audio, sample_rate, window_ms=55.0, hop_ms=25.0)
    if values.size < 24:
        return
    active_threshold = float(np.percentile(values, 65))
    gate = values > active_threshold
    transitions = int(np.sum(gate[1:] != gate[:-1]))
    duration = max(1.0, audio.shape[0] / sample_rate)
    transition_rate = transitions / duration
    if transition_rate > 7.5:
        _add_issue(
            issues,
            source=source,
            issue_type="suspicious_vocal_chop_artifact",
            timestamp=float(times[np.argmax(np.abs(np.diff(gate.astype(np.float32))))]) if values.size > 1 else 0.0,
            severity="medium" if transition_rate < 11.0 else "high",
            likely_cause="rapid on/off vocal gating resembles random AI chop or splice artifacts",
            suggested_action="quarantine this vocal layer unless a human confirms it is intentional",
            quarantine_related_stem=True,
        )


def _spectral_centroid_proxy(audio: np.ndarray, sample_rate: int) -> float:
    samples = mono(audio)
    if samples.size < 32:
        return 0.0
    window = np.hanning(samples.size).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(samples * window))
    freqs = np.fft.rfftfreq(samples.size, 1.0 / sample_rate)
    denom = float(np.sum(spectrum)) + 1e-12
    return float(np.sum(freqs * spectrum) / denom)


def _detect_vocal_texture_instability(
    issues: list[AudioQCIssue],
    audio: np.ndarray,
    sample_rate: int,
    source: str,
    category: str,
) -> None:
    if category not in {MALE_LEAD_VOCAL, FEMALE_BGV, VOCAL_ARTIFACT_QUARANTINE}:
        return
    frames, times = _frame_rms_db(audio, sample_rate, window_ms=120.0, hop_ms=60.0)
    if frames.size < 12:
        return
    active = frames > max(-55.0, float(np.percentile(frames, 55)))
    if not np.any(active):
        return
    samples = mono(audio)
    window = max(256, int(sample_rate * 0.12))
    hop = max(128, int(sample_rate * 0.06))
    centroids: list[float] = []
    zcrs: list[float] = []
    frame_times: list[float] = []
    for index, start in enumerate(range(0, max(1, samples.size - window), hop)):
        if index >= active.size or not active[index]:
            continue
        frame = samples[start : start + window]
        centroids.append(_spectral_centroid_proxy(frame, sample_rate))
        zcrs.append(float(np.mean(np.abs(np.diff(np.signbit(frame).astype(np.float32))))))
        frame_times.append(start / sample_rate)
    if len(centroids) < 6:
        return
    centroid_delta = np.abs(np.diff(np.asarray(centroids, dtype=np.float32)))
    zcr_delta = np.abs(np.diff(np.asarray(zcrs, dtype=np.float32)))
    if float(np.percentile(centroid_delta, 92)) > 1850.0:
        spike_index = int(np.argmax(centroid_delta))
        _add_issue(
            issues,
            source=source,
            issue_type="unstable_pitch_formant_artifact",
            timestamp=frame_times[min(spike_index + 1, len(frame_times) - 1)],
            severity="high",
            likely_cause="rapid vocal spectral centroid jump suggests AI pitch/formant instability",
            suggested_action="mark for pitch correction/manual edit; regenerate or re-record if instability remains audible",
            quarantine_related_stem=category == VOCAL_ARTIFACT_QUARANTINE,
        )
    if float(np.percentile(zcr_delta, 95)) > 0.14:
        spike_index = int(np.argmax(zcr_delta))
        _add_issue(
            issues,
            source=source,
            issue_type="unnatural_syllable_ending_or_splice",
            timestamp=frame_times[min(spike_index + 1, len(frame_times) - 1)],
            severity="medium",
            likely_cause="rapid zero-crossing texture change can indicate syllable cutoff or hard vocal splice",
            suggested_action="create REAPER marker and inspect clip gain/fades around the syllable ending",
            quarantine_related_stem=category == VOCAL_ARTIFACT_QUARANTINE,
            reaper_marker=True,
        )


def analyze_audio_array(
    audio: np.ndarray,
    sample_rate: int,
    *,
    source_name: str = "array",
    category: str | None = None,
) -> dict[str, object]:
    samples = to_stereo(audio)
    category = category or classify_source_file(source_name).category
    issues: list[AudioQCIssue] = []
    source = str(source_name)

    peak = peak_db(samples)
    overall_rms_db = rms_db(samples)
    if overall_rms_db < -62.0 and peak < -38.0:
        return {
            "source": source,
            "category": category,
            "metrics": {
                "peak_dbfs": round(float(peak), 2),
                "oversampled_peak_proxy_dbfs": round(float(peak), 2),
                "rms_dbfs": round(float(overall_rms_db), 2),
                "loudness_range_proxy_db": 0.0,
                "left_right_correlation": 1.0,
                "side_mid_db": -120.0,
                "mono_level_delta_db": 0.0,
                "harshness_score_db": -120.0,
                "sibilance_score_db": -120.0,
            },
            "issues": [],
            "quarantine_recommended": False,
            "near_silent_source": True,
        }
    oversampled = float(peak_db(signal.resample_poly(samples, 4, 1, axis=0))) if samples.size else float("-inf")
    clip_count = clipping_count(samples, threshold=0.995)
    if peak > -0.35 or oversampled > -0.1 or clip_count > 0:
        severity = "critical" if peak >= -0.05 or oversampled >= 0.0 else "high"
        _add_issue(
            issues,
            source=source,
            issue_type="clipping_risk",
            timestamp=0.0,
            severity=severity,
            likely_cause="rendered source is too close to digital full scale",
            suggested_action="do not use this as a production stem without gain staging or re-export",
            quarantine_related_stem=False,
        )

    short_values, _ = _frame_rms_db(samples, sample_rate, window_ms=400.0, hop_ms=100.0)
    loudness_range = float(np.percentile(short_values, 95) - np.percentile(short_values, 10)) if short_values.size else 0.0
    if loudness_range < 2.8 and rms_db(samples) > -13.0:
        _add_issue(
            issues,
            source=source,
            issue_type="over_compression_low_loudness_range",
            timestamp=0.0,
            severity="high" if loudness_range < 1.8 else "medium",
            likely_cause="Suno/fullmix-like limiting or flattened dynamics",
            suggested_action="treat as reference only or rebuild from WAV stems with conservative levels",
            quarantine_related_stem=False,
        )

    compatibility = mono_compatibility(samples)
    corr = float(compatibility["left_right_correlation"])
    width = side_mid_db(samples)
    mono_delta = float(compatibility["mono_level_delta_db"])
    if corr < 0.15 or mono_delta < -3.0 or width > -2.0:
        severity = "critical" if corr < -0.2 or mono_delta < -6.0 else "high"
        _add_issue(
            issues,
            source=source,
            issue_type="phase_or_stereo_width_anomaly",
            timestamp=0.0,
            severity=severity,
            likely_cause="anti-phase widening or unstable generated stereo image",
            suggested_action="route to ARTIFACT_QUARANTINE or narrow the side channel before production",
            quarantine_related_stem=severity == "critical",
        )

    harsh = harshness_score(samples, sample_rate)
    sib = sibilance_score(samples, sample_rate)
    if harsh > -5.5 or sib > -15.0:
        _add_issue(
            issues,
            source=source,
            issue_type="excessive_high_frequency_harshness",
            timestamp=0.0,
            severity=_severity_from_margin(max(harsh + 5.5, sib + 15.0), 1.5, 4.0, 7.0),
            likely_cause="harsh digital top-end, sibilant vocal artifact, or noisy AI fill",
            suggested_action="de-ess/dynamic EQ or quarantine if it is a non-musical glitch",
            quarantine_related_stem=category in {FX, VOCAL_ARTIFACT_QUARANTINE} and harsh > -2.0,
        )

    low_mid = rms_db(bandpass(samples, 120.0, 360.0, sample_rate))
    presence = rms_db(bandpass(samples, 1_500.0, 5_000.0, sample_rate))
    if low_mid - presence > 8.0 and category in {MALE_LEAD_VOCAL, MUSIC_OR_SYNTH, BASS_OR_808}:
        _add_issue(
            issues,
            source=source,
            issue_type="low_end_mud_or_vocal_masking",
            timestamp=0.0,
            severity="medium" if low_mid - presence < 13.0 else "high",
            likely_cause="low-mid buildup can mask main vocal intelligibility",
            suggested_action="use dynamic EQ around 120-360 Hz and carve vocal pocket before master limiting",
            quarantine_related_stem=False,
        )

    tail_band = rms_db(bandpass(samples, 5_500.0, 12_000.0, sample_rate))
    if category in {MALE_LEAD_VOCAL, FEMALE_BGV} and tail_band - overall_rms_db > -8.0:
        _add_issue(
            issues,
            source=source,
            issue_type="vocal_noise_floor_or_wash_risk",
            timestamp=0.0,
            severity="medium",
            likely_cause="top-end energy/noise floor may make de-essing, reverb, or delay sound messy",
            suggested_action="use filtered send FX, de-ess before ambience, and avoid printing heavy wet vocal ambience",
            quarantine_related_stem=False,
        )

    _detect_dropouts_and_splices(issues, samples, sample_rate, source, category)
    _detect_energy_spikes_and_sections(issues, samples, sample_rate, source, category)
    _detect_vocal_chop_artifacts(issues, samples, sample_rate, source, category)
    _detect_vocal_texture_instability(issues, samples, sample_rate, source, category)

    issue_payloads = [asdict(issue) for issue in issues]
    if category in {REFERENCE_ONLY, PROBLEM_REFERENCE, TECHNICAL_MIX_REFERENCE}:
        for issue in issue_payloads:
            issue["reaper_marker"] = False

    return {
        "source": source,
        "category": category,
        "metrics": {
            "peak_dbfs": round(float(peak), 2),
            "oversampled_peak_proxy_dbfs": round(float(oversampled), 2),
            "rms_dbfs": round(float(overall_rms_db), 2),
            "loudness_range_proxy_db": round(float(loudness_range), 2),
            "left_right_correlation": round(corr, 4),
            "side_mid_db": width,
            "mono_level_delta_db": round(mono_delta, 2),
            "harshness_score_db": harsh,
            "sibilance_score_db": sib,
            "low_mid_120_360_dbfs": round(float(low_mid), 2),
            "presence_1500_5000_dbfs": round(float(presence), 2),
        },
        "issues": issue_payloads,
        "quarantine_recommended": any(issue.quarantine_related_stem for issue in issues),
    }


def analyze_audio_file(path: str | Path) -> dict[str, object]:
    sample_rate, audio = read_wav(path)
    classification = classify_source_file(path)
    result = analyze_audio_array(audio, sample_rate, source_name=str(path), category=classification.category)
    result["sample_rate"] = sample_rate
    return result


def write_audio_qc_reports(paths: Iterable[str | Path], report_dir: str | Path) -> dict[str, object]:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    analyzed = []
    for path in sorted((Path(p) for p in paths), key=lambda item: str(item).lower()):
        if path.suffix.lower() != ".wav":
            continue
        analyzed.append(analyze_audio_file(path))

    issues = [issue for result in analyzed for issue in result["issues"]]
    payload = {
        "schema_version": "audio_qc.v1",
        "analyzed_count": len(analyzed),
        "issue_count": len(issues),
        "quarantine_sources": sorted(
            {result["source"] for result in analyzed if result.get("quarantine_recommended")}
        ),
        "results": analyzed,
        "issues": issues,
    }
    json_path = report_path / "audio_qc.json"
    md_path = report_path / "audio_qc.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Audio QC",
        "",
        f"- Files analyzed: {payload['analyzed_count']}",
        f"- Issues detected: {payload['issue_count']}",
        f"- Quarantine sources: {len(payload['quarantine_sources'])}",
        "",
        "| source | time | severity | issue | likely cause | suggested action | quarantine | REAPER marker |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    if not issues:
        lines.append("| none | 0.000 | low | none | no automated issue detected | continue manual review | false | false |")
    for issue in issues:
        lines.append(
            f"| {Path(str(issue['source'])).name} | {issue['timestamp']:.3f} | {issue['severity']} | "
            f"{issue['issue_type']} | {issue['likely_cause']} | {issue['suggested_action']} | "
            f"{str(issue['quarantine_related_stem']).lower()} | {str(issue.get('reaper_marker', False)).lower()} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload
